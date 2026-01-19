# API Gateway

Central API management and authentication gateway for SkySentinel services.

## Features

- **Authentication & Authorization**: JWT, OAuth2, API Key support
- **Rate Limiting**: Request throttling and quota management
- **Load Balancing**: Service discovery and load distribution
- **API Documentation**: OpenAPI/Swagger integration
- **Monitoring**: Request/response logging and metrics

## Endpoints

- `/api/v1/events` - Event ingestion
- `/api/v1/threats` - Threat intelligence
- `/api/v1/policies` - Policy management
- `/api/v1/compliance` - Compliance reports

## Usage

```bash
# Start API Gateway
cd api-gateway
npm install
npm start

# API Documentation
http://localhost:3000/docs
```
