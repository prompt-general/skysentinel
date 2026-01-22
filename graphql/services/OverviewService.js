/**
 * Overview Service for SkySentinel
 * Dedicated service for computing overview metrics from Neo4j
 */

class OverviewService {
  constructor(driver) {
    this.driver = driver;
  }

  /**
   * Get complete overview metrics
   */
  async getOverview(tenantId, timeframe = 'LAST_30_DAYS') {
    const session = this.driver.session();
    
    try {
      // Get base metrics
      const baseMetrics = await this.getBaseMetrics(tenantId);
      
      // Get recent violations
      const recentViolations = await this.getRecentViolations(tenantId, 10);
      
      // Get recent evaluations
      const recentEvaluations = await this.getRecentEvaluations(tenantId, 10);
      
      // Get trends data
      const trends = await this.getTrends(tenantId, timeframe);
      
      // Get compliance breakdown
      const complianceBreakdown = await this.getComplianceBreakdown(tenantId);
      
      // Get resource distribution
      const resourceDistribution = await this.getResourceDistribution(tenantId);
      
      // Get risk distribution
      const riskDistribution = await this.getRiskDistribution(tenantId);
      
      // Get performance metrics
      const performanceMetrics = await this.getPerformanceMetrics(tenantId);

      return {
        ...baseMetrics,
        recentViolations,
        recentEvaluations,
        trends,
        complianceBreakdown,
        resourceDistribution,
        riskDistribution,
        performanceMetrics,
        lastUpdated: new Date().toISOString()
      };
    } catch (error) {
      console.error('Error in OverviewService.getOverview:', error);
      throw error;
    } finally {
      await session.close();
    }
  }

  /**
   * Get base overview metrics
   */
  async getBaseMetrics(tenantId) {
    const session = this.driver.session();
    
    try {
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
          // Violations by severity
          MATCH (v:Violation {tenantId: $tenantId})
          WITH v.severity as severity, count(v) as count
          RETURN severity, count
        }
        CALL {
          // Active Policies
          MATCH (p:Policy {tenantId: $tenantId, enabled: true})
          RETURN count(p) as activePolicies
        }
        CALL {
          // Compliance Score
          MATCH (c:ComplianceReport {tenantId: $tenantId})
          RETURN avg(c.overallScore) as complianceScore
        }
        CALL {
          // Risk Score
          MATCH (r:Resource {tenantId: $tenantId})
          WHERE r.riskScore IS NOT NULL
          RETURN avg(r.riskScore) as riskScore
        }
        CALL {
          // Last Scan
          MATCH (r:Resource {tenantId: $tenantId})
          WHERE r.lastScanned IS NOT NULL
          RETURN max(r.lastScanned) as lastScan
        }
        CALL {
          // Total Evaluations
          MATCH (e:Evaluation {tenantId: $tenantId})
          RETURN count(e) as totalEvaluations
        }
        CALL {
          // Active Evaluations
          MATCH (e:Evaluation {tenantId: $tenantId, status: 'RUNNING'})
          RETURN count(e) as activeEvaluations
        }
        RETURN 
          totalResources,
          totalViolations,
          collect({severity, count}) as violationsBySeverity,
          activePolicies,
          coalesce(complianceScore, 0.0) as complianceScore,
          coalesce(riskScore, 0.0) as riskScore,
          coalesce(lastScan, datetime()) as lastScan,
          totalEvaluations,
          activeEvaluations
        `,
        { tenantId }
      );

      const record = result.records[0];
      const violationsBySeverity = record.get('violationsBySeverity') || [];
      
      // Extract violation counts by severity
      const violationCounts = violationsBySeverity.reduce((acc, item) => {
        acc[item.severity.toLowerCase() + 'Violations'] = item.count;
        return acc;
      }, {
        criticalViolations: 0,
        highViolations: 0,
        mediumViolations: 0,
        lowViolations: 0,
        infoViolations: 0
      });

      return {
        totalResources: record.get('totalResources') || 0,
        totalViolations: record.get('totalViolations') || 0,
        ...violationCounts,
        activePolicies: record.get('activePolicies') || 0,
        complianceScore: record.get('complianceScore') || 0.0,
        riskScore: record.get('riskScore') || 0.0,
        lastScan: record.get('lastScan'),
        totalEvaluations: record.get('totalEvaluations') || 0,
        activeEvaluations: record.get('activeEvaluations') || 0
      };
    } catch (error) {
      console.error('Error getting base metrics:', error);
      throw error;
    } finally {
      await session.close();
    }
  }

  /**
   * Get recent violations with detailed information
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
        OPTIONAL MATCH (v)-[:HAS_REMEDIATION]->(rem:Remediation)
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
          .details,
          policy: p {
            .id,
            .name,
            .severity,
            .category,
            .cloudProvider,
            .resourceType,
            .mlEnhanced,
            .mlThreshold,
            .mlWeight
          },
          resource: r {
            .id,
            .name,
            .type,
            .cloud,
            .region,
            .account,
            .state,
            .tags,
            .properties,
            .riskScore,
            .owner,
            .environment
          },
          mlPrediction: ml {
            .violationProbability,
            .confidence,
            .predictedViolations,
            .explanation,
            .modelType,
            .modelVersion,
            .features,
            .riskFactors
          },
          remediation: rem {
            .id,
            .type,
            .status,
            .automated,
            .estimatedTime,
            .riskReduction,
            .createdAt,
            .completedAt,
            .triggeredBy,
            steps
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
   * Get recent evaluations with detailed information
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
            .status,
            .policy {
              .id,
              .name,
              .severity
            },
            .resource {
              .id,
              .name,
              .type,
              .cloud
            }
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
            .state,
            .riskScore
          }),
          policies: collect(DISTINCT p {
            .id,
            .name,
            .severity,
            .category,
            .enabled,
            .mlEnhanced
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
  async getTrends(tenantId, timeframe = 'LAST_30_DAYS') {
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
          // Violations trend
          MATCH (v:Violation {tenantId: $tenantId})
          WHERE v.timestamp >= datetime() - ${duration}
          WITH date(v.timestamp) as date, count(v) as violations
          ORDER BY date
          RETURN collect({
            timestamp: toString(datetime({year: date.year, month: date.month, day: date.day})),
            value: toFloat(violations),
            label: toString(date)
          }) as violations
        }
        CALL {
          // Risk score trend
          MATCH (r:Resource {tenantId: $tenantId})
          WHERE r.lastScanned >= datetime() - ${duration}
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
          // Compliance trend
          MATCH (c:ComplianceReport {tenantId: $tenantId})
          WHERE c.generatedAt >= datetime() - ${duration}
          WITH date(c.generatedAt) as date, avg(c.overallScore) as avgCompliance
          ORDER BY date
          RETURN collect({
            timestamp: toString(datetime({year: date.year, month: date.month, day: date.day})),
            value: avgCompliance,
            label: toString(date)
          }) as compliance
        }
        CALL {
          // Resources trend
          MATCH (r:Resource {tenantId: $tenantId})
          WHERE r.createdAt >= datetime() - ${duration}
          WITH date(r.createdAt) as date, count(r) as resources
          ORDER BY date
          RETURN collect({
            timestamp: toString(datetime({year: date.year, month: date.month, day: date.day})),
            value: toFloat(resources),
            label: toString(date)
          }) as resources
        }
        CALL {
          // Evaluations trend
          MATCH (e:Evaluation {tenantId: $tenantId})
          WHERE e.timestamp >= datetime() - ${duration}
          WITH date(e.timestamp) as date, count(e) as evaluations
          ORDER BY date
          RETURN collect({
            timestamp: toString(datetime({year: date.year, month: date.month, day: date.day})),
            value: toFloat(evaluations),
            label: toString(date)
          }) as evaluations
        }
        RETURN violations, riskScore, compliance, resources, evaluations
        `,
        { tenantId }
      );

      const record = result.records[0];
      return {
        violations: record.get('violations') || [],
        riskScore: record.get('riskScore') || [],
        compliance: record.get('compliance') || [],
        resources: record.get('resources') || [],
        evaluations: record.get('evaluations') || []
      };
    } catch (error) {
      console.error('Error getting trends:', error);
      return {
        violations: [],
        riskScore: [],
        compliance: [],
        resources: [],
        evaluations: []
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
               c.status as status,
               collect(DISTINCT f {
                 .framework,
                 .version,
                 .score,
                 .status,
                 .lastAssessed,
                 controls: collect(DISTINCT f.controls {
                   .controlId,
                   .controlName,
                   .description,
                   .category,
                   .status,
                   .score,
                   .lastTested,
                   .automated
                 })
               }) as frameworks
        `,
        { tenantId }
      );

      const record = result.records[0];
      return record ? {
        overallScore: record.get('overallScore') || 0.0,
        status: record.get('status') || 'UNKNOWN',
        frameworks: record.get('frameworks') || []
      } : {
        overallScore: 0.0,
        status: 'UNKNOWN',
        frameworks: []
      };
    } catch (error) {
      console.error('Error getting compliance breakdown:', error);
      return {
        overallScore: 0.0,
        status: 'UNKNOWN',
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
        WITH r.cloud as cloud, count(r) as count
        RETURN cloud, count
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

  /**
   * Get risk distribution
   */
  async getRiskDistribution(tenantId) {
    const session = this.driver.session();
    
    try {
      const result = await session.run(
        `
        MATCH (r:Resource {tenantId: $tenantId})
        WHERE r.riskScore IS NOT NULL
        WITH 
          CASE 
            WHEN r.riskScore >= 0.8 THEN 'CRITICAL'
            WHEN r.riskScore >= 0.6 THEN 'HIGH'
            WHEN r.riskScore >= 0.4 THEN 'MEDIUM'
            WHEN r.riskScore >= 0.2 THEN 'LOW'
            ELSE 'MINIMAL'
          END as riskLevel,
          count(r) as count
        RETURN riskLevel, count
        ORDER BY 
          CASE riskLevel
            WHEN 'CRITICAL' THEN 1
            WHEN 'HIGH' THEN 2
            WHEN 'MEDIUM' THEN 3
            WHEN 'LOW' THEN 4
            WHEN 'MINIMAL' THEN 5
          END
        `,
        { tenantId }
      );

      return result.records.map(record => ({
        riskLevel: record.get('riskLevel'),
        count: record.get('count')
      }));
    } catch (error) {
      console.error('Error getting risk distribution:', error);
      return [];
    } finally {
      await session.close();
    }
  }

  /**
   * Get performance metrics
   */
  async getPerformanceMetrics(tenantId) {
    const session = this.driver.session();
    
    try {
      const result = await session.run(
        `
        WITH $tenantId as tenantId
        CALL {
          // Average evaluation duration
          MATCH (e:Evaluation {tenantId: $tenantId})
          WHERE e.duration IS NOT NULL
          RETURN avg(e.duration) as avgEvaluationDuration
        }
        CALL {
          // Violations resolved in last 30 days
          MATCH (v:Violation {tenantId: $tenantId})
          WHERE v.resolvedAt >= datetime() - duration({days: 30})
          RETURN count(v) as resolvedViolations30d
        }
        CALL {
          // New violations in last 30 days
          MATCH (v:Violation {tenantId: $tenantId})
          WHERE v.timestamp >= datetime() - duration({days: 30})
          RETURN count(v) as newViolations30d
        }
        CALL {
          // ML prediction accuracy
          MATCH (v:Violation {tenantId: $tenantId})
          WHERE v.mlPrediction IS NOT NULL
            AND v.falsePositive = false
          RETURN avg(v.mlPrediction.confidence) as avgMLConfidence
        }
        RETURN 
          coalesce(avgEvaluationDuration, 0.0) as avgEvaluationDuration,
          coalesce(resolvedViolations30d, 0) as resolvedViolations30d,
          coalesce(newViolations30d, 0) as newViolations30d,
          coalesce(avgMLConfidence, 0.0) as avgMLConfidence
        `,
        { tenantId }
      );

      const record = result.records[0];
      return {
        avgEvaluationDuration: record.get('avgEvaluationDuration') || 0.0,
        resolvedViolations30d: record.get('resolvedViolations30d') || 0,
        newViolations30d: record.get('newViolations30d') || 0,
        avgMLConfidence: record.get('avgMLConfidence') || 0.0
      };
    } catch (error) {
      console.error('Error getting performance metrics:', error);
      return {
        avgEvaluationDuration: 0.0,
        resolvedViolations30d: 0,
        newViolations30d: 0,
        avgMLConfidence: 0.0
      };
    } finally {
      await session.close();
    }
  }

  /**
   * Get real-time overview updates
   */
  async getOverviewUpdates(tenantId, since) {
    const session = this.driver.session();
    
    try {
      const result = await session.run(
        `
        WITH $tenantId as tenantId, $since as since
        CALL {
          // New violations since timestamp
          MATCH (v:Violation {tenantId: $tenantId})
          WHERE v.timestamp >= $since
          RETURN count(v) as newViolations
        }
        CALL {
          // Resolved violations since timestamp
          MATCH (v:Violation {tenantId: $tenantId})
          WHERE v.resolvedAt >= $since
          RETURN count(v) as resolvedViolations
        }
        CALL {
          // New evaluations since timestamp
          MATCH (e:Evaluation {tenantId: $tenantId})
          WHERE e.timestamp >= $since
          RETURN count(e) as newEvaluations
        }
        CALL {
          // Completed evaluations since timestamp
          MATCH (e:Evaluation {tenantId: $tenantId})
          WHERE e.completedAt >= $since
          RETURN count(e) as completedEvaluations
        }
        RETURN newViolations, resolvedViolations, newEvaluations, completedEvaluations
        `,
        { tenantId, since }
      );

      const record = result.records[0];
      return {
        newViolations: record.get('newViolations') || 0,
        resolvedViolations: record.get('resolvedViolations') || 0,
        newEvaluations: record.get('newEvaluations') || 0,
        completedEvaluations: record.get('completedEvaluations') || 0,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('Error getting overview updates:', error);
      return {
        newViolations: 0,
        resolvedViolations: 0,
        newEvaluations: 0,
        completedEvaluations: 0,
        timestamp: new Date().toISOString()
      };
    } finally {
      await session.close();
    }
  }
}

module.exports = OverviewService;
