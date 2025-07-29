"""
Application Factory - Clean Flask App Creation

This module provides a clean application factory pattern that replaces
the monolithic app file with a modular, maintainable structure.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_babel import Babel
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from src.config.unified_config import UnifiedConfig
from src.database.models import db, User

from src.security.secrets_manager import initialize_secrets
from src.services.realtime_service import socketio
from utils.logger import logger

def create_app(config_name: str = 'development') -> Flask:
    """
    Application factory function.
    
    Args:
        config_name: Configuration environment name
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__, template_folder='templates')
    
    # Load configuration
    config = UnifiedConfig()
    app.config.update(config.get_flask_config())
    
    # Initialize extensions
    _init_extensions(app)
    
    # Register blueprints
    _register_blueprints(app)
    
    # Set up error handlers
    _setup_error_handlers(app)
    
    # Initialize security
    _init_security(app)
    
    # Set up logging
    _setup_logging(app)
    
    # Initialize monitoring services
    _init_monitoring_services(app)
    
    logger.info(f"Flask application created successfully (config: {config_name})")
    
    return app

def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    # Database
    db.init_app(app)
    
    socketio.init_app(app, cors_allowed_origins="*")
    
    # CSRF Protection
    csrf = CSRFProtect(app)
    
    # Make CSRF token and user context available to all templates
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        from flask_login import current_user
        # Provide default service status to prevent template errors
        service_status = {
            'ocr_status': True,  # Default to online
            'llm_status': True   # Default to online
        }
        # Provide default storage stats to prevent template errors
        storage_stats = {
            'total_size_mb': 0,  # Default storage usage
            'max_size_mb': 1000  # Default max storage
        }
        return dict(
            csrf_token=generate_csrf(), 
            csrf_token_func=generate_csrf,
            service_status=service_status,
            storage_stats=storage_stats,
            current_user=current_user,
            app_version="1.0.0",
            current_year=2025
        )
    
    # Internationalization
    babel = Babel(app)
    
    # Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, user_id)

def _register_blueprints(app: Flask) -> None:
    """Register application blueprints."""
    # Main web routes
    from webapp.routes.main_routes import main_bp
    app.register_blueprint(main_bp)
    
    # Authentication routes (Flask-Login based)
    from webapp.routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp)
    
    # Processing routes
    from webapp.routes.processing_routes import processing_bp
    app.register_blueprint(processing_bp)
    
    # Guide processing routes
    from webapp.routes.guide_processing_routes import guide_processing_bp
    app.register_blueprint(guide_processing_bp)
    
    # Admin routes
    from webapp.routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp)
    
    # LLM Training routes
    from webapp.routes.llm_training_routes import llm_training_bp
    app.register_blueprint(llm_training_bp)
    
    # Monitoring routes
    from webapp.routes.monitoring_routes import monitoring_routes_bp
    app.register_blueprint(monitoring_routes_bp)
    
    # Monitoring API
    from webapp.api.monitoring_api import monitoring_bp
    app.register_blueprint(monitoring_bp)
    
    # Reporting routes
    from webapp.routes.reporting_routes import reporting_bp
    app.register_blueprint(reporting_bp)
    
    # Webapp API
    from webapp.api import unified_api_bp
    app.register_blueprint(unified_api_bp)
    
    # Unified API
    from src.api.unified_api import api
    app.register_blueprint(api)

def _setup_error_handlers(app: Flask) -> None:
    """Set up global error handlers."""
    from webapp.error_handlers import (
        handle_400, handle_403, handle_404, handle_413, 
        handle_500, handle_csrf_error
    )
    
    app.register_error_handler(400, handle_400)
    app.register_error_handler(403, handle_403)
    app.register_error_handler(404, handle_404)
    app.register_error_handler(413, handle_413)
    app.register_error_handler(500, handle_500)
    from flask_wtf.csrf import CSRFError
    app.register_error_handler(CSRFError, handle_csrf_error)

def _init_security(app: Flask) -> None:
    """Initialize security components."""
    try:
        initialize_secrets()
        logger.info("Security components initialized")
    except Exception as e:
        logger.error(f"Failed to initialize security: {e}")
        raise

def _setup_logging(app: Flask) -> None:
    """Set up application logging."""
    try:
        from src.config.logging_config import create_startup_summary
        from src.config.unified_config import UnifiedConfig
        config = UnifiedConfig()
        host = config.server.host
        port = config.server.port
        startup_msg = create_startup_summary(host, port)
        logger.info(startup_msg)
        logger.info("Logging configured successfully")
    except Exception as e:
        logger.warning(f"Logging setup failed: {e}")

def _init_monitoring_services(app: Flask) -> None:
    """Initialize monitoring services."""
    try:
        from src.services.monitoring_service_manager import monitoring_service_manager
        
        # Start monitoring services in a separate thread to avoid blocking app startup
        import threading
        
        def start_monitoring():
            try:
                success = monitoring_service_manager.start_all_services()
                if success:
                    logger.info("Monitoring services started successfully")
                else:
                    logger.warning("Some monitoring services failed to start")
            except Exception as e:
                logger.error(f"Error starting monitoring services: {e}")
        
        # Start monitoring services in background
        monitoring_thread = threading.Thread(target=start_monitoring, daemon=True)
        monitoring_thread.start()
        
        # Register cleanup function
        import atexit
        atexit.register(_cleanup_monitoring_services)
        
        logger.info("Monitoring services initialization initiated")
        
    except Exception as e:
        logger.error(f"Failed to initialize monitoring services: {e}")

def _cleanup_monitoring_services():
    """Clean up monitoring services on shutdown."""
    try:
        from src.services.monitoring_service_manager import monitoring_service_manager
        monitoring_service_manager.stop_all_services()
        logger.info("Monitoring services cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up monitoring services: {e}")

def create_database_tables(app: Flask) -> None:
    """Create database tables if they don't exist."""
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

def cleanup_services() -> None:
    """Clean up services on application shutdown."""
    try:
        # Stop monitoring services
        _cleanup_monitoring_services()
        
        # Stop file cleanup service
        try:
            from src.services.file_cleanup_service import FileCleanupService
            from src.config.unified_config import UnifiedConfig
            config = UnifiedConfig()
            cleanup_service = FileCleanupService(config)
            cleanup_service.stop()
        except Exception as e:
            logger.error(f"Error stopping file cleanup service: {e}")
        
        try:
            from flask import has_app_context
            if has_app_context():
                db.session.close()
            else:
                logger.info("No app context available for database cleanup")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
        
        logger.info("Services cleaned up successfully")
        
    except Exception as e:
        logger.error(f"Error during service cleanup: {e}")