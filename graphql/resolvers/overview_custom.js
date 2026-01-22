/**
 * Custom Overview Resolver for SkySentinel GraphQL API
 * Runs multiple Cypher queries to compute overview metrics
 */

const resolvers = {
  Query: {
    overview: async (parent, args, context, info) => {
      const session = context.driver.session();
      const tenantId = context.tenantId || 'default-tenant';
      
      try {
        // Query for total resources
        const totalResourcesResult = await session.run(
          'MATCH (r:Resource {tenantId: $tenantId}) WHERE r.valid_to IS NULL RETURN count(r) as totalResources',
          { tenantId }
        );
        const totalResources = totalResourcesResult.records[0].get('totalResources').toNumber();

        // Query for violations by severity
        const violationsResult = await session.run(`
          MATCH (v:Violation {tenantId: $tenantId})
          WHERE v.status = 'open'
          RETURN v.severity as severity, count(v) as count
        `, { tenantId });

        // Process violationsResult to get counts by severity
        const violationsBySeverity = violationsResult.records.reduce((acc, record) => {
          const severity = record.get('severity');
          const count = record.get('count').toNumber();
          acc[severity.toLowerCase() + 'Violations'] = count;
          return acc;
        }, {
          criticalViolations: 0,
          highViolations: 0,
          mediumViolations: 0,
          lowViolations: 0,
          infoViolations: 0
        });

        // Query for total violations
        const totalViolations = Object.values(violationsBySeverity).reduce((sum, count) => sum + count, 0);

        // Query for recent violations
        const recentViolationsResult = await session.run(`
          MATCH (v:Violation {tenantId: $tenantId})
          OPTIONAL MATCH (v)-[:VIOLATES_POLICY]->(p:Policy)
          OPTIONAL MATCH (v)-[:AFFECTS_RESOURCE]->(r:Resource)
          RETURN v {
            .id,
            .severity,
            .description,
            .timestamp,
            .status,
            .confidence,
            .falsePositive,
            .tags,
            .evidence,
            policy: p {
              .id,
              .name,
              .severity,
              .category
            },
            resource: r {
              .id,
              .name,
              .type,
              .cloud,
              .region,
              .account
            }
          }
          ORDER BY v.timestamp DESC
          LIMIT 10
        `, { tenantId });

        const recentViolations = recentViolationsResult.records.map(record => record.get('v'));

        // Query for recent evaluations
        const recentEvaluationsResult = await session.run(`
          MATCH (e:Evaluation {tenantId: $tenantId})
          OPTIONAL MATCH (e)-[:HAS_IAC_PLAN]->(iac:IACPlan)
          OPTIONAL MATCH (e)-[:EVALUATES_VIOLATION]->(v:Violation)
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
              .repository,
              .branch,
              .commit,
              .resources,
              .dependencies
            },
            .duration,
            .triggeredBy,
            .environment,
            .branch,
            .commit,
            violations: collect(DISTINCT v {
              .id,
              .severity,
              .description,
              .status
            })
          }
          ORDER BY e.timestamp DESC
          LIMIT 10
        `, { tenantId });

        const recentEvaluations = recentEvaluationsResult.records.map(record => record.get('e'));

        // Query for compliance score
        const complianceScoreResult = await session.run(
          'MATCH (c:ComplianceReport {tenantId: $tenantId}) RETURN avg(c.overallScore) as complianceScore',
          { tenantId }
        );
        const complianceScore = complianceScoreResult.records[0].get('complianceScore') || 0.0;

        // Query for risk score
        const riskScoreResult = await session.run(
          'MATCH (r:Resource {tenantId: $tenantId}) WHERE r.riskScore IS NOT NULL RETURN avg(r.riskScore) as riskScore',
          { tenantId }
        );
        const riskScore = riskScoreResult.records[0].get('riskScore') || 0.0;

        // Query for active policies
        const activePoliciesResult = await session.run(
          'MATCH (p:Policy {tenantId: $tenantId, enabled: true}) RETURN count(p) as activePolicies',
          { tenantId }
        );
        const activePolicies = activePoliciesResult.records[0].get('activePolicies').toNumber();

        // Query for last scan time
        const lastScanResult = await session.run(
          'MATCH (r:Resource {tenantId: $tenantId}) WHERE r.lastScanned IS NOT NULL RETURN max(r.lastScanned) as lastScan',
          { tenantId }
        );
        const lastScan = lastScanResult.records[0].get('lastScan');

        // Query for trends data (last 30 days)
        const trendsResult = await session.run(`
          WITH $tenantId as tenantId
          CALL {
            // Violations trend
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
            // Risk score trend
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
            // Compliance trend
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
          RETURN violations, riskScore, compliance
        `, { tenantId });

        const trendsRecord = trendsResult.records[0];
        const trends = {
          violations: trendsRecord.get('violations') || [],
          riskScore: trendsRecord.get('riskScore') || [],
          compliance: trendsRecord.get('compliance') || []
        };

        // Return the overview object
        return {
          totalResources,
          totalViolations,
          ...violationsBySeverity,
          complianceScore,
          riskScore,
          activePolicies,
          lastScan,
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
    },
  },
};

module.exports = resolvers;
