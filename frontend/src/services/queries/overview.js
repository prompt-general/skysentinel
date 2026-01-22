import { gql } from '@apollo/client';

export const OVERVIEW_QUERY = gql`
  query GetOverview($input: OverviewInput!) {
    overview(input: $input) {
      totalResources
      totalViolations
      criticalViolations
      highViolations
      mediumViolations
      lowViolations
      complianceScore
      riskScore
      activePolicies
      lastScan
      recentViolations {
        id
        policy {
          id
          name
          severity
          category
          mlEnhanced
        }
        resource {
          id
          name
          type
          cloud
          region
          account
        }
        severity
        description
        timestamp
        status
        confidence
        falsePositive
        firstDetected
        lastDetected
        resolvedAt
        resolvedBy
        tags
        evidence
        mlPrediction {
          violationProbability
          confidence
          predictedViolations
          explanation
          modelType
          modelVersion
          features
          riskFactors {
            factor
            weight
            value
            description
          }
        }
        remediation {
          id
          type
          status
          automated
          estimatedTime
          riskReduction
          createdAt
          completedAt
          triggeredBy
        }
      }
      recentEvaluations {
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
            cloud
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
        completedAt
        duration
        mlPredictions {
          violationProbability
          confidence
          predictedViolations
          explanation
          modelType
          modelVersion
          features
          riskFactors {
            factor
            weight
            value
            description
          }
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
        resources {
          id
          name
          type
          cloud
          region
          account
          state
        }
        policies {
          id
          name
          severity
          category
          enabled
        }
        environment
        branch
        commit
      }
      trends {
        violations {
          timestamp
          value
          label
        }
        riskScore {
          timestamp
          value
          label
        }
        compliance {
          timestamp
          value
          label
        }
        resources {
          timestamp
          value
          label
        }
      }
    }
  }
`;

// Simplified overview query for dashboard cards
export const OVERVIEW_CARDS_QUERY = gql`
  query GetOverviewCards($input: OverviewInput!) {
    overview(input: $input) {
      totalResources
      totalViolations
      criticalViolations
      highViolations
      mediumViolations
      lowViolations
      complianceScore
      riskScore
      activePolicies
      lastScan
    }
  }
`;

// Overview query with recent violations only
export const OVERVIEW_VIOLATIONS_QUERY = gql`
  query GetOverviewViolations($input: OverviewInput!) {
    overview(input: $input) {
      totalViolations
      criticalViolations
      highViolations
      mediumViolations
      lowViolations
      recentViolations {
        id
        policy {
          id
          name
          severity
          category
        }
        resource {
          id
          name
          type
          cloud
          region
          account
        }
        severity
        description
        timestamp
        status
        confidence
        falsePositive
        tags
        mlPrediction {
          violationProbability
          confidence
          modelType
          modelVersion
        }
      }
    }
  }
`;

// Overview query with recent evaluations only
export const OVERVIEW_EVALUATIONS_QUERY = gql`
  query GetOverviewEvaluations($input: OverviewInput!) {
    overview(input: $input) {
      recentEvaluations {
        id
        type
        status
        result
        score
        confidence
        timestamp
        iacPlan {
          type
          repository
          branch
          commit
          resources
          dependencies
        }
        duration
        triggeredBy
        environment
        violations {
          id
          severity
          status
        }
        mlPredictions {
          violationProbability
          confidence
          modelType
          modelVersion
        }
      }
    }
  }
`;

// Overview query with trends only
export const OVERVIEW_TRENDS_QUERY = gql`
  query GetOverviewTrends($input: OverviewInput!) {
    overview(input: $input) {
      trends {
        violations {
          timestamp
          value
          label
        }
        riskScore {
          timestamp
          value
          label
        }
        compliance {
          timestamp
          value
          label
        }
        resources {
          timestamp
          value
          label
        }
      }
    }
  }
`;

// Real-time overview subscription
export const OVERVIEW_SUBSCRIPTION = gql`
  subscription OverviewUpdated($tenantId: String!) {
    overviewUpdated(tenantId: $tenantId) {
      totalResources
      totalViolations
      criticalViolations
      highViolations
      mediumViolations
      lowViolations
      complianceScore
      riskScore
      activePolicies
      lastScan
      timestamp
    }
  }
`;

// Violations subscription for overview
export const OVERVIEW_VIOLATIONS_SUBSCRIPTION = gql`
  subscription OverviewViolationsUpdated($tenantId: String!) {
    violationCreated(tenantId: $tenantId) {
      id
      policy {
        id
        name
        severity
        category
      }
      resource {
        id
        name
        type
        cloud
        region
        account
      }
      severity
      description
      timestamp
      status
      confidence
      falsePositive
      tags
      mlPrediction {
        violationProbability
        confidence
        modelType
        modelVersion
      }
    }
  }
`;

// Evaluations subscription for overview
export const OVERVIEW_EVALUATIONS_SUBSCRIPTION = gql`
  subscription OverviewEvaluationsUpdated($tenantId: String!) {
    evaluationCompleted(tenantId: $tenantId) {
      id
      type
      status
      result
      score
      confidence
      timestamp
      iacPlan {
        type
        repository
        branch
        commit
        resources
        dependencies
      }
      duration
      triggeredBy
      environment
      violations {
        id
        severity
        status
      }
      mlPredictions {
        violationProbability
        confidence
        modelType
        modelVersion
      }
    }
  }
`;
