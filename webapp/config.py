"""
Configuration settings for Exam Grader Flask Web Application
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'exam-grader-secret-key-change-in-production'
    
    # Application settings
    APP_NAME = 'Exam Grader'
    APP_VERSION = '2.0.0'
    
    # Server settings
    HOST = os.environ.get('FLASK_HOST') or '127.0.0.1'
    PORT = int(os.environ.get('FLASK_PORT') or 5000)
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 'yes', 'on']
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    ALLOWED_EXTENSIONS = {
        'pdf', 'docx', 'doc', 'txt',
        'jpg', 'jpeg', 'png', 'tiff', 'bmp', 'gif'
    }
    
    # Directory settings
    TEMP_DIR = BASE_DIR / 'temp'
    OUTPUT_DIR = BASE_DIR / 'output'
    STATIC_DIR = BASE_DIR / 'static'
    TEMPLATES_DIR = BASE_DIR / 'templates'
    
    # Session settings
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'exam_grader:'
    
    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # API settings
    API_RATE_LIMIT = "100 per hour"
    
    @staticmethod
    def init_app(app):
        """Initialize application with this configuration"""
        # Create necessary directories
        Config.UPLOAD_FOLDER.mkdir(exist_ok=True)
        Config.TEMP_DIR.mkdir(exist_ok=True)
        Config.OUTPUT_DIR.mkdir(exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Development-specific settings
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Disable caching in development

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production-specific settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-this-in-production'
    
    # Security headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Content-Security-Policy': "default-src 'self'"
    }
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Log to syslog in production
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    
    # Use in-memory database for testing
    TEMP_DIR = BASE_DIR / 'test_temp'
    OUTPUT_DIR = BASE_DIR / 'test_output'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])

# File type validation
def allowed_file(filename):
    """Check if file extension is allowed"""
    if not filename:
        return False
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# Utility functions
def get_file_size_mb(file_path):
    """Get file size in MB"""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except OSError:
        return 0.0

def create_directories():
    """Create necessary directories"""
    directories = [
        Config.UPLOAD_FOLDER,
        Config.TEMP_DIR,
        Config.OUTPUT_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# Initialize directories when module is imported
create_directories()
