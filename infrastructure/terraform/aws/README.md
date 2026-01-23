# SkySentinel AWS Infrastructure

This Terraform configuration creates the complete AWS infrastructure for SkySentinel's production deployment.

## Architecture Overview

The infrastructure includes:

- **EKS Cluster**: Kubernetes cluster for container orchestration
- **VPC**: Multi-AZ VPC with public and private subnets
- **RDS PostgreSQL**: Managed database for user management and metadata
- **ElastiCache Redis**: In-memory caching layer
- **S3 Buckets**: Storage for backups, ML models, and data
- **Load Balancer**: Network Load Balancer for API Gateway
- **Monitoring**: CloudWatch logs, metrics, and alarms
- **Security**: IAM roles, security groups, and encryption

## Prerequisites

Before deploying, ensure you have:

1. **Terraform >= 1.5.0** installed
2. **AWS CLI** configured with appropriate permissions
3. **kubectl** installed for Kubernetes management
4. **Helm** installed for package management

## Required Permissions

The AWS user/role deploying this infrastructure needs:

- AdministratorAccess (for initial setup)
- Or specific permissions for:
  - EKS cluster management
  - VPC and networking
  - RDS and ElastiCache
  - S3 and IAM
  - CloudWatch and SNS

## Configuration

1. **Copy the example variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit terraform.tfvars with your values:**
   ```hcl
   aws_region     = "us-east-1"
   aws_account_id = "123456789012"
   db_username    = "skysentinel_admin"
   db_password    = "your-secure-password-here"
   slack_webhook_url = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
   ```

## Backend Configuration

The configuration uses S3 for state management with DynamoDB locking. Before first deployment:

1. **Create S3 bucket for state:**
   ```bash
   aws s3api create-bucket \
     --bucket skysentinel-tfstate \
     --region us-east-1
   ```

2. **Create DynamoDB table for locking:**
   ```bash
   aws dynamodb create-table \
     --table-name skysentinel-tfstate-lock \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST \
     --region us-east-1
   ```

## Deployment Steps

1. **Initialize Terraform:**
   ```bash
   terraform init
   ```

2. **Plan the deployment:**
   ```bash
   terraform plan
   ```

3. **Apply the configuration:**
   ```bash
   terraform apply
   ```

4. **Configure kubectl:**
   ```bash
   aws eks update-kubeconfig --region us-east-1 --name skysentinel-eks
   ```

## Post-Deployment Setup

After infrastructure deployment:

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

2. **Deploy Kubernetes manifests:**
   ```bash
   cd ../../kubernetes/production
   kubectl apply -f 01-namespace-serviceaccounts.yaml
   kubectl apply -f 02-configmaps-secrets.yaml
   # ... continue with other manifests
   ```

## Infrastructure Components

### EKS Cluster
- **Version**: Kubernetes 1.27
- **Node Groups**: 
  - Compute optimized (m6i.xlarge, m6a.xlarge)
  - Monitoring (t3.medium)
- **Autoscaling**: 3-10 nodes for compute, 2-4 for monitoring
- **Security**: IRSA enabled, security groups configured

### VPC Networking
- **CIDR**: 10.0.0.0/16
- **Availability Zones**: 3 AZs (us-east-1a, b, c)
- **Subnets**: 
  - Private: 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24
  - Public: 10.0.101.0/24, 10.0.102.0/24, 10.0.103.0/24
- **Gateways**: NAT Gateway per AZ, Internet Gateway

### Databases
- **RDS PostgreSQL 15.3**: db.t3.large, 100GB encrypted storage
- **ElastiCache Redis 7.0**: cache.m6g.large, 3-node cluster
- **Backup**: 30-day retention, automated snapshots

### Storage
- **S3 Bucket**: skysentinel-data-{account-id}
- **Encryption**: Server-side encryption enabled
- **Lifecycle**: 30 days to IA, 90 days to Glacier, 365 days expiration

### Monitoring & Alerting
- **CloudWatch Logs**: 30-day retention
- **Alarms**: High error rate, CPU utilization
- **SNS**: Alert notifications to Slack

## Security Features

- **Encryption**: All data encrypted at rest and in transit
- **IAM Roles**: Least privilege access with IRSA
- **Network Security**: Private subnets, security groups
- **VPC Flow Logs**: Enabled for network monitoring
- **Secrets Management**: AWS Secrets Manager integration

## Cost Optimization

- **Reserved Instances**: Consider for predictable workloads
- **S3 Lifecycle**: Automatic storage class transitions
- **Right-sizing**: Monitor and adjust instance sizes
- **Auto Scaling**: Scale based on demand

## Maintenance

### Regular Tasks
- Review CloudWatch alarms and logs
- Update Kubernetes versions
- Rotate database passwords
- Monitor cost and usage
- Backup and test disaster recovery

### Updates
```bash
# Update Terraform modules
terraform init -upgrade

# Plan and apply updates
terraform plan
terraform apply
```

## Troubleshooting

### Common Issues

1. **EKS Cluster Creation Fails**
   - Check IAM permissions
   - Verify VPC and subnet configuration
   - Review security group rules

2. **Database Connection Issues**
   - Check security group inbound rules
   - Verify subnet group configuration
   - Review database credentials

3. **Load Balancer Health Checks Failing**
   - Check target group health
   - Verify security group allows traffic
   - Review application health endpoints

### Useful Commands

```bash
# Check EKS cluster status
aws eks describe-cluster --name skysentinel-eks

# List node groups
aws eks list-nodegroups --cluster-name skysentinel-eks

# Check RDS instance status
aws rds describe-db-instances --db-instance-identifier skysentinel-db

# View CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix /skysentinel

# Check Terraform state
terraform show
terraform state list
```

## Disaster Recovery

1. **Backups**: Automated daily backups with 30-day retention
2. **Cross-Region**: Consider multi-region deployment for critical workloads
3. **Documentation**: Keep this documentation updated
4. **Testing**: Regular disaster recovery drills

## Support

For issues with this infrastructure:

1. Check AWS CloudWatch logs and metrics
2. Review Terraform state and configuration
3. Consult AWS documentation for specific services
4. Contact the SkySentinel infrastructure team

## Security Considerations

- Regularly rotate secrets and passwords
- Monitor IAM access and permissions
- Enable AWS Config and CloudTrail
- Implement network ACLs where needed
- Regular security audits and penetration testing
