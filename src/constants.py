"""
Application Constants

This module contains all hard-coded strings and configuration constants
used throughout the application to improve maintainability and consistency.
"""

# Environment variable names
ENV_FLASK_APP = "FLASK_APP"
ENV_FLASK_ENV = "FLASK_ENV"
ENV_HOST = "HOST"
ENV_PORT = "PORT"
ENV_DEBUG = "DEBUG"
ENV_DATABASE_URL = "DATABASE_URL"
ENV_SECRET_KEY = "SECRET_KEY"
ENV_HANDWRITING_OCR_API_KEY = "HANDWRITING_OCR_API_KEY"
ENV_DEEPSEEK_API_KEY = "DEEPSEEK_API_KEY"
ENV_LOG_LEVEL = "LOG_LEVEL"
ENV_PYTHONIOENCODING = "PYTHONIOENCODING"

# Default values
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "8501"
DEFAULT_DEBUG = "True"
DEFAULT_DATABASE_URL = "sqlite:///exam_grader.db"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_ENCODING = "utf-8"

# Flask application defaults
DEFAULT_FLASK_APP = "webapp.app"
DEFAULT_FLASK_ENV = "development"

# Database status values
DB_STATUS_PENDING = "pending"
DB_STATUS_PROCESSING = "processing"
DB_STATUS_COMPLETED = "completed"
DB_STATUS_FAILED = "failed"

# Training job statuses
TRAINING_STATUS_PENDING = "pending"
TRAINING_STATUS_PREPARING = "preparing"
TRAINING_STATUS_TRAINING = "training"
TRAINING_STATUS_EVALUATING = "evaluating"
TRAINING_STATUS_COMPLETED = "completed"
TRAINING_STATUS_FAILED = "failed"
TRAINING_STATUS_CANCELLED = "cancelled"

# File processing constants
SUPPORTED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"]
SUPPORTED_DOCUMENT_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt"]
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS + SUPPORTED_DOCUMENT_EXTENSIONS

# Directory names
DIR_TEMP = "temp"
DIR_OUTPUT = "output"
DIR_UPLOADS = "uploads"
DIR_LOGS = "logs"
DIR_INSTANCE = "instance"

# File naming patterns
UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

# API endpoints and URLs
DEEPSEEK_DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
HANDWRITING_OCR_DEFAULT_URL = "https://www.handwritingocr.com/api/v3"

# Model names
DEFAULT_LLM_MODEL = "deepseek-chat"

# Cache settings
DEFAULT_CACHE_SIZE = 10000
DEFAULT_CACHE_TTL = 86400  # 24 hours

# Rate limiting
DEFAULT_REQUESTS_PER_MINUTE = 60
DEFAULT_REQUESTS_PER_HOUR = 3600

# Retry settings
DEFAULT_MAX_RETRIES = 10
DEFAULT_RETRY_DELAY = 0.5
DEFAULT_MAX_BACKOFF_DELAY = 60.0

# File size limits
DEFAULT_MAX_FILE_SIZE_MB = 20
DEFAULT_STORAGE_MAX_SIZE_MB = 1000

# Session settings
DEFAULT_SESSION_TIMEOUT = 3600  # 1 hour

# Logging settings
DEFAULT_LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_LOG_BACKUP_COUNT = 5

# Performance settings
DEFAULT_CONNECTION_POOL_SIZE = 3
DEFAULT_DATABASE_POOL_SIZE = 10
DEFAULT_DATABASE_POOL_TIMEOUT = 30
DEFAULT_DATABASE_POOL_RECYCLE = 3600

# Security settings
MIN_SECRET_KEY_LENGTH = 32

# Processing settings
DEFAULT_CLEANUP_INTERVAL_HOURS = 24
DEFAULT_STORAGE_EXPIRATION_DAYS = 30

# Error messages
ERROR_NO_API_KEY = "API key not configured"
ERROR_SERVICE_UNAVAILABLE = "Service not available"
ERROR_PARSING_FAILED = "Response parsing failed"
ERROR_CONNECTION_FAILED = "Connection failed"
ERROR_RATE_LIMITED = "Rate limit exceeded"

# Success messages
SUCCESS_INITIALIZED = "Service initialized successfully"
SUCCESS_CLEANUP_COMPLETED = "Cleanup completed"
SUCCESS_DATABASE_CREATED = "Database tables created successfully"

# Status indicators
STATUS_ONLINE = "online"
STATUS_OFFLINE = "offline"
STATUS_DEGRADED = "degraded"
STATUS_HEALTHY = "healthy"
STATUS_UNHEALTHY = "unhealthy"

# User interface messages
UI_DEBUG_ON = "ON"
UI_DEBUG_OFF = "OFF"
UI_SHUTDOWN_MESSAGE = "Shutting down server..."
UI_STARTUP_MESSAGE = "Starting Exam Grader..."
UI_PRESS_CTRL_C = "Press Ctrl+C to stop the server"

# Command line responses
CLI_YES_RESPONSES = ["yes", "y"]
CLI_NO_RESPONSES = ["no", "n"]

# File operations
FILE_MODE_APPEND = "a"
FILE_MODE_READ = "r"
FILE_MODE_WRITE = "w"

# Encoding
ENCODING_UTF8 = "utf-8"

# Time formats
ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
SIMPLE_DATE_FORMAT = "%Y-%m-%d"
SIMPLE_TIME_FORMAT = "%H:%M:%S"
