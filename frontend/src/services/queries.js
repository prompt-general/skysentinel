import { gql } from '@apollo/client';

// Overview Query
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
        }
        resource {
          id
          name
          type
          cloud
        }
        severity
        description
        timestamp
        status
        confidence
        mlPrediction {
          violationProbability
          confidence
          modelType
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
          severity
          description
        }
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

// Policies Query
export const POLICIES_QUERY = gql`
  query GetPolicies($filter: PolicyFilter, $tenantId: String!) {
    policies(filter: $filter, tenantId: $tenantId) {
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
      lastEvaluated
      evaluationCount
      violations {
        id
        severity
        status
        timestamp
      }
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

// Single Policy Query
export const POLICY_QUERY = gql`
  query GetPolicy($id: ID!, $tenantId: String!) {
    policy(id: $id, tenantId: $tenantId) {
      id
      name
      description
      severity
      enabled
      category
      cloudProvider
      resourceTypes
      resources {
        type
        properties {
          key
          operator
          value
        }
        tags {
          key
          operator
          value
        }
        regions
        accounts
      }
      condition {
        operator
        conditions {
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
      mlEnhanced
      mlThreshold
      mlWeight
      tags
      createdAt
      updatedAt
      createdBy
      version
      lastEvaluated
      evaluationCount
      violations {
        id
        severity
        status
        timestamp
        resource {
          id
          name
          type
          cloud
        }
      }
    }
  }
`;

// Violations Query
export const VIOLATIONS_QUERY = gql`
  query GetViolations($filter: ViolationFilter, $tenantId: String!) {
    violations(filter: $filter, tenantId: $tenantId) {
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
        state
        tags {
          key
          value
          source
        }
        properties
      }
      severity
      description
      details
      timestamp
      status
      confidence
      falsePositive
      firstDetected
      lastDetected
      resolvedAt
      resolvedBy
      resolution {
        type
        notes
        evidence
        approvedBy
        approvedAt
      }
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
      attackPaths {
        id
        path {
          id
          name
          type
          cloud
        }
        riskScore
        description
        severity
        length
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
        steps {
          order
          description
          command
          parameters
          rollbackCommand
          estimatedTime
          dependencies
        }
      }
    }
  }
`;

// Single Violation Query
export const VIOLATION_QUERY = gql`
  query GetViolation($id: ID!, $tenantId: String!) {
    violation(id: $id, tenantId: $tenantId) {
      id
      policy {
        id
        name
        description
        severity
        category
        cloudProvider
        resourceTypes
        mlEnhanced
        mlThreshold
        condition {
          operator
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
      resource {
        id
        name
        type
        cloud
        region
        account
        state
        tags {
          key
          value
          source
          managed
        }
        properties
        violations {
          id
          severity
          status
          timestamp
        }
        connections {
          id
          target {
            id
            name
            type
            cloud
          }
          type
          strength
          description
          bidirectional
        }
        compliance {
          score
          status
          frameworks {
            framework
            score
            status
            lastAssessed
          }
          lastAssessed
          issues {
            framework
            control
            severity
            description
            recommendation
          }
        }
        riskScore
        owner
        environment
        cost {
          monthly
          currency
          trend
          projected
          breakdown {
            category
            amount
            percentage
            trend
          }
        }
        createdAt
        updatedAt
        lastScanned
      }
      severity
      description
      details
      timestamp
      status
      confidence
      falsePositive
      firstDetected
      lastDetected
      resolvedAt
      resolvedBy
      resolution {
        type
        notes
        evidence
        approvedBy
        approvedAt
      }
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
      attackPaths {
        id
        path {
          id
          name
          type
          cloud
          region
          account
          state
        }
        riskScore
        description
        severity
        exploitability
        techniques {
          id
          name
          description
          tactic
          techniqueId
          mitigations
          references
          severity
        }
        mitigations {
          id
          name
          description
          type
          effectiveness
          implementation
          automated
          cost
          timeToImplement
        }
        detectedAt
        confidence
        length
        entryPoints {
          id
          name
          type
          cloud
        }
        criticalAssets {
          id
          name
          type
          cloud
        }
      }
      remediation {
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
  }
`;

// Resources Query
export const RESOURCES_QUERY = gql`
  query GetResources($filter: ResourceFilter, $tenantId: String!) {
    resources(filter: $filter, tenantId: $tenantId) {
      id
      name
      type
      cloud
      region
      account
      state
      tags {
        key
        value
        source
        managed
      }
      properties
      violations {
        id
        severity
        status
        timestamp
      }
      connections {
        id
        target {
          id
          name
          type
          cloud
        }
        type
        strength
        description
        bidirectional
      }
      compliance {
        score
        status
        frameworks {
          framework
          score
          status
          lastAssessed
        }
        lastAssessed
        issues {
          framework
          control
          severity
          description
          recommendation
        }
      }
      riskScore
      owner
      environment
      cost {
        monthly
        currency
        trend
        projected
        breakdown {
          category
          amount
          percentage
          trend
        }
      }
      createdAt
      updatedAt
      lastScanned
    }
  }
`;

// Single Resource Query
export const RESOURCE_QUERY = gql`
  query GetResource($id: ID!, $tenantId: String!) {
    resource(id: $id, tenantId: $tenantId) {
      id
      name
      type
      cloud
      region
      account
      state
      tags {
        key
        value
        source
        managed
      }
      properties
      violations {
        id
        policy {
          id
          name
          severity
        }
        severity
        description
        timestamp
        status
        confidence
        mlPrediction {
          violationProbability
          confidence
          modelType
        }
      }
      connections {
        id
        target {
          id
          name
          type
          cloud
          region
        }
        type
        strength
        description
        bidirectional
      }
      compliance {
        score
        status
        frameworks {
          framework
          version
          score
          status
          controls {
            controlId
            controlName
            description
            category
            status
            score
            evidence
            exceptions
            lastTested
            automated
          }
          lastAssessed
          requirements {
            requirementId
            requirementName
            description
            category
            status
            score
            controls {
              controlId
              controlName
              status
              score
            }
            gaps {
              requirement
              description
              severity
              impact
              recommendation
              effort
              priority
            }
            lastAssessed
          }
          gaps {
            requirement
            description
            severity
            impact
            recommendation
            effort
            priority
          }
          trends {
            timeframe
            score
            change
            controls
            gaps
            resolved
            new
          }
        }
        lastAssessed
        issues {
          framework
          control
          severity
          description
          recommendation
        }
      }
      riskScore
      owner
      environment
      cost {
        monthly
        currency
        trend
        projected
        breakdown {
          category
          amount
          percentage
          trend
        }
      }
      createdAt
      updatedAt
      lastScanned
      metadata
    }
  }
`;

// Attack Paths Query
export const ATTACK_PATHS_QUERY = gql`
  query GetAttackPaths($from: String, $to: String, $tenantId: String!) {
    attackPaths(from: $from, to: $to, tenantId: $tenantId) {
      id
      path {
        id
        name
        type
        cloud
        region
        account
        state
        tags {
          key
          value
        }
        riskScore
      }
      riskScore
      description
      severity
      exploitability
      techniques {
        id
        name
        description
        tactic
        techniqueId
        mitigations
        references
        severity
      }
      mitigations {
        id
        name
        description
        type
        effectiveness
        implementation
        automated
        cost
        timeToImplement
      }
      detectedAt
      confidence
      length
      entryPoints {
        id
        name
        type
        cloud
      }
      criticalAssets {
        id
        name
        type
        cloud
      }
    }
  }
`;

// Evaluations Query
export const EVALUATIONS_QUERY = gql`
  query GetEvaluations($filter: EvaluationFilter, $tenantId: String!) {
    evaluations(filter: $filter, tenantId: $tenantId) {
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
      completedAt
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
      resources {
        id
        name
        type
        cloud
      }
      policies {
        id
        name
        severity
        category
      }
      environment
      branch
      commit
    }
  }
`;

// Single Evaluation Query
export const EVALUATION_QUERY = gql`
  query GetEvaluation($id: ID!, $tenantId: String!) {
    evaluation(id: $id, tenantId: $tenantId) {
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
          description
          severity
          category
          mlEnhanced
          condition {
            operator
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
        resource {
          id
          name
          type
          cloud
          region
          account
          state
          tags {
            key
            value
          }
          properties
        }
        severity
        description
        details
        timestamp
        status
        confidence
        falsePositive
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
        }
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
        tags {
          key
          value
        }
        properties
        violations {
          id
          severity
          status
        }
        compliance {
          score
          status
        }
        riskScore
      }
      policies {
        id
        name
        description
        severity
        category
        enabled
        mlEnhanced
        mlThreshold
        condition {
          operator
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
      environment
      branch
      commit
    }
  }
`;

// Compliance Report Query
export const COMPLIANCE_REPORT_QUERY = gql`
  query GetComplianceReport($tenantId: String!, $timeframe: String) {
    complianceReport(tenantId: $tenantId, timeframe: $timeframe) {
      id
      overallScore
      status
      standards {
        id
        name
        description
        version
        category
        requirements {
          id
          name
          description
          category
          severity
          controls {
            id
            name
            description
            category
            automated
            score
            status
            tests {
              id
              name
              description
              type
              result
              score
              details
              executedAt
              duration
            }
            lastTested
          }
          score
          status
          evidence
          gaps {
            requirement
            description
            severity
            impact
            recommendation
            effort
            priority
          }
        }
        score
        status
        lastAssessed
      }
      frameworks {
        framework
        version
        score
        status
        controls {
          controlId
          controlName
          description
          category
          status
          score
          evidence
          exceptions
          lastTested
          automated
        }
        lastAssessed
        requirements {
          requirementId
          requirementName
          description
          category
          status
          score
          controls {
            controlId
            controlName
            status
            score
          }
          gaps {
            requirement
            description
            severity
            impact
            recommendation
            effort
            priority
          }
          lastAssessed
        }
        gaps {
          requirement
          description
          severity
          impact
          recommendation
          effort
          priority
        }
        trends {
          timeframe
          score
          change
          controls
          gaps
          resolved
          new
        }
      }
      policies {
        policy {
          id
          name
          severity
          category
        }
        status
        violations
        lastEvaluated
        trend {
          timeframe
          score
          change
          violations
          resolved
          new
        }
      }
      resources {
        resource {
          id
          name
          type
          cloud
        }
        score
        status
        violations {
          id
          severity
          status
        }
        frameworks {
          framework
          score
          status
          lastAssessed
        }
      }
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
        timestamp
        status
      }
      trends {
        timeframe
        score
        change
        violations
        resolved
        new
        frameworks {
          framework
          score
          change
          controls
          gaps
          resolved
          new
        }
      }
      generatedAt
      timeframe
      tenantId
    }
  }
`;
