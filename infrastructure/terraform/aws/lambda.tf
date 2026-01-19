# Lambda function for event processing
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_function.py"
  output_path = "${path.module}/lambda_function.zip"
}

# Lambda IAM role
resource "aws_iam_role" "lambda_execution" {
  name = "SkySentinel-Lambda-Execution-Role"
  description = "IAM role for SkySentinel Lambda execution"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Application = "SkySentinel"
    Purpose = "LambdaExecution"
  }
}

# Lambda execution policy
resource "aws_iam_policy" "lambda_execution" {
  name        = "SkySentinel-Lambda-Execution-Policy"
  description = "Permissions for SkySentinel Lambda execution"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      },
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
          "secretsmanager:GetSecretValue"
        ]
        Effect   = "Allow"
        Resource = var.neo4j_credentials_secret_arn
      }
    ]
  })
  
  tags = {
    Application = "SkySentinel"
    Purpose = "LambdaExecution"
  }
}

# Attach execution policy to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_execution_attach" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_execution.arn
}

# Lambda function
resource "aws_lambda_function" "skysentinel_collector" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "skysentinel-event-collector"
  role            = aws_iam_role.lambda_execution.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"
  timeout          = 300
  memory_size      = 512
  
  environment {
    variables = {
      NEO4J_URI = var.neo4j_uri
      NEO4J_USERNAME_SECRET = var.neo4j_credentials_secret_arn
      S3_BUCKET = aws_s3_bucket.skysentinel_data.id
      LOG_LEVEL = var.log_level
    }
  }
  
  tags = {
    Application = "SkySentinel"
    Purpose = "EventCollection"
  }
  
  depends_on = [
    data.archive_file.lambda_zip
  ]
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.skysentinel_collector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cloudtrail_events.arn
}

# Lambda permission for security events
resource "aws_lambda_permission" "allow_security_eventbridge" {
  statement_id  = "AllowExecutionFromSecurityEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.skysentinel_collector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.security_events.arn
}

# EventBridge target for CloudTrail events
resource "aws_cloudwatch_event_target" "cloudtrail_target" {
  rule      = aws_cloudwatch_event_rule.cloudtrail_events.name
  target_id = aws_lambda_function.skysentinel_collector.arn
  arn       = aws_lambda_function.skysentinel_collector.arn
  
  input_transformer {
    input_paths = {
      event_id = "$.id"
      event_time = "$.time"
      event_name = "$.detail.eventName"
      principal = "$.detail.userIdentity.arn"
      source_ip = "$.detail.sourceIPAddress"
      user_agent = "$.detail.userAgent"
      request_params = "$.detail.requestParameters"
      response_elements = "$.detail.responseElements"
      error_code = "$.detail.errorCode"
      error_message = "$.detail.errorMessage"
      aws_region = "$.region"
      aws_account = "$.account"
    }
    input_template = <<EOF
{
  "event_type": "cloudtrail",
  "event_id": "<event_id>",
  "timestamp": "<event_time>",
  "event_name": "<event_name>",
  "principal": "<principal>",
  "source_ip": "<source_ip>",
  "user_agent": "<user_agent>",
  "request_parameters": <request_params>,
  "response_elements": <response_elements>,
  "error_code": "<error_code>",
  "error_message": "<error_message>",
  "aws_region": "<aws_region>",
  "aws_account": "<aws_account>",
  "raw_event": <aws.events.event>
}
EOF
  }
}

# EventBridge target for security events
resource "aws_cloudwatch_event_target" "security_target" {
  rule      = aws_cloudwatch_event_rule.security_events.name
  target_id = aws_lambda_function.skysentinel_collector.arn
  arn       = aws_lambda_function.skysentinel_collector.arn
  
  input_transformer {
    input_paths = {
      event_id = "$.detail.id"
      event_time = "$.detail.updatedAt"
      event_name = "$.detail.type"
      principal = "$.detail.resource.accountId"
      severity = "$.detail.severity"
      title = "$.detail.title"
      description = "$.detail.description"
      service = "$.detail.service"
      aws_region = "$.region"
      aws_account = "$.account"
    }
    input_template = <<EOF
{
  "event_type": "security",
  "event_id": "<event_id>",
  "timestamp": "<event_time>",
  "event_name": "<event_name>",
  "principal": "<principal>",
  "severity": "<severity>",
  "title": "<title>",
  "description": "<description>",
  "service": "<service>",
  "aws_region": "<aws_region>",
  "aws_account": "<aws_account>",
  "raw_event": <aws.events.event>
}
EOF
  }
}

# Lambda function code
resource "aws_s3_object" "lambda_function" {
  bucket = aws_s3_bucket.lambda_deployment.id
  key    = "lambda_function.zip"
  source = data.archive_file.lambda_zip.output_path
  
  etag = data.archive_file.lambda_zip.output_md5
}

# Lambda layer for shared dependencies
resource "aws_lambda_layer_version" "skysentinel_dependencies" {
  layer_name          = "skysentinel-dependencies"
  compatible_runtimes = ["python3.9"]
  
  filename = "${path.module}/dependencies.zip"
  
  source_code_hash = data.archive_file.dependencies_zip.output_base64sha256
}

# Create dependencies zip
data "archive_file" "dependencies_zip" {
  type        = "zip"
  output_path = "${path.module}/dependencies.zip"
  
  source {
    content = <<-EOF
# Placeholder for dependencies
# In production, this would include actual Python packages
EOF
    filename = "README.txt"
  }
}
