import { Neo4jGraphQL } from "@neo4j/graphql";
import neo4j from "neo4j-driver";
import { GraphQLError } from "graphql";

export const createResolvers = (driver: neo4j.Driver) => {
  return {
    Query: {
      dashboardOverview: async (_: any, { tenantId }: { tenantId: string }, context: any) => {
        try {
          const session = driver.session();
          
          // Get total resources
          const resourcesResult = await session.run(
            `MATCH (r:Resource)
             WHERE r.tenant_id = $tenantId AND r.valid_to IS NULL
             RETURN count(r) as totalResources`,
            { tenantId }
          );
          
          // Get violation counts by severity
          const violationsResult = await session.run(
            `MATCH (v:Violation)-[:DETECTED_ON]->(r:Resource)
             WHERE r.tenant_id = $tenantId AND v.status = 'OPEN'
             RETURN v.severity as severity, count(v) as count`,
            { tenantId }
          );
          
          // Get recent violations
          const recentViolationsResult = await session.run(
            `MATCH (v:Violation)-[:DETECTED_ON]->(r:Resource)
             WHERE r.tenant_id = $tenantId
             RETURN v
             ORDER BY v.detected_at DESC
             LIMIT 10`,
            { tenantId }
          );
          
          // Get compliance score
          const complianceResult = await session.run(
            `MATCH (r:Resource {tenant_id: $tenantId, valid_to: null})
             OPTIONAL MATCH (r)<-[:DETECTED_ON]-(v:Violation {status: 'OPEN'})
             WITH r, count(v) as violationCount
             RETURN 
               count(r) as totalResources,
               sum(CASE WHEN violationCount = 0 THEN 1 ELSE 0 END) as compliantResources`,
            { tenantId }
          );
          
          const totalResources = resourcesResult.records[0]?.get('totalResources').toNumber() || 0;
          const compliantResources = complianceResult.records[0]?.get('compliantResources').toNumber() || 0;
          const complianceScore = totalResources > 0 ? (compliantResources / totalResources) * 100 : 100;
          
          // Process violation counts
          const violationCounts = {
            critical: 0,
            high: 0,
            medium: 0,
            low: 0,
            total: 0
          };
          
          violationsResult.records.forEach(record => {
            const severity = record.get('severity').toLowerCase();
            const count = record.get('count').toNumber();
            violationCounts[severity as keyof typeof violationCounts] = count;
            violationCounts.total += count;
          });
          
          return {
            metrics: {
              totalResources,
              totalViolations: violationCounts.total,
              criticalViolations: violationCounts.critical,
              highViolations: violationCounts.high,
              mediumViolations: violationCounts.medium,
              lowViolations: violationCounts.low,
              complianceScore,
              attackPathsCount: 0, // To be implemented
              avgRemediationTime: 0, // To be implemented
              costOptimization: {
                estimatedSavings: 0,
                optimizationOpportunities: 0
              }
            },
            recentViolations: recentViolationsResult.records.map(record => 
              formatViolation(record.get('v').properties)
            ),
            topPolicies: [],
            complianceTrend: [],
            resourceSummary: {
              byCloud: {},
              byType: {}
            },
            mlInsights: {
              highRiskPredictions: 0,
              modelAccuracy: 0,
              driftDetected: false
            }
          };
          
        } catch (error) {
          throw new GraphQLError(`Failed to fetch dashboard overview: ${error.message}`);
        }
      },
      
      violations: async (
        _: any, 
        { 
          tenantId, 
          filters = {}, 
          pagination = { page: 1, pageSize: 20 },
          sortBy = { field: 'detected_at', direction: 'DESC' }
        }: any, 
        context: any
      ) => {
        try {
          const session = driver.session();
          const skip = (pagination.page - 1) * pagination.pageSize;
          const limit = pagination.pageSize;
          
          // Build WHERE clause based on filters
          const whereConditions = [`r.tenant_id = $tenantId`];
          const parameters: any = { tenantId, skip, limit };
          
          if (filters.severity?.length) {
            whereConditions.push(`v.severity IN $severities`);
            parameters.severities = filters.severity;
          }
          
          if (filters.status?.length) {
            whereConditions.push(`v.status IN $statuses`);
            parameters.statuses = filters.status;
          }
          
          if (filters.cloudProvider?.length) {
            whereConditions.push(`r.cloud IN $cloudProviders`);
            parameters.cloudProviders = filters.cloudProvider;
          }
          
          if (filters.resourceType?.length) {
            whereConditions.push(`r.type IN $resourceTypes`);
            parameters.resourceTypes = filters.resourceType;
          }
          
          if (filters.policyId?.length) {
            whereConditions.push(`v.policy_id IN $policyIds`);
            parameters.policyIds = filters.policyId;
          }
          
          if (filters.dateRange) {
            whereConditions.push(`v.detected_at >= $startDate AND v.detected_at <= $endDate`);
            parameters.startDate = filters.dateRange.start;
            parameters.endDate = filters.dateRange.end;
          }
          
          const whereClause = whereConditions.length > 0 
            ? `WHERE ${whereConditions.join(' AND ')}` 
            : '';
          
          // Build ORDER BY clause
          const orderByClause = `ORDER BY v.${sortBy.field} ${sortBy.direction}`;
          
          // Query for violations
          const query = `
            MATCH (v:Violation)-[:DETECTED_ON]->(r:Resource)
            ${whereClause}
            RETURN v, r
            ${orderByClause}
            SKIP $skip
            LIMIT $limit
          `;
          
          const countQuery = `
            MATCH (v:Violation)-[:DETECTED_ON]->(r:Resource)
            ${whereClause}
            RETURN count(v) as totalCount
          `;
          
          const [violationsResult, countResult] = await Promise.all([
            session.run(query, parameters),
            session.run(countQuery, parameters)
          ]);
          
          const totalCount = countResult.records[0]?.get('totalCount').toNumber() || 0;
          const totalPages = Math.ceil(totalCount / pagination.pageSize);
          
          return {
            items: violationsResult.records.map(record => 
              formatViolation(record.get('v').properties, record.get('r').properties)
            ),
            totalCount,
            pageInfo: {
              hasNextPage: pagination.page < totalPages,
              hasPreviousPage: pagination.page > 1,
              currentPage: pagination.page,
              totalPages
            }
          };
          
        } catch (error) {
          throw new GraphQLError(`Failed to fetch violations: ${error.message}`);
        }
      },
      
      attackPaths: async (
        _: any,
        { tenantId, from, to, maxDepth = 5 }: any,
        context: any
      ) => {
        try {
          const session = driver.session();
          
          let matchPattern = '';
          if (from && to) {
            matchPattern = `MATCH path = shortestPath((start:Resource {id: $from})-[*1..${maxDepth}]-(end: Resource {id: $to}))`;
          } else if (from) {
            matchPattern = `MATCH path = (start:Resource {id: $from})-[*1..${maxDepth}]-(connected:Resource)`;
          } else {
            // Find all internet-exposed resources with paths to sensitive resources
            matchPattern = `
              MATCH (internet:Resource {type: 'internet'})
              MATCH (sensitive:Resource)
              WHERE sensitive.tags.confidentiality IN ['high', 'critical']
              MATCH path = shortestPath((internet)-[*1..${maxDepth}]->(sensitive))
            `;
          }
          
          const query = `
            ${matchPattern}
            WHERE ALL(r IN nodes(path) WHERE r.tenant_id = $tenantId AND r.valid_to IS NULL)
            WITH path, 
                 nodes(path) as nodes,
                 relationships(path) as relationships,
                 length(path) as pathLength
            RETURN 
              reduce(score = 0, r IN nodes(path) | score + CASE 
                WHEN r.severity_score IS NOT NULL THEN r.severity_score 
                ELSE 1 
              END) as riskScore,
              [n IN nodes(path) | {id: n.id, type: n.type, name: n.name}] as nodes,
              [r IN relationships(path) | {type: type(r), properties: r}] as relationships
            ORDER BY riskScore DESC
            LIMIT 20
          `;
          
          const result = await session.run(query, { tenantId, from, to, maxDepth });
          
          return result.records.map((record, index) => ({
            id: `attack-path-${index}`,
            path: record.get('nodes'),
            riskScore: record.get('riskScore'),
            description: `Attack path with ${record.get('nodes').length} hops`,
            severity: calculateSeverity(record.get('riskScore')),
            steps: record.get('relationships').map((rel: any, idx: number) => ({
              step: idx + 1,
              from: record.get('nodes')[idx],
              to: record.get('nodes')[idx + 1],
              via: rel.type,
              risk: calculateStepRisk(rel.properties)
            })),
            mitigations: generateMitigations(record.get('nodes'), record.get('relationships')),
            lastAnalyzed: new Date().toISOString()
          }));
          
        } catch (error) {
          throw new GraphQLError(`Failed to fetch attack paths: ${error.message}`);
        }
      }
    },
    
    Mutation: {
      createPolicy: async (_: any, { input }: { input: any }, context: any) => {
        try {
          const session = driver.session();
          const policyId = `policy-${Date.now()}`;
          const now = new Date().toISOString();
          
          const query = `
            CREATE (p:Policy {
              id: $policyId,
              name: $name,
              description: $description,
              severity: $severity,
              enabled: $enabled,
              resources: $resources,
              condition: $condition,
              actions: $actions,
              enforcement: $enforcement,
              created_at: $createdAt,
              updated_at: $updatedAt,
              created_by: $createdBy,
              tenant_id: $tenantId
            })
            RETURN p
          `;
          
          const result = await session.run(query, {
            policyId,
            name: input.name,
            description: input.description,
            severity: input.severity,
            enabled: true,
            resources: JSON.stringify(input.resources),
            condition: JSON.stringify(input.condition),
            actions: JSON.stringify(input.actions),
            enforcement: JSON.stringify(input.enforcement),
            createdAt: now,
            updatedAt: now,
            createdBy: context.user?.id || 'system',
            tenantId: context.tenantId
          });
          
          return formatPolicy(result.records[0].get('p').properties);
          
        } catch (error) {
          throw new GraphQLError(`Failed to create policy: ${error.message}`);
        }
      },
      
      updateViolation: async (_: any, { id, input }: { id: string, input: any }, context: any) => {
        try {
          const session = driver.session();
          
          const query = `
            MATCH (v:Violation {id: $id})
            SET v += $updates,
                v.updated_at = $updatedAt
            RETURN v
          `;
          
          const result = await session.run(query, {
            id,
            updates: {
              status: input.status,
              notes: input.notes,
              assigned_to: input.assignedTo,
              resolution_reason: input.resolutionReason
            },
            updatedAt: new Date().toISOString()
          });
          
          if (result.records.length === 0) {
            throw new GraphQLError(`Violation not found: ${id}`);
          }
          
          return formatViolation(result.records[0].get('v').properties);
          
        } catch (error) {
          throw new GraphQLError(`Failed to update violation: ${error.message}`);
        }
      }
    },
    
    Subscription: {
      violationCreated: {
        subscribe: (_: any, { tenantId }: { tenantId: string }, context: any) => {
          return context.pubSub.asyncIterator(`VIOLATION_CREATED_${tenantId}`);
        }
      }
    }
  };
};

// Helper functions
const formatViolation = (violationProps: any, resourceProps?: any) => {
  return {
    id: violationProps.id,
    policyId: violationProps.policy_id,
    policyName: violationProps.policy_name,
    resourceId: violationProps.resource_id,
    resourceType: resourceProps?.type || violationProps.resource_type,
    resourceName: resourceProps?.name || violationProps.resource_name,
    cloudProvider: resourceProps?.cloud || violationProps.cloud_provider,
    severity: violationProps.severity,
    status: violationProps.status,
    description: violationProps.description,
    detectedAt: violationProps.detected_at,
    lastUpdated: violationProps.updated_at,
    context: JSON.parse(violationProps.context || '{}'),
    metadata: JSON.parse(violationProps.metadata || '{}')
  };
};

const formatPolicy = (policyProps: any) => {
  return {
    id: policyProps.id,
    name: policyProps.name,
    description: policyProps.description,
    severity: policyProps.severity,
    enabled: policyProps.enabled,
    resources: JSON.parse(policyProps.resources || '{}'),
    condition: JSON.parse(policyProps.condition || '{}'),
    actions: JSON.parse(policyProps.actions || '[]'),
    enforcement: JSON.parse(policyProps.enforcement || '{}'),
    createdAt: policyProps.created_at,
    updatedAt: policyProps.updated_at,
    createdBy: policyProps.created_by
  };
};

const calculateSeverity = (riskScore: number) => {
  if (riskScore >= 8) return 'CRITICAL';
  if (riskScore >= 6) return 'HIGH';
  if (riskScore >= 4) return 'MEDIUM';
  if (riskScore >= 2) return 'LOW';
  return 'INFO';
};

const calculateStepRisk = (relationship: any) => {
  // Calculate risk based on relationship properties
  return 1.0;
};

const generateMitigations = (nodes: any[], relationships: any[]) => {
  return nodes.map((node, index) => ({
    resourceId: node.id,
    action: 'review_security_group',
    description: `Review security configuration for ${node.type}`,
    priority: index === 0 ? 'HIGH' : 'MEDIUM'
  }));
};
