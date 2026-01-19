from neo4j import GraphDatabase
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from shared.models.events import NormalizedEvent


class GraphEngine:
    """Neo4j Graph Engine for SkySentinel - manages security graph relationships"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(
            neo4j_uri, 
            auth=(neo4j_user, neo4j_password)
        )
        self.logger = logging.getLogger(__name__)
        
    def close(self):
        """Close the database connection"""
        if self.driver:
            self.driver.close()
    
    def upsert_resource(self, resource: Dict[str, Any]) -> None:
        """Upsert a resource node with temporal versioning"""
        query = """
        MERGE (r:Resource {id: $id})
        ON CREATE SET 
            r.created_at = $now,
            r.valid_from = $now,
            r.valid_to = null,
            r += $properties
        ON MATCH SET
            r.valid_to = $now
        WITH r
        CREATE (r_new:Resource {id: $id})
        SET r_new = $properties,
            r_new.valid_from = $now,
            r_new.valid_to = null,
            r_new.created_at = coalesce($properties.created_at, $now)
        MERGE (r)-[:PREVIOUS_VERSION]->(r_new)
        """
        
        with self.driver.session() as session:
            session.run(query, 
                id=resource['id'],
                properties=resource,
                now=datetime.utcnow().timestamp()
            )
    
    def upsert_identity(self, identity: Dict[str, Any]) -> None:
        """Upsert an identity node with temporal versioning"""
        query = """
        MERGE (i:Identity {id: $id})
        ON CREATE SET 
            i.created_at = $now,
            i.valid_from = $now,
            i.valid_to = null,
            i += $properties
        ON MATCH SET
            i.valid_to = $now
        WITH i
        CREATE (i_new:Identity {id: $id})
        SET i_new = $properties,
            i_new.valid_from = $now,
            i_new.valid_to = null,
            i_new.created_at = coalesce($properties.last_activity, $now)
        MERGE (i)-[:PREVIOUS_VERSION]->(i_new)
        """
        
        with self.driver.session() as session:
            session.run(query,
                id=identity['id'],
                properties=identity,
                now=datetime.utcnow().timestamp()
            )
    
    def create_event_node(self, event: NormalizedEvent) -> None:
        """Create an event node in the graph"""
        query = """
        CREATE (e:Event {
            id: $id,
            cloud: $cloud,
            event_type: $event_type,
            event_time: $event_time,
            operation: $operation,
            source_ip: $source_ip,
            user_agent: $user_agent,
            request_parameters: $request_parameters,
            response_elements: $response_elements,
            raw_event: $raw_event,
            created_at: $now,
            valid_from: $now,
            valid_to: null
        })
        """
        
        with self.driver.session() as session:
            session.run(query,
                id=event.id,
                cloud=event.cloud.value,
                event_type=event.event_type,
                event_time=event.event_time.timestamp(),
                operation=event.operation,
                source_ip=event.source_ip,
                user_agent=event.user_agent,
                request_parameters=event.request_parameters,
                response_elements=event.response_elements,
                raw_event=event.raw_event,
                now=datetime.utcnow().timestamp()
            )
    
    def create_relationship(self, 
                          from_id: str, 
                          to_id: str, 
                          rel_type: str,
                          properties: Dict[str, Any] = None) -> None:
        """Create or update a relationship between nodes"""
        query = f"""
        MATCH (a {{id: $from_id}})
        MATCH (b {{id: $to_id}})
        WHERE a.valid_to IS NULL AND b.valid_to IS NULL
        MERGE (a)-[r:{rel_type}]->(b)
        ON CREATE SET r += $properties,
                      r.valid_from = $now,
                      r.valid_to = null
        ON MATCH SET 
            r.valid_to = $now
        WITH a, b
        CREATE (a)-[r_new:{rel_type} $properties]->(b)
        SET r_new.valid_from = $now,
            r_new.valid_to = null
        """
        
        with self.driver.session() as session:
            session.run(query,
                from_id=from_id,
                to_id=to_id,
                properties=properties or {},
                now=datetime.utcnow().timestamp()
            )
    
    def process_event(self, event: NormalizedEvent) -> None:
        """Process a normalized event and update graph"""
        try:
            # 1. Update resource node
            self.upsert_resource({
                'id': event.resource.id,
                'type': event.resource.type,
                'cloud': event.cloud.value,
                'region': event.resource.region,
                'account': event.resource.account,
                'name': event.resource.name,
                'last_modified': event.event_time.timestamp(),
                'state': self._determine_state(event),
                'tags': event.resource.tags
            })
            
            # 2. Update identity node
            self.upsert_identity({
                'id': event.principal.id,
                'type': event.principal.type,
                'arn': event.principal.arn,
                'principal': event.principal.arn or event.principal.id,
                'name': event.principal.name,
                'cloud': event.cloud.value,
                'last_activity': event.event_time.timestamp()
            })
            
            # 3. Create event node
            self.create_event_node(event)
            
            # 4. Update relationships
            if event.principal.id and event.resource.id:
                self.create_relationship(
                    from_id=event.principal.id,
                    to_id=event.resource.id,
                    rel_type='PERFORMED_ACTION_ON',
                    properties={
                        'operation': event.operation,
                        'timestamp': event.event_time.timestamp(),
                        'success': self._was_successful(event)
                    }
                )
            
            self.logger.debug(f"Successfully processed event {event.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to process event {event.id}: {e}")
            raise
    
    def get_resource_lineage(self, resource_id: str) -> List[Dict]:
        """Get historical versions of a resource"""
        query = """
        MATCH (r:Resource {id: $id})
        OPTIONAL MATCH (r)-[:PREVIOUS_VERSION*0..10]->(older)
        RETURN collect(DISTINCT older) as versions
        ORDER BY older.valid_from DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query, id=resource_id)
            return [dict(record) for record in result]
    
    def get_resource_relationships(self, resource_id: str, rel_type: str = None) -> List[Dict]:
        """Get relationships for a resource"""
        rel_filter = f":{rel_type}" if rel_type else ""
        query = f"""
        MATCH (r:Resource {{id: $id}})
        OPTIONAL MATCH (r)-[r_rel{rel_filter}]-(related)
        WHERE r.valid_to IS NULL
        RETURN type(r_rel) as relationship_type, 
               related.id as related_id, 
               labels(related) as related_labels,
               properties(r_rel) as relationship_properties
        """
        
        with self.driver.session() as session:
            result = session.run(query, id=resource_id)
            return [dict(record) for record in result]
    
    def find_attack_paths(self, source_id: str, target_id: str, max_depth: int = 5) -> List[Dict]:
        """Find potential attack paths between entities"""
        query = """
        MATCH path = shortestPath((start:Identity|Resource {id: $source_id})-[*1..$max_depth]-(end:Resource {id: $target_id}))
        WHERE all(r IN relationships(path) WHERE r.valid_to IS NULL)
        RETURN [node IN nodes(path) | {
            id: node.id,
            labels: labels(node),
            properties: properties(node)
        }] as path_nodes,
        [rel IN relationships(path) | {
            type: type(rel),
            properties: properties(rel)
        }] as path_relationships,
        length(path) as path_length
        ORDER BY path_length
        LIMIT 10
        """
        
        with self.driver.session() as session:
            result = session.run(query, source_id=source_id, target_id=target_id, max_depth=max_depth)
            return [dict(record) for record in result]
    
    def get_identity_permissions(self, identity_id: str) -> List[Dict]:
        """Get all permissions for an identity"""
        query = """
        MATCH (i:Identity {id: $id})
        WHERE i.valid_to IS NULL
        OPTIONAL MATCH (i)-[r:CAN_ACCESS]->(resource:Resource)
        WHERE resource.valid_to IS NULL AND r.valid_to IS NULL
        RETURN resource.id as resource_id,
               resource.type as resource_type,
               r.permission as permission,
               r.valid_from as granted_at
        ORDER BY resource.type, resource.id
        """
        
        with self.driver.session() as session:
            result = session.run(query, id=identity_id)
            return [dict(record) for record in result]
    
    def detect_anomalous_access(self, time_window_hours: int = 24) -> List[Dict]:
        """Detect anomalous access patterns"""
        query = """
        MATCH (i:Identity)-[r:PERFORMED_ACTION_ON]->(res:Resource)
        WHERE r.timestamp > timestamp() - ($time_window * 3600 * 1000)
          AND r.valid_to IS NULL
          AND res.valid_to IS NULL
        WITH i, count(r) as action_count, collect(DISTINCT res.type) as resource_types
        WHERE action_count > 100 OR size(resource_types) > 10
        RETURN i.id as identity_id,
               i.type as identity_type,
               action_count,
               resource_types,
               size(resource_types) as variety_score
        ORDER BY action_count DESC
        LIMIT 50
        """
        
        with self.driver.session() as session:
            result = session.run(query, time_window=time_window_hours)
            return [dict(record) for record in result]
    
    def get_resource_dependencies(self, resource_id: str) -> List[Dict]:
        """Get dependencies for a resource"""
        query = """
        MATCH (r:Resource {id: $id})
        WHERE r.valid_to IS NULL
        OPTIONAL MATCH (r)-[dep:DEPENDS_ON]->(dep_res:Resource)
        OPTIONAL MATCH (other_res:Resource)-[:DEPENDS_ON]->(r)
        WHERE (dep_res.valid_to IS NULL OR dep_res.valid_to IS NULL)
          AND (other_res.valid_to IS NULL OR other_res.valid_to IS NULL)
        RETURN 'dependency' as direction,
               dep_res.id as related_id,
               dep_res.type as related_type,
               dep.critical as criticality
        UNION
        RETURN 'dependent' as direction,
               other_res.id as related_id,
               other_res.type as related_type,
               null as criticality
        """
        
        with self.driver.session() as session:
            result = session.run(query, id=resource_id)
            return [dict(record) for record in result]
    
    def _determine_state(self, event: NormalizedEvent) -> str:
        """Determine resource state from event"""
        if event.event_type in ['RESOURCE_DELETE', 'DATABASE_DELETE']:
            return 'DELETED'
        elif event.event_type in ['RESOURCE_CREATE', 'DATABASE_CREATE']:
            return 'ACTIVE'
        elif event.event_type in ['COMPUTE_STOP', 'COMPUTE_TERMINATE']:
            return 'STOPPED'
        else:
            return 'ACTIVE'
    
    def _was_successful(self, event: NormalizedEvent) -> bool:
        """Determine if event was successful"""
        # Check response elements for success indicators
        if event.response_elements:
            # AWS typically returns error codes in response
            if 'Error' in event.response_elements:
                return False
        
        # Check for known failure patterns
        if event.operation and event.operation.startswith('Delete'):
            # Delete operations are successful if no error
            return True
        
        # Default to success for most operations
        return True
    
    def initialize_schema(self) -> None:
        """Initialize database schema with constraints and indexes"""
        constraints_queries = [
            "CREATE CONSTRAINT resource_id IF NOT EXISTS FOR (r:Resource) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT identity_id IF NOT EXISTS FOR (i:Identity) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE",
            "CREATE INDEX resource_type_index IF NOT EXISTS FOR (r:Resource) ON (r.type)",
            "CREATE INDEX resource_cloud_index IF NOT EXISTS FOR (r:Resource) ON (r.cloud)",
            "CREATE INDEX identity_type_index IF NOT EXISTS FOR (i:Identity) ON (i.type)",
            "CREATE INDEX event_time_index IF NOT EXISTS FOR (e:Event) ON (e.event_time)",
            "CREATE INDEX event_type_index IF NOT EXISTS FOR (e:Event) ON (e.event_type)"
        ]
        
        with self.driver.session() as session:
            for query in constraints_queries:
                try:
                    session.run(query)
                    self.logger.info(f"Applied schema: {query}")
                except Exception as e:
                    self.logger.warning(f"Schema query failed (may already exist): {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on graph database"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 'healthy' as status, count(*) as node_count")
                record = result.single()
                return {
                    'status': record['status'],
                    'node_count': record['node_count'],
                    'timestamp': datetime.utcnow().isoformat()
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
