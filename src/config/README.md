# Configuration System Documentation

## Overview

The Exam Grader application uses a unified configuration system that consolidates all settings into a single, centralized system with environment-specific settings, validation, and migration utilities.

## Architecture

### Core Components

1. **UnifiedConfig**: Main configuration class that loads and validates all settings
2. **Configuration Data Classes**: Typed configuration sections (SecurityConfig, DatabaseConfig, etc.)
3. **ConfigurationMigrator**: Handles migration of deprecated environment variables
4. **ConfigurationValidator**: Validates configuration settings and provides warnings
5. **ConfigurationUtils**: Utility functions for configuration management

### Configuration Sections

- **SecurityConfig**: Authentication, sessions, CSRF protection
- **DatabaseConfig**: Database connection and pool settings
- **FileConfig**: File processing, storage, and format settings
- **APIConfig**: External API keys and endpoints
- **CacheConfig**: Caching strategy and settings
- **LoggingConfig**: Logging levels and output configuration
- **ServerConfig**: Web server host, port, and debug settings

## Environment Variables

### Required Variables

```bash
SECRET_KEY=your_secret_key_here_at_least_32_characters
DATABASE_URL=sqlite:///exam_grader.db
```

### Optional Variables

```bash
# Security Settings
SESSION_TIMEOUT=3600
CSRF_ENABLED=True

# Database Settings
DATABASE_ECHO=False

# File Processing Settings
MAX_FILE_SIZE_MB=20
SUPPORTED_FORMATS=.pdf,.docx,.jpg,.png
TEMP_DIR=temp
OUTPUT_DIR=output
UPLOAD_DIR=uploads

# API Settings
HANDWRITING_OCR_API_KEY=your_ocr_api_key
HANDWRITING_OCR_API_URL=https://www.handwritingocr.com/api/v3
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_MODEL=deepseek-chat

# Server Settings
HOST=127.0.0.1
PORT=5000
DEBUG=False
FLASK_ENV=development

# Logging Settings
LOG_LEVEL=INFO
LOG_FILE=

# Cache Settings
CACHE_TYPE=simple
```

## Usage Examples

### Basic Usage

```python
from src.config.unified_config import UnifiedConfig

# Initialize configuration
config = UnifiedConfig()

# Access configuration sections
print(f"Server running on {config.server.host}:{config.server.port}")
print(f"Database: {config.database.database_url}")
print(f"Max file size: {config.files.max_file_size_mb}MB")
```

### Flask Integration

```python
from src.config.unified_config import UnifiedConfig
from flask import Flask

config = UnifiedConfig()
app = Flask(__name__)

# Apply Flask configuration
app.config.update(config.get_flask_config())
```

### Configuration Validation

```python
from src.config.unified_config import UnifiedConfig

config = UnifiedConfig()

# Validate configuration
if config.validate():
    print("Configuration is valid")
else:
    print("Configuration has issues")

# Get configuration summary
summary = config.get_configuration_summary()
print(f"Environment: {summary['environment']}")
print(f"API Keys configured: OCR={summary['api']['ocr_configured']}, LLM={summary['api']['llm_configured']}")
```

### Configuration Health Check

```python
from src.config.config_utils import ConfigurationUtils
from src.config.unified_config import UnifiedConfig

config = UnifiedConfig()
health = ConfigurationUtils.check_configuration_health(config)

print(f"Overall status: {health['overall_status']}")
if health['issues']:
    print("Issues found:")
    for issue in health['issues']:
        print(f"  - {issue}")
```

### Environment File Management

```python
from src.config.config_utils import ConfigurationUtils
from src.config.unified_config import UnifiedConfig

# Create environment file template
config = UnifiedConfig()
ConfigurationUtils.create_environment_file(config, ".env.example")

# Validate environment file
is_valid, issues = ConfigurationUtils.validate_environment_file(".env")
if not is_valid:
    print("Environment file issues:")
    for issue in issues:
        print(f"  - {issue}")

# Backup environment file
backup_path = ConfigurationUtils.backup_environment_file(".env")
print(f"Environment file backed up to: {backup_path}")
```

## Environment-Specific Settings

### Development Environment

```bash
FLASK_ENV=development
DEBUG=True
LOG_LEVEL=DEBUG
SESSION_COOKIE_SECURE=False
```

### Testing Environment

```bash
FLASK_ENV=testing
DEBUG=True
DATABASE_URL=sqlite:///:memory:
CSRF_ENABLED=False
```

### Production Environment

```bash
FLASK_ENV=production
DEBUG=False
LOG_LEVEL=INFO
SESSION_COOKIE_SECURE=True
CSRF_ENABLED=True
```

## Configuration Migration

### Deprecated Environment Variables

The system automatically migrates deprecated environment variables:

- `DATABASE_URI` → `DATABASE_URL`
- `DEEPSEEK_SEED` → `DEEPSEEK_RANDOM_SEED`
- `DEEPSEEK_TOKEN_LIMIT` → `DEEPSEEK_MAX_TOKENS`
- `NOTIFICATION_LEVEL` → `LOG_LEVEL`

### Migration Process

1. Old variables are detected during configuration loading
2. Values are automatically copied to new variable names
3. Warnings are logged about deprecated usage
4. Application continues with new variable names

## Configuration Loading Priority

1. **Instance environment file**: `instance/.env` (highest priority)
2. **Root environment file**: `.env`
3. **System environment variables**: OS environment
4. **Default values**: Built-in defaults

## Validation and Error Handling

### Automatic Validation

- **Secret key length**: Must be at least 32 characters
- **Database URL format**: Must be valid database URL
- **Port numbers**: Must be between 1-65535
- **File sizes**: Must be positive integers
- **Directory permissions**: Checks read/write access

### Error Handling

- **Missing required variables**: Raises ValueError
- **Invalid values**: Raises ValueError with descriptive message
- **Missing directories**: Automatically created if possible
- **Permission issues**: Logged as warnings

## Best Practices

### Security

1. **Never commit `.env` files** to version control
2. **Use strong secret keys** (at least 32 characters)
3. **Enable CSRF protection** in production
4. **Use secure cookies** in production
5. **Set appropriate session timeouts**

### Performance

1. **Configure database pooling** for production
2. **Set appropriate file size limits**
3. **Use efficient caching strategies**
4. **Configure proper logging levels**

### Maintenance

1. **Regularly backup configuration files**
2. **Validate configuration after changes**
3. **Monitor configuration health**
4. **Update deprecated variables**

## Troubleshooting

### Common Issues

1. **"SECRET_KEY must be at least 32 characters"**
   - Generate a longer secret key: `python -c "import secrets; print(secrets.token_hex(32))"`

2. **"DATABASE_URL is required"**
   - Set DATABASE_URL environment variable
   - Check .env file exists and is readable

3. **"Directory not writable"**
   - Check directory permissions
   - Ensure application has write access

4. **"API key not configured"**
   - Set HANDWRITING_OCR_API_KEY and/or DEEPSEEK_API_KEY
   - Application will run in limited mode without API keys

### Debug Mode

Enable debug logging to see configuration loading details:

```bash
LOG_LEVEL=DEBUG
```

### Health Check

Run configuration health check:

```python
from src.config.config_utils import ConfigurationUtils
from src.config.unified_config import UnifiedConfig

config = UnifiedConfig()
health = ConfigurationUtils.check_configuration_health(config)
print(health)
```

## API Reference

See the individual module documentation for detailed API reference:

- `src.config.unified_config`: Main configuration classes
- `src.config.config_utils`: Configuration utilities
- `tests.unit.config`: Configuration tests and examples