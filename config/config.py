"""
Configuration management for the Exam Grader application.
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration."""
    
    # Core settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    APP_ENV = os.getenv('APP_ENV', 'production')
    
    # Directory settings
    TEMP_DIR = os.getenv('TEMP_DIR', 'temp')
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
    LOG_DIR = os.getenv('LOG_DIR', 'logs')
    
    # File processing settings
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '20').split('#')[0].strip())
    
    SUPPORTED_FORMATS = set(os.getenv('SUPPORTED_FORMATS', '.txt,.docx,.pdf,.jpg,.jpeg,.png,.tiff,.bmp,.gif').split(','))
    
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3').split('#')[0].strip())
    
    TIMEOUT_SECONDS = int(os.getenv('TIMEOUT_SECONDS', '300').split('#')[0].strip())
    
    # Web interface settings
    HOST = os.getenv('HOST', '127.0.0.1')
    PORT = int(os.getenv('PORT', '8501').split('#')[0].strip())
    ENABLE_CORS = os.getenv('ENABLE_CORS', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY')
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:8501,http://127.0.0.1:8501').split(',')
    
    # OCR settings
    OCR_API_KEY = os.getenv('HANDWRITING_OCR_API_KEY')
    OCR_API_URL = os.getenv('HANDWRITING_OCR_API_URL', 'https://www.handwritingocr.com/api/v3')
    OCR_DELETE_AFTER = int(os.getenv('HANDWRITING_OCR_DELETE_AFTER', '86400').split('#')[0].strip())
    
    # DeepSeek API settings
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
    
    # Processing settings
    SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', 0.8))
    OCR_CONFIDENCE_THRESHOLD = float(os.getenv('OCR_CONFIDENCE_THRESHOLD', 0.7))
    MAX_BATCH_SIZE = int(os.getenv('MAX_BATCH_SIZE', '10').split('#')[0].strip())
    
    # Performance settings
    WORKERS = int(os.getenv('WORKERS', '4').split('#')[0].strip())
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000').split('#')[0].strip())
    
    # Cache settings
    ENABLE_CACHE = os.getenv('ENABLE_CACHE', 'True').lower() == 'true'
    CACHE_TTL = int(os.getenv('CACHE_TTL', '3600').split('#')[0].strip())
    
    # LLM settings
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '1000').split('#')[0].strip())
    TEMPERATURE = float(os.getenv('TEMPERATURE', 0.0))
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return getattr(cls, key.upper(), default)
    
    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        """Return all configuration values as a dictionary."""
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith('_') and not callable(value)
        }

# Initialize configuration
config = Config()
