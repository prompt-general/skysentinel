# Event Collectors

Cloud-specific event collectors for ingesting security events from various cloud providers.

## Supported Providers

### AWS
- **CloudTrail**: API audit events
- **EventBridge**: Real-time event streaming
- **GuardDuty**: Threat detection events
- **Security Hub**: Security findings

### Azure
- **Activity Log**: Azure platform events
- **Sentinel**: Security analytics events
- **Monitor**: Diagnostic and monitoring data

### GCP
- **Cloud Audit Logs**: Admin activity events
- **Cloud Logging**: Service and application logs
- **Security Command Center**: Threat detection

## Architecture

```
event-collectors/
├── aws/           # AWS event collector
├── azure/         # Azure event collector  
├── gcp/           # GCP event collector
└── shared/        # Common collector utilities
```

## Usage

```python
from event_collectors.aws import AWSEventCollector

config = {"region": "us-east-1", "credentials": {...}}
collector = AWSEventCollector(config)

for event in collector.stream_events():
    print(event)
```
