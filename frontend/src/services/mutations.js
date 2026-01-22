import { gql } from '@apollo/client';

// Create Policy Mutation
export const CREATE_POLICY_MUTATION = gql`
  mutation CreatePolicy($input: PolicyInput!, $tenantId: String!) {
    createPolicy(input: $input, tenantId: $tenantId) {
      id
      name
      description
      severity
      enabled
      category
      cloudProvider
      resourceTypes
      mlEnhanced
      mlThreshold
      mlWeight
      tags
      createdAt
      updatedAt
      createdBy
      version
      condition {
        operator
        conditions {
          operator
        }
        rules {
          field
          operator
          value
          description
          severity
        }
      }
      actions {
        type
        severity
        message
        automated
        parameters
      }
      enforcement
    }
  }
`;

// Update Policy Mutation
export const UPDATE_POLICY_MUTATION = gql`
  mutation UpdatePolicy($id: ID!, $input: PolicyInput!, $tenantId: String!) {
    updatePolicy(id: $id, input: $input, tenantId: $tenantId) {
      id
      name
      description
      severity
      enabled
      category
      cloudProvider
      resourceTypes
      mlEnhanced
      mlThreshold
      mlWeight
      tags
      updatedAt
      version
      condition {
        operator
        conditions {
          operator
        }
        rules {
          field
          operator
          value
          description
          severity
        }
      }
      actions {
        type
        severity
        message
        automated
        parameters
      }
      enforcement
    }
  }
`;

// Delete Policy Mutation
export const DELETE_POLICY_MUTATION = gql`
  mutation DeletePolicy($id: ID!, $tenantId: String!) {
    deletePolicy(id: $id, tenantId: $tenantId)
  }
`;

// Enable Policy Mutation
export const ENABLE_POLICY_MUTATION = gql`
  mutation EnablePolicy($id: ID!, $tenantId: String!) {
    enablePolicy(id: $id, tenantId: $tenantId) {
      id
      name
      enabled
      updatedAt
    }
  }
`;

// Disable Policy Mutation
export const DISABLE_POLICY_MUTATION = gql`
  mutation DisablePolicy($id: ID!, $tenantId: String!) {
    disablePolicy(id: $id, tenantId: $tenantId) {
      id
      name
      enabled
      updatedAt
    }
  }
`;

// Resolve Violation Mutation
export const RESOLVE_VIOLATION_MUTATION = gql`
  mutation ResolveViolation($id: ID!, $resolution: ViolationResolutionInput!, $tenantId: String!) {
    resolveViolation(id: $id, resolution: $resolution, tenantId: $tenantId) {
      id
      status
      resolvedAt
      resolvedBy
      resolution {
        type
        notes
        evidence
        approvedBy
        approvedAt
      }
    }
  }
`;

// Ignore Violation Mutation
export const IGNORE_VIOLATION_MUTATION = gql`
  mutation IgnoreViolation($id: ID!, $reason: String!, $tenantId: String!) {
    ignoreViolation(id: $id, reason: $reason, tenantId: $tenantId) {
      id
      status
      ignoreReason
      updatedAt
    }
  }
`;

// Remediate Violation Mutation
export const REMEDIATE_VIOLATION_MUTATION = gql`
  mutation RemediateViolation($id: ID!, $remediationType: RemediationType!, $tenantId: String!) {
    remediateViolation(id: $id, remediationType: $remediationType, tenantId: $tenantId) {
      id
      type
      status
      steps {
        order
        description
        command
        parameters
        rollbackCommand
        estimatedTime
        dependencies
      }
      automated
      estimatedTime
      riskReduction
      createdAt
      completedAt
      triggeredBy
    }
  }
`;

// Trigger Evaluation Mutation
export const TRIGGER_EVALUATION_MUTATION = gql`
  mutation TriggerEvaluation($iacType: IACType!, $content: String!, $context: JSON!, $tenantId: String!) {
    triggerEvaluation(iacType: $iacType, content: $content, context: $context, tenantId: $tenantId) {
      id
      type
      status
      result
      score
      confidence
      violations {
        id
        policy {
          id
          name
          severity
        }
        resource {
          id
          name
          type
        }
        severity
        description
        status
      }
      timestamp
      iacPlan {
        type
        format
        size
        resources
        dependencies
        hash
        repository
        branch
        commit
        path
      }
      context
      triggeredBy
      triggeredAt
      duration
      mlPredictions {
        violationProbability
        confidence
        predictedViolations
        explanation
        modelType
        modelVersion
      }
      recommendations {
        id
        type
        title
        description
        priority
        effort
        impact
        actionable
        automated
        steps
        resources
        estimatedTime
        cost
        riskReduction
      }
      environment
      branch
      commit
    }
  }
`;

// Update Resource Mutation
export const UPDATE_RESOURCE_MUTATION = gql`
  mutation UpdateResource($id: ID!, $input: ResourceInput!, $tenantId: String!) {
    updateResource(id: $id, input: $input, tenantId: $tenantId) {
      id
      name
      tags {
        key
        value
        source
        managed
      }
      properties
      updatedAt
    }
  }
`;

// Tag Resource Mutation
export const TAG_RESOURCE_MUTATION = gql`
  mutation TagResource($id: ID!, $tags: [TagInput!], $tenantId: String!) {
    tagResource(id: $id, tags: $tags, tenantId: $tenantId) {
      id
      name
      tags {
        key
        value
        source
        managed
      }
      updatedAt
    }
  }
`;

// Create Account Mutation
export const CREATE_ACCOUNT_MUTATION = gql`
  mutation CreateAccount($input: AccountInput!) {
    createAccount(input: $input) {
      id
      name
      tenantId
      cloudProviders
      createdAt
      updatedAt
      settings {
        alertThresholds {
          critical
          high
          medium
          low
        }
        remediationSettings {
          autoRemediate
          requireApproval
          timeout
        }
        mlSettings {
          enabled
          threshold
          weight
        }
        notificationSettings {
          email
          slack
          webhook
        }
      }
      subscription {
        id
        plan
        status
        limits {
          resources
          policies
          evaluations
          users
        }
        expiresAt
        features {
          name
          enabled
        }
      }
      users {
        id
        email
        name
        role
        permissions
        lastLogin
        createdAt
      }
    }
  }
`;

// Update Account Mutation
export const UPDATE_ACCOUNT_MUTATION = gql`
  mutation UpdateAccount($id: ID!, $input: AccountInput!) {
    updateAccount(id: $id, input: $input) {
      id
      name
      tenantId
      cloudProviders
      updatedAt
      settings {
        alertThresholds {
          critical
          high
          medium
          low
        }
        remediationSettings {
          autoRemediate
          requireApproval
          timeout
        }
        mlSettings {
          enabled
          threshold
          weight
        }
        notificationSettings {
          email
          slack
          webhook
        }
      }
      subscription {
        id
        plan
        status
        limits {
          resources
          policies
          evaluations
          users
        }
        expiresAt
        features {
          name
          enabled
        }
      }
    }
  }
`;

// Delete Account Mutation
export const DELETE_ACCOUNT_MUTATION = gql`
  mutation DeleteAccount($id: ID!) {
    deleteAccount(id: $id)
  }
`;

// Train ML Model Mutation
export const TRAIN_ML_MODEL_MUTATION = gql`
  mutation TrainMLModel($tenantId: String!, $modelType: MLModelType!) {
    trainMLModel(tenantId: $tenantId, modelType: $modelType) {
      trainingId
      modelType
      status
      tenantId
      startedAt
      estimatedDuration
      progress
      logs
      error
    }
  }
`;

// Update ML Weights Mutation
export const UPDATE_ML_WEIGHTS_MUTATION = gql`
  mutation UpdateMLWeights($tenantId: String!, $weights: MLWeightsInput!) {
    updateMLWeights(tenantId: $tenantId, weights: $weights) {
      tenantId
      policy
      ml
      updatedAt
      updatedBy
    }
  }
`;

// Enable ML Integration Mutation
export const ENABLE_ML_INTEGRATION_MUTATION = gql`
  mutation EnableMLIntegration($tenantId: String!, $policyId: ID!) {
    enableMLIntegration(tenantId: $tenantId, policyId: $policyId) {
      id
      name
      mlEnhanced
      mlThreshold
      mlWeight
      updatedAt
    }
  }
`;

// Scan Resources Mutation
export const SCAN_RESOURCES_MUTATION = gql`
  mutation ScanResources($resourceIds: [ID!], $tenantId: String!) {
    scanResources(resourceIds: $resourceIds, tenantId: $tenantId) {
      scanId
      status
      startedAt
      estimatedDuration
      resourcesScanned
      violationsFound
      error
    }
  }
`;

// Bulk Resolve Violations Mutation
export const BULK_RESOLVE_VIOLATIONS_MUTATION = gql`
  mutation BulkResolveViolations($violationIds: [ID!], $resolution: ViolationResolutionInput!, $tenantId: String!) {
    bulkResolveViolations(violationIds: $violationIds, resolution: $resolution, tenantId: $tenantId) {
      success
      resolved
      failed
      errors
    }
  }
`;

// Bulk Ignore Violations Mutation
export const BULK_IGNORE_VIOLATIONS_MUTATION = gql`
  mutation BulkIgnoreViolations($violationIds: [ID!], $reason: String!, $tenantId: String!) {
    bulkIgnoreViolations(violationIds: $violationIds, reason: $reason, tenantId: $tenantId) {
      success
      ignored
      failed
      errors
    }
  }
`;

// Create Recommendation Mutation
export const CREATE_RECOMMENDATION_MUTATION = gql`
  mutation CreateRecommendation($input: RecommendationInput!, $tenantId: String!) {
    createRecommendation(input: $input, tenantId: $tenantId) {
      id
      type
      title
      description
      priority
      effort
      impact
      actionable
      automated
      steps
      resources
      estimatedTime
      cost
      riskReduction
      createdAt
      status
    }
  }
`;

// Update Recommendation Mutation
export const UPDATE_RECOMMENDATION_MUTATION = gql`
  mutation UpdateRecommendation($id: ID!, $input: RecommendationInput!, $tenantId: String!) {
    updateRecommendation(id: $id, input: $input, tenantId: $tenantId) {
      id
      type
      title
      description
      priority
      effort
      impact
      actionable
      automated
      steps
      resources
      estimatedTime
      cost
      riskReduction
      updatedAt
      status
    }
  }
`;

// Delete Recommendation Mutation
export const DELETE_RECOMMENDATION_MUTATION = gql`
  mutation DeleteRecommendation($id: ID!, $tenantId: String!) {
    deleteRecommendation(id: $id, tenantId: $tenantId)
  }
`;

// Create Alert Mutation
export const CREATE_ALERT_MUTATION = gql`
  mutation CreateAlert($input: AlertInput!, $tenantId: String!) {
    createAlert(input: $input, tenantId: $tenantId) {
      id
      type
      severity
      title
      description
      source
      resourceId
      violationId
      acknowledged
      acknowledgedBy
      acknowledgedAt
      resolved
      resolvedAt
      createdAt
    }
  }
`;

// Acknowledge Alert Mutation
export const ACKNOWLEDGE_ALERT_MUTATION = gql`
  mutation AcknowledgeAlert($id: ID!, $tenantId: String!) {
    acknowledgeAlert(id: $id, tenantId: $tenantId) {
      id
      acknowledged
      acknowledgedBy
      acknowledgedAt
    }
  }
`;

// Resolve Alert Mutation
export const RESOLVE_ALERT_MUTATION = gql`
  mutation ResolveAlert($id: ID!, $tenantId: String!) {
    resolveAlert(id: $id, tenantId: $tenantId) {
      id
      resolved
      resolvedAt
    }
  }
`;

// Export Data Mutation
export const EXPORT_DATA_MUTATION = gql`
  mutation ExportData($input: ExportInput!, $tenantId: String!) {
    exportData(input: $input, tenantId: $tenantId) {
      exportId
      status
      format
      filters
      startedAt
      completedAt
      downloadUrl
      error
    }
  }
`;

// Import Data Mutation
export const IMPORT_DATA_MUTATION = gql`
  mutation ImportData($input: ImportInput!, $tenantId: String!) {
    importData(input: $input, tenantId: $tenantId) {
      importId
      status
      type
      startedAt
      completedAt
      recordsProcessed
      recordsCreated
      recordsUpdated
      recordsFailed
      errors
    }
  }
`;
