# SkySentinel

A comprehensive cloud security monitoring and threat detection platform that provides real-time visibility across multi-cloud environments.

## Architecture

SkySentinel is built with a modular microservices architecture:

```
skysentinel/
├── infrastructure/          # Terraform/IaC for deployment
├── event-collectors/
│   ├── aws/                # AWS CloudTrail, GuardDuty, VPC Flow Logs
│   ├── azure/              # Azure Sentinel, Activity Logs
│   └── gcp/                # Google Cloud Security Command Center
├── graph-engine/           # Relationship mapping and anomaly detection
├── policy-engine/          # Security policy evaluation and enforcement
├── api-gateway/           # Central API management and authentication
├── cli/                   # Command-line interface for operations
├── dashboard/             # Web-based monitoring and analytics UI
└── shared/
    ├── models/            # Shared data models
    ├── schemas/          # JSON schemas for validation
    └── utils/            # Common utilities
```

## Features

- **Multi-Cloud Support**: Collect and analyze security events from AWS, Azure, and GCP
- **Real-time Threat Detection**: Advanced graph-based anomaly detection
- **Policy Engine**: Configurable security rules and compliance checks
- **Interactive Dashboard**: Comprehensive visualization of security posture
- **CLI Tools**: Powerful command-line interface for automation
- **Scalable Architecture**: Microservices design for horizontal scaling

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/prompt-general/skysentinel.git
   cd skysentinel
   ```

2. Set up infrastructure:
   ```bash
   cd infrastructure
   terraform init
   terraform apply
   ```

3. Configure cloud providers in `event-collectors/`

4. Deploy services:
   ```bash
   docker-compose up -d
   ```

## Documentation

- [API Reference](./docs/api.md)
- [Configuration Guide](./docs/configuration.md)
- [Deployment Guide](./docs/deployment.md)

## Contributing

Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
