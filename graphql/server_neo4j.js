/**
 * Neo4j GraphQL Server for SkySentinel
 * Production-ready GraphQL server with Neo4j integration
 */

const { ApolloServer } = require('@apollo/server');
const { startStandaloneServer } = require('@apollo/server/standalone');
const { expressMiddleware } = require('@apollo/server/express4');
const { ApolloServerPluginDrainHttpServer } = require('@apollo/server/plugin/drainHttpServer');
const express = require('express');
const http = require('http');
const cors = require('cors');
const { json } = require('body-parser');
const { WebSocketServer } = require('ws');
const { useServer } = require('graphql-ws/lib/use/ws');
const { makeExecutableSchema } = require('@graphql-tools/schema');

// Import Neo4j integration
const Neo4jGraphQLIntegration = require('./neo4j_integration');
const { createSchema } = require('./schema');

// Import resolvers
const { QueryResolver, MutationResolver, SubscriptionResolver } = require('./resolvers');

class Neo4jGraphQLServer {
  constructor(config) {
    this.config = config;
    this.neo4jIntegration = new Neo4jGraphQLIntegration(config);
    this.app = express();
    this.httpServer = http.createServer(this.app);
    this.wsServer = new WebSocketServer({
      server: this.httpServer,
      path: '/graphql',
    });
    this.apolloServer = null;
    this.schema = null;
  }

  /**
   * Initialize the server
   */
  async initialize() {
    try {
      // Initialize Neo4j integration
      await this.neo4jIntegration.initialize();

      // Create GraphQL schema
      this.schema = await this.createSchema();

      // Create Apollo Server
      this.apolloServer = new ApolloServer({
        schema: this.schema,
        plugins: [
          ApolloServerPluginDrainHttpServer({ httpServer: this.httpServer }),
          {
            serverWillStart() {
              console.log('🚀 GraphQL server starting...');
            },
            serverDidStart() {
              console.log('✅ GraphQL server started successfully');
            },
          },
        ],
        introspection: this.config.apollo.introspection,
        csrfPrevention: this.config.apollo.csrfPrevention,
        cache: this.config.apollo.cache,
      });

      // Setup middleware
      this.setupMiddleware();

      // Setup WebSocket subscriptions
      this.setupSubscriptions();

      // Setup health check endpoint
      this.setupHealthCheck();

      // Setup metrics endpoint
      this.setupMetrics();

      console.log('✅ Neo4j GraphQL server initialized');
    } catch (error) {
      console.error('❌ Failed to initialize server:', error);
      throw error;
    }
  }

  /**
   * Create GraphQL schema with Neo4j integration
   */
  async createSchema() {
    try {
      // Get Neo4j GraphQL schema
      const neo4jSchema = this.neo4jIntegration.getSchema();

      // Create resolvers
      const resolvers = {
        Query: new QueryResolver(this.neo4jIntegration.getDriver()),
        Mutation: new MutationResolver(this.neo4jIntegration.getDriver()),
        Subscription: new SubscriptionResolver(),
      };

      // Create executable schema
      const schema = makeExecutableSchema({
        typeDefs: neo4jSchema.typeDefs,
        resolvers: resolvers,
      });

      return schema;
    } catch (error) {
      console.error('❌ Failed to create GraphQL schema:', error);
      throw error;
    }
  }

  /**
   * Setup Express middleware
   */
  setupMiddleware() {
    // CORS configuration
    this.app.use(cors({
      origin: this.config.cors.origin,
      credentials: this.config.cors.credentials,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Tenant-ID'],
    }));

    // Body parsing
    this.app.use(json({ limit: '10mb' }));

    // Request logging
    this.app.use((req, res, next) => {
      console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
      next();
    });

    // Apollo Server middleware
    this.app.use(
      '/graphql',
      expressMiddleware(this.apolloServer, {
        context: async ({ req }) => {
          // Extract authentication token
          const token = req.headers.authorization || '';
          
          // Extract tenant ID
          const tenantId = req.headers['x-tenant-id'] || 'default-tenant';

          // Create context
          return {
            token,
            tenantId,
            driver: this.neo4jIntegration.getDriver(),
            neoSchema: this.neo4jIntegration.getNeoSchema(),
            req,
          };
        },
      })
    );

    // GraphQL Playground endpoint
    if (this.config.apollo.playground) {
      this.app.get('/', (req, res) => {
        res.send(this.getPlaygroundHTML());
      });
    }
  }

  /**
   * Setup WebSocket subscriptions
   */
  setupSubscriptions() {
    // Cleanup for WebSocket server
    this.apolloServer.addPlugin({
      async serverWillStart() {
        return {
          async drainServer() {
            await this.wsServer.close();
          },
        };
      },
    });

    // Setup WebSocket server
    useServer(
      {
        schema: this.schema,
        context: async (ctx) => {
          // Extract authentication from connection params
          const token = ctx.connectionParams?.authorization || '';
          const tenantId = ctx.connectionParams?.tenantId || 'default-tenant';

          return {
            token,
            tenantId,
            driver: this.neo4jIntegration.getDriver(),
            neoSchema: this.neo4jIntegration.getNeoSchema(),
          };
        },
      },
      this.wsServer
    );

    console.log('✅ WebSocket subscriptions configured');
  }

  /**
   * Setup health check endpoint
   */
  setupHealthCheck() {
    this.app.get('/health', async (req, res) => {
      try {
        const neo4jHealth = await this.neo4jIntegration.healthCheck();
        const stats = await this.neo4jIntegration.getDatabaseStats();
        
        res.json({
          status: 'healthy',
          timestamp: new Date().toISOString(),
          version: require('../package.json').version,
          neo4j: neo4jHealth,
          database: stats,
        });
      } catch (error) {
        res.status(500).json({
          status: 'unhealthy',
          timestamp: new Date().toISOString(),
          error: error.message,
        });
      }
    });
  }

  /**
   * Setup metrics endpoint
   */
  setupMetrics() {
    this.app.get('/metrics', async (req, res) => {
      try {
        const stats = await this.neo4jIntegration.getDatabaseStats();
        
        res.json({
          timestamp: new Date().toISOString(),
          metrics: {
            database: stats,
            server: {
              uptime: process.uptime(),
              memory: process.memoryUsage(),
              cpu: process.cpuUsage(),
            },
          },
        });
      } catch (error) {
        res.status(500).json({
          error: error.message,
          timestamp: new Date().toISOString(),
        });
      }
    });
  }

  /**
   * Get GraphQL Playground HTML
   */
  getPlaygroundHTML() {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>SkySentinel GraphQL Playground</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" />
        <style>
          body {
            margin: 0;
            font-family: Arial, sans-serif;
          }
          .header {
            background: #2c3e50;
            color: white;
            padding: 1rem;
            text-align: center;
          }
          .playground-container {
            height: calc(100vh - 60px);
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>SkySentinel Neo4j GraphQL API</h1>
          <p>Cloud Security Policy Management with Graph Database</p>
        </div>
        <div class="playground-container" id="playground"></div>
        <script crossorigin src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/index.js"></script>
        <script>
          window.addEventListener('load', () => {
            GraphQLPlayground.init(document.getElementById('playground'), {
              endpoint: '/graphql',
              subscriptionEndpoint: '/graphql',
              headers: {
                'X-Tenant-ID': 'default-tenant'
              },
              workspaceName: 'SkySentinel',
              settings: {
                'schema.polling.enable': false,
                'schema.polling.interval': 10000,
                'editor.theme': 'dark',
                'editor.fontSize': 14,
              }
            });
          });
        </script>
      </body>
      </html>
    `;
  }

  /**
   * Start the server
   */
  async start() {
    try {
      await this.initialize();

      // Start Apollo Server
      await this.apolloServer.start();

      // Start HTTP server
      const port = this.config.server.port || 4000;
      const host = this.config.server.host || 'localhost';

      this.httpServer.listen(port, host, () => {
        console.log(`🚀 Neo4j GraphQL Server ready at http://${host}:${port}/graphql`);
        console.log(`🎮 GraphQL Playground available at http://${host}:${port}/`);
        console.log(`📊 Health check available at http://${host}:${port}/health`);
        console.log(`📈 Metrics available at http://${host}:${port}/metrics`);
      });

      return this.httpServer;
    } catch (error) {
      console.error('❌ Failed to start server:', error);
      throw error;
    }
  }

  /**
   * Stop the server
   */
  async stop() {
    try {
      if (this.apolloServer) {
        await this.apolloServer.stop();
      }

      if (this.httpServer) {
        await new Promise((resolve) => {
          this.httpServer.close(resolve);
        });
      }

      if (this.neo4jIntegration) {
        await this.neo4jIntegration.close();
      }

      console.log('✅ Server stopped gracefully');
    } catch (error) {
      console.error('❌ Failed to stop server:', error);
      throw error;
    }
  }

  /**
   * Graceful shutdown handler
   */
  setupGracefulShutdown() {
    const shutdown = async (signal) => {
      console.log(`\n📡 Received ${signal}, shutting down gracefully...`);
      
      try {
        await this.stop();
        process.exit(0);
      } catch (error) {
        console.error('❌ Error during shutdown:', error);
        process.exit(1);
      }
    };

    process.on('SIGTERM', () => shutdown('SIGTERM'));
    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGUSR2', () => shutdown('SIGUSR2')); // For nodemon
  }
}

// Default configuration
const defaultConfig = {
  neo4j: {
    uri: process.env.NEO4J_URI || 'neo4j://localhost:7687',
    username: process.env.NEO4J_USERNAME || 'neo4j',
    password: process.env.NEO4J_PASSWORD || 'password',
  },
  apollo: {
    introspection: process.env.NODE_ENV !== 'production',
    csrfPrevention: true,
    playground: process.env.NODE_ENV !== 'production',
    cache: 'bounded',
  },
  cors: {
    origin: process.env.CORS_ORIGIN || ['http://localhost:3000'],
    credentials: true,
  },
  server: {
    port: process.env.PORT || 4000,
    host: process.env.HOST || 'localhost',
  },
  jwt: {
    secret: process.env.JWT_SECRET || 'your-secret-key',
  },
};

// Create and start server if run directly
if (require.main === module) {
  const server = new Neo4jGraphQLServer(defaultConfig);
  
  server.setupGracefulShutdown();
  
  server.start().catch((error) => {
    console.error('❌ Failed to start server:', error);
    process.exit(1);
  });
}

module.exports = Neo4jGraphQLServer;
