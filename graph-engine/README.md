# SkySentinel Graph Engine

The graph engine is the core component of SkySentinel that provides relationship mapping, anomaly detection, and advanced security analytics using Neo4j.

## Schema Overview

The graph schema is designed to model cloud security relationships with temporal versioning for complete audit trails.

### Node Types

#### Core Entities
- **Account**: Cloud accounts (AWS, Azure, GCP)
- **Resource**: Cloud resources (S3 buckets, EC2 instances, etc.)
- **Identity**: Users, roles, service principals
- **Event**: Audit trail of all activities

#### Security Entities
- **Policy**: Security policies and compliance rules
- **Threat**: Detected security threats and anomalies
- **Compliance**: Compliance frameworks and requirements

#### Infrastructure
- **Network**: Network resources and configurations
- **Location**: Geographic and network location data

### Relationship Types

#### Ownership & Access
- **OWNS**: Account owns resources
- **CAN_ACCESS**: Identity permissions on resources
- **MEMBER_OF**: Identity hierarchy and group membership

#### Activity & Events
- **PERFORMED**: Identity performs events
- **TARGETED**: Events target resources
- **CORRELATES_WITH**: Event correlation and pattern analysis

#### Security & Compliance
- **APPLIES_TO**: Policies apply to resources
- **AFFECTS**: Threats affect resources/identities
- **REQUIRES**: Compliance requirements

#### Infrastructure
- **CONTAINS**: Network containment relationships
- **DEPENDS_ON**: Resource dependencies
- **ORIGINATED_FROM**: Geographic origins

#### Temporal
- **SUPERSEDED_BY**: Versioning and change tracking

## Temporal Versioning

All nodes and relationships include temporal fields:
- `valid_from`: When the entity becomes valid
- `valid_to`: When the entity expires (null for current)
- `created_at`: Creation timestamp
- `last_modified`: Last modification timestamp

## Schema Files

- `schema/constraints.cypher`: Database constraints and indexes
- `schema/nodes.cypher`: Node definitions and examples
- `schema/relationships.cypher`: Relationship definitions and examples

## Common Query Patterns

### Find all resources an identity can access
```cypher
MATCH (i:Identity {principal: "alice"})-[:CAN_ACCESS]->(r:Resource)
RETURN r.type, r.region, r.state
```

### Detect suspicious access patterns
```cypher
MATCH (i:Identity)-[:PERFORMED]->(e:Event)-[:TARGETED]->(r:Resource)
WHERE e.source_ip <> i.known_ips
AND e.event_time > timestamp() - 3600000
RETURN i.principal, r.id, COUNT(*) as suspicious_activities
```

### Compliance checking
```cypher
MATCH (p:Policy)-[:APPLIES_TO]->(r:Resource)
WHERE p.type = "COMPLIANCE" AND p.severity = "HIGH"
RETURN p.name, r.id, r.type
```

### Threat impact analysis
```cypher
MATCH (t:Threat)-[:AFFECTS]->(r:Resource)<-[:OWNS]-(a:Account)
WHERE t.status = "ACTIVE"
RETURN a.name, r.type, t.severity
```

## Performance Considerations

1. **Indexes**: All commonly queried fields are indexed
2. **Constraints**: Uniqueness constraints prevent duplicates
3. **Temporal Queries**: Use `valid_from/valid_to` for time-based filtering
4. **Batch Operations**: Use UNWIND for bulk data operations

## Data Model Extensions

The schema is designed to be extensible:
- Add new node types for additional cloud services
- Extend properties for service-specific attributes
- Create custom relationships for complex security scenarios
- Implement custom indexes for optimized queries

## Security Considerations

- All sensitive data is encrypted at rest
- Access control through Neo4j role-based security
- Audit logging for all graph modifications
- Data retention policies for temporal data
