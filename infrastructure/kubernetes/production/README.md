# SkySentinel Kubernetes Production Deployment

This directory contains the complete Kubernetes production deployment configuration for SkySentinel.

## Files Overview

1. **01-namespace-serviceaccounts.yaml** - Namespace and service accounts with least privilege
2. **02-configmaps-secrets.yaml** - Configuration maps and secrets (secrets need to be populated)
3. **03-database-clusters.yaml** - Neo4j Enterprise and Redis cluster configurations
4. **04-api-gateway.yaml** - API Gateway deployment and service configuration
5. **05-policy-engine.yaml** - Policy Engine and ML worker deployments
6. **06-scaling-policies.yaml** - HPA and Pod Disruption Budget configurations
7. **07-networking.yaml** - Network policies and Ingress configuration
8. **08-cert-manager.yaml** - SSL certificate management with Let's Encrypt

## Prerequisites

Before deploying, ensure you have:

- Kubernetes cluster (v1.25+)
- Neo4j Operator installed
- Redis Operator installed
- NGINX Ingress Controller installed
- cert-manager installed
- AWS Load Balancer Controller (for NLB)

## Deployment Steps

1. **Install required operators:**
   ```bash
   # Neo4j Operator
   kubectl apply -f https://github.com/neo4j/neo4j-operator/releases/latest/download/neo4j-operator.yaml
   
   # Redis Operator
   kubectl apply -f https://raw.githubusercontent.com/OT-CONTAINER-KIT/redis-operator/master/deploy/redis-operator.yaml
   
   # NGINX Ingress Controller
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/aws/deploy.yaml
   
   # cert-manager
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
   ```

2. **Populate secrets:**
   - Update `02-configmaps-secrets.yaml` with actual base64-encoded secret values
   - Create Neo4j auth secret: `neo4j-auth-secret`

3. **Deploy in order:**
   ```bash
   kubectl apply -f 01-namespace-serviceaccounts.yaml
   kubectl apply -f 02-configmaps-secrets.yaml
   kubectl apply -f 03-database-clusters.yaml
   kubectl apply -f 04-api-gateway.yaml
   kubectl apply -f 05-policy-engine.yaml
   kubectl apply -f 06-scaling-policies.yaml
   kubectl apply -f 07-networking.yaml
   kubectl apply -f 08-cert-manager.yaml
   ```

## Security Features

- **Least Privilege**: Dedicated service accounts for different components
- **Network Policies**: Restrict traffic between pods
- **Security Contexts**: Non-root containers, dropped capabilities
- **Pod Security Standards**: Seccomp profiles, read-only filesystems
- **TLS/SSL**: Automatic SSL certificate management
- **Secrets Management**: Encrypted secrets with proper access controls

## Scaling Configuration

- **API Gateway**: 3-10 replicas based on CPU/Memory utilization
- **Policy Engine**: 3 replicas with dedicated ML workers
- **Databases**: 3-node clusters for high availability
- **Load Balancing**: AWS NLB with SSL termination

## Monitoring & Observability

- **Prometheus Metrics**: Enabled for all components
- **Health Checks**: Liveness, readiness, and startup probes
- **Resource Limits**: Proper CPU and memory constraints
- **Pod Disruption Budgets**: Ensure availability during maintenance

## Environment Variables

Key configuration options in ConfigMaps:
- `FEATURE_ML_PREDICTIONS`: Enable/disable ML predictions
- `FEATURE_REAL_TIME_UPDATES`: Enable real-time updates
- `FEATURE_INLINE_ENFORCEMENT`: Policy enforcement mode
- `RATE_LIMIT_ENABLED`: Rate limiting toggle
- `CACHE_ENABLED`: Caching toggle

## Backup & Recovery

- **Neo4j**: Daily automated backups with 30-day retention
- **Redis**: Persistent storage with automatic failover
- **StatefulSets**: Ensures data persistence across restarts

## Troubleshooting

Common issues and solutions:

1. **Pods not starting**: Check resource limits and node selectors
2. **Database connection failures**: Verify service names and credentials
3. **SSL certificate issues**: Check cert-manager logs and DNS records
4. **Ingress not working**: Verify ingress controller and DNS configuration

## Production Considerations

- Monitor resource utilization and adjust HPA thresholds
- Regularly rotate secrets and certificates
- Implement proper logging and alerting
- Test disaster recovery procedures
- Keep operators and dependencies updated
