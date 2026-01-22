/**
 * Overview Resolver for SkySentinel GraphQL API
 * Custom resolver for computing overview metrics from Neo4j
 */

class OverviewResolver {
  constructor(driver) {
    this.driver = driver;
  }

  /**
   * Resolve overview metrics
   */
  async overview(parent, args, context, info) {
    const session = this.driver.session();
    
    try {
      // Get tenant ID from context
      const tenantId = context.tenantId || 'default-tenant';
      
      // Execute overview query
      const result = await session.run(
        `
        WITH $tenantId as tenantId
        CALL {
          // Total Resources
          MATCH (r:Resource {tenantId: $tenantId})
          RETURN count(r) as totalResources
        }
        CALL {
          // Total Violations
          MATCH (v:Violation {tenantId: $tenantId})
          RETURN count(v) as totalViolations
        }
        CALL {
          // Critical Violations
          MATCH (v:Violation {tenantId: $tenantId, severity: 'CRITICAL'})
          RETURN count(v) as criticalViolations
        }
        CALL {
          // High Violations
          MATCH (v:Violation {tenantId: $tenantId, severity: 'HIGH'})
          RETURN count(v) as highViolations
        }
        CALL {
          // Medium Violations
          MATCH (v:Violation {tenantId: $tenantId, severity: 'MEDIUM'})
          RETURN count(v) as mediumViolations
        }
        CALL {
          // Low Violations
          MATCH (v:Violation {tenantId: $tenantId, severity: 'LOW'})
          RETURN count(v) as lowViolations
        }
        CALL {
          // Active Policies
          MATCH (p:Policy {tenantId: $tenantId, enabled: true})
          RETURN count(p) as activePolicies
        }
        CALL {
          // Compliance Score (weighted average of all frameworks)
          MATCH (c:ComplianceReport {tenantId: $tenantId})
          RETURN avg(c.overallScore) as complianceScore
        }
        CALL {
          // Risk Score (weighted average of resource risks)
          MATCH (r:Resource {tenantId: $tenantId})
          WHERE r.riskScore IS NOT NULL
          RETURN avg(r.riskScore) as riskScore
        }
        CALL {
          // Last Scan Time
          MATCH (r:Resource {tenantId: $tenantId})
          WHERE r.lastScanned IS NOT NULL
          RETURN max(r.lastScanned) as lastScan
        }
        RETURN 
          totalResources,
          totalViolations,
          criticalViolations,
          highViolations,
          mediumViolations,
          lowViolations,
          activePolicies,
          coalesce(complianceScore, 0.0) as complianceScore,
          coalesce(riskScore, 0.0) as riskScore,
          coalesce(lastScan, datetime()) as lastScan
        `,
        { tenantId }
      );

      const overview = result.records[0]?.toObject() || {};

      // Get recent violations
      const recentViolations = await this.getRecentViolations(tenantId, 10);
      
      // Get recent evaluations
      const recentEvaluations = await this.getRecentEvaluations(tenantId, 10);
      
      // Get trends data
      const trends = await this.getTrends(tenantId);

      return {
        ...overview,
        recentViolations,
        recentEvaluations,
        trends
      };
    } catch (error) {
      console.error('Error in overview resolver:', error);
      throw error;
    } finally {
      await session.close();
    }
  }

  /**
   * Get recent violations
   */
  async getRecentViolations(tenantId, limit = 10) {
    const session = this.driver.session();
    
    try {
      const result = await session.run(
        `
        MATCH (v:Violation {tenantId: $tenantId})
        OPTIONAL MATCH (v)-[:VIOLATES_POLICY]->(p:Policy)
        OPTIONAL MATCH (v)-[:AFFECTS_RESOURCE]->(r:Resource)
        OPTIONAL MATCH (v)-[:HAS_PREDICTION]->(ml:MLPrediction)
        RETURN v {
          .id,
          .severity,
          .description,
          .timestamp,
          .status,
          .confidence,
          .falsePositive,
          .firstDetected,
          .lastDetected,
          .resolvedAt,
          .resolvedBy,
          .tags,
          .evidence,
          policy: p {
            .id,
            .name,
            .severity,
            .category,
            .mlEnhanced
          },
          resource: r {
            .id,
            .name,
            .type,
            .cloud,
            .region,
            .account,
            .state
          },
          mlPrediction: ml {
            .violationProbability,
            .confidence,
            .predictedViolations,
            .explanation,
            .modelType,
            .modelVersion,
            .features
          }
        }
        ORDER BY v.timestamp DESC
        LIMIT $limit
        `,
        { tenantId, limit }
      );

      return result.records.map(record => record.get('v'));
    } catch (error) {
      console.error('Error getting recent violations:', error);
      return [];
    } finally {
      await session.close();
    }
  }

  /**
   * Get recent evaluations
   */
  async getRecentEvaluations(tenantId, limit = 10) {
    const session = this.driver.session();
    
    try {
      const result = await session.run(
        `
        MATCH (e:Evaluation {tenantId: $tenantId})
        OPTIONAL MATCH (e)-[:EVALUATES_VIOLATION]->(v:Violation)
        OPTIONAL MATCH (e)-[:HAS_IAC_PLAN]->(iac:IACPlan)
        OPTIONAL MATCH (e)-[:HAS_PREDICTION]->(ml:MLPrediction)
        OPTIONAL MATCH (e)-[:GENERATES_RECOMMENDATION]->(rec:Recommendation)
        OPTIONAL MATCH (e)-[:EVALUATES_RESOURCE]->(r:Resource)
        OPTIONAL MATCH (e)-[:USES_POLICY]->(p:Policy)
        RETURN e {
          .id,
          .type,
          .status,
          .result,
          .score,
          .confidence,
          .timestamp,
          .iacPlan: iac {
            .type,
            .format,
            .size,
            .resources,
            .dependencies,
            .hash,
            .repository,
            .branch,
            .commit,
            .path
          },
          .context,
          .triggeredBy,
          .triggeredAt,
          .completedAt,
          .duration,
          .environment,
          .branch,
          .commit,
          violations: collect(DISTINCT v {
            .id,
            .severity,
            .description,
            .status
          }),
          mlPredictions: collect(DISTINCT ml {
            .violationProbability,
            .confidence,
            .predictedViolations,
            .explanation,
            .modelType,
            .modelVersion,
            .features
          }),
          recommendations: collect(DISTINCT rec {
            .id,
            .type,
            .title,
            .description,
            .priority,
            .effort,
            .impact,
            .actionable,
            .automated,
            .steps,
            .resources,
            .estimatedTime,
            .cost,
            .riskReduction
          }),
          resources: collect(DISTINCT r {
            .id,
            .name,
            .type,
            .cloud,
            .region,
            .account,
            .state
          }),
          policies: collect(DISTINCT p {
            .id,
            .name,
            .severity,
            .category,
            .enabled
          })
        }
        ORDER BY e.timestamp DESC
        LIMIT $limit
        `,
        { tenantId, limit }
      );

      return result.records.map(record => record.get('e'));
    } catch (error) {
      console.error('Error getting recent evaluations:', error);
      return [];
    } finally {
      await session.close();
    }
  }

  /**
   * Get trends data for charts
   */
  async getTrends(tenantId) {
    const session = this.driver.session();
    
    try {
      const result = await session.run(
        `
        WITH $tenantId as tenantId
        CALL {
          // Violations trend (last 30 days)
          MATCH (v:Violation {tenantId: $tenantId})
          WHERE v.timestamp >= datetime() - duration({days: 30})
          WITH date(v.timestamp) as date, count(v) as violations
          ORDER BY date
          RETURN collect({
            timestamp: toString(datetime({year: date.year, month: date.month, day: date.day})),
            value: toFloat(violations),
            label: toString(date)
          }) as violations
        }
        CALL {
          // Risk score trend (last 30 days)
          MATCH (r:Resource {tenantId: $tenantId})
          WHERE r.lastScanned >= datetime() - duration({days: 30})
            AND r.riskScore IS NOT NULL
          WITH date(r.lastScanned) as date, avg(r.riskScore) as avgRiskScore
          ORDER BY date
          RETURN collect({
            timestamp: toString(datetime({year: date.year, month: date.month, day: date.day})),
            value: avgRiskScore,
            label: toString(date)
          }) as riskScore
        }
        CALL {
          // Compliance trend (last 30 days)
          MATCH (c:ComplianceReport {tenantId: $tenantId})
          WHERE c.generatedAt >= datetime() - duration({days: 30})
          WITH date(c.generatedAt) as date, avg(c.overallScore) as avgCompliance
          ORDER BY date
          RETURN collect({
            timestamp: toString(datetime({year: date.year, month: date.month, day: date.day})),
            value: avgCompliance,
            label: toString(date)
          }) as compliance
        }
        CALL {
          // Resources trend (last 30 days)
          MATCH (r:Resource {tenantId: $tenantId})
          WHERE r.createdAt >= datetime() - duration({days: 30})
          WITH date(r.createdAt) as date, count(r) as resources
          ORDER BY date
          RETURN collect({
            timestamp: toString(datetime({year: date.year, month: date.month, day: date.day})),
            value: toFloat(resources),
            label: toString(date)
          }) as resources
        }
        RETURN violations, riskScore, compliance, resources
        `,
        { tenantId }
      );

      return result.records[0]?.toObject() || {
        violations: [],
        riskScore: [],
        compliance: [],
        resources: []
      };
    } catch (error) {
      console.error('Error getting trends:', error);
      return {
        violations: [],
        riskScore: [],
        compliance: [],
        resources: []
      };
    } finally {
      await session.close();
    }
  }

  /**
   * Get overview statistics for a specific timeframe
   */
  async getOverviewStats(tenantId, timeframe = 'LAST_30_DAYS') {
    const session = this.driver.session();
    
    try {
      let duration;
      switch (timeframe) {
        case 'LAST_24_HOURS':
          duration = 'duration({hours: 24})';
          break;
        case 'LAST_7_DAYS':
          duration = 'duration({days: 7})';
          break;
        case 'LAST_30_DAYS':
          duration = 'duration({days: 30})';
          break;
        case 'LAST_90_DAYS':
          duration = 'duration({days: 90})';
          break;
        default:
          duration = 'duration({days: 30})';
      }

      const result = await session.run(
        `
        WITH $tenantId as tenantId
        CALL {
          // New violations in timeframe
          MATCH (v:Violation {tenantId: $tenantId})
          WHERE v.timestamp >= datetime() - ${duration}
          RETURN count(v) as newViolations
        }
        CALL {
          // Resolved violations in timeframe
          MATCH (v:Violation {tenantId: $tenantId})
          WHERE v.resolvedAt >= datetime() - ${duration}
          RETURN count(v) as resolvedViolations
        }
        CALL {
          // Evaluations in timeframe
          MATCH (e:Evaluation {tenantId: $tenantId})
          WHERE e.timestamp >= datetime() - ${duration}
          RETURN count(e) as evaluations
        }
        CALL {
          // Resources scanned in timeframe
          MATCH (r:Resource {tenantId: $tenantId})
          WHERE r.lastScanned >= datetime() - ${duration}
          RETURN count(DISTINCT r) as resourcesScanned
        }
        RETURN newViolations, resolvedViolations, evaluations, resourcesScanned
        `,
        { tenantId }
      );

      return result.records[0]?.toObject() || {
        newViolations: 0,
        resolvedViolations: 0,
        evaluations: 0,
        resourcesScanned: 0
      };
    } catch (error) {
      console.error('Error getting overview stats:', error);
      return {
        newViolations: 0,
        resolvedViolations: 0,
        evaluations: 0,
        resourcesScanned: 0
      };
    } finally {
      await session.close();
    }
  }

  /**
   * Get compliance breakdown by framework
   */
  async getComplianceBreakdown(tenantId) {
    const session = this.driver.session();
    
    try {
      const result = await session.run(
        `
        MATCH (c:ComplianceReport {tenantId: $tenantId})
        OPTIONAL MATCH (c)-[:HAS_FRAMEWORK]->(f:FrameworkCompliance)
        RETURN c.overallScore as overallScore,
               collect(DISTINCT f {
                 .framework,
                 .version,
                 .score,
                 .status,
                 .lastAssessed
               }) as frameworks
        `,
        { tenantId }
      );

      const record = result.records[0];
      return record ? {
        overallScore: record.get('overallScore'),
        frameworks: record.get('frameworks')
      } : {
        overallScore: 0,
        frameworks: []
      };
    } catch (error) {
      console.error('Error getting compliance breakdown:', error);
      return {
        overallScore: 0,
        frameworks: []
      };
    } finally {
      await session.close();
    }
  }

  /**
   * Get resource distribution by cloud provider
   */
  async getResourceDistribution(tenantId) {
    const session = this.driver.session();
    
    try {
      const result = await session.run(
        `
        MATCH (r:Resource {tenantId: $tenantId})
        WHERE r.cloud IS NOT NULL
        RETURN r.cloud as cloud, count(r) as count
        ORDER BY count DESC
        `,
        { tenantId }
      );

      return result.records.map(record => ({
        cloud: record.get('cloud'),
        count: record.get('count')
      }));
    } catch (error) {
      console.error('Error getting resource distribution:', error);
      return [];
    } finally {
      await session.close();
    }
  }
}

module.exports = OverviewResolver;
