"""
Vercel-specific configuration for the Flask app
"""

import os
from pathlib import Path

def setup_vercel_environment():
    """Set up environment variables for Vercel deployment."""
    
    # Set basic Flask configuration
    os.environ.setdefault('FLASK_ENV', 'production')
    os.environ.setdefault('FLASK_DEBUG', 'False')
    
    # Database configuration - use SQLite for simplicity
    project_root = Path(__file__).parent.parent
    db_path = project_root / 'instance' / 'exam_grader.db'
    os.environ.setdefault('DATABASE_URL', f'sqlite:///{db_path}')
    
    # Disable features that don't work well in serverless
    os.environ.setdefault('DISABLE_BACKGROUND_TASKS', 'True')
    os.environ.setdefault('DISABLE_FILE_CLEANUP', 'True')
    os.environ.setdefault('DISABLE_MONITORING', 'True')
    
    # Set reasonable defaults for serverless
    os.environ.setdefault('MAX_CONTENT_LENGTH', '16777216')  # 16MB
    os.environ.setdefault('UPLOAD_TIMEOUT', '60')  # 1 minute
    
    # Security settings
    os.environ.setdefault('SECRET_KEY', 'vercel-deployment-key-change-in-production')
    os.environ.setdefault('WTF_CSRF_TIME_LIMIT', '3600')  # 1 hour
    
    # API settings - these should be set as Vercel environment variables
    # os.environ.setdefault('OPENAI_API_KEY', '')
    # os.environ.setdefault('HANDWRITING_OCR_API_KEY', '')
    # os.environ.setdefault('DEEPSEEK_API_KEY', '')
    
    return True