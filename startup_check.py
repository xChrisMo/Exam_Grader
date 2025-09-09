#!/usr/bin/env python3
"""
Startup Check Script for Exam Grader
Validates environment and dependencies before starting the application.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment_variables():
    """Check required environment variables."""
    logger.info("Checking environment variables...")
    
    required_vars = {
        'SECRET_KEY': 'Application secret key for security',
        'DEEPSEEK_API_KEY': 'DeepSeek API key for LLM services',
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.warning("Application may not function properly without these variables.")
    else:
        logger.info("All required environment variables are set.")
    
    # Check optional variables
    optional_vars = {
        'LLM_API_KEY': 'Alternative LLM API key (will use DEEPSEEK_API_KEY if not set)',
        'HANDWRITING_OCR_API_KEY': 'OCR API key for handwriting recognition',
        'DATABASE_URL': 'Database connection URL',
    }
    
    for var, description in optional_vars.items():
        if os.getenv(var):
            logger.info(f"Optional variable {var} is set.")
        else:
            logger.debug(f"Optional variable {var} is not set: {description}")

def check_python_dependencies():
    """Check Python package dependencies."""
    logger.info("Checking Python dependencies...")
    
    # Core dependencies that must be available
    core_deps = [
        'flask',
        'flask_wtf',
        'flask_login',
        'flask_sqlalchemy',
        'requests',
        'python_dotenv',
    ]
    
    # Optional dependencies
    optional_deps = {
        'PyPDF2': 'PDF text extraction',
        'pdfplumber': 'Advanced PDF text extraction',
        'python-docx': 'DOCX file processing',
        'docx2txt': 'Alternative DOCX processing',
        'striprtf': 'RTF file processing',
        'beautifulsoup4': 'HTML processing',
        'chardet': 'Character encoding detection',
    }
    
    missing_core = []
    for dep in core_deps:
        try:
            __import__(dep.replace('-', '_'))
            logger.info(f"✓ {dep} is available")
        except ImportError:
            missing_core.append(dep)
            logger.error(f"✗ {dep} is missing (REQUIRED)")
    
    if missing_core:
        logger.error(f"Missing core dependencies: {', '.join(missing_core)}")
        logger.error("Please install missing dependencies: pip install " + " ".join(missing_core))
        return False
    
    # Check optional dependencies
    available_optional = []
    missing_optional = []
    
    for dep, description in optional_deps.items():
        try:
            if dep == 'python-docx':
                import docx
            elif dep == 'beautifulsoup4':
                import bs4
            else:
                __import__(dep.replace('-', '_'))
            available_optional.append(dep)
            logger.info(f"✓ {dep} is available ({description})")
        except ImportError:
            missing_optional.append(dep)
            logger.warning(f"⚠ {dep} is not available ({description})")
    
    logger.info(f"Available optional dependencies: {', '.join(available_optional)}")
    if missing_optional:
        logger.warning(f"Missing optional dependencies: {', '.join(missing_optional)}")
        logger.warning("Some features may be limited without these dependencies.")
    
    return True

def check_system_commands():
    """Check system command dependencies."""
    logger.info("Checking system command dependencies...")
    
    system_commands = {
        'antiword': 'Legacy DOC file processing (optional)',
    }
    
    available_commands = []
    missing_commands = []
    
    for cmd, description in system_commands.items():
        try:
            result = subprocess.run(['which', cmd], capture_output=True, timeout=5)
            if result.returncode == 0:
                available_commands.append(cmd)
                logger.info(f"✓ {cmd} is available ({description})")
            else:
                missing_commands.append(cmd)
                logger.warning(f"⚠ {cmd} is not available ({description})")
        except Exception as e:
            missing_commands.append(cmd)
            logger.warning(f"⚠ {cmd} check failed: {e}")
    
    if available_commands:
        logger.info(f"Available system commands: {', '.join(available_commands)}")
    if missing_commands:
        logger.warning(f"Missing system commands: {', '.join(missing_commands)}")
        logger.warning("Some file processing features may use fallback methods.")

def check_directories():
    """Check and create required directories."""
    logger.info("Checking required directories...")
    
    required_dirs = [
        'uploads',
        'temp',
        'output',
        'logs',
        'instance',
    ]
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"✓ Created directory: {dir_name}")
            except Exception as e:
                logger.error(f"✗ Failed to create directory {dir_name}: {e}")
        else:
            logger.info(f"✓ Directory exists: {dir_name}")

def check_database():
    """Check database configuration."""
    logger.info("Checking database configuration...")
    
    db_url = os.getenv('DATABASE_URL', 'sqlite:///exam_grader.db')
    logger.info(f"Database URL: {db_url}")
    
    if db_url.startswith('sqlite:///'):
        db_file = db_url.replace('sqlite:///', '')
        db_path = Path(db_file)
        if not db_path.exists():
            logger.info(f"Database file {db_file} will be created on first run.")
        else:
            logger.info(f"✓ Database file exists: {db_file}")
    else:
        logger.info("Using external database (PostgreSQL/MySQL)")

def main():
    """Run all startup checks."""
    logger.info("Starting Exam Grader startup checks...")
    
    try:
        # Run all checks
        check_environment_variables()
        
        if not check_python_dependencies():
            logger.error("Core dependencies are missing. Exiting.")
            sys.exit(1)
        
        check_system_commands()
        check_directories()
        check_database()
        
        logger.info("✓ All startup checks completed successfully!")
        logger.info("The application should start without issues.")
        
    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
