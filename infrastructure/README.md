# Infrastructure

This directory contains Terraform/IaC files for deploying SkySentinel infrastructure.

## Components

- **AWS**: EKS, RDS, ElastiCache, VPC configuration
- **Azure**: AKS, Cosmos DB, Virtual Network setup  
- **GCP**: GKE, Cloud SQL, VPC configuration

## Usage

```bash
cd infrastructure/aws
terraform init
terraform plan
terraform apply
```

## Structure

```
infrastructure/
├── aws/           # AWS Terraform configurations
├── azure/         # Azure ARM templates/Bicep
├── gcp/           # Google Cloud Deployment Manager
└── modules/       # Reusable infrastructure modules
```
