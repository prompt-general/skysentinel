/**
 * Simple Neo4j GraphQL Server for SkySentinel
 * Basic setup with Overview resolver as requested
 */

const { ApolloServer } = require('@apollo/server');
const { startStandaloneServer } = require('@apollo/server/standalone');
const { Neo4jGraphQL } = require('@neo4j/graphql');
const neo4j = require('neo4j-driver');

// Import custom resolvers
const OverviewResolver = require('./resolvers/overview');

// GraphQL Schema
const typeDefs = `
  scalar DateTime
  scalar JSON

  enum Severity {
    CRITICAL
    HIGH
    MEDIUM
    LOW
    INFO
  }

  enum ViolationStatus {
    OPEN
    IN_PROGRESS
    RESOLVED
    IGNORED
    FALSE_POSITIVE
  }

  enum EvaluationType {
    CI_CD
    RUNTIME
    MANUAL
    SCHEDULED
  }

  enum EvaluationStatus {
    PENDING
    RUNNING
    COMPLETED
    FAILED
    CANCELLED
  }

  enum EvaluationResult {
    PASS
    WARN
    BLOCK
    ERROR
  }

  enum CloudProvider {
    AWS
    AZURE
    GCP
    KUBERNETES
  }

  type Policy {
    id: ID!
    name: String!
    description: String
    severity: Severity!
    category: String!
    cloudProvider: CloudProvider!
    resourceType: String!
    enabled: Boolean!
    mlEnhanced: Boolean!
    mlThreshold: Float
    mlWeight: Float
    tags: [String!]
    createdAt: DateTime!
    updatedAt: DateTime!
    createdBy: String!
  }

  type Resource {
    id: ID!
    name: String!
    type: String!
    cloud: CloudProvider!
    region: String!
    account: String!
    state: String!
    tags: [Tag!]!
    properties: JSON!
    createdAt: DateTime!
    updatedAt: DateTime!
    lastScanned: DateTime
  }

  type Tag {
    key: String!
    value: String!
    source: String!
    managed: Boolean!
  }

  type MLPrediction {
    violationProbability: Float!
    confidence: Float!
    predictedViolations: [String!]!
    explanation: JSON!
    modelType: String!
    modelVersion: String!
    features: JSON!
  }

  type Violation {
    id: ID!
    policy: Policy!
    resource: Resource!
    severity: Severity!
    description: String!
    timestamp: DateTime!
    status: ViolationStatus!
    confidence: Float!
    falsePositive: Boolean!
    tags: [String!]
    evidence: [String!]
    mlPrediction: MLPrediction
  }

  type IACPlan {
    type: String!
    format: String!
    size: Int!
    resources: Int!
    dependencies: Int!
    hash: String!
    repository: String!
    branch: String!
    commit: String!
    path: String!
  }

  type Evaluation {
    id: ID!
    type: EvaluationType!
    status: EvaluationStatus!
    result: EvaluationResult!
    score: Float!
    confidence: Float!
    violations: [Violation!]!
    timestamp: DateTime!
    iacPlan: IACPlan!
    context: JSON!
    triggeredBy: String!
    triggeredAt: DateTime!
    completedAt: DateTime!
    duration: Float!
    environment: String!
    branch: String!
    commit: String!
  }

  type TrendPoint {
    timestamp: String!
    value: Float!
    label: String!
  }

  type Trends {
    violations: [TrendPoint!]!
    riskScore: [TrendPoint!]!
    compliance: [TrendPoint!]!
    resources: [TrendPoint!]!
  }

  type Overview {
    totalResources: Int!
    totalViolations: Int!
    criticalViolations: Int!
    highViolations: Int!
    mediumViolations: Int!
    lowViolations: Int!
    complianceScore: Float!
    riskScore: Float!
    activePolicies: Int!
    lastScan: DateTime!
    recentViolations: [Violation!]!
    recentEvaluations: [Evaluation!]!
    trends: Trends!
  }

  input OverviewInput {
    tenantId: String!
    timeframe: String
  }

  type Query {
    overview(input: OverviewInput!): Overview!
  }
`;

// Create Neo4j driver
const driver = neo4j.driver(
  process.env.NEO4J_URI || 'neo4j://localhost:7687',
  neo4j.auth.basic(
    process.env.NEO4J_USER || 'neo4j',
    process.env.NEO4J_PASSWORD || 'password'
  ),
  {
    maxConnectionLifetime: 30 * 60 * 1000, // 30 minutes
    maxConnectionPoolSize: 50,
    connectionAcquisitionTimeout: 60000,
  }
);

// Create Neo4j GraphQL schema
const neoSchema = new Neo4jGraphQL({
  typeDefs,
  driver,
  features: {
    authorization: {
      key: process.env.JWT_SECRET || 'your-secret-key',
    },
  },
});

// Create custom resolvers
const overviewResolver = new OverviewResolver(driver);

// Custom resolvers object
const resolvers = {
  Query: {
    overview: overviewResolver.overview.bind(overviewResolver),
  },
};

// Create Apollo Server
async function startServer() {
  try {
    // Test Neo4j connection
    await driver.verifyConnectivity();
    console.log('✅ Neo4j connection established');

    // Get Neo4j GraphQL schema
    const schema = await neoSchema.getSchema();

    // Create Apollo Server with custom resolvers
    const server = new ApolloServer({
      schema,
      introspection: true,
      csrfPrevention: true,
      plugins: [
        {
          serverWillStart() {
            console.log('🚀 GraphQL server starting...');
          },
          serverDidStart() {
            console.log('✅ GraphQL server started successfully');
          },
        },
      ],
    });

    // Start server
    const { url } = await startStandaloneServer(server, {
      listen: { port: process.env.PORT || 4000 },
      context: async ({ req }) => {
        // Extract tenant ID from headers
        const tenantId = req.headers['x-tenant-id'] || 'default-tenant';
        
        // Extract authorization token
        const token = req.headers.authorization || '';
        
        return {
          tenantId,
          token,
          driver,
        };
      },
    });

    console.log(`🚀 Server ready at ${url}`);
    console.log(`🎮 GraphQL Playground: ${url}graphql`);
    
    // Setup graceful shutdown
    const shutdown = async (signal) => {
      console.log(`\n📡 Received ${signal}, shutting down gracefully...`);
      
      try {
        await driver.close();
        console.log('✅ Neo4j connection closed');
        process.exit(0);
      } catch (error) {
        console.error('❌ Error during shutdown:', error);
        process.exit(1);
      }
    };

    process.on('SIGTERM', () => shutdown('SIGTERM'));
    process.on('SIGINT', () => shutdown('SIGINT'));

  } catch (error) {
    console.error('❌ Failed to start server:', error);
    process.exit(1);
  }
}

// Start server
startServer();

module.exports = { driver, neoSchema, resolvers };
