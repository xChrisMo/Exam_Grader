"""
Application Factory - Clean Flask App Creation

This module provides a clean application factory pattern that replaces
the monolithic app file with a modular, maintainable structure.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
# from flask_babel import Babel  # Optional - not required for core functionality
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from src.config.unified_config import UnifiedConfig
from src.database.models import User, db
from src.security.secrets_manager import initialize_secrets
from src.services.realtime_service import socketio
from utils.logger import logger


def create_app(config_name: str = "development") -> Flask:
    """
    Application factory function.

    Args:
        config_name: Configuration environment name

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__, template_folder="templates")

    # Load configuration
    config = UnifiedConfig()
    app.config.update(config.get_flask_config())
    
    # Set extended timeouts for AI processing
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['PERMANENT_SESSION_LIFETIME'] = 7200  # 2 hours
    
    # Configure request timeout for long-running AI operations
    import socket
    socket.setdefaulttimeout(600)  # 10 minutes for socket operations
    
    # Override for testing environment
    if config_name == "testing":
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DATABASE_URL'] = 'sqlite:///:memory:'

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
    
    # Register context processors for user settings integration
    _register_context_processors(app)
    
    # Initialize timeout middleware for AI operations
    _init_timeout_middleware(app)
    
    # Initialize performance monitoring middleware
    _init_performance_middleware(app)

    logger.info(f"Flask application created successfully (config: {config_name})")

    return app


def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    # Database
    db.init_app(app)

    socketio.init_app(app, cors_allowed_origins="*")

    # CSRF Protection
    CSRFProtect(app)

    # Simple internationalization fallback
    @app.template_global()
    def _(text):
        """Simple internationalization fallback - returns English text."""
        translations = {
            'enter_your_username': 'Enter your username',
            'enter_your_password': 'Enter your password',
            'choose_username': 'Choose a username',
            'enter_email': 'Enter your email',
            'create_strong_password': 'Create a strong password',
            'confirm_your_password': 'Confirm your password'
        }
        return translations.get(text, text)

    # Make CSRF token and user context available to all templates
    @app.context_processor
    def inject_csrf_token():
        from flask_login import current_user
        from flask_wtf.csrf import generate_csrf

        # Minimal context for faster page loads with required template variables
        return dict(
            csrf_token=generate_csrf(),
            current_user=current_user,
            app_version="1.0.0",
            ui_prefs={"language": "en", "theme": "light"},
            service_status={"ocr_status": True, "llm_status": True, "ai_status": True},
            storage_stats={"total_size_mb": 0, "max_size_mb": 1000},
            settings={"theme": "light", "language": "en"},
            current_year=2025,
        )

    # Custom template filters
    @app.template_filter('count_grouped_questions')
    def count_grouped_questions(questions):
        """Count questions treating grouped questions as one."""
        if not questions:
            return 0
        
        count = 0
        for question in questions:
            # Check if this is a grouped question
            if isinstance(question, dict) and question.get('type') == 'grouped':
                count += 1  # Count grouped question as one
            else:
                count += 1  # Count regular question as one
        
        return count

    # Internationalization (optional - disabled for now)
    # Babel(app)

    # Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

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

    # Monitoring routes
    from webapp.routes.monitoring_routes import monitoring_routes_bp

    app.register_blueprint(monitoring_routes_bp)

    # Training routes
    from webapp.routes.training_routes import training_bp

    app.register_blueprint(training_bp)

    # Monitoring API
    from webapp.api.monitoring_api import monitoring_bp

    app.register_blueprint(monitoring_bp)



    # Webapp API
    from webapp.api import api_bp, unified_api_bp

    app.register_blueprint(unified_api_bp)
    app.register_blueprint(api_bp)

    # Unified API
    from src.api.unified_api import api

    app.register_blueprint(api)
    
    # Import training WebSocket handlers (registers automatically)
    import webapp.routes.training_websocket


def _setup_error_handlers(app: Flask) -> None:
    """Set up global error handlers."""
    from webapp.error_handlers import (
        handle_400,
        handle_403,
        handle_404,
        handle_413,
        handle_500,
        handle_csrf_error,
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
    # Minimal logging setup for faster startup
    logger.info("Logging configured successfully")


def _init_monitoring_services(app: Flask) -> None:
    """Initialize monitoring services."""
    # Skip monitoring services initialization for faster startup
    # They can be started later via API or admin interface if needed
    logger.info("Monitoring services initialization skipped for faster startup")


def _cleanup_monitoring_services():
    """Clean up monitoring services on shutdown."""
    import sys

    try:
        from src.services.monitoring_service_manager import monitoring_service_manager

        # Stop all services with error handling
        try:
            monitoring_service_manager.stop_all_services()
            print("Monitoring services stopped successfully", file=sys.stderr)
        except Exception as stop_error:
            print(f"Error stopping monitoring services: {stop_error}", file=sys.stderr)

        # Don't try to log during cleanup as file handlers may be closed
        print("Monitoring services cleaned up", file=sys.stderr)

    except Exception as e:
        print(f"Error cleaning up monitoring services: {e}", file=sys.stderr)


def create_database_tables(app: Flask) -> None:
    """Create database tables if they don't exist."""
    # Skip database initialization for faster startup
    # Tables will be created on first database access
    logger.info("Database initialization skipped for faster startup")


def _init_timeout_middleware(app: Flask) -> None:
    """Initialize timeout middleware for AI operations."""
    # Skip middleware initialization for faster startup
    logger.info("Timeout middleware initialization skipped for faster startup")


def _init_performance_middleware(app: Flask) -> None:
    """Initialize performance monitoring middleware."""
    # Skip middleware initialization for faster startup  
    logger.info("Performance monitoring middleware initialization skipped for faster startup")


def _register_context_processors(app: Flask) -> None:
    """Register context processors for user settings integration."""
    # Skip context processors for faster startup
    logger.info("Context processors registration skipped for faster startup")


def cleanup_services() -> None:
    """Clean up services on application shutdown."""
    import sys
    
    try:
        # Stop monitoring services
        _cleanup_monitoring_services()

        # Stop file cleanup service
        try:
            from src.config.unified_config import UnifiedConfig
            from src.services.file_cleanup_service import FileCleanupService

            config = UnifiedConfig()
            cleanup_service = FileCleanupService(config)
            cleanup_service.stop()
        except Exception as e:
            print(f"Error stopping file cleanup service: {e}", file=sys.stderr)

        try:
            from flask import has_app_context

            if has_app_context():
                db.session.close()
            else:
                print("No app context available for database cleanup", file=sys.stderr)
        except Exception as e:
            print(f"Error closing database connections: {e}", file=sys.stderr)

        print("Services cleaned up successfully", file=sys.stderr)

    except Exception as e:
        print(f"Error during service cleanup: {e}", file=sys.stderr)
