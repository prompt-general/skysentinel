# SkySentinel GraphQL API

## Overview

This GraphQL API provides a comprehensive interface for the SkySentinel cloud security platform, integrating with Neo4j for graph-based data storage and analysis.

## Architecture

The API is built using:
- **Apollo Server**: GraphQL server implementation
- **Neo4j GraphQL**: Automatic GraphQL schema generation from Neo4j
- **Custom Resolvers**: Hand-written resolvers for complex queries
- **Neo4j Driver**: Direct database access for custom queries

## Setup

### Prerequisites

1. Neo4j database running
2. Node.js 18+ installed
3. Environment variables configured

### Environment Variables

```bash
# Neo4j Configuration
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Server Configuration
PORT=4000
JWT_SECRET=your-secret-key

# CORS Configuration
CORS_ORIGIN=http://localhost:3000
```

## Running the Server

### Simple Server (Custom Resolvers)

```bash
node server_custom_resolver.js
```

### Full Production Server

```bash
node server_neo4j.js
```

### Development Mode

```bash
npm run dev
```

## GraphQL Schema

The schema includes types for:

- **Overview**: Dashboard metrics and statistics
- **Policy**: Security policies and rules
- **Violation**: Security violations and incidents
- **Resource**: Cloud resources and infrastructure
- **Evaluation**: CI/CD and runtime evaluations
- **Compliance**: Compliance reports and frameworks
- **AttackPath**: Attack path analysis
- **MLModel**: Machine learning models and predictions

## Custom Resolvers

### Overview Resolver

The overview resolver demonstrates how to write custom resolvers that run multiple Cypher queries:

```javascript
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

        // Process results...
        return {
          totalResources,
          // ... other metrics
        };
      } finally {
        await session.close();
      }
    },
  },
};
```

## Key Features

### Multi-Tenant Support

All queries include tenant isolation:

```javascript
const tenantId = context.tenantId || 'default-tenant';
```

### Complex Queries

Custom resolvers can run multiple Cypher queries to compute complex metrics:

- Aggregated statistics
- Trend analysis
- Compliance calculations
- Risk scoring

### Real-time Updates

WebSocket subscriptions for real-time data updates:

```javascript
subscription ViolationCreated($tenantId: String!) {
  violationCreated(tenantId: $tenantId) {
    id
    policy { name }
    resource { name }
    severity
    timestamp
  }
}
```

## Database Schema

The Neo4j database uses the following node types:

- **Resource**: Cloud resources (EC2, S3, etc.)
- **Policy**: Security policies
- **Violation**: Security violations
- **Evaluation**: CI/CD evaluations
- **User**: Platform users
- **Tenant**: Multi-tenant organizations

## Relationships

- `(Resource)-[:VIOLATES_POLICY]->(Policy)`
- `(Violation)-[:AFFECTS_RESOURCE]->(Resource)`
- `(Evaluation)-[:EVALUATES_RESOURCE]->(Resource)`
- `(User)-[:MEMBER_OF]->(Tenant)`

## Performance Considerations

### Connection Pooling

The Neo4j driver uses connection pooling:

```javascript
const driver = neo4j.driver(uri, auth, {
  maxConnectionPoolSize: 50,
  connectionAcquisitionTimeout: 60000,
});
```

### Session Management

Always close sessions:

```javascript
const session = driver.session();
try {
  // Run queries
} finally {
  await session.close();
}
```

### Query Optimization

Use indexes and constraints for performance:

```cypher
CREATE CONSTRAINT resource_id_unique FOR (r:Resource) REQUIRE r.id IS UNIQUE;
CREATE INDEX resource_tenant_index FOR (r:Resource) ON (r.tenantId);
```

## Testing

### Unit Tests

```bash
npm test
```

### Integration Tests

```bash
npm run test:integration
```

### GraphQL Testing

Use GraphQL Playground at `http://localhost:4000/graphql`

## Deployment

### Docker

```bash
docker build -t skysentinel-graphql .
docker run -p 4000:4000 skysentinel-graphql
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: skysentinel-graphql
spec:
  replicas: 3
  selector:
    matchLabels:
      app: skysentinel-graphql
  template:
    metadata:
      labels:
        app: skysentinel-graphql
    spec:
      containers:
      - name: graphql
        image: skysentinel-graphql:latest
        ports:
        - containerPort: 4000
        env:
        - name: NEO4J_URI
          value: "neo4j://neo4j:7687"
```

## Monitoring

### Health Check

```bash
curl http://localhost:4000/health
```

### Metrics

```bash
curl http://localhost:4000/metrics
```

## Security

### Authentication

JWT-based authentication with tenant isolation:

```javascript
const token = req.headers.authorization || '';
const tenantId = req.headers['x-tenant-id'] || 'default-tenant';
```

### Authorization

Role-based access control through Neo4j GraphQL plugin:

```javascript
const neoSchema = new Neo4jGraphQL({
  typeDefs,
  driver,
  features: {
    authorization: {
      key: process.env.JWT_SECRET,
    },
  },
});
```

## Troubleshooting

### Common Issues

1. **Connection Errors**: Check Neo4j URI and credentials
2. **Slow Queries**: Add indexes and optimize Cypher queries
3. **Memory Issues**: Increase connection pool size or add pagination

### Debug Logging

Enable debug logging:

```bash
DEBUG=neo4j* node server_custom_resolver.js
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details.
