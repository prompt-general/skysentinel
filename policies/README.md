# SkySentinel Policy Library

This directory contains policy definitions for the SkySentinel cloud security platform.

## Policy Structure

Each policy file follows a standardized YAML structure based on the SkySentinel Policy DSL:

```yaml
policy:
  name: policy-name
  description: Policy description
  version: "1.0"
  severity: critical|high|medium|low|info
  
  resources:
    cloud: aws|azure|gcp|all
    resource_types: []
    tags: {}
    # ... other resource selectors
  
  condition:
    # Field conditions or graph conditions
    all: []  # AND logic
    any: []  # OR logic
    not: {}  # NOT logic
  
  enforcement:
    runtime: {}
    cicd: {}
    scheduled: {}
  
  actions: []
  
  metadata: {}
```

## Available Policies

### 1. no-public-storage.yaml
**Purpose**: Prevents public access to storage resources containing sensitive data
- **Severity**: Critical
- **Resources**: S3 buckets, Azure blob containers, GCS buckets
- **Condition**: Detects public ACLs or policies on resources with sensitive data tags
- **Actions**: Block access, notify security team, apply compliance tags

### 2. attack-path-detection.yaml
**Purpose**: Detects potential attack paths from internet to production databases
- **Severity**: High
- **Resources**: All database types
- **Condition**: Graph traversal from internet to database through network components
- **Actions**: Alert security team, escalate for critical resources

### 3. cost-optimization.yaml
**Purpose**: Identifies and cleans up unused resources to reduce costs
- **Severity**: Medium
- **Resources**: EC2 instances, RDS databases, ElastiCache clusters
- **Condition**: Low CPU and network utilization over 30 days
- **Actions**: Notify finance team, schedule resource stoppage

## Policy Categories

### Security Policies
- **Data Protection**: Prevent data exposure and unauthorized access
- **Network Security**: Control network access and detect attack paths
- **Identity & Access**: Manage permissions and access controls

### Compliance Policies
- **Regulatory**: GDPR, HIPAA, PCI DSS, SOC 2 compliance
- **Industry Standards**: ISO 27001, NIST CSF, CIS benchmarks
- **Internal Policies**: Organization-specific security requirements

### Operations Policies
- **Cost Optimization**: Resource utilization and waste reduction
- **Resource Management**: Lifecycle management and cleanup
- **Monitoring**: Alerting and notification policies

## Policy Development Guidelines

### 1. Naming Conventions
- Use kebab-case for policy names
- Be descriptive but concise
- Include the domain (e.g., `security`, `cost`, `compliance`)

### 2. Severity Levels
- **Critical**: Immediate threat to data/system security
- **High**: Significant security risk or compliance violation
- **Medium**: Moderate risk or operational issue
- **Low**: Minor risk or optimization opportunity
- **Info**: Informational or monitoring purposes

### 3. Resource Selection
- Be specific about resource types
- Use tags to target relevant resources
- Consider multi-cloud compatibility

### 4. Condition Logic
- Use clear, testable conditions
- Combine multiple conditions appropriately
- Consider false positive minimization

### 5. Enforcement Modes
- **inline-deny**: Block actions in real-time
- **post-event**: Take action after event occurs
- **scheduled**: Run on a schedule
- **audit-only**: Log violations without action

### 6. Action Configuration
- Include appropriate notification channels
- Consider escalation paths
- Provide clear action messages

## Testing Policies

Before deploying policies, test them in a non-production environment:

1. **Validation**: Use the policy engine validation tools
2. **Dry Run**: Test with `dry_run: true` enabled
3. **Impact Assessment**: Evaluate potential impact on existing resources
4. **Performance**: Test policy evaluation performance

## Policy Lifecycle

1. **Development**: Create policy following guidelines
2. **Testing**: Validate in staging environment
3. **Approval**: Review by security and operations teams
4. **Deployment**: Deploy with appropriate monitoring
5. **Monitoring**: Track policy effectiveness and false positives
6. **Maintenance**: Update as requirements change

## Contributing

When adding new policies:

1. Follow the established structure and naming conventions
2. Include comprehensive documentation
3. Add test cases for validation
4. Consider impact on existing policies
5. Update this README with new policy information

## Support

For policy-related questions or issues:
- Contact the security team
- Review the policy engine documentation
- Check the policy validation logs
- Consult the compliance requirements documentation
