# SkySentinel Backup & Disaster Recovery

Complete backup and disaster recovery solution for SkySentinel production environment.

## Overview

**RTO (Recovery Time Objective):** 4 hours  
**RPO (Recovery Point Objective):** 1 hour

## Components

### 1. Velero for Kubernetes Backup
- **Purpose**: Backup/restore Kubernetes resources and persistent volumes
- **Schedule**: Daily at 1 AM
- **Retention**: 30 days (720 hours)
- **Storage**: AWS S3 with cross-region replication

### 2. Neo4j Database Backup
- **Purpose**: Backup Neo4j graph database
- **Schedule**: Daily at 2 AM
- **Method**: Neo4j enterprise dump
- **Storage**: S3 with 7-day local retention

### 3. Backup Verification
- **Purpose**: Verify backup integrity and availability
- **Schedule**: Daily at 6 AM
- **Method**: Automated verification with Slack alerts

### 4. Monitoring & Alerting
- **Metrics**: Prometheus monitoring of backup status
- **Alerts**: Slack notifications for backup failures
- **Dashboards**: Grafana visualization of backup health

## Prerequisites

Before deploying, ensure you have:

1. **AWS S3 bucket** for backup storage
2. **IAM credentials** with S3 access
3. **Neo4j Enterprise** license
4. **Slack webhook** for notifications

## Environment Variables

Set these before deployment:

```bash
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
```

## Deployment Steps

1. **Create namespaces:**
```bash
kubectl create namespace velero
kubectl create namespace skysentinel-production  # if not exists
```

2. **Set environment variables:**
```bash
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
```

3. **Deploy backup stack:**
```bash
# Deploy Velero
kubectl apply -f 01-velero.yaml

# Wait for Velero to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=velero -n velero --timeout=300s

# Deploy Neo4j backup
kubectl apply -f 02-neo4j-backup.yaml

# Deploy disaster recovery runbook
kubectl apply -f 03-disaster-recovery-runbook.yaml

# Deploy backup verification
kubectl apply -f 04-backup-verification.yaml

# Deploy monitoring
kubectl apply -f 05-backup-monitoring.yaml
```

## Backup Operations

### Manual Backup

**Create Velero backup:**
```bash
velero backup create manual-backup --from-namespaces skysentinel-production,monitoring
```

**Create Neo4j backup:**
```bash
kubectl create job --from=cronjob/neo4j-backup manual-neo4j-backup
```

### Restore Operations

**Restore Kubernetes resources:**
```bash
# List available backups
velero backup get

# Restore from specific backup
velero restore create --from-backup daily-backup-20240123-010000

# Monitor restore progress
velero restore get
velero restore describe <restore-name>
```

**Restore Neo4j database:**
```bash
# Get latest backup from S3
LATEST_BACKUP=$(aws s3 ls s3://skysentinel-backups/neo4j/ | sort | tail -1 | awk '{print $4}')

# Scale down Neo4j
kubectl scale deployment neo4j --replicas=0 -n skysentinel-production

# Download and restore
aws s3 cp s3://skysentinel-backups/neo4j/$LATEST_BACKUP /tmp/
kubectl exec -it neo4j-0 -n skysentinel-production -- neo4j-admin database load --from-path=/tmp/$LATEST_BACKUP --database=neo4j --force

# Scale up Neo4j
kubectl scale deployment neo4j --replicas=1 -n skysentinel-production
```

## Disaster Recovery Procedures

### Complete Outage Recovery

1. **Assess Damage**
   ```bash
   # Check Velero backup status
   velero backup get
   
   # Verify S3 backups exist
   aws s3 ls s3://skysentinel-backups/
   ```

2. **Restore Kubernetes Resources**
   ```bash
   # Restore from latest backup
   velero restore create --from-backup daily-backup --wait
   
   # Verify restored resources
   kubectl get all -n skysentinel-production
   ```

3. **Restore Neo4j Database**
   ```bash
   # Get latest backup
   LATEST_BACKUP=$(aws s3 ls s3://skysentinel-backups/neo4j/ | sort | tail -1 | awk '{print $4}')
   
   # Restore database
   aws s3 cp s3://skysentinel-backups/neo4j/$LATEST_BACKUP /tmp/
   kubectl exec -it neo4j-0 -n skysentinel-production -- neo4j-admin database load --from-path=/tmp/$LATEST_BACKUP --database=neo4j --force
   ```

4. **Verify System Health**
   ```bash
   # Check all pods
   kubectl get pods -n skysentinel-production
   
   # Test API Gateway
   curl -k https://api.skysentinel.io/health
   
   # Test policy evaluations
   curl -k https://api.skysentinel.io/policies/test
   ```

### Data Corruption Recovery

1. **Identify Corrupted Data**
   ```bash
   # Check Neo4j consistency
   kubectl exec -it neo4j-0 -n skysentinel-production -- neo4j-admin check-consistency --database=neo4j
   ```

2. **Point-in-Time Recovery**
   ```bash
   # Find backup from specific time
   aws s3 ls s3://skysentinel-backups/neo4j/ | grep "20240123"
   
   # Restore from specific backup
   aws s3 cp s3://skysentinel-backups/neo4j/neo4j-20240123-020000.dump /tmp/
   kubectl exec -it neo4j-0 -n skysentinel-production -- neo4j-admin database load --from-path=/tmp/neo4j-20240123-020000.dump --database=neo4j --force
   ```

## Monitoring

### Backup Status

**Check Velero status:**
```bash
velero backup get
velero schedule get
```

**Check CronJob status:**
```bash
kubectl get cronjobs -n skysentinel-production
kubectl get jobs -n skysentinel-production
```

**Check backup logs:**
```bash
# Velero logs
kubectl logs -n velero deployment/velero

# Neo4j backup logs
kubectl logs job/neo4j-backup-<timestamp> -n skysentinel-production

# Backup verification logs
kubectl logs job/backup-verification-<timestamp> -n skysentinel-production
```

### Metrics and Alerts

**Prometheus metrics:**
- `velero_backup_status` - Backup completion status
- `kube_cronjob_status_failed` - CronJob failure status
- `aws_s3_bucket_size_bytes` - Backup storage usage

**Alert conditions:**
- Backup failures (critical)
- Missing daily backups (warning)
- High storage usage (warning)
- Old backup age (critical)

## Testing

### Backup Testing

**Test Velero backup:**
```bash
# Create test backup
velero backup create test-backup --from-namespaces skysentinel-production

# Verify backup
velero backup get test-backup

# Test restore (in non-prod)
velero restore create --from-backup test-backup --wait
```

**Test Neo4j backup:**
```bash
# Create test backup job
kubectl create job --from=cronjob/neo4j-backup test-neo4j-backup

# Verify backup in S3
aws s3 ls s3://skysentinel-backups/neo4j/

# Test restore (in non-prod)
```

### Disaster Recovery Drills

**Monthly DR drill:**
1. Schedule maintenance window
2. Perform complete restore in test environment
3. Verify data integrity
4. Document recovery time
5. Update procedures based on lessons learned

## Troubleshooting

### Common Issues

1. **Velero backup fails**
   - Check AWS credentials
   - Verify S3 bucket permissions
   - Review Velero logs

2. **Neo4j backup fails**
   - Check Neo4j pod status
   - Verify storage access
   - Review backup job logs

3. **Backup verification fails**
   - Check S3 bucket contents
   - Verify backup file integrity
   - Review verification script

### Recovery Commands

**Emergency restore:**
```bash
# Quick restore from latest backup
LATEST_BACKUP=$(velero backup get | grep Completed | head -1 | awk '{print $1}')
velero restore create --from-backup $LATEST_BACKUP --wait
```

**Force restore:**
```bash
# Force restore even if resources exist
velero restore create --from-backup daily-backup --wait --existing-resources-policy=update
```

## Maintenance

### Regular Tasks

- **Weekly**: Review backup logs and status
- **Monthly**: Test restore procedures
- **Quarterly**: Update disaster recovery documentation
- **Annually**: Full disaster recovery drill

### Backup Cleanup

**Clean up old backups:**
```bash
# Delete old Velero backups
velero backup delete <backup-name>

# Clean up old S3 backups
aws s3 ls s3://skysentinel-backups/neo4j/ | while read line; do
  date=$(echo $line | awk '{print $1}')
  backup=$(echo $line | awk '{print $4}')
  if [[ $(date -d "$date" +%s) -lt $(date -d "30 days ago" +%s) ]]; then
    aws s3 rm s3://skysentinel-backups/neo4j/$backup
  fi
done
```

## Security

### Access Control

- **IAM**: Least privilege access to S3
- **RBAC**: Service accounts with minimal permissions
- **Encryption**: Server-side encryption for all backups
- **Network**: VPC endpoints for S3 access

### Compliance

- **Data Retention**: Configurable retention policies
- **Audit Logs**: CloudTrail for backup operations
- **Documentation**: Regular updates to runbook

## Contact Information

- **Platform Team**: platform@skysentinel.io
- **Security Team**: security@skysentinel.io
- **On-Call Engineer**: +1-XXX-XXX-XXXX
- **Emergency Contact**: emergency@skysentinel.io

## Cost Optimization

- **Storage Lifecycle**: S3 IA to Glacier transitions
- **Compression**: Enable backup compression
- **Deduplication**: Velero incremental backups
- **Monitoring**: Track backup storage costs
