# Project Structure Documentation

**Updated:** January 4, 2025  
**Version:** Post-Cleanup Architecture  
**Status:** Production Ready

## Overview

This document describes the updated project structure after the comprehensive codebase cleanup and service consolidation. The architecture now follows a clean, modular design with well-defined service boundaries and clear separation of concerns.

## Root Directory Structure

```
exam-grader/
├── .kiro/                      # Kiro IDE configuration
│   ├── specs/                  # Feature specifications
│   └── steering/               # Development guidelines
├── backup_services/            # Backup of original services (for reference)
├── cache/                      # Application cache storage
│   ├── l3_disk/               # Level 3 disk cache
│   └── l4_hybrid/             # Level 4 hybrid cache
├── config/                     # Configuration files
│   ├── deployment_development.json
│   ├── deployment_production.json
│   ├── performance.json
│   ├── processing.json
│   └── security.json
├── docs/                       # Documentation (NEW)
│   ├── API_DOCUMENTATION.md
│   ├── PROJECT_STRUCTURE.md
│   └── SERVICE_DOCUMENTATION.md
├── instance/                   # Instance-specific files
│   ├── exam_grader.db         # SQLite database
│   └── secrets.enc            # Encrypted secrets
├── logs/                       # Application logs
│   ├── app.log                # Main application log
│   ├── processing.log         # Processing operations log
│   └── processing_errors.log  # Error-specific log
├── migrations/                 # Database migrations
│   ├── versions/              # Migration versions
│   └── *.py                   # Migration scripts
├── output/                     # Generated outputs
├── scripts/                    # Deployment and utility scripts
├── src/                        # Core application logic (RESTRUCTURED)
├── temp/                       # Temporary files
├── templates/                  # Report templates
├── tests/                      # Test suite
├── uploads/                    # File upload storage
├── utils/                      # Shared utilities
├── webapp/                     # Flask web application
├── .env                        # Environment variables
├── .env.local                  # Local environment overrides
├── requirements.txt            # Python dependencies
├── run_app.py                  # Application entry point
└── README.md                   # Project documentation
```

## Core Application Structure (`src/`)

### New Service Architecture

```
src/
├── api/                        # API layer
│   ├── endpoints/             # API endpoint definitions
│   ├── middleware/            # API middleware
│   └── responses/             # Response models
├── config/                     # Configuration management
│   ├── unified_config.py      # Main configuration manager
│   ├── environment.py         # Environment handling
│   └── validation.py          # Configuration validation
├── constants.py                # Application constants
├── database/                   # Database layer
│   ├── models.py              # SQLAlchemy models
│   ├── migrations/            # Database migrations
│   └── utils.py               # Database utilities
├── exceptions/                 # Custom exceptions
│   ├── base.py                # Base exception classes
│   ├── service_exceptions.py  # Service-specific exceptions
│   └── validation_exceptions.py # Validation exceptions
├── logging/                    # Logging configuration
│   ├── config.py              # Logging setup
│   ├── formatters.py          # Log formatters
│   └── handlers.py            # Custom log handlers
├── models/                     # Data models
│   ├── request_models.py      # Request data models
│   ├── response_models.py     # Response data models
│   └── validation_models.py   # Validation models
├── parsing/                    # Content parsing utilities
│   ├── document_parser.py     # Document parsing
│   ├── text_extractor.py      # Text extraction
│   └── format_detector.py     # Format detection
├── performance/                # Performance monitoring
│   ├── metrics.py             # Performance metrics
│   ├── profiler.py            # Performance profiling
│   └── optimization.py        # Performance optimization
├── security/                   # Security layer
│   ├── authentication.py      # User authentication
│   ├── authorization.py       # Access control
│   ├── encryption.py          # Data encryption
│   └── validation.py          # Input validation
├── services/                   # Business logic services (CONSOLIDATED)
│   ├── core/                  # Core business services
│   ├── monitoring/            # Monitoring services
│   ├── background/            # Background task services
│   ├── reporting/             # Reporting services
│   └── consolidated_*.py      # Legacy consolidated services
└── utils/                      # Internal utilities
    ├── file_utils.py          # File handling utilities
    ├── text_utils.py          # Text processing utilities
    └── validation_utils.py    # Validation utilities
```

### Service Layer Details

#### Core Services (`src/services/core/`)

```
core/
├── error_service.py            # Centralized error handling
│   ├── ErrorService class
│   ├── Error categorization and severity
│   ├── Recovery strategies
│   └── Error tracking and analytics
└── file_processing_service.py # Unified file processing
    ├── FileProcessingService class
    ├── Multi-format support
    ├── Fallback mechanisms
    └── Progress tracking
```

#### Monitoring Services (`src/services/monitoring/`)

```
monitoring/
└── monitoring_service.py       # System monitoring and health checks
    ├── MonitoringService class
    ├── Health check management
    ├── Performance metrics collection
    ├── Alert management
    └── Dashboard data aggregation
```

#### Background Services (`src/services/background/`)

```
background/
├── task_manager.py             # Background task execution
│   ├── TaskManager class
│   ├── Priority-based queuing
│   ├── Worker thread management
│   └── Task retry mechanisms
├── scheduler_service.py        # Task scheduling
│   ├── SchedulerService class
│   ├── APScheduler integration
│   ├── Cron-like scheduling
│   └── Job persistence
└── file_cleanup_service.py     # Automated file cleanup
    ├── FileCleanupService class
    ├── Retention policy management
    ├── Safe deletion with backup
    └── Storage monitoring
```

#### Reporting Services (`src/services/reporting/`)

```
reporting/
├── report_generator.py         # Multi-format report generation
│   ├── ReportGenerator class
│   ├── HTML, JSON, CSV support
│   ├── Template system
│   └── Chart generation
└── analytics_service.py        # Data analytics and insights
    ├── AnalyticsService class
    ├── Data aggregation
    ├── Trend analysis
    └── Statistical reporting
```

#### Consolidated Services (Legacy)

```
services/
├── consolidated_llm_service.py     # LLM operations
│   ├── ConsolidatedLLMService class
│   ├── Multiple provider support
│   ├── Connection pooling
│   ├── Rate limiting
│   └── Response caching
├── consolidated_ocr_service.py     # OCR processing
│   ├── ConsolidatedOCRService class
│   ├── Multiple OCR engines
│   ├── Image preprocessing
│   ├── Multi-language support
│   └── Confidence scoring
├── consolidated_grading_service.py # Automated grading
│   ├── ConsolidatedGradingService class
│   ├── Multiple grading strategies
│   ├── Partial credit assignment
│   ├── Feedback generation
│   └── Grade validation
├── consolidated_mapping_service.py # Answer mapping
│   ├── ConsolidatedMappingService class
│   ├── Answer extraction
│   ├── Question-answer pairing
│   └── Confidence scoring
├── enhanced_training_service.py    # LLM training capabilities
│   ├── EnhancedTrainingService class
│   ├── Flexible marking guide processing
│   ├── Model testing
│   └── Research report generation
└── file_processing_service.py      # Enhanced file processing
    ├── FileProcessingService class (Enhanced)
    ├── Fallback mechanisms
    ├── Content validation
    └── Quality scoring
```

## Web Application Structure (`webapp/`)

```
webapp/
├── api/                        # Web API endpoints
│   ├── auth_api.py            # Authentication API
│   ├── document_api.py        # Document processing API
│   ├── grading_api.py         # Grading API
│   ├── monitoring_api.py      # Monitoring API
│   └── training_api.py        # LLM training API
├── config/                     # Web application configuration
│   ├── flask_config.py        # Flask configuration
│   └── security_config.py     # Security configuration
├── logs/                       # Web application logs
├── output/                     # Generated web outputs
├── routes/                     # Blueprint-based routing
│   ├── admin_routes.py        # Administrative routes
│   ├── auth_routes.py         # Authentication routes
│   ├── main_routes.py         # Main application routes
│   ├── monitoring_routes.py   # Monitoring routes
│   └── processing_routes.py   # File processing routes
├── static/                     # Static assets
│   ├── css/                   # Stylesheets (Tailwind CSS)
│   ├── js/                    # JavaScript files
│   └── images/                # Image assets
├── templates/                  # Jinja2 templates
│   ├── auth/                  # Authentication templates
│   ├── dashboard/             # Dashboard templates
│   ├── processing/            # Processing templates
│   ├── reports/               # Report templates
│   ├── base.html              # Base template
│   └── layout.html            # Layout template
├── temp/                       # Temporary web files
├── types/                      # TypeScript type definitions
├── uploads/                    # Web upload storage
├── app.py                      # Main Flask application
├── app_factory.py             # Application factory pattern
├── error_handlers.py          # Global error handlers
├── forms.py                    # WTForms definitions
├── security.py                # Web security middleware
└── security_middleware.py     # Additional security middleware
```

## Shared Utilities (`utils/`)

```
utils/
├── cleanup/                    # Cleanup utilities
├── cache.py                    # Caching utilities
├── error_handler.py           # Error handling utilities
├── file_processor.py          # File processing utilities
├── guide_verification.py      # Guide verification utilities
├── input_sanitizer.py         # Input sanitization
├── loading_states.py          # Loading state management
├── logger.py                   # Logging utilities
├── rate_limiter.py            # Rate limiting utilities
└── startup_validator.py       # Application startup validation
```

## Test Structure (`tests/`)

```
tests/
├── e2e/                        # End-to-end tests
│   ├── test_complete_workflow.py
│   └── test_user_journey.py
├── integration/                # Integration tests
│   ├── test_service_integration.py
│   └── test_database_integration.py
├── performance/                # Performance tests
│   ├── test_load_performance.py
│   └── test_memory_usage.py
├── test_enhanced_file_processing.py
├── test_error_handling_system.py
├── test_file_processing_service.py
├── test_llm_training_basic.py
├── test_model_testing_service.py
├── test_monitoring_system.py
├── test_performance_monitoring.py
├── test_validation_service.py
└── run_all_tests.py
```

## Configuration Management

### Environment Variables (`.env`)

```bash
# Database Configuration
DATABASE_URL=sqlite:///instance/exam_grader.db

# API Keys
DEEPSEEK_API_KEY=your_deepseek_api_key
HANDWRITING_OCR_API_KEY=your_ocr_api_key
OPENAI_API_KEY=your_openai_api_key

# Security
SECRET_KEY=your_secret_key
SECRETS_MASTER_KEY=your_master_key

# Application Settings
DEBUG=False
HOST=127.0.0.1
PORT=5000
FLASK_ENV=production

# Service Configuration
MAX_FILE_SIZE_MB=50
UPLOAD_TIMEOUT_SECONDS=300
PROCESSING_TIMEOUT_SECONDS=600

# Logging
LOG_LEVEL=INFO
LOG_FILE_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5
```

### Configuration Files (`config/`)

#### `deployment_development.json`
```json
{
  "environment": "development",
  "debug": true,
  "database": {
    "echo": true,
    "pool_size": 5
  },
  "logging": {
    "level": "DEBUG",
    "console": true
  }
}
```

#### `deployment_production.json`
```json
{
  "environment": "production",
  "debug": false,
  "database": {
    "echo": false,
    "pool_size": 20
  },
  "logging": {
    "level": "INFO",
    "console": false
  }
}
```

## Key Modules and Responsibilities

### Core Application Entry Points

#### `run_app.py` - Main Application Entry Point
```python
"""
Main application entry point
- Environment setup
- Configuration loading
- Flask app creation and startup
- Error handling for startup failures
"""
```

#### `webapp/app_factory.py` - Application Factory
```python
"""
Flask application factory
- Clean app creation with configuration
- Blueprint registration
- Extension initialization
- Error handler setup
"""
```

### Service Initialization

#### Service Registry Pattern
```python
"""
Services are registered and initialized through a centralized registry:
- Dependency injection
- Health check registration
- Graceful startup and shutdown
- Service discovery
"""
```

### Database Models (`src/database/models.py`)

#### Key Models
- **User** - User authentication and profiles
- **Submission** - Student submission data
- **MarkingGuide** - Grading criteria and rubrics
- **GradingResult** - Automated grading results
- **LLMTrainingJob** - LLM training job tracking
- **LLMDocument** - Training document management
- **ProcessingJob** - File processing job tracking

### API Endpoints

#### Core API Routes
- `/api/health` - System health check
- `/api/status` - Detailed system status
- `/api/documents/upload` - Document upload
- `/api/grading/submit` - Grading submission
- `/api/llm/training/start` - Start LLM training
- `/api/monitoring/metrics` - System metrics

## Development Workflow

### Adding New Features

1. **Service Layer** - Implement business logic in appropriate service
2. **API Layer** - Create API endpoints in `webapp/api/`
3. **Web Routes** - Add web routes in `webapp/routes/`
4. **Templates** - Create UI templates in `webapp/templates/`
5. **Tests** - Add comprehensive tests in `tests/`
6. **Documentation** - Update relevant documentation

### Service Development Guidelines

1. **Single Responsibility** - Each service has one clear purpose
2. **Dependency Injection** - Services receive dependencies through constructor
3. **Error Handling** - Use centralized error service
4. **Logging** - Follow established logging patterns
5. **Configuration** - Use unified configuration system
6. **Testing** - Maintain high test coverage

### Database Changes

1. **Model Updates** - Modify models in `src/database/models.py`
2. **Migration Creation** - Create migration in `migrations/`
3. **Testing** - Test migration locally
4. **Service Updates** - Update related services
5. **API Updates** - Update API endpoints if needed

## Deployment Architecture

### Development Environment
```
Local Development
├── SQLite Database
├── File-based logging
├── Debug mode enabled
├── Hot reload enabled
└── Development configuration
```

### Production Environment
```
Production Deployment
├── Production database (SQLite/PostgreSQL)
├── Centralized logging
├── Performance monitoring
├── Security hardening
└── Production configuration
```

### Docker Support
```dockerfile
# Dockerfile structure
FROM python:3.8+
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "run_app.py"]
```

## Performance Considerations

### Service Performance
- **Initialization Time** - Average 1.27s for all services
- **Memory Usage** - Optimized through service consolidation
- **Response Time** - Sub-second for most operations
- **Throughput** - Handles concurrent requests efficiently

### Database Performance
- **Query Optimization** - All queries use SQLAlchemy ORM
- **Indexing** - Proper indexes on frequently queried columns
- **Connection Pooling** - Optimized connection pool settings
- **Caching** - Strategic caching for frequently accessed data

### File Processing Performance
- **Parallel Processing** - Background task processing
- **Caching** - Content caching for repeated operations
- **Streaming** - Large file streaming support
- **Cleanup** - Automated cleanup of temporary files

## Security Architecture

### Authentication and Authorization
- **Session Management** - Flask-Login integration
- **CSRF Protection** - Flask-WTF CSRF tokens
- **Input Validation** - Comprehensive input sanitization
- **Access Control** - Role-based access control

### File Security
- **Upload Validation** - File type and size validation
- **Secure Storage** - UUID-based file naming
- **Access Control** - Proper file permissions
- **Cleanup** - Automated cleanup of temporary files

### Configuration Security
- **Environment Variables** - Sensitive data in environment variables
- **Secrets Management** - Encrypted secrets storage
- **API Key Management** - Secure API key handling
- **Configuration Validation** - Startup configuration validation

## Monitoring and Observability

### Health Monitoring
- **Service Health** - Individual service health checks
- **System Health** - Overall system health status
- **Database Health** - Database connectivity and performance
- **External Services** - API service availability

### Performance Monitoring
- **Response Times** - API and service response times
- **Throughput** - Request processing rates
- **Error Rates** - Error frequency and categorization
- **Resource Usage** - CPU, memory, and disk usage

### Logging Strategy
- **Structured Logging** - JSON-formatted logs with metadata
- **Log Levels** - Appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- **Log Rotation** - Automatic log file rotation
- **Centralized Logging** - Unified logging configuration

## Future Considerations

### Scalability
- **Microservices** - Consider service separation for high-load components
- **Load Balancing** - Horizontal scaling preparation
- **Caching Strategy** - Redis/Memcached integration
- **Database Scaling** - Database sharding or replication

### Technology Upgrades
- **Python Version** - Regular Python version updates
- **Framework Updates** - Flask and dependency updates
- **Security Updates** - Regular security patch application
- **Performance Optimization** - Continuous performance improvements

### Feature Expansion
- **API Versioning** - Support for multiple API versions
- **Plugin Architecture** - Extensible plugin system
- **Multi-tenancy** - Support for multiple organizations
- **Advanced Analytics** - Enhanced reporting and analytics

---

**Document Version:** 2.0  
**Last Updated:** January 4, 2025  
**Status:** Current and Accurate  
**Maintainer:** Development Team