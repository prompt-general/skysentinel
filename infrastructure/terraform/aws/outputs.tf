output "skysentinel_bucket_arn" {
  description = "ARN of the SkySentinel S3 bucket"
  value       = aws_s3_bucket.skysentinel_data.arn
}

output "skysentinel_bucket_name" {
  description = "Name of the SkySentinel S3 bucket"
  value       = aws_s3_bucket.skysentinel_data.id
}

output "lambda_deployment_bucket_arn" {
  description = "ARN of the Lambda deployment S3 bucket"
  value       = aws_s3_bucket.lambda_deployment.arn
}

output "lambda_function_arn" {
  description = "ARN of the SkySentinel Lambda function"
  value       = aws_lambda_function.skysentinel_collector.arn
}

output "lambda_function_name" {
  description = "Name of the SkySentinel Lambda function"
  value       = aws_lambda_function.skysentinel_collector.function_name
}

output "cloudtrail_rule_arn" {
  description = "ARN of the CloudTrail EventBridge rule"
  value       = aws_cloudwatch_event_rule.cloudtrail_events.arn
}

output "security_rule_arn" {
  description = "ARN of the security EventBridge rule"
  value       = aws_cloudwatch_event_rule.security_events.arn
}

output "vpc_id" {
  description = "ID of the SkySentinel VPC"
  value       = aws_vpc.skysentinel.id
}

output "private_subnet_a_id" {
  description = "ID of private subnet A"
  value       = aws_subnet.private_a.id
}

output "private_subnet_b_id" {
  description = "ID of private subnet B"
  value       = aws_subnet.private_b.id
}

output "public_subnet_a_id" {
  description = "ID of public subnet A"
  value       = aws_subnet.public_a.id
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.skysentinel.id
}

output "nat_gateway_id" {
  description = "ID of the NAT Gateway"
  value       = aws_nat_gateway.skysentinel.id
}

output "kms_key_arn" {
  description = "ARN of the KMS encryption key"
  value       = aws_kms_key.skysentinel.arn
}

output "neo4j_credentials_secret_arn" {
  description = "ARN of the Neo4j credentials secret"
  value       = aws_secretsmanager_secret.neo4j_credentials.arn
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "collector_role_arn" {
  description = "ARN of the collector role"
  value       = aws_iam_role.skysentinel_collector.arn
}
