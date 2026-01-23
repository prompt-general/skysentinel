terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
  
  backend "s3" {
    bucket         = "skysentinel-tfstate"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "skysentinel-tfstate-lock"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "SkySentinel"
      Environment = "production"
      ManagedBy   = "Terraform"
    }
  }
}

# VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  
  name = "skysentinel-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway     = true
  single_nat_gateway     = false
  one_nat_gateway_per_az = true
  
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    "kubernetes.io/cluster/skysentinel-eks" = "shared"
  }
  
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
  
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"
  
  cluster_name    = "skysentinel-eks"
  cluster_version = "1.27"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true
  
  eks_managed_node_groups = {
    compute = {
      name           = "compute-node-group"
      instance_types = ["m6i.xlarge", "m6a.xlarge"]
      min_size       = 3
      max_size       = 10
      desired_size   = 3
      
      disk_size      = 50
      disk_type      = "gp3"
      
      labels = {
        node-type = "compute-optimized"
      }
      
      taints = {
        dedicated = {
          key    = "dedicated"
          value  = "skysentinel"
          effect = "NO_SCHEDULE"
        }
      }
      
      tags = {
        "k8s.io/cluster-autoscaler/enabled"               = "true"
        "k8s.io/cluster-autoscaler/skysentinel-eks" = "owned"
      }
    }
    
    monitoring = {
      name           = "monitoring-node-group"
      instance_types = ["t3.medium"]
      min_size       = 2
      max_size       = 4
      desired_size   = 2
      
      labels = {
        node-type = "monitoring"
      }
    }
  }
  
  node_security_group_additional_rules = {
    ingress_allow_access_from_control_plane = {
      type                          = "ingress"
      protocol                      = "tcp"
      from_port                     = 1025
      to_port                       = 65535
      source_cluster_security_group = true
      description                   = "Allow traffic from control plane to webhook port of AWS load balancer controller"
    }
  }
}

# RDS for PostgreSQL (for user management and metadata)
module "db" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"
  
  identifier = "skysentinel-db"
  
  engine               = "postgres"
  engine_version       = "15.3"
  instance_class       = "db.t3.large"
  allocated_storage    = 100
  storage_encrypted    = true
  storage_type         = "gp3"
  
  db_name  = "skysentinel"
  username = var.db_username
  password = var.db_password
  port     = 5432
  
  vpc_security_group_ids = [module.eks.cluster_primary_security_group_id]
  
  maintenance_window = "Mon:00:00-Mon:03:00"
  backup_window      = "03:00-06:00"
  backup_retention_period = 30
  
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn
  
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  performance_insights_enabled = true
  performance_insights_retention_period = 7
  
  create_db_subnet_group = true
  subnet_ids             = module.vpc.private_subnets
  
  family = "postgres15"
  
  parameters = [
    {
      name  = "autovacuum"
      value = 1
    },
    {
      name  = "client_encoding"
      value = "utf8"
    }
  ]
  
  tags = {
    Owner       = "sky-sentinel"
    Environment = "production"
  }
}

# Elasticache Redis
resource "aws_elasticache_subnet_group" "redis" {
  name       = "skysentinel-redis-subnet-group"
  subnet_ids = module.vpc.private_subnets
  
  tags = {
    Name = "SkySentinel Redis Subnet Group"
  }
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "skysentinel-redis"
  engine              = "redis"
  node_type           = "cache.m6g.large"
  num_cache_nodes     = 3
  parameter_group_name = "default.redis7"
  engine_version      = "7.0"
  port                = 6379
  
  subnet_group_name = aws_elasticache_subnet_group.redis.name
  security_group_ids = [module.eks.cluster_primary_security_group_id]
  
  snapshot_retention_limit = 7
  snapshot_window         = "05:00-09:00"
  
  maintenance_window = "sun:05:00-sun:09:00"
  
  tags = {
    Name = "skysentinel-redis"
  }
}

# S3 for backups and ML models
resource "aws_s3_bucket" "skysentinel_data" {
  bucket = "skysentinel-data-${var.aws_account_id}"
  
  tags = {
    Name        = "SkySentinel Data"
    Environment = "Production"
  }
}

resource "aws_s3_bucket_versioning" "skysentinel_data" {
  bucket = aws_s3_bucket.skysentinel_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "skysentinel_data" {
  bucket = aws_s3_bucket.skysentinel_data.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "skysentinel_data" {
  bucket = aws_s3_bucket.skysentinel_data.id
  
  rule {
    id     = "backup_retention"
    status = "Enabled"
    
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    
    expiration {
      days = 365
    }
  }
}

# IAM Roles for Service Accounts (IRSA)
module "iam_assumable_role_admin" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role-with-oidc"
  version = "~> 5.0"
  
  create_role = true
  
  role_name = "skysentinel-policy-engine"
  
  provider_url = module.eks.oidc_provider
  role_policy_arns = [
    "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
    "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
    aws_iam_policy.policy_engine_custom.arn
  ]
  
  oidc_fully_qualified_subjects = [
    "system:serviceaccount:skysentinel-production:policy-engine"
  ]
}

resource "aws_iam_policy" "policy_engine_custom" {
  name        = "SkySentinelPolicyEngine"
  description = "Custom permissions for SkySentinel Policy Engine"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudtrail:LookupEvents",
          "cloudtrail:GetEventSelectors",
          "config:DescribeConfigurationRecorders",
          "config:DescribeConfigRules",
          "config:GetComplianceDetailsByConfigRule"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketPolicy",
          "s3:GetBucketAcl",
          "s3:GetBucketTagging"
        ]
        Resource = "arn:aws:s3:::*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:GetRole",
          "iam:GetRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "skysentinel" {
  name              = "/aws/eks/skysentinel-eks/cluster"
  retention_in_days = 30
  
  tags = {
    Application = "SkySentinel"
  }
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/skysentinel/api-gateway"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "policy_engine" {
  name              = "/skysentinel/policy-engine"
  retention_in_days = 30
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "api_gateway_high_error_rate" {
  alarm_name          = "skysentinel-api-gateway-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "5XXError"
  namespace          = "AWS/ApplicationELB"
  period             = "300"
  statistic          = "Sum"
  threshold          = "10"
  alarm_description  = "This metric monitors API Gateway 5XX errors"
  
  dimensions = {
    LoadBalancer = aws_lb.api_gateway.arn_suffix
  }
  
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_cpu_utilization" {
  alarm_name          = "skysentinel-high-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "CPUUtilization"
  namespace          = "AWS/ECS"
  period             = "300"
  statistic          = "Average"
  threshold          = "80"
  alarm_description  = "This metric monitors ECS service CPU utilization"
  
  dimensions = {
    ClusterName = "skysentinel-eks"
    ServiceName = "api-gateway"
  }
  
  alarm_actions = [aws_sns_topic.alerts.arn]
}

# SNS for Alerts
resource "aws_sns_topic" "alerts" {
  name = "skysentinel-alerts"
  
  tags = {
    Application = "SkySentinel"
  }
}

resource "aws_sns_topic_subscription" "alerts_slack" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "https"
  endpoint  = var.slack_webhook_url
}

# Load Balancer
resource "aws_lb" "api_gateway" {
  name               = "skysentinel-api-gateway"
  internal           = false
  load_balancer_type = "network"
  subnets            = module.vpc.public_subnets

  enable_deletion_protection = false

  tags = {
    Environment = "production"
    Application = "SkySentinel"
  }
}

# RDS Monitoring Role
resource "aws_iam_role" "rds_monitoring" {
  name = "skysentinel-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
