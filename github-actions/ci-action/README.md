# SkySentinel CI Action

A simplified GitHub Action for evaluating Infrastructure as Code (IaC) files against SkySentinel security policies.

## Quick Start

```yaml
- name: SkySentinel Security Check
  uses: skysentinel/ci-action@v1
  with:
    api-url: ${{ secrets.SKYSENTINEL_API_URL }}
    api-key: ${{ secrets.SKYSENTINEL_API_KEY }}
    iac-type: terraform
    iac-file: tfplan.json
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `api-url` | SkySentinel API URL | Yes | - |
| `api-key` | SkySentinel API key | Yes | - |
| `iac-type` | IaC type (terraform, cloudformation, arm, kubernetes) | Yes | - |
| `iac-file` | Path to IaC file | Yes | - |
| `context` | Additional context (JSON) | No | `{}` |
| `fail-on-critical` | Fail on critical violations | No | `true` |
| `fail-on-high` | Fail on high violations | No | `false` |
| `timeout` | Timeout in seconds | No | `300` |

## Outputs

| Output | Description |
|--------|-------------|
| `status` | Evaluation status |
| `violations` | Total violations |
| `critical-violations` | Critical count |
| `high-violations` | High count |
| `medium-violations` | Medium count |
| `low-violations` | Low count |
| `evaluation-id` | Evaluation ID |

## Example Usage

### Terraform

```yaml
- name: Setup Terraform
  uses: hashicorp/setup-terraform@v3

- name: Terraform Plan
  run: |
    terraform init
    terraform plan -out=tfplan
    terraform show -json tfplan > tfplan.json

- name: SkySentinel Security Check
  uses: skysentinel/ci-action@v1
  with:
    api-url: ${{ secrets.SKYSENTINEL_API_URL }}
    api-key: ${{ secrets.SKYSENTINEL_API_KEY }}
    iac-type: terraform
    iac-file: tfplan.json
    fail-on-critical: true
    context: '{"environment": "production", "team": "platform"}'
```

### CloudFormation

```yaml
- name: SkySentinel Security Check
  uses: skysentinel/ci-action@v1
  with:
    api-url: ${{ secrets.SKYSENTINEL_API_URL }}
    api-key: ${{ secrets.SKYSENTINEL_API_KEY }}
    iac-type: cloudformation
    iac-file: template.yaml
```

## Features

- ✅ Multi-IaC support (Terraform, CloudFormation, ARM, Kubernetes)
- ✅ Async evaluation with progress tracking
- ✅ Configurable failure thresholds
- ✅ PR comment integration
- ✅ Detailed violation reporting
- ✅ GitHub outputs for workflow integration

## License

MIT License - see LICENSE file for details.
