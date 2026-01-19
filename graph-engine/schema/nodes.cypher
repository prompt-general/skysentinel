// SkySentinel Neo4j Node Definitions
// Core data models with temporal versioning

// Account Node - Represents cloud accounts
CREATE (:Account {
  id: "arn:aws:iam::123456789012:root",
  cloud: "aws",
  account_id: "123456789012",
  name: "production",
  created_at: timestamp(),
  valid_from: timestamp(),
  valid_to: null,
  tags: {
    env: "prod",
    team: "security"
  },
  metadata: {
    organization_id: "o-123456789",
    billing_contact: "finance@company.com"
  }
});

// Resource Node - Cloud resources with full lifecycle tracking
CREATE (:Resource {
  id: "arn:aws:s3:::my-bucket",
  arn: "arn:aws:s3:::my-bucket",
  cloud: "aws",
  type: "aws:s3:bucket",
  region: "us-east-1",
  state: "ACTIVE",
  created_at: timestamp(),
  last_modified: timestamp(),
  valid_from: timestamp(),
  valid_to: null,
  properties: {
    versioning: "Enabled",
    encryption: "AES256",
    public_read: false,
    logging: true,
    mfa_delete: true
  },
  tags: {
    env: "prod",
    owner: "team-security",
    classification: "confidential"
  }
});

// Identity Node - Users, roles, and service principals
CREATE (:Identity {
  id: "arn:aws:iam::123456789012:user/alice",
  cloud: "aws",
  type: "IAMUser",
  principal: "alice",
  arn: "arn:aws:iam::123456789012:user/alice",
  valid_from: timestamp(),
  valid_to: null,
  properties: {
    mfa_enabled: true,
    access_keys: 2,
    console_access: true,
    password_last_changed: timestamp()
  }
});

// Event Node - Audit trail of all activities
CREATE (:Event {
  id: "event-123",
  cloud: "aws",
  event_type: "ApiCall",
  event_name: "CreateBucket",
  event_time: timestamp(),
  principal_arn: "arn:aws:iam::123456789012:user/alice",
  source_ip: "192.0.2.1",
  user_agent: "aws-cli/1.0",
  request_parameters: {
    BucketName: "my-bucket",
    ACL: "private"
  },
  response_elements: {
    Location: "/my-bucket"
  },
  raw_event: {
    eventVersion: "1.08",
    userIdentity: {
      type: "IAMUser",
      principalId: "AIDACKCEVSQ6C2EXAMPLE"
    }
  }
});

// Policy Node - Security policies and compliance rules
CREATE (:Policy {
  id: "policy-s3-encryption",
  name: "S3 Bucket Encryption Policy",
  type: "COMPLIANCE",
  severity: "HIGH",
  created_at: timestamp(),
  valid_from: timestamp(),
  valid_to: null,
  description: "All S3 buckets must have encryption enabled",
  rules: {
    encryption_required: true,
    allowed_encryption_types: ["AES256", "aws:kms"],
    exceptions: ["backup-*"]
  }
});

// Threat Node - Detected security threats and anomalies
CREATE (:Threat {
  id: "threat-456",
  type: "UNAUTHORIZED_ACCESS",
  severity: "HIGH",
  status: "ACTIVE",
  detected_at: timestamp(),
  valid_from: timestamp(),
  valid_to: null,
  confidence: 0.95,
  description: "Suspicious access attempt from unknown IP",
  indicators: {
    source_ip: "203.0.113.1",
    user_agent: "curl/7.68.0",
    failed_attempts: 5
  },
  mitigation: {
    recommended_action: "BLOCK_IP",
    auto_remediate: true
  }
});

// Network Node - Network resources and configurations
CREATE (:Network {
  id: "vpc-12345678",
  cloud: "aws",
  type: "aws:ec2:vpc",
  region: "us-east-1",
  cidr: "10.0.0.0/16",
  state: "ACTIVE",
  created_at: timestamp(),
  valid_from: timestamp(),
  valid_to: null,
  properties: {
    dns_hostnames: true,
    dns_resolution: true,
    tenancy: "default"
  }
});

// Compliance Node - Compliance frameworks and requirements
CREATE (:Compliance {
  id: "compliance-cis-aws",
  name: "CIS AWS Foundations Benchmark",
  framework: "CIS",
  version: "1.4.0",
  created_at: timestamp(),
  valid_from: timestamp(),
  valid_to: null,
  requirements: {
    "1.1": "Avoid the use of the root account",
    "1.2": "Ensure multi-factor authentication (MFA) is enabled for all IAM users",
    "1.3": "Ensure IAM password policy requires at least one uppercase letter"
  }
});
