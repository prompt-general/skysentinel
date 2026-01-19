variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "skysentinel_bucket_name" {
  description = "S3 bucket name for SkySentinel data"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for SkySentinel VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_a_cidr" {
  description = "CIDR block for private subnet A"
  type        = string
  default     = "10.0.1.0/24"
}

variable "private_subnet_b_cidr" {
  description = "CIDR block for private subnet B"
  type        = string
  default     = "10.0.2.0/24"
}

variable "public_subnet_a_cidr" {
  description = "CIDR block for public subnet A"
  type        = string
  default     = "10.0.10.0/24"
}

variable "neo4j_uri" {
  description = "Neo4j database URI"
  type        = string
  sensitive   = true
}

variable "neo4j_username" {
  description = "Neo4j database username"
  type        = string
  sensitive   = true
}

variable "neo4j_password" {
  description = "Neo4j database password"
  type        = string
  sensitive   = true
}

variable "neo4j_credentials_secret_arn" {
  description = "ARN of Secrets Manager secret for Neo4j credentials"
  type        = string
  sensitive   = true
}

variable "neo4j_kms_key_arn" {
  description = "ARN of KMS key for Neo4j encryption"
  type        = string
  sensitive   = true
}

variable "log_level" {
  description = "Logging level for Lambda functions"
  type        = string
  default     = "INFO"
  
  validation {
    condition     = contains(["DEBUG", "INFO", "WARN", "ERROR"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARN, ERROR."
  }
}
