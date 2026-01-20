# SkySentinel GitHub Action

This GitHub Action evaluates Infrastructure as Code (IaC) files against SkySentinel security policies to prevent security violations in your infrastructure deployments.

## Features

- **Multi-IaC Support**: Terraform, CloudFormation, ARM Templates, Kubernetes
- **Policy Evaluation**: Comprehensive security policy checking
- **PR Integration**: Automatic comments on pull requests
- **Flexible Configuration**: Configurable failure thresholds
- **Detailed Reporting**: Violation details and recommendations
- **Async Processing**: Non-blocking evaluation with progress tracking

## Usage

### Basic Usage

```yaml
name: Security Check

on:
  pull_request:
    branches: [main]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: SkySentinel Evaluation
        uses: skysentinel/ci-action@v1
        with:
          api-url: ${{ secrets.SKYSENTINEL_API_URL }}
          api-key: ${{ secrets.SKYSENTINEL_API_KEY }}
          iac-type: terraform
          iac-files: 'tfplan.json'
```

### Advanced Usage

```yaml
- name: SkySentinel Evaluation
  uses: skysentinel/ci-action@v1
  with:
    api-url: ${{ secrets.SKYSENTINEL_API_URL }}
    api-key: ${{ secrets.SKYSENTINEL_API_KEY }}
    iac-type: terraform
    iac-files: 'tfplan-*.json'
    context: |
      {
        "environment": "production",
        "team": "platform",
        "compliance": "SOC2"
      }
    fail-on-critical: true
    fail-on-high: false
    generate-comment: true
    timeout: 600
    retry-count: 3
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `api-url` | SkySentinel API URL | Yes | - |
| `api-key` | SkySentinel API key | Yes | - |
| `iac-type` | IaC type (terraform, cloudformation, arm, kubernetes) | Yes | - |
| `iac-files` | Glob pattern for IaC files | Yes | - |
| `file-filter` | Filter pattern for file selection | No | - |
| `context` | Additional context (JSON string) | No | `{}` |
| `fail-on-critical` | Fail on critical violations | No | `true` |
| `fail-on-high` | Fail on high severity violations | No | `false` |
| `generate-comment` | Generate PR comment | No | `true` |
| `timeout` | Evaluation timeout (seconds) | No | `300` |
| `retry-count` | Number of retries | No | `3` |

## Outputs

| Output | Description |
|--------|-------------|
| `status` | Overall evaluation status |
| `violations-count` | Total violations found |
| `critical-count` | Critical violations count |
| `high-count` | High severity violations count |
| `evaluation-id` | SkySentinel evaluation ID |
| `result-file` | Path to result file |

## Setup

### 1. Get SkySentinel API Credentials

1. Sign up for SkySentinel at [https://skysentinel.ai](https://skysentinel.ai)
2. Create an API key in your dashboard
3. Note your API URL and key

### 2. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

```bash
# GitHub Repository Settings > Secrets and variables > Actions
SKYSENTINEL_API_URL=https://api.skysentinel.ai
SKYSENTINEL_API_KEY=your_api_key_here
```

### 3. Configure Cloud Credentials (Optional)

For Terraform/CloudFormation evaluations, add cloud provider credentials:

```bash
# AWS
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# Azure
AZURE_CREDENTIALS=your_azure_credentials_json
AZURE_RESOURCE_GROUP=your_resource_group
AZURE_SUBSCRIPTION_ID=your_subscription_id

# Kubernetes
KUBECONFIG=your_kubeconfig_base64
K8S_CLUSTER_NAME=your_cluster_name
K8S_NAMESPACE=default
```

## IaC Type Specific Setup

### Terraform

```yaml
- name: Setup Terraform
  uses: hashicorp/setup-terraform@v3
  with:
    terraform_version: 1.5.0

- name: Terraform Plan
  run: |
    terraform init
    terraform plan -out=tfplan
    terraform show -json tfplan > tfplan.json

- name: SkySentinel Evaluation
  uses: skysentinel/ci-action@v1
  with:
    api-url: ${{ secrets.SKYSENTINEL_API_URL }}
    api-key: ${{ secrets.SKYSENTINEL_API_KEY }}
    iac-type: terraform
    iac-files: 'tfplan.json'
```

### CloudFormation

```yaml
- name: SkySentinel Evaluation
  uses: skysentinel/ci-action@v1
  with:
    api-url: ${{ secrets.SKYSENTINEL_API_URL }}
    api-key: ${{ secrets.SKYSENTINEL_API_KEY }}
    iac-type: cloudformation
    iac-files: '**/*.yaml,**/*.yml,**/*.json'
    file-filter: 'cloudformation|cfn'
```

### ARM Templates

```yaml
- name: Setup Azure CLI
  uses: azure/login@v1
  with:
    creds: ${{ secrets.AZURE_CREDENTIALS }}

- name: Generate ARM What-If
  run: |
    az deployment group what-if \
      --resource-group ${{ secrets.AZURE_RESOURCE_GROUP }} \
      --template-file template.json \
      --output json > arm-what-if.json

- name: SkySentinel Evaluation
  uses: skysentinel/ci-action@v1
  with:
    api-url: ${{ secrets.SKYSENTINEL_API_URL }}
    api-key: ${{ secrets.SKYSENTINEL_API_KEY }}
    iac-type: arm
    iac-files: 'arm-what-if.json'
```

### Kubernetes

```yaml
- name: Setup kubectl
  uses: azure/setup-kubectl@v3
  with:
    version: 'v1.28.0'

- name: Generate Kubernetes Diff
  run: |
    kubectl diff -f deployment.yaml --output=json > k8s-diff.json

- name: SkySentinel Evaluation
  uses: skysentinel/ci-action@v1
  with:
    api-url: ${{ secrets.SKYSENTINEL_API_URL }}
    api-key: ${{ secrets.SKYSENTINEL_API_KEY }}
    iac-type: kubernetes
    iac-files: 'k8s-diff.json'
```

## Configuration Examples

### Environment-Specific Policies

```yaml
- name: SkySentinel Evaluation
  uses: skysentinel/ci-action@v1
  with:
    api-url: ${{ secrets.SKYSENTINEL_API_URL }}
    api-key: ${{ secrets.SKYSENTINEL_API_KEY }}
    iac-type: terraform
    iac-files: 'tfplan.json'
    context: |
      {
        "environment": "${{ github.ref_name }}",
        "team": "platform",
        "compliance_requirements": ["SOC2", "GDPR"],
        "cost_threshold": 1000
      }
    fail-on-critical: true
    fail-on-high: ${{ github.ref_name == 'main' }}
```

### Multi-IaC Repository

```yaml
strategy:
  matrix:
    iac-type: [terraform, cloudformation, arm, kubernetes]

steps:
  - name: SkySentinel Evaluation
    uses: skysentinel/ci-action@v1
    with:
      api-url: ${{ secrets.SKYSENTINEL_API_URL }}
      api-key: ${{ secrets.SKYSENTINEL_API_KEY }}
      iac-type: ${{ matrix.iac-type }}
      iac-files: '${{ matrix.iac-type }}-plan.json'
```

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check API URL and key
   - Verify network connectivity
   - Check API key permissions

2. **File Not Found**
   - Verify file paths and patterns
   - Check file existence before action
   - Use absolute paths if needed

3. **Invalid JSON/YAML**
   - Validate file syntax
   - Use proper file extensions
   - Check for encoding issues

4. **Timeout**
   - Increase timeout value
   - Check evaluation complexity
   - Verify API performance

### Debug Mode

Enable debug logging:

```yaml
- name: SkySentinel Evaluation
  uses: skysentinel/ci-action@v1
  env:
    ACTIONS_STEP_DEBUG: true
  with:
    api-url: ${{ secrets.SKYSENTINEL_API_URL }}
    api-key: ${{ secrets.SKYSENTINEL_API_KEY }}
    iac-type: terraform
    iac-files: 'tfplan.json'
```

### Local Testing

Test the action locally:

```bash
# Install dependencies
pip install requests pydantic

# Run evaluator
python skysentinel_evaluator.py \
  --api-url https://api.skysentinel.ai \
  --api-key your_api_key \
  --iac-type terraform \
  --files tfplan.json \
  --context '{"environment": "test"}'
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This action is released under the MIT License.

## Support

- 📖 [Documentation](https://docs.skysentinel.ai)
- 🐛 [Issue Tracker](https://github.com/skysentinel/ci-action/issues)
- 💬 [Discord Community](https://discord.gg/skysentinel)
- 📧 [Support Email](support@skysentinel.ai)
