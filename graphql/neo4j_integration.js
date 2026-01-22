/**
 * Neo4j GraphQL Integration for SkySentinel
 * Integrates GraphQL schema with Neo4j database using Neo4j GraphQL library
 */

const { Neo4jGraphQL } = require('@neo4j/graphql');
const neo4j = require('neo4j-driver');
const { readFileSync } = require('fs');
const { join } = require('path');

// Import custom resolvers
const { QueryResolver, MutationResolver, SubscriptionResolver } = require('./resolvers');
const { createSchema } = require('./schema');

class Neo4jGraphQLIntegration {
  constructor(config) {
    this.config = config;
    this.driver = null;
    this.neoSchema = null;
    this.graphqlSchema = null;
    this.resolvers = {
      Query: new QueryResolver(),
      Mutation: new MutationResolver(),
      Subscription: new SubscriptionResolver()
    };
  }

  /**
   * Initialize Neo4j driver and GraphQL schema
   */
  async initialize() {
    try {
      // Create Neo4j driver
      this.driver = neo4j.driver(
        this.config.neo4j.uri,
        neo4j.auth.basic(
          this.config.neo4j.username,
          this.config.neo4j.password
        ),
        {
          maxConnectionLifetime: 30 * 60 * 1000, // 30 minutes
          maxConnectionPoolSize: 50,
          connectionAcquisitionTimeout: 60000,
          disableLosslessIntegers: true
        }
      );

      // Test connection
      await this.driver.verifyConnectivity();
      console.log('✅ Neo4j connection established');

      // Load GraphQL schema
      const typeDefs = this.loadSchema();
      
      // Create Neo4j GraphQL schema with custom resolvers
      this.neoSchema = new Neo4jGraphQL({
        typeDefs,
        driver: this.driver,
        resolvers: this.resolvers,
        features: {
          authorization: {
            key: this.config.jwt.secret,
            rolesPath: 'roles',
            isAuthenticated: true
          },
          populatedBy: {
            callbacks: {
              createdAt: () => new Date().toISOString(),
              updatedAt: () => new Date().toISOString()
            }
          }
        }
      });

      // Generate executable schema
      this.graphqlSchema = await this.neoSchema.getSchema();
      console.log('✅ Neo4j GraphQL schema generated');

      // Initialize database constraints and indexes
      await this.initializeDatabase();
      
      return this.graphqlSchema;
    } catch (error) {
      console.error('❌ Failed to initialize Neo4j GraphQL:', error);
      throw error;
    }
  }

  /**
   * Load GraphQL schema from file
   */
  loadSchema() {
    try {
      const schemaPath = join(__dirname, 'schema.graphql');
      const typeDefs = readFileSync(schemaPath, 'utf8');
      return typeDefs;
    } catch (error) {
      console.error('❌ Failed to load GraphQL schema:', error);
      throw error;
    }
  }

  /**
   * Initialize database constraints and indexes
   */
  async initializeDatabase() {
    const session = this.driver.session();
    
    try {
      // Create constraints for unique identifiers
      const constraints = [
        'CREATE CONSTRAINT account_id_unique IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE',
        'CREATE CONSTRAINT policy_id_unique IF NOT EXISTS FOR (p:Policy) REQUIRE p.id IS UNIQUE',
        'CREATE CONSTRAINT resource_id_unique IF NOT EXISTS FOR (r:Resource) REQUIRE r.id IS UNIQUE',
        'CREATE CONSTRAINT violation_id_unique IF NOT EXISTS FOR (v:Violation) REQUIRE v.id IS UNIQUE',
        'CREATE CONSTRAINT evaluation_id_unique IF NOT EXISTS FOR (e:Evaluation) REQUIRE e.id IS UNIQUE',
        'CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE',
        'CREATE CONSTRAINT tenant_id_unique IF NOT EXISTS FOR (t:Tenant) REQUIRE t.id IS UNIQUE'
      ];

      // Create indexes for performance
      const indexes = [
        'CREATE INDEX account_name_index IF NOT EXISTS FOR (a:Account) ON (a.name)',
        'CREATE INDEX policy_name_index IF NOT EXISTS FOR (p:Policy) ON (p.name)',
        'CREATE INDEX policy_category_index IF NOT EXISTS FOR (p:Policy) ON (p.category)',
        'CREATE INDEX policy_severity_index IF NOT EXISTS FOR (p:Policy) ON (p.severity)',
        'CREATE INDEX resource_type_index IF NOT EXISTS FOR (r:Resource) ON (r.type)',
        'CREATE INDEX resource_cloud_index IF NOT EXISTS FOR (r:Resource) ON (r.cloud)',
        'CREATE INDEX resource_region_index IF NOT EXISTS FOR (r:Resource) ON (r.region)',
        'CREATE INDEX violation_severity_index IF NOT EXISTS FOR (v:Violation) ON (v.severity)',
        'CREATE INDEX violation_status_index IF NOT EXISTS FOR (v:Violation) ON (v.status)',
        'CREATE INDEX violation_timestamp_index IF NOT EXISTS FOR (v:Violation) ON (v.timestamp)',
        'CREATE INDEX evaluation_type_index IF NOT EXISTS FOR (e:Evaluation) ON (e.type)',
        'CREATE INDEX evaluation_status_index IF NOT EXISTS FOR (e:Evaluation) ON (e.status)',
        'CREATE INDEX evaluation_timestamp_index IF NOT EXISTS FOR (e:Evaluation) ON (e.timestamp)',
        'CREATE INDEX user_email_index IF NOT EXISTS FOR (u:User) ON (u.email)',
        'CREATE INDEX tenant_name_index IF NOT EXISTS FOR (t:Tenant) ON (t.name)'
      ];

      // Create full-text search indexes
      const fullTextIndexes = [
        'CREATE FULLTEXT INDEX policy_search_index IF NOT EXISTS FOR (p:Policy) ON EACH [p.name, p.description]',
        'CREATE FULLTEXT INDEX resource_search_index IF NOT EXISTS FOR (r:Resource) ON EACH [r.name, r.type]',
        'CREATE FULLTEXT INDEX violation_search_index IF NOT EXISTS FOR (v:Violation) ON EACH [v.description]'
      ];

      // Execute all constraints and indexes
      for (const constraint of constraints) {
        await session.run(constraint);
      }

      for (const index of indexes) {
        await session.run(index);
      }

      for (const fullTextIndex of fullTextIndexes) {
        await session.run(fullTextIndex);
      }

      console.log('✅ Database constraints and indexes created');
    } catch (error) {
      console.error('❌ Failed to initialize database:', error);
      throw error;
    } finally {
      await session.close();
    }
  }

  /**
   * Get Neo4j GraphQL schema
   */
  getSchema() {
    if (!this.graphqlSchema) {
      throw new Error('GraphQL schema not initialized. Call initialize() first.');
    }
    return this.graphqlSchema;
  }

  /**
   * Get Neo4j driver
   */
  getDriver() {
    if (!this.driver) {
      throw new Error('Neo4j driver not initialized. Call initialize() first.');
    }
    return this.driver;
  }

  /**
   * Get Neo4j GraphQL instance
   */
  getNeoSchema() {
    if (!this.neoSchema) {
      throw new Error('Neo4j GraphQL not initialized. Call initialize() first.');
    }
    return this.neoSchema;
  }

  /**
   * Execute GraphQL query with Neo4j
   */
  async executeQuery(query, variables = {}, context = {}) {
    try {
      const result = await this.neoSchema.execute(query, variables, context);
      return result;
    } catch (error) {
      console.error('❌ GraphQL query execution failed:', error);
      throw error;
    }
  }

  /**
   * Health check for Neo4j connection
   */
  async healthCheck() {
    try {
      const session = this.driver.session();
      const result = await session.run('RETURN 1 as health');
      await session.close();
      return { status: 'healthy', timestamp: new Date().toISOString() };
    } catch (error) {
      return { status: 'unhealthy', error: error.message, timestamp: new Date().toISOString() };
    }
  }

  /**
   * Close Neo4j driver
   */
  async close() {
    if (this.driver) {
      await this.driver.close();
      console.log('✅ Neo4j connection closed');
    }
  }

  /**
   * Get database statistics
   */
  async getDatabaseStats() {
    const session = this.driver.session();
    
    try {
      const stats = await session.run(`
        CALL {
          MATCH (a:Account) RETURN count(a) as accounts
        }
        CALL {
          MATCH (p:Policy) RETURN count(p) as policies
        }
        CALL {
          MATCH (r:Resource) RETURN count(r) as resources
        }
        CALL {
          MATCH (v:Violation) RETURN count(v) as violations
        }
        CALL {
          MATCH (e:Evaluation) RETURN count(e) as evaluations
        }
        CALL {
          MATCH (u:User) RETURN count(u) as users
        }
        CALL {
          MATCH (t:Tenant) RETURN count(t) as tenants
        }
        RETURN accounts, policies, resources, violations, evaluations, users, tenants
      `);

      return stats.records[0].properties;
    } catch (error) {
      console.error('❌ Failed to get database stats:', error);
      throw error;
    } finally {
      await session.close();
    }
  }

  /**
   * Seed database with initial data
   */
  async seedDatabase() {
    const session = this.driver.session();
    
    try {
      // Create default tenant
      await session.run(`
        MERGE (t:Tenant {id: 'default-tenant'})
        SET t.name = 'Default Tenant', t.createdAt = datetime(), t.updatedAt = datetime()
      `);

      // Create default admin user
      await session.run(`
        MERGE (u:User {id: 'admin-user'})
        SET u.email = 'admin@skysentinel.com', 
            u.name = 'System Administrator',
            u.role = 'ADMIN',
            u.createdAt = datetime(),
            u.updatedAt = datetime()
        `);

      // Connect admin to default tenant
      await session.run(`
        MATCH (u:User {id: 'admin-user'}), (t:Tenant {id: 'default-tenant'})
        MERGE (u)-[:MEMBER_OF]->(t)
      `);

      // Create sample policies
      const samplePolicies = [
        {
          id: 's3-public-access',
          name: 'S3 Public Access Denied',
          description: 'S3 buckets should not have public read access',
          category: 'SECURITY',
          severity: 'HIGH',
          cloudProvider: 'AWS',
          resourceType: 'aws:s3:bucket',
          enabled: true
        },
        {
          id: 'ec2-security-group',
          name: 'EC2 Security Group Restricted',
          description: 'EC2 instances should use restricted security groups',
          category: 'SECURITY',
          severity: 'MEDIUM',
          cloudProvider: 'AWS',
          resourceType: 'aws:ec2:instance',
          enabled: true
        }
      ];

      for (const policy of samplePolicies) {
        await session.run(`
          MERGE (p:Policy {id: $id})
          SET p.name = $name,
              p.description = $description,
              p.category = $category,
              p.severity = $severity,
              p.cloudProvider = $cloudProvider,
              p.resourceType = $resourceType,
              p.enabled = $enabled,
              p.createdAt = datetime(),
              p.updatedAt = datetime()
        `, policy);
      }

      console.log('✅ Database seeded with initial data');
    } catch (error) {
      console.error('❌ Failed to seed database:', error);
      throw error;
    } finally {
      await session.close();
    }
  }

  /**
   * Backup database
   */
  async backupDatabase(backupPath) {
    const session = this.driver.session();
    
    try {
      // Export all nodes and relationships
      const result = await session.run(`
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, r, m
      `);

      const backup = {
        timestamp: new Date().toISOString(),
        nodes: [],
        relationships: []
      };

      result.records.forEach(record => {
        const node = record.get('n');
        const relationship = record.get('r');
        const targetNode = record.get('m');

        if (node && !backup.nodes.find(n => n.id === node.identity.toNumber())) {
          backup.nodes.push({
            id: node.identity.toNumber(),
            labels: node.labels,
            properties: node.properties
          });
        }

        if (relationship && targetNode) {
          backup.relationships.push({
            id: relationship.identity.toNumber(),
            type: relationship.type,
            startNodeId: relationship.start.toNumber(),
            endNodeId: relationship.end.toNumber(),
            properties: relationship.properties
          });
        }
      });

      // Write backup to file (in production, use proper file system)
      require('fs').writeFileSync(backupPath, JSON.stringify(backup, null, 2));
      
      console.log(`✅ Database backup created: ${backupPath}`);
      return backup;
    } catch (error) {
      console.error('❌ Failed to backup database:', error);
      throw error;
    } finally {
      await session.close();
    }
  }
}

module.exports = Neo4jGraphQLIntegration;
