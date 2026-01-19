// SkySentinel Neo4j Relationship Definitions
// Defines connections between entities with temporal tracking

// Account to Resource relationships
MATCH (a:Account {id: "arn:aws:iam::123456789012:root"})
MATCH (r:Resource {id: "arn:aws:s3:::my-bucket"})
CREATE (a)-[:OWNS {
  created_at: timestamp(),
  valid_from: timestamp(),
  valid_to: null,
  relationship_type: "ownership"
}]->(r);

// Identity to Resource relationships (permissions)
MATCH (i:Identity {id: "arn:aws:iam::123456789012:user/alice"})
MATCH (r:Resource {id: "arn:aws:s3:::my-bucket"})
CREATE (i)-[:CAN_ACCESS {
  permission: "s3:*",
  granted_at: timestamp(),
  granted_by: "arn:aws:iam::123456789012:role/admin",
  valid_from: timestamp(),
  valid_to: null,
  access_type: "direct"
}]->(r);

// Event relationships
MATCH (e:Event {id: "event-123"})
MATCH (i:Identity {id: "arn:aws:iam::123456789012:user/alice"})
MATCH (r:Resource {id: "arn:aws:s3:::my-bucket"})
CREATE (i)-[:PERFORMED {
  action: "CreateBucket",
  timestamp: timestamp(),
  result: "SUCCESS"
}]->(e);
CREATE (e)-[:TARGETED {
  resource_type: "aws:s3:bucket",
  impact: "CREATION"
}]->(r);

// Policy to Resource relationships
MATCH (p:Policy {id: "policy-s3-encryption"})
MATCH (r:Resource {id: "arn:aws:s3:::my-bucket"})
CREATE (p)-[:APPLIES_TO {
  evaluation_result: "COMPLIANT",
  last_evaluated: timestamp(),
  next_evaluation: timestamp() + 3600000,
  valid_from: timestamp(),
  valid_to: null
}]->(r);

// Threat relationships
MATCH (t:Threat {id: "threat-456"})
MATCH (r:Resource {id: "arn:aws:s3:::my-bucket"})
MATCH (i:Identity {id: "arn:aws:iam::123456789012:user/alice"})
CREATE (t)-[:AFFECTS {
  impact_level: "HIGH",
  first_detected: timestamp(),
  ongoing: true
}]->(r);
CREATE (t)-[:INVOLVES {
  role: "VICTIM",
  confidence: 0.8
}]->(i);

// Network relationships
MATCH (n:Network {id: "vpc-12345678"})
MATCH (r:Resource {id: "arn:aws:s3:::my-bucket"})
CREATE (n)-[:CONTAINS {
  relationship_type: "network_location",
  created_at: timestamp(),
  valid_from: timestamp(),
  valid_to: null
}]->(r);

// Compliance relationships
MATCH (c:Compliance {id: "compliance-cis-aws"})
MATCH (p:Policy {id: "policy-s3-encryption"})
CREATE (c)-[:REQUIRES {
  requirement_id: "2.1.4",
  mapping_type: "DIRECT",
  created_at: timestamp(),
  valid_from: timestamp(),
  valid_to: null
}]->(p);

// Identity hierarchy relationships
MATCH (i1:Identity {id: "arn:aws:iam::123456789012:user/alice"})
MATCH (i2:Identity {id: "arn:aws:iam::123456789012:role/developers"})
CREATE (i1)-[:MEMBER_OF {
  role_type: "IAM_ROLE",
  granted_at: timestamp(),
  granted_by: "arn:aws:iam::123456789012:user/admin",
  valid_from: timestamp(),
  valid_to: null
}]->(i2);

// Resource dependency relationships
MATCH (r1:Resource {id: "arn:aws:s3:::my-bucket"})
MATCH (r2:Resource {id: "arn:aws:iam::123456789012:role/s3-access"})
CREATE (r1)-[:DEPENDS_ON {
  dependency_type: "IAM_ROLE",
  created_at: timestamp(),
  critical: true,
  valid_from: timestamp(),
  valid_to: null
}]->(r2);

// Event correlation relationships
MATCH (e1:Event {id: "event-123"})
MATCH (e2:Event {id: "event-124"})
CREATE (e1)-[:CORRELATES_WITH {
  correlation_type: "SAME_SESSION",
  confidence: 0.9,
  time_window: 300,
  created_at: timestamp()
}]->(e2);

// Geographic relationships
MATCH (e:Event {id: "event-123"})
CREATE (e)-[:ORIGINATED_FROM {
  country: "US",
  city: "New York",
  isp: "AWS",
  coordinates: {lat: 40.7128, lon: -74.0060},
  created_at: timestamp()
}]->(:Location {
  ip: "192.0.2.1",
  is_known: true,
  risk_score: 0.1
});

// Temporal relationships for versioning
MATCH (r_old:Resource {id: "arn:aws:s3:::my-bucket", valid_to: timestamp()})
MATCH (r_new:Resource {id: "arn:aws:s3:::my-bucket", valid_from: timestamp()})
CREATE (r_old)-[:SUPERSEDED_BY {
  change_type: "CONFIGURATION_UPDATE",
  changed_at: timestamp(),
  changed_by: "arn:aws:iam::123456789012:user/alice"
}]->(r_new);
