"""Configuration module for the Exam Grader application."""
import os
from pathlib import Path
from typing import Optional, Union
from dotenv import load_dotenv

# Load environment variables from root .env file
load_dotenv('.env', override=True)

# Application Configuration
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(32).hex())
APP_VERSION = os.getenv('APP_VERSION', '2.0.0')
APP_ENV = os.getenv('APP_ENV', 'development')

# Server Configuration
HOST = os.getenv('HOST', '127.0.0.1')
PORT = int(os.getenv('PORT', '8501'))

# File Upload Configuration
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '20'))
MAX_CONTENT_LENGTH = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes

# Supported file formats from .env
SUPPORTED_FORMATS_STR = os.getenv('SUPPORTED_FORMATS', '.pdf,.docx,.doc,.txt,.jpg,.jpeg,.png,.bmp,.tiff,.gif')
SUPPORTED_FORMATS = set(format.strip() for format in SUPPORTED_FORMATS_STR.split(','))

# Directory Configuration
BASE_DIR = Path(__file__).parent
TEMP_DIR = Path(os.getenv('TEMP_DIR', 'temp'))
OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', 'output'))
LOG_DIR = Path(os.getenv('LOG_DIR', 'logs'))
UPLOAD_DIR = BASE_DIR / 'uploads'

# Create directories if they don't exist
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# API Configuration
HANDWRITING_OCR_API_KEY = os.getenv('HANDWRITING_OCR_API_KEY')
HANDWRITING_OCR_API_URL = os.getenv('HANDWRITING_OCR_API_URL', 'https://www.handwritingocr.com/api/v3')
HANDWRITING_OCR_DELETE_AFTER = int(os.getenv('HANDWRITING_OCR_DELETE_AFTER', '86400'))

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com')

# Processing Configuration
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
TIMEOUT_SECONDS = int(os.getenv('TIMEOUT_SECONDS', '300'))
SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.8'))
OCR_CONFIDENCE_THRESHOLD = float(os.getenv('OCR_CONFIDENCE_THRESHOLD', '0.7'))
MAX_BATCH_SIZE = int(os.getenv('MAX_BATCH_SIZE', '10'))

# Performance Settings
WORKERS = int(os.getenv('WORKERS', '4'))
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))

# Cache Configuration
ENABLE_CACHE = os.getenv('ENABLE_CACHE', 'True').lower() == 'true'
CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))

# LLM Configuration
MAX_TOKENS = int(os.getenv('MAX_TOKENS', '1000'))
TEMPERATURE = float(os.getenv('TEMPERATURE', '0.0'))

# Web Interface Configuration
ENABLE_CORS = os.getenv('ENABLE_CORS', 'False').lower() == 'true'
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:8501,http://127.0.0.1:8501').split(',')

# Storage Configuration
STORAGE_MAX_SIZE_MB = int(os.getenv('STORAGE_MAX_SIZE_MB', '500'))
STORAGE_EXPIRATION_DAYS = int(os.getenv('STORAGE_EXPIRATION_DAYS', '30'))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'exam_grader.log')


class Config:
    """Configuration class for the application."""

    def __init__(self):
        # Application Configuration
        self.debug = DEBUG
        self.secret_key = SECRET_KEY
        self.app_version = APP_VERSION
        self.app_env = APP_ENV

        # Server Configuration
        self.host = HOST
        self.port = PORT

        # File Upload Configuration
        self.max_content_length = MAX_CONTENT_LENGTH
        self.max_file_size_mb = MAX_FILE_SIZE_MB
        self.supported_formats = SUPPORTED_FORMATS

        # Directory Configuration
        self.temp_dir = TEMP_DIR
        self.output_dir = OUTPUT_DIR
        self.log_dir = LOG_DIR
        self.upload_dir = UPLOAD_DIR

        # API Configuration
        self.handwriting_ocr_api_key = HANDWRITING_OCR_API_KEY
        self.handwriting_ocr_api_url = HANDWRITING_OCR_API_URL
        self.handwriting_ocr_delete_after = HANDWRITING_OCR_DELETE_AFTER
        self.deepseek_api_key = DEEPSEEK_API_KEY
        self.deepseek_api_url = DEEPSEEK_API_URL

        # Processing Configuration
        self.max_retries = MAX_RETRIES
        self.timeout_seconds = TIMEOUT_SECONDS
        self.similarity_threshold = SIMILARITY_THRESHOLD
        self.ocr_confidence_threshold = OCR_CONFIDENCE_THRESHOLD
        self.max_batch_size = MAX_BATCH_SIZE

        # Performance Settings
        self.workers = WORKERS
        self.chunk_size = CHUNK_SIZE

        # Cache Configuration
        self.enable_cache = ENABLE_CACHE
        self.cache_ttl = CACHE_TTL

        # LLM Configuration
        self.max_tokens = MAX_TOKENS
        self.temperature = TEMPERATURE

        # Web Interface Configuration
        self.enable_cors = ENABLE_CORS
        self.allowed_origins = ALLOWED_ORIGINS

        # Storage Configuration
        self.storage_max_size_mb = STORAGE_MAX_SIZE_MB
        self.storage_expiration_days = STORAGE_EXPIRATION_DAYS

        # Logging Configuration
        self.log_level = LOG_LEVEL
        self.log_file = LOG_FILE

    @staticmethod
    def init_app(app):
        """Initialize the Flask application with this configuration."""
        config_instance = Config()
        app.config['SECRET_KEY'] = config_instance.secret_key
        app.config['DEBUG'] = config_instance.debug
        app.config['HOST'] = config_instance.host
        app.config['PORT'] = config_instance.port
        app.config['MAX_CONTENT_LENGTH'] = config_instance.max_content_length
        # Add other configuration variables as needed



def get_config():
    """Return the configuration class.

    Returns:
        Config: The configuration class for the application
    """
    return Config


def allowed_file(filename: Optional[str]) -> bool:
    """Check if a file has an allowed extension.

    Args:
        filename: The name of the file to check

    Returns:
        bool: True if the file extension is allowed, False otherwise
    """
    if not filename:
        return False
    try:
        ext = '.' + filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        return ext in SUPPORTED_FORMATS
    except (IndexError, AttributeError):
        return False
