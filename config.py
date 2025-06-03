"""Configuration module for the Exam Grader application."""
import os
from pathlib import Path
from typing import Optional, Union

# Application Configuration
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Generate secure secret key if not provided
def generate_secret_key():
    """Generate a cryptographically secure secret key."""
    import secrets
    return secrets.token_urlsafe(64)

# Validate and get secret key
def get_secret_key():
    """Get secret key from environment or generate secure one."""
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        logger = __import__('utils.logger', fromlist=['logger']).logger
        logger.warning("SECRET_KEY not set in environment. Generating temporary key.")
        logger.warning("For production, set SECRET_KEY environment variable to a secure random string.")
        return generate_secret_key()

    # Validate secret key strength
    if len(secret_key) < 32:
        logger = __import__('utils.logger', fromlist=['logger']).logger
        logger.error("SECRET_KEY is too short. Must be at least 32 characters.")
        raise ValueError("SECRET_KEY must be at least 32 characters long")

    return secret_key

SECRET_KEY = get_secret_key()

# Server Configuration
HOST = os.getenv('HOST', '127.0.0.1')
PORT = int(os.getenv('PORT', '5000'))

# File Upload Configuration
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '16'))

# Supported file formats
SUPPORTED_FORMATS = {'.pdf', '.docx', '.doc', '.txt', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}

# Directory Configuration
BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / 'temp'
OUTPUT_DIR = BASE_DIR / 'output'
UPLOAD_DIR = BASE_DIR / 'uploads'

# Create directories if they don't exist
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# API Configuration
HANDWRITING_OCR_API_KEY = os.getenv('HANDWRITING_OCR_API_KEY')
HANDWRITING_OCR_API_URL = os.getenv('HANDWRITING_OCR_API_URL', 'https://www.handwritingocr.com/api/v3')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# Storage Configuration
STORAGE_MAX_SIZE_MB = 500
STORAGE_EXPIRATION_DAYS = 30

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_FILE = 'exam_grader.log'


class Config:
    """Configuration class for the application."""

    def __init__(self):
        self.debug = DEBUG
        self.secret_key = SECRET_KEY
        self.host = HOST
        self.port = PORT
        self.max_content_length = MAX_CONTENT_LENGTH
        self.max_file_size_mb = MAX_FILE_SIZE_MB
        self.supported_formats = SUPPORTED_FORMATS
        self.temp_dir = TEMP_DIR
        self.output_dir = OUTPUT_DIR
        self.upload_dir = UPLOAD_DIR
        self.storage_max_size_mb = STORAGE_MAX_SIZE_MB
        self.storage_expiration_days = STORAGE_EXPIRATION_DAYS
        self.log_level = LOG_LEVEL
        self.log_file = LOG_FILE
        self.handwriting_ocr_api_key = HANDWRITING_OCR_API_KEY
        self.handwriting_ocr_api_url = HANDWRITING_OCR_API_URL
        self.deepseek_api_key = DEEPSEEK_API_KEY

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
