# Project Organization and Structure

## Root Directory Layout

```
exam-grader/
├── src/                    # Core application logic
├── webapp/                 # Flask web application
├── utils/                  # Shared utilities
├── tests/                  # Test suite
├── config/                 # Configuration files
├── docs/                   # Documentation
├── logs/                   # Application logs
├── instance/               # Instance-specific files (database, secrets)
├── uploads/                # File upload storage
├── temp/                   # Temporary files
├── output/                 # Generated outputs
├── cache/                  # Application cache
└── migrations/             # Database migrations
```

## Core Application (`src/`)

### Service Layer Architecture
- `src/services/`: Business logic services (60+ services)
  - AI processing services (OCR, LLM, grading, mapping)
  - Background task management
  - Monitoring and health checks
  - File processing and validation
  - Error handling and reporting

### Configuration Management
- `src/config/`: Centralized configuration system
  - `unified_config.py`: Main configuration manager
  - Environment-specific settings
  - Validation and type safety

### Database Layer
- `src/database/`: Database models and utilities
  - SQLAlchemy models with optimizations
  - Migration utilities
  - Progress tracking models

### Security Layer
- `src/security/`: Authentication and security
  - Session management
  - Input validation
  - Secrets management
  - Security middleware

### API Layer
- `src/api/`: Core API endpoints
  - Unified API structure
  - Response models
  - Error handling

## Web Application (`webapp/`)

### Flask Application Structure
- `app.py`: Clean main application file
- `app_factory.py`: Application factory pattern
- `error_handlers.py`: Global error handling
- `forms.py`: WTForms definitions
- `security.py`: Web security middleware

### Route Organization
- `webapp/routes/`: Blueprint-based routing
  - `main_routes.py`: Landing and dashboard
  - `auth_routes.py`: Authentication
  - `processing_routes.py`: File processing
  - `admin_routes.py`: Administrative functions
  - `monitoring_routes.py`: System monitoring

### API Endpoints
- `webapp/api/`: Web API layer
  - Document processing APIs
  - Status and monitoring APIs
  - Training and reporting APIs

### Frontend Assets
- `webapp/static/`: Static assets
  - `css/`: Tailwind CSS builds
  - `js/`: JavaScript modules
- `webapp/templates/`: Jinja2 templates
  - Modular template structure
  - Responsive design components

## Shared Utilities (`utils/`)

### Common Utilities
- File processing helpers
- Logging configuration
- Input validation
- Error handling
- Cache management
- Startup validation

## Testing Structure (`tests/`)

### Test Organization
- `tests/unit/`: Unit tests for individual components
- `tests/integration/`: Integration tests
- `tests/e2e/`: End-to-end tests
- `tests/performance/`: Performance tests
- Test markers: `unit`, `integration`, `api`, `database`, `services`

## Configuration Files (`config/`)

### Environment-Specific Configuration
- `deployment_development.json`: Development settings
- `deployment_production.json`: Production settings
- `performance.json`: Performance tuning
- `processing.json`: Processing parameters
- `security.json`: Security configuration

## File Storage Organization

### Upload Directories
- `uploads/submissions/`: Student submissions
- `uploads/marking_guides/`: Grading criteria
- `uploads/secure/`: Encrypted file storage
- `uploads/llm_training/`: Training data

### Temporary Storage
- `temp/`: Processing temporary files
- `cache/`: Application-level caching
- `output/`: Generated reports and results

## Naming Conventions

### Python Files
- **Services**: `*_service.py` (e.g., `file_processing_service.py`)
- **Models**: `*_models.py` or `models.py`
- **Routes**: `*_routes.py` (e.g., `auth_routes.py`)
- **APIs**: `*_api.py` (e.g., `monitoring_api.py`)
- **Utilities**: `*_utils.py` or descriptive names

### Database Models
- PascalCase class names (e.g., `MarkingGuide`, `GradingResult`)
- Snake_case table names (auto-generated)
- Descriptive relationship names

### Templates
- Snake_case filenames (e.g., `marking_guides.html`)
- Organized by feature/section
- Shared layouts in root template directory

## Import Patterns

### Absolute Imports
```python
from src.services.file_processing_service import FileProcessingService
from webapp.routes.auth_routes import auth_bp
from utils.logger import logger
```

### Relative Imports (within modules)
```python
from .base_service import BaseService
from ..models import User
```

## Code Organization Principles

### Service Layer
- Single responsibility principle
- Dependency injection
- Interface-based design
- Error handling and logging

### Route Organization
- Blueprint-based modular routing
- Clear separation of concerns
- Consistent error handling
- CSRF protection

### Configuration Management
- Environment-based configuration
- Type-safe configuration classes
- Validation at startup
- Hot-reload capabilities

### Database Design
- Normalized schema design
- Optimized queries
- Progress tracking
- Audit trails

## File Naming Standards

### Python Modules
- Lowercase with underscores
- Descriptive names
- Consistent suffixes (`_service`, `_routes`, `_api`)

### Templates
- Lowercase with underscores
- Feature-based organization
- Consistent naming patterns

### Static Assets
- Lowercase with hyphens for CSS/JS
- Organized by type and feature
- Minified versions for production

## Development Workflow

### Adding New Features
1. Create service in `src/services/`
2. Add routes in `webapp/routes/`
3. Create templates in `webapp/templates/`
4. Add tests in `tests/`
5. Update configuration if needed

### Database Changes
1. Update models in `src/database/models.py`
2. Create migration in `migrations/`
3. Test migration locally
4. Update related services

### API Development
1. Define models in `src/models/`
2. Implement service logic
3. Create API endpoints
4. Add comprehensive tests
5. Update documentation