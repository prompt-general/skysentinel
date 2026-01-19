// SkySentinel Neo4j Schema Constraints
// Ensures data integrity and performance

// Core node uniqueness constraints
CREATE CONSTRAINT resource_id IF NOT EXISTS 
FOR (r:Resource) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT identity_id IF NOT EXISTS 
FOR (i:Identity) REQUIRE i.id IS UNIQUE;

CREATE CONSTRAINT account_id IF NOT EXISTS 
FOR (a:Account) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT event_id IF NOT EXISTS 
FOR (e:Event) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT policy_id IF NOT EXISTS 
FOR (p:Policy) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT threat_id IF NOT EXISTS 
FOR (t:Threat) REQUIRE t.id IS UNIQUE;

// Indexes for common query patterns
CREATE INDEX resource_type_index IF NOT EXISTS 
FOR (r:Resource) ON (r.type);

CREATE INDEX resource_region_index IF NOT EXISTS 
FOR (r:Resource) ON (r.region);

CREATE INDEX resource_state_index IF NOT EXISTS 
FOR (r:Resource) ON (r.state);

CREATE INDEX identity_type_index IF NOT EXISTS 
FOR (i:Identity) ON (i.type);

CREATE INDEX identity_principal_index IF NOT EXISTS 
FOR (i:Identity) ON (i.principal);

CREATE INDEX account_cloud_index IF NOT EXISTS 
FOR (a:Account) ON (a.cloud);

CREATE INDEX event_type_index IF NOT EXISTS 
FOR (e:Event) ON (e.event_type);

CREATE INDEX event_time_index IF NOT EXISTS 
FOR (e:Event) ON (e.event_time);

CREATE INDEX threat_severity_index IF NOT EXISTS 
FOR (t:Threat) ON (t.severity);

CREATE INDEX threat_status_index IF NOT EXISTS 
FOR (t:Threat) ON (t.status);

// Composite indexes for temporal queries
CREATE INDEX resource_validity_index IF NOT EXISTS 
FOR (r:Resource) ON (r.valid_from, r.valid_to);

CREATE INDEX identity_validity_index IF NOT EXISTS 
FOR (i:Identity) ON (i.valid_from, i.valid_to);

CREATE INDEX event_time_range_index IF NOT EXISTS 
FOR (e:Event) ON (e.event_time, e.cloud);
