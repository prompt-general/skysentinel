# Shared Components

Common utilities, models, and schemas used across SkySentinel components.

## Structure

### models/
- **events.py**: Normalized event data models
- **resources.py**: Cloud resource models
- **policies.py**: Security policy models
- **threats.py**: Threat intelligence models

### schemas/
- **events.json**: JSON schema for events
- **resources.json**: JSON schema for resources
- **policies.json**: JSON schema for policies

### utils/
- **logger.py**: Centralized logging utilities
- **config.py**: Configuration management
- **crypto.py**: Encryption/decryption utilities
- **validation.py**: Data validation functions

## Usage

```python
from shared.models import NormalizedEvent
from shared.utils import get_logger

logger = get_logger(__name__)
event = NormalizedEvent(...)
```
