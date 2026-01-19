terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    Environment = var.environment
    Application = "SkySentinel"
    ManagedBy = "Terraform"
  }
}

# IAM Role for EventBridge to invoke Lambda
resource "aws_iam_role" "skysentinel_collector" {
  name = "SkySentinel-Collector-Role"
  description = "IAM role for SkySentinel event collector Lambda function"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Purpose = "EventCollection"
  }
}

# IAM Policy for CloudTrail access
resource "aws_iam_policy" "cloudtrail_read" {
  name        = "SkySentinel-CloudTrail-Read"
  description = "Permissions to read CloudTrail events"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "cloudtrail:LookupEvents",
          "cloudtrail:GetEventSelectors",
          "cloudtrail:GetTrailStatus",
          "cloudtrail:ListTrails"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
  
  tags = {
    Purpose = "EventCollection"
  }
}

# IAM Policy for resource discovery
resource "aws_iam_policy" "resource_discovery" {
  name        = "SkySentinel-Resource-Discovery"
  description = "Permissions for AWS resource discovery"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeVolumes",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeNetworkInterfaces",
          "s3:ListAllMyBuckets",
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning",
          "s3:GetBucketEncryption",
          "s3:GetBucketWebsite",
          "s3:GetBucketAcl",
          "s3:GetBucketTagging",
          "iam:ListUsers",
          "iam:ListRoles",
          "iam:ListPolicies",
          "iam:ListAttachedUserPolicies",
          "iam:ListAttachedRolePolicies",
          "iam:GetUser",
          "iam:GetRole",
          "iam:GetPolicy",
          "rds:DescribeDBInstances",
          "rds:DescribeDBSubnetGroups",
          "lambda:ListFunctions",
          "lambda:GetFunction",
          "dynamodb:ListTables",
          "dynamodb:DescribeTable",
          "ecs:ListClusters",
          "ecs:DescribeClusters"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
  
  tags = {
    Purpose = "ResourceDiscovery"
  }
}

# IAM Policy for Neo4j access
resource "aws_iam_policy" "neo4j_access" {
  name        = "SkySentinel-Neo4j-Access"
  description = "Permissions to access Neo4j cluster"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Effect   = "Allow"
        Resource = var.neo4j_kms_key_arn
      },
      {
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Effect   = "Allow"
        Resource = var.neo4j_credentials_secret_arn
      }
    ]
  })
  
  tags = {
    Purpose = "DatabaseAccess"
  }
}

# Attach policies to collector role
resource "aws_iam_role_policy_attachment" "cloudtrail_attach" {
  role       = aws_iam_role.skysentinel_collector.name
  policy_arn = aws_iam_policy.cloudtrail_read.arn
}

resource "aws_iam_role_policy_attachment" "discovery_attach" {
  role       = aws_iam_role.skysentinel_collector.name
  policy_arn = aws_iam_policy.resource_discovery.arn
}

resource "aws_iam_role_policy_attachment" "neo4j_attach" {
  role       = aws_iam_role.skysentinel_collector.name
  policy_arn = aws_iam_policy.neo4j_access.arn
}

# EventBridge Rule for CloudTrail events
resource "aws_cloudwatch_event_rule" "cloudtrail_events" {
  name        = "sky-sentinel-cloudtrail"
  description = "Capture CloudTrail events for SkySentinel"
  
  event_pattern = jsonencode({
    source = [
      "aws.ec2",
      "aws.s3", 
      "aws.iam",
      "aws.rds",
      "aws.lambda",
      "aws.ecs",
      "aws.dynamodb"
    ]
    detail-type = ["AWS API Call via CloudTrail"]
  })
  
  tags = {
    Application = "SkySentinel"
    Purpose = "EventCollection"
  }
}

# EventBridge Rule for security events
resource "aws_cloudwatch_event_rule" "security_events" {
  name        = "sky-sentinel-security"
  description = "Capture security events for SkySentinel"
  
  event_pattern = jsonencode({
    source = [
      "aws.guardduty",
      "aws.securityhub",
      "aws.macie"
    ]
    detail-type = ["GuardDuty Finding", "Security Hub Findings", "Macie Finding"]
  })
  
  tags = {
    Application = "SkySentinel"
    Purpose = "SecurityMonitoring"
  }
}

# S3 Bucket for SkySentinel data
resource "aws_s3_bucket" "skysentinel_data" {
  bucket = var.skysentinel_bucket_name
  
  tags = {
    Application = "SkySentinel"
    Purpose = "DataStorage"
    Environment = var.environment
  }
}

# S3 Bucket versioning
resource "aws_s3_bucket_versioning" "skysentinel_data_versioning" {
  bucket = aws_s3_bucket.skysentinel_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "skysentinel_data_encryption" {
  bucket = aws_s3_bucket.skysentinel_data.id
  
  rule {
    apply_server_side_encryption_by_default = true
    sse_algorithm = "AES256"
  }
}

# S3 Bucket for Lambda deployment
resource "aws_s3_bucket" "lambda_deployment" {
  bucket = "${var.skysentinel_bucket_name}-lambda"
  
  tags = {
    Application = "SkySentinel"
    Purpose = "LambdaDeployment"
    Environment = var.environment
  }
}

# KMS Key for encryption
resource "aws_kms_key" "skysentinel" {
  description = "KMS key for SkySentinel data encryption"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_current.account_id}:root"
        }
        Action = "kms:*"
        Resource = "*"
      }
    ]
  })
  
  tags = {
    Application = "SkySentinel"
    Purpose = "Encryption"
  }
}

# Secrets Manager for Neo4j credentials
resource "aws_secretsmanager_secret" "neo4j_credentials" {
  name = "skysentinel/neo4j-credentials"
  description = "Neo4j database credentials for SkySentinel"
  
  secret_string = jsonencode({
    username = var.neo4j_username
    password = var.neo4j_password
    uri = var.neo4j_uri
  })
  
  tags = {
    Application = "SkySentinel"
    Purpose = "DatabaseCredentials"
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "skysentinel_lambda" {
  name = "/aws/lambda/skysentinel-collector"
  
  tags = {
    Application = "SkySentinel"
    Purpose = "Logging"
  }
}

# VPC for SkySentinel resources
resource "aws_vpc" "skysentinel" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "skysentinel-vpc"
    Application = "SkySentinel"
    Purpose = "Network"
  }
}

# Subnets
resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.skysentinel.id
  cidr_block        = var.private_subnet_a_cidr
  availability_zone = "${var.aws_region}a"
  
  tags = {
    Name = "skysentinel-private-a"
    Application = "SkySentinel"
    Purpose = "Network"
    Type = "Private"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.skysentinel.id
  cidr_block        = var.private_subnet_b_cidr
  availability_zone = "${var.aws_region}b"
  
  tags = {
    Name = "skysentinel-private-b"
    Application = "SkySentinel"
    Purpose = "Network"
    Type = "Private"
  }
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.skysentinel.id
  cidr_block              = var.public_subnet_a_cidr
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  
  tags = {
    Name = "skysentinel-public-a"
    Application = "SkySentinel"
    Purpose = "Network"
    Type = "Public"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "skysentinel" {
  vpc_id = aws_vpc.skysentinel.id
  
  tags = {
    Name = "skysentinel-igw"
    Application = "SkySentinel"
    Purpose = "Network"
  }
}

# Route table for public subnet
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.skysentinel.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.skysentinel.id
  }
  
  tags = {
    Name = "skysentinel-public-rt"
    Application = "SkySentinel"
    Purpose = "Network"
  }
}

# Route table association for public subnet
resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

# EIP for NAT Gateway
resource "aws_eip" "nat" {
  vpc = true
  
  tags = {
    Name = "skysentinel-nat-eip"
    Application = "SkySentinel"
    Purpose = "Network"
  }
}

# NAT Gateway
resource "aws_nat_gateway" "skysentinel" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.private_a.id
  
  tags = {
    Name = "skysentinel-nat"
    Application = "SkySentinel"
    Purpose = "Network"
  }
}

# Route table for private subnets
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.skysentinel.id
  
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.skysentinel.id
  }
  
  tags = {
    Name = "skysentinel-private-rt"
    Application = "SkySentinel"
    Purpose = "Network"
  }
}

# Route table associations for private subnets
resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}
