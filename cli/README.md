# CLI

Command-line interface for SkySentinel operations and automation.

## Features

- **Event Management**: Query and analyze security events
- **Policy Operations**: Manage security policies
- **Threat Response**: Automated threat mitigation
- **Compliance Reports**: Generate compliance assessments
- **Configuration**: System configuration and deployment

## Installation

```bash
pip install skysentinel-cli
```

## Usage

```bash
# Query events
skysentinel events query --cloud aws --last 24h

# Check compliance
skysentinel compliance check --framework cis

# Deploy policies
skysentinel policies deploy --file policy.yaml

# Threat response
skysentinel threats respond --threat-id 123
```

## Commands

- `events` - Event management and querying
- `policies` - Policy management
- `threats` - Threat intelligence and response
- `compliance` - Compliance operations
- `config` - Configuration management
- `deploy` - Deployment operations
