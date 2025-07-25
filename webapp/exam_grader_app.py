#!/usr/bin/env python3
"""
Exam Grader Flask Web Application
Modern educational assessment platform with AI-powered grading capabilities.

This module provides the main Flask application with comprehensive features including:
- AI-powered exam grading
- OCR text extraction
- Real-time progress tracking
- Secure file handling
- User authentication and session management
"""

# Standard library imports
import atexit
import json
import os
import signal
import sys
import time
import uuid
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Third-party imports
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.exceptions import RequestEntityTooLarge
from flask_babel import Babel
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

# Load environment variables early
load_dotenv()

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Local imports
from src.config.logging_config import create_startup_summary
from src.services.realtime_service import socketio
from utils.error_handler import add_recent_activity


# Project-specific imports
try:
    # Configuration
    from src.config.unified_config import UnifiedConfig

    # Database
    from src.database import (
        DatabaseUtils,
        GradingResult,
        MarkingGuide,
        Submission,
        User,
        db,
    )

    # Security
    from src.security.flask_session_interface import SecureSessionInterface
    from src.security.secrets_manager import initialize_secrets, secrets_manager
    from src.security.session_manager import SecureSessionManager

    # Services
    from src.services.file_cleanup_service import FileCleanupService
    from src.services.grading_service import GradingService
    from src.services.llm_service import LLMService
    from src.services.mapping_service import MappingService
    from src.services.ocr_service import OCRService
    from src.services.training_service import training_service
    from src.services.report_service import report_service

    # Parsing
    from src.parsing.parse_guide import parse_marking_guide
    from src.parsing.parse_submission import parse_student_submission

    # Utilities
    from utils.input_sanitizer import sanitize_form_data, validate_file_upload
    from utils.loading_states import get_loading_state_for_template, loading_manager
    from utils.logger import logger

    # Authentication
    from webapp.auth import get_current_user, init_auth, login_required

    # Handle case where logger might be None
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)

except ImportError as e:
    # Use stderr for critical errors before logger is initialized
    sys.stderr.write(f"ERROR: Failed to import required modules: {e}\n")
    sys.exit(1)

# Initialize secrets manager early
try:
    initialize_secrets()
    logger.info("Secrets manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize secrets manager: {str(e)}")
    # Continue without secrets manager - will fall back to environment variables

# Temporary inline function to avoid import issues
def is_guide_in_use(guide_id):
    """Check if a marking guide is currently being used for processing."""
    try:
        from src.database.models import Submission, GradingResult
        from datetime import datetime, timedelta
        
        # Check for submissions currently being processed with this guide
        active_submissions = Submission.query.filter(
            Submission.marking_guide_id == guide_id,
            Submission.processing_status.in_(['processing', 'pending'])
        ).count()
        
        if active_submissions > 0:
            return True
            
        # Check for recent grading results (within last 5 minutes)
        recent_threshold = datetime.utcnow() - timedelta(minutes=5)
        recent_results = GradingResult.query.filter(
            GradingResult.marking_guide_id == guide_id,
            GradingResult.created_at >= recent_threshold
        ).count()
        
        return recent_results > 0
        
    except Exception as e:
        logger.error(f"Error checking if guide {guide_id} is in use: {str(e)}")
        return False

# Prevent multiple initialization
if 'app' not in globals():
    # Initialize Flask application
    # Configure static folder path relative to webapp directory
    app = Flask(__name__, static_folder='static', static_url_path='/static')

    # Apply security hardening for production
    try:
        from webapp.security_middleware import add_security_headers
        add_security_headers(app)
        logger.info("Security middleware applied successfully")
    except ImportError:
        logger.warning("Security middleware not found - this is normal in development")

    # Add caching headers for static files
    @app.after_request
    def add_cache_headers(response):
        """Add appropriate cache headers for static files."""
        if request.endpoint == 'static':
            # Cache static files for 1 hour
            response.cache_control.max_age = 3600
            response.cache_control.public = True
        elif request.path.startswith('/api/'):
            # Don't cache API responses
            response.cache_control.no_cache = True
            response.cache_control.no_store = True
            response.cache_control.must_revalidate = True
        return response

else:
    logger.info("Flask app already initialized, skipping re-initialization")

# Configure Babel settings
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'

# Define locale selector function
def get_locale():
    return session.get('locale', 'en')

# Initialize Babel with the new API for Flask 3.x
babel = Babel()
babel.init_app(app, locale_selector=get_locale)

# Load and validate configuration
try:
    config = UnifiedConfig()
    config.validate()
    app.config.update(config.get_flask_config())
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "dev-key-123"  # Fallback for development
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB file upload limit
    logger.info(f"Configuration loaded for environment: {config.environment}")
except Exception as e:
    logger.critical(f"Failed to load configuration: {str(e)}")
    sys.stderr.write(f"CRITICAL ERROR: Failed to load configuration: {e}\n")
    sys.exit(1)

# Initialize CSRF protection
try:
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Configure CSRF settings
    app.config.update(
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_CHECK_DEFAULT=True,
        WTF_CSRF_SSL_STRICT=False,  # Allow CSRF token with HTTP
        WTF_CSRF_TIME_LIMIT=86400,  # 24 hours
        WTF_CSRF_METHODS=['POST', 'PUT', 'PATCH', 'DELETE'],
        WTF_CSRF_HEADERS=['X-CSRFToken', 'X-CSRF-Token'],
        WTF_CSRF_FIELD_NAME='csrf_token',
        # Session-based CSRF tokens (more reliable than cookies)
        WTF_CSRF_SECRET_KEY=app.config.get('SECRET_KEY'),
        # Disable CSRF session protection to avoid conflicts with custom session interface
        WTF_CSRF_SESSION_KEY=None,
        # Add missing CSRF cookie configuration
        CSRF_COOKIE_NAME='csrf_token',
        CSRF_TIME_LIMIT=86400,
        CSRF_COOKIE_SECURE=False,  # Set to True in production with HTTPS
        CSRF_COOKIE_HTTPONLY=True,
        CSRF_COOKIE_SAMESITE='Lax'
    )

    logger.info(f"CSRF protection initialized with cookie: {app.config['CSRF_COOKIE_NAME']}, Timeout: {app.config['CSRF_TIME_LIMIT']}s")
except Exception as e:
    logger.critical(f"Failed to initialize CSRF protection: {str(e)}")
    sys.stderr.write(f"CRITICAL ERROR: Failed to initialize CSRF protection: {e}\n")
    sys.exit(1)

# Initialize comprehensive logging system
try:
    from src.logging.flask_integration import setup_flask_logging
    from src.exceptions.flask_error_integration import FlaskErrorIntegration
    
    # Setup comprehensive logging
    logging_integration = setup_flask_logging(
        app=app,
        logger_name='exam_grader_app',
        log_level=getattr(config, 'LOG_LEVEL', 'INFO'),
        log_requests=True,
        log_responses=True,
        log_performance=True,
        exclude_paths=['/health', '/favicon.ico', '/static']
    )
    
    # Setup error handling integration
    error_integration = FlaskErrorIntegration(app)
    
    logger.info("Comprehensive logging and error handling initialized")
except Exception as e:
    logger.error(f"Failed to initialize comprehensive logging: {str(e)}")
    # Don't exit - use fallback logging

# Initialize database
try:
    db.init_app(app)
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        logger.info("Database tables created/verified")
    
    logger.info("Database initialized")
except Exception as e:
    logger.critical(f"Failed to initialize database: {str(e)}")
    sys.stderr.write(f"CRITICAL ERROR: Failed to initialize database: {e}\n")
    sys.exit(1)

# Initialize enhanced security system
# Initialize session_manager as None first to ensure it's always defined
session_manager = None
try:
    # Initialize security configuration
    from src.security.security_config import init_security_config
    from src.security.security_middleware import SecurityMiddleware
    from src.security.auth_system import init_auth_manager
    from src.security.secure_file_service import init_secure_file_service
    
    # Load security configuration based on environment
    environment = os.getenv('FLASK_ENV', 'production')
    security_config = init_security_config(environment=environment)
    
    # Configure security settings using enhanced configuration
    app.config.update(
        SESSION_COOKIE_NAME='secure_session',
        SESSION_COOKIE_HTTPONLY=security_config.session.session_cookie_httponly,
        SESSION_COOKIE_SECURE=security_config.session.session_cookie_secure,
        SESSION_COOKIE_SAMESITE=security_config.session.session_cookie_samesite
    )
    
    # Initialize session manager with app's secret key
    session_manager = SecureSessionManager(
        app.config["SECRET_KEY"],
        security_config.session.session_timeout_minutes * 60
    )
    
    # Configure session interface using Flask's standard cookie settings
    app.session_interface = SecureSessionInterface(
        session_manager=session_manager,
        app_secret_key=app.config["SECRET_KEY"]
    )
    
    # Initialize enhanced authentication manager
    auth_manager = init_auth_manager(
        session_timeout=security_config.authentication.lockout_duration_minutes,
        max_failed_attempts=security_config.authentication.max_failed_attempts,
        lockout_duration=security_config.authentication.lockout_duration_minutes
    )
    
    # Initialize secure file service
    upload_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'secure')
    secure_file_service = init_secure_file_service(
        storage_path=upload_path,
        enable_malware_scan=security_config.file_upload.scan_for_malware
    )
    
    # Initialize security middleware
    security_middleware = SecurityMiddleware(app, security_config)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        # Validate session using custom session manager
        from flask import session
        
        session_user_id = session.get("user_id")
        session_sid = getattr(session, 'sid', None)

        # Check if user_id matches session and session is valid
        if not session_user_id or str(session_user_id) != str(user_id):
            return None

        if not session_sid:
            return None
            
        try:
            # Use the local session_manager instead of importing from webapp.auth
            if not session_manager:
                logger.error("Session manager not initialized in user_loader")
                return None
                
            secure_session = session_manager.get_session(session_sid)

            if not secure_session or secure_session.get('user_id') != session_user_id:
                return None

            user = User.query.get(user_id)
            return user
        except Exception as e:
            logger.error(f"Error in user_loader: {str(e)}")
            return None

    logger.info("Enhanced security system initialized")
except Exception as e:
    logger.critical(f"Failed to initialize enhanced security: {str(e)}")
    sys.stderr.write(f"CRITICAL ERROR: Failed to initialize enhanced security: {e}\n")
    sys.exit(1)

# Initialize performance optimization system
try:
    from src.performance.optimization_manager import init_performance_optimizer
    
    # Get Redis URL from environment or use None for memory-only caching
    redis_url = os.getenv('REDIS_URL')
    
    # Initialize performance optimizer
    performance_optimizer = init_performance_optimizer(app, redis_url)
    
    logger.info(f"Performance optimization system initialized (Redis: {'enabled' if redis_url else 'disabled'})")
except Exception as e:
    logger.error(f"Failed to initialize performance optimization: {str(e)}")
    # Don't exit - this is not critical for basic functionality

# Initialize authentication system
try:
    if session_manager is None:
        logger.warning("Session manager not initialized, creating fallback session manager")
        # Create a fallback session manager if security initialization failed
        session_manager = SecureSessionManager(
            app.config["SECRET_KEY"],
            3600  # 1 hour timeout as fallback
        )
    
    init_auth(app, session_manager)
    logger.info("Authentication system initialized")
except Exception as e:
    logger.critical(f"Failed to initialize authentication: {str(e)}")
    sys.stderr.write(f"CRITICAL ERROR: Failed to initialize authentication: {e}\n")
    sys.exit(1)

# Initialize SocketIO for real-time features
try:
    from src.services.realtime_service import init_realtime_service
    
    # Initialize real-time service (it will create its own WebSocket manager)
    init_realtime_service(app)
    logger.info("SocketIO real-time service with WebSocket manager initialized")
except Exception as e:
    logger.error(f"Failed to initialize SocketIO service: {str(e)}")
    # Don't exit - this is not critical for basic functionality

# Register optimized routes blueprint
try:
    from webapp.optimized_routes import optimized_bp
    app.register_blueprint(optimized_bp)
    logger.info("Optimized routes blueprint registered")
except Exception as e:
    logger.error(f"Failed to register optimized routes: {str(e)}")
    # Don't exit - this is not critical for basic functionality

# Register refactored AI processing routes blueprint
try:
    from webapp.refactored_routes import refactored_bp
    app.register_blueprint(refactored_bp)
    logger.info("Refactored AI processing routes blueprint registered")
    
    # Initialize progress tracker for refactored AI endpoints
    try:
        from src.api.refactored_ai_endpoints import init_progress_tracker
        init_progress_tracker(socketio)
        
        # Set WebSocket manager for progress tracker if available
        try:
            from src.services.progress_tracker import progress_tracker
            if 'websocket_manager' in locals():
                progress_tracker.websocket_manager = websocket_manager
                logger.info("Progress tracker WebSocket manager integration completed")
        except Exception as ws_error:
            logger.warning(f"Could not integrate WebSocket manager with progress tracker: {ws_error}")
        
        # Initialize persistent progress tracker
        try:
            from src.services.persistent_progress_tracker import persistent_progress_tracker
            if 'websocket_manager' in locals():
                persistent_progress_tracker.websocket_manager = websocket_manager
                logger.info("Persistent progress tracker WebSocket manager integration completed")
        except ImportError as import_error:
            logger.warning(f"Could not import persistent progress tracker: {import_error}")
        except Exception as persistent_error:
            logger.warning(f"Could not integrate WebSocket manager with persistent progress tracker: {persistent_error}")
            
        logger.info("Refactored AI progress tracker initialized")
    except Exception as tracker_error:
        logger.error(f"Failed to initialize refactored AI progress tracker: {tracker_error}")
        
except Exception as e:
    logger.error(f"Failed to register refactored routes: {str(e)}")
    # Don't exit - this is not critical for basic functionality

# Register upload endpoints blueprint for duplicate detection
try:
    from src.api.upload_endpoints import upload_bp, init_upload_services
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    
    # Initialize upload services
    init_upload_services(app)
    
    logger.info("Upload endpoints blueprint registered with duplicate detection and services initialized")
except Exception as e:
    logger.error(f"Failed to register upload endpoints: {str(e)}")
    # Don't exit - this is not critical for basic functionality

# Register enhanced processing endpoints blueprint
try:
    from src.api.enhanced_processing_endpoints import enhanced_processing_bp, init_enhanced_processing_services
    app.register_blueprint(enhanced_processing_bp)
    init_enhanced_processing_services(app)
    logger.info("Enhanced processing endpoints blueprint registered")
except Exception as e:
    logger.error(f"Failed to register enhanced processing endpoints: {str(e)}")
    # Don't exit - this is not critical for basic functionality

# Register basic API endpoints blueprint
try:
    from src.api.basic_endpoints import basic_api_bp, init_basic_api_services
    app.register_blueprint(basic_api_bp)
    init_basic_api_services(app)
    logger.info("Basic API endpoints blueprint registered")
except Exception as e:
    logger.error(f"Failed to register basic API endpoints: {str(e)}")
    # Don't exit - this is not critical for basic functionality

# Register unified API router with consolidated endpoints
try:
    from src.api.unified_router import init_unified_api
    from src.api.consolidated_endpoints import init_consolidated_services
    
    # Initialize unified API router
    init_unified_api(app)
    
    # Initialize consolidated services
    init_consolidated_services(app)
    
    logger.info("Unified API router registered with consolidated endpoints")
except Exception as e:
    logger.error(f"Failed to register unified API router: {str(e)}")
    # Don't exit - this is not critical for basic functionality

# Register LLM Training routes blueprint
try:
    from webapp.llm_training_routes import llm_training_bp
    app.register_blueprint(llm_training_bp)
    logger.info("LLM Training routes blueprint registered")
except Exception as e:
    logger.error(f"Failed to register LLM Training routes blueprint: {str(e)}")
    # Don't exit - this is not critical for basic functionality

# Register monitoring endpoints blueprint
try:
    from src.api.monitoring_endpoints import init_monitoring_endpoints
    init_monitoring_endpoints(app)
    logger.info("Monitoring endpoints blueprint registered")
except ImportError as e:
    logger.warning(f"Failed to import monitoring endpoints: {str(e)}")
except Exception as e:
    logger.error(f"Failed to register monitoring endpoints: {str(e)}")

# Context processor to make csrf_token available in all templates
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    try:
        # Generate the token and return it as a string
        token = generate_csrf()
        logger.debug(f"Generated CSRF token: {token[:8]}... for request {request.path}")
        return dict(csrf_token=token)
    except Exception as e:
        logger.error(f"Failed to inject CSRF token: {str(e)}")
        return dict(csrf_token=None)

# Route for monitoring dashboard
@app.route('/admin/monitoring')
def monitoring_dashboard():
    """Serve the monitoring dashboard for administrators."""
    try:
        # Check if user is authenticated and has admin role
        from flask import g, render_template, redirect, url_for, flash
        
        if not hasattr(g, 'current_user') or not g.current_user:
            flash('Please log in to access the monitoring dashboard.', 'warning')
            return redirect(url_for('login'))
        
        # Check admin role
        user_role = getattr(g.current_user, 'role', None)
        if not user_role or user_role.value not in ['admin', 'super_admin']:
            flash('Admin access required for monitoring dashboard.', 'error')
            return redirect(url_for('index'))
        
        return render_template('admin/monitoring_dashboard.html')
        
    except Exception as e:
        logger.error(f"Error serving monitoring dashboard: {str(e)}")
        flash('Error loading monitoring dashboard.', 'error')
        return redirect(url_for('index'))

# Route to get a fresh CSRF token via AJAX
@app.route('/get-csrf-token', methods=['GET'])
def get_csrf_token():
    from flask_wtf.csrf import generate_csrf
    try:
        token = generate_csrf()
        logger.debug(f"Generated fresh CSRF token via endpoint: {token[:8]}...")
        
        # Set response headers to prevent caching
        response = jsonify({'csrf_token': token})
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    except Exception as e:
        logger.error(f"Failed to generate CSRF token: {str(e)}")
        return jsonify({'error': 'Failed to generate token', 'details': str(e)}), 500

# Context processor to make session variables available in templates
@app.context_processor
def inject_session_variables():
    try:
        # Make session variables available in templates
        return dict(session=session)
    except Exception as e:
        logger.error(f"Failed to inject session variables: {str(e)}")
        return dict(session={})


def allowed_file(filename):
    """Check if file type is allowed."""
    if not filename:
        return False
    ext = "." + filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    return ext in config.files.supported_formats


# Initialize services (only once)
if 'services_initialized' not in globals():
    try:
        ocr_api_key = secrets_manager.get_secret("HANDWRITING_OCR_API_KEY")
        llm_api_key = secrets_manager.get_secret("DEEPSEEK_API_KEY")
        ocr_service = OCRService(api_key=ocr_api_key, enable_fallback=False) if ocr_api_key else None
        llm_service = LLMService(api_key=llm_api_key) if llm_api_key else None
        mapping_service = MappingService(llm_service=llm_service)
        grading_service = GradingService(
            llm_service=llm_service, mapping_service=mapping_service
        )

        file_cleanup_service = FileCleanupService(config)
        file_cleanup_service.start_scheduled_cleanup()

        # Initialize training and report services
        import asyncio
        try:
            # Initialize training service
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(training_service.initialize())
            loop.run_until_complete(report_service.initialize())
            loop.close()
            logger.info("Training and report services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize training services: {e}")

        services_initialized = True
        logger.info("Services initialized")
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
        logger.critical(f"Failed to initialize services: {str(e)}")
        sys.stderr.write(f"CRITICAL ERROR: Failed to initialize services: {e}\n")
        ocr_service = None
        llm_service = None
        mapping_service = None
else:
    logger.info("Services already initialized, skipping re-initialization")
    grading_service = None
    file_cleanup_service = None
    sys.exit(1)



# Utility functions


def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB."""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except OSError:
        return 0.0


@app.route("/optimized-dashboard")
@login_required
def optimized_dashboard():
    """Optimized AI processing dashboard route."""
    try:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            flash("Please log in to access the optimized dashboard.", "error")
            return redirect(url_for("auth.login"))

        # Get marking guides for selection
        marking_guides = MarkingGuide.query.filter_by(user_id=current_user.id).all()
        
        # Get submissions for processing
        submissions = Submission.query.filter_by(user_id=current_user.id).order_by(Submission.created_at.desc()).all()
        
        context = {
            "page_title": "Optimized AI Dashboard",
            "marking_guides": marking_guides,
            "submissions": submissions,
        }
        
        return render_template("optimized_dashboard.html", **context)
        
    except Exception as e:
        logger.error(f"Error loading optimized dashboard: {str(e)}")
        flash("Error loading optimized dashboard. Please try again.", "error")
        return render_template(
             "optimized_dashboard.html",
             page_title="Optimized AI Dashboard",
             marking_guides=[],
             submissions=[],
         )


def get_storage_stats():
    """Get storage statistics for temp and output directories."""
    try:
        temp_dir = str(config.files.temp_dir)
        output_dir = str(config.files.output_dir)
        
        temp_size = 0
        output_size = 0
        
        if os.path.exists(temp_dir):
            temp_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(temp_dir)
                for filename in filenames
            ) / (1024 * 1024)

        if os.path.exists(output_dir):
            output_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(output_dir)
                for filename in filenames
            ) / (1024 * 1024)

        max_file_size = config.files.max_file_size_mb

        return {
            "temp_size_mb": round(temp_size, 2),
            "output_size_mb": round(output_size, 2),
            "total_size_mb": round(temp_size + output_size, 2),
            "max_size_mb": max_file_size * 10,
        }
    except Exception as e:
        logger.error(f"Error calculating storage stats: {str(e)}")
        return {
            "temp_size_mb": 0.0,
            "output_size_mb": 0.0,
            "total_size_mb": 0.0,
            "max_size_mb": 160.0,
        }


# Service status cache
_service_status_cache = {}
_service_status_cache_time = 0
SERVICE_STATUS_CACHE_DURATION = 300  # 5 minutes


def _update_guide_uploaded_status(user_id):
    """Updates the session's 'guide_uploaded' status based on existing guides for the user."""
    from src.database import (
        MarkingGuide,
    )  # Import here to avoid circular dependency if models.py imports app

    remaining_guides = MarkingGuide.query.filter_by(user_id=user_id).first()
    if not remaining_guides:
        session["guide_uploaded"] = False
        session.modified = True
        logger.info(
            "No marking guides remaining for user. Setting guide_uploaded to False."
        )
    else:
        session["guide_uploaded"] = True
        session.modified = True
        logger.info("Marking guides exist for user. Setting guide_uploaded to True.")


def refresh_session_statistics(user_id):
    """Refresh all session statistics for the current user."""
    from src.database.models import Submission
    
    # Update submission statistics
    submission_stats = (
        db.session.query(
            db.func.count(Submission.id).label("total"),
            db.func.count(
                db.case((Submission.processing_status == "completed", 1))
            ).label("processed"),
        )
        .filter(Submission.user_id == user_id)
        .filter_by(archived=False)
        .first()
    )
    
    session["total_submissions"] = submission_stats.total if submission_stats else 0
    session["processed_submissions"] = submission_stats.processed if submission_stats else 0
    
    # Refresh other session statistics as needed
    # ...
    
    session.modified = True
    logger.info(f"Refreshed session statistics: Total: {session['total_submissions']}, Processed: {session['processed_submissions']}")



def get_service_status() -> Dict[str, bool]:
    """Check status of all services with caching."""
    global _service_status_cache, _service_status_cache_time

    current_time = time.time()
    if (
        current_time - _service_status_cache_time
    ) < SERVICE_STATUS_CACHE_DURATION and _service_status_cache:
        return _service_status_cache

    try:
        # Check service availability
        ocr_available = bool(ocr_service and ocr_service.api_key)
        llm_available = bool(llm_service and llm_service.api_key)

        # Check database
        storage_available = False
        try:
            from flask import has_app_context

            if has_app_context():
                User.query.count()
                storage_available = True
            else:
                with app.app_context():
                    User.query.count()
                    storage_available = True
        except Exception:
            storage_available = False

        # Cache result
        _service_status_cache = {
            "ocr_status": ocr_available,
            "llm_status": llm_available,
            "storage_status": storage_available,
            "config_status": True,
            "guide_storage_available": storage_available,
            "submission_storage_available": storage_available,
        }
        _service_status_cache_time = current_time
        return _service_status_cache

    except Exception as e:
        logger.error(f"Error checking service status: {str(e)}")
        return {
            "ocr_status": False,
            "llm_status": False,
            "storage_status": False,
            "config_status": True,
            "guide_storage_available": False,
            "submission_storage_available": False,
        }


# Error handlers
@app.errorhandler(413)
def too_large(e):
    flash(
        f"File too large. Maximum size is {config.files.max_file_size_mb}MB.", "error"
    )
    return redirect(request.url)


@app.errorhandler(404)
def not_found(e):
    return (
        render_template(
            "error.html",
            error_code=404,
            error_message="Page not found",
            service_status=get_service_status(),
        ),
        404,
    )


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")


    return (
        render_template(
            "error.html",
            error_code=500,
            error_message="Internal server error",
            service_status=get_service_status(),
        ),
        500,
    )


@app.errorhandler(400)
def bad_request(e):
    """Handle bad request errors."""
    logger.warning(f"Bad request: {str(e)} - URL: {request.url}")
    return (
        render_template(
            "error.html",
            error_code=400,
            error_message="Bad request. Please check your input and try again.",
        ),
        400,
    )


@app.errorhandler(403)
def forbidden(e):
    """Handle forbidden access errors."""
    logger.warning(f"Forbidden access: {str(e)} - URL: {request.url}")
    return (
        render_template(
            "error.html",
            error_code=403,
            error_message="Access forbidden. You don't have permission to access this resource.",
        ),
        403,
    )


# Rate limiting removed - no 429 error handler needed
# @app.errorhandler(429)
# def rate_limit_exceeded(e):
#     """Handle rate limit exceeded errors."""
#     logger.warning(f"Rate limit exceeded: {request.remote_addr}")
#     if request.is_json or request.path.startswith("/api/"):
#         return (
#             jsonify(
#                 {
#                     "error": "Rate limit exceeded",
#                     "message": "Too many requests. Please wait before trying again.",
#                     "status_code": 429,
#                 }
#             ),
#             429,
#         )
#     else:
#         flash("Too many requests. Please wait before trying again.", "warning")
#         return (
#             render_template(
#                 "error.html",
#                 error_code=429,
#                 error_message="Rate limit exceeded. Please wait before trying again.",
#             ),
#             429,
#         )


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Handle CSRF validation errors with improved error reporting."""
    logger.warning(f"CSRF validation error: {str(e)} - IP: {request.remote_addr}")
    
    # Enhanced debugging for CSRF issues
    csrf_token_from_form = request.form.get('csrf_token')
    csrf_token_from_header = request.headers.get('X-CSRFToken') or request.headers.get('X-CSRF-Token')
    
    logger.debug(f"CSRF error details - Path: {request.path}, Method: {request.method}")
    logger.debug(f"Form CSRF token: {csrf_token_from_form[:8] if csrf_token_from_form else 'None'}...")
    logger.debug(f"Header CSRF token: {csrf_token_from_header[:8] if csrf_token_from_header else 'None'}...")
    logger.debug(f"Session ID: {session.get('_id', 'None')}")

    # Generate a fresh CSRF token for the response
    try:
        from flask_wtf.csrf import generate_csrf
        fresh_token = generate_csrf()
        logger.debug(f"Generated fresh CSRF token: {fresh_token[:8]}...")
    except Exception as token_error:
        logger.error(f"Failed to generate fresh CSRF token: {str(token_error)}")
        fresh_token = None

    if request.is_json or request.path.startswith("/api/"):
        error_response = {
            "error": "CSRF token validation failed",
            "message": str(e),
            "status_code": 400,
            "csrf_token_refresh_required": True,
        }

        if fresh_token:
            error_response["fresh_csrf_token"] = fresh_token

        return jsonify(error_response), 400
    else:
        flash("Your form session has expired. Please refresh the page and try again.", "warning")
        
        # For login page, redirect back to login with fresh token
        if request.path == '/auth/login':
            return redirect(url_for('auth.login'))
        
        # For other pages, redirect to the same page
        return redirect(request.url)


# Template context processor
@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    try:
        loading_manager.auto_cleanup()
        loading_states = get_loading_state_for_template()
    except Exception:
        loading_states = {
            "loading_operations": {},
            "has_active_operations": False,
            "total_active_operations": 0,
        }

    # Get file configuration
    try:
        max_file_size = getattr(config.files, 'max_file_size_mb', 100) * 1024 * 1024  # Convert MB to bytes
        allowed_types = getattr(config, 'ALLOWED_FILE_TYPES', [
            ".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"
        ])
    except Exception:
        max_file_size = 100 * 1024 * 1024  # 100MB default
        allowed_types = [".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"]

    return {
        "app_version": "2.0.0",
        "current_year": datetime.now().year,
        "service_status": get_service_status(),
        "storage_stats": get_storage_stats(),
        "loading_states": loading_states,
        "max_file_size": max_file_size,
        "allowed_types": allowed_types,
    }


# Routes
@app.route("/landing")
def landing():
    """Public landing page."""
    try:
        # Check if user is authenticated
        current_user = get_current_user()
        is_authenticated = current_user is not None

        context = {
            "page_title": "Welcome to Exam Grader",
            "is_authenticated": is_authenticated,
            "current_user": current_user,
        }
        return render_template("landing.html", **context)
    except Exception as e:
        logger.error(f"Error loading landing page: {str(e)}")
        # Fallback to basic landing page
        return render_template(
            "landing.html",
            page_title="Welcome to Exam Grader",
            is_authenticated=False,
            current_user=None,
        )


@app.route("/")
def root():
    """Root route - redirect based on authentication status."""
    try:
        current_user = get_current_user()
        if current_user:
            # User is authenticated, redirect to dashboard
            return redirect(url_for("dashboard"))
        else:
            # User is not authenticated, show landing page
            return redirect(url_for("landing"))
    except Exception as e:
        logger.error(f"Error in root route: {str(e)}")
        # Fallback to landing page
        return redirect(url_for("landing"))


@app.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard route."""
    try:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            flash("Please log in to access the dashboard.", "error")
            return redirect(url_for("auth.login"))

        # Ensure CSRF token is refreshed
        from flask_wtf.csrf import generate_csrf
        csrf_token = generate_csrf()


        logger.info(f"Dashboard: session['guide_id'] is {session.get('guide_id')}")

        # Use session data for dashboard statistics if available
        from src.database.models import Submission, MarkingGuide, GradingResult
        
        # Always sync session counts with database for consistency
        total_submissions, processed_submissions = sync_session_submission_counts(current_user.id)

        logger.info(
            f"Dashboard: Using total_submissions: {total_submissions}, processed_submissions: {processed_submissions}"
        )

        # Ensure guide_uploaded status is accurate based on database
        _update_guide_uploaded_status(current_user.id)
        guide_uploaded = session.get("guide_uploaded", False)

        # Get recent submissions as activity (user-specific) - limited to 5
        recent_submissions = (
            Submission.query.filter_by(user_id=current_user.id)
            .order_by(Submission.created_at.desc())
            .limit(5)
            .all()
        )

        # Build activity list efficiently from database
        recent_activity = [
            {
                "type": "submission_upload",
                "message": f"Processed submission: {submission.filename}",
                "timestamp": submission.created_at.isoformat(),
                "icon": "document",
            }
            for submission in recent_submissions
        ]

        # If no database submissions, use session activity as fallback
        if not recent_activity:
            session_activity = session.get("recent_activity", [])
            recent_activity = session_activity[:5]  # Limit to 5 most recent
            logger.info(f"Using session activity: {len(recent_activity)} items")

        # Ensure session['submissions'] is updated with database submissions for UI visibility
        # Also ensure session counts match database counts for consistency
        session["submissions"] = [s.to_dict() for s in recent_submissions]
        
        # Force session counts to match database counts to prevent UI inconsistencies
        session["total_submissions"] = total_submissions
        session["processed_submissions"] = processed_submissions

        # Always calculate last score from database for accuracy
        # Get the most recent grading result score
        latest_result = (
            db.session.query(GradingResult.percentage)
            .join(Submission, GradingResult.submission_id == Submission.id)
            .filter(Submission.user_id == current_user.id)
            .order_by(GradingResult.created_at.desc())
            .first()
        )
        
        last_score = round(latest_result[0], 1) if latest_result and latest_result[0] else 0
        
        # Calculate average score from all grading results (user-specific)
        avg_result = (
            db.session.query(db.func.avg(GradingResult.percentage))
            .join(Submission, GradingResult.submission_id == Submission.id)
            .filter(Submission.user_id == current_user.id)
            .scalar()
        )
        avg_score = round(avg_result, 1) if avg_result else 0
        
        # Update session with calculated values
        session["last_score"] = last_score
        session["avg_score"] = avg_score
        session.modified = True

        service_status = get_service_status()
        context = {
            "page_title": "Dashboard",
            "total_submissions": total_submissions,
            "processed_submissions": processed_submissions,
            "guide_uploaded": guide_uploaded,
            "last_score": last_score,
            "avg_score": avg_score,
            "recent_activity": recent_activity,
            "submissions": [
                s.to_dict() for s in recent_submissions
            ],  # Convert to dict for template
            "service_status": service_status,  # Add service_status for dashboard
            "guide_storage_available": service_status.get(
                "guide_storage_available", False
            ),
            "submission_storage_available": service_status.get(
                "submission_storage_available", False
            ),
        }
        return render_template("dashboard.html", **context)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash("Error loading dashboard. Please try again.", "error")
        return render_template(
            "dashboard.html",
            page_title="Dashboard",
            total_submissions=0,
            processed_submissions=0,
            guide_uploaded=False,
            last_score=0,
            avg_score=0,
            recent_activity=[],
            submissions=[],
        )


@app.route("/upload-guide", methods=["GET", "POST"])
@login_required
def upload_guide():
    """Upload and process marking guide."""
    if request.method == "GET":
        from flask_wtf.csrf import generate_csrf
        return render_template("upload_guide.html", page_title="Upload Marking Guide", csrf_token=generate_csrf())


    # Log CSRF token information for debugging
    csrf_cookie = request.cookies.get('csrf_token', 'Not found')
    csrf_header = request.headers.get('X-CSRFToken', 'Not found')
    logger.info(f"UPLOAD GUIDE: CSRF Cookie: {csrf_cookie}, X-CSRFToken Header: {csrf_header}")

    try:
        # Import validation utilities
        from src.utils.validation_utils import ValidationUtils
        from src.services.content_validation_service import ContentValidationService
        
        if "guide_file" not in request.files:
            flash("No file selected.", "error")
            return redirect(request.url)

        file = request.files["guide_file"]
        
        # Comprehensive file validation
        file_validation = ValidationUtils.validate_file_upload(file)
        if not file_validation['success']:
            flash(file_validation['error'], "error")
            return redirect(request.url)
            
        # Get form data for metadata validation
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        

        
        # Validate metadata
        metadata_validation = ValidationUtils.validate_marking_guide_metadata(title, description)
        if not metadata_validation['success']:
            for issue in metadata_validation['issues']:
                flash(issue['message'], "error")
            return redirect(request.url)

        # Create temp directory if it doesn't exist
        temp_dir = str(config.files.temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(temp_dir, f"guide_{uuid.uuid4().hex}_{filename}")
        file.save(file_path)

        # Process guide with LLM extraction
        try:


            if "parse_marking_guide" in globals():
                guide, error_message = parse_marking_guide(file_path)
                if error_message:
                    flash(f"Error processing guide: {error_message}", "error")
                    os.remove(file_path)
                    return redirect(request.url)
                if guide:
                    # Extract questions and marks using LLM service
                    questions = []
                    total_marks = 0
                    extraction_method = "none"

                    try:


                        # Import and use the mapping service for LLM extraction
                        if mapping_service and guide.raw_content:

                            try:
                                logger.info("Starting LLM extraction from Word document...")
                                extraction_result = (
                                    mapping_service.extract_questions_and_total_marks(
                                        guide.raw_content
                                    )
                                )
        
                                if extraction_result and isinstance(extraction_result, dict):
                                    questions = extraction_result.get("questions", [])
                                    total_marks = extraction_result.get("total_marks", 0)
                                    extraction_method = extraction_result.get("extraction_method", "llm")
                                    
                                    if questions and len(questions) > 0:
                                        logger.info(f"✓ LLM extraction successful: {len(questions)} questions, {total_marks} total marks")
                                    else:
                                        logger.warning(f"⚠ LLM extraction completed but found no questions (document may not contain structured questions)")
                                        extraction_method = "llm_no_questions"
                                else:
                                    logger.warning("⚠ LLM extraction returned empty result")
                                    questions = []
                                    total_marks = 0
                                    extraction_method = "llm_empty"
                                    
                            except Exception as llm_error:
                                error_msg = str(llm_error)
                                if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                                    logger.error("✗ LLM extraction timed out - document may be too complex")
                                    flash("AI processing timed out. The document was uploaded but question extraction failed.", "warning")
                                else:
                                    logger.error(f"✗ LLM extraction failed: {error_msg}")
                                    flash("AI extraction failed - document uploaded successfully but questions need manual review", "warning")
                                
                                questions = []
                                total_marks = 0
                                extraction_method = "llm_error"
                        else:
                            if not mapping_service:
                                logger.warning("⚠ LLM service not available")
                                flash("AI service unavailable - document uploaded but questions need manual review", "warning")
                            if not guide.raw_content:
                                logger.warning("⚠ No text content extracted from Word document")
                                flash("Document appears empty - please check your Word document", "warning")
                            questions = []
                            total_marks = 0
                            extraction_method = "no_service"

                    except Exception as llm_error:
                        logger.error(f"LLM extraction failed: {str(llm_error)}")
                        logger.error(f"LLM extraction error traceback: ", exc_info=True)
                        # Continue with empty questions/marks rather than failing completely

                    guide_data = {
                        "raw_content": guide.raw_content,
                        "filename": filename,
                        "questions": questions,
                        "total_marks": total_marks,
                        "extraction_method": extraction_method,
                        "processed_at": datetime.now().isoformat(),
                    }
                else:
                    flash("Error: Could not process guide.", "error")
                    os.remove(file_path)
                    return redirect(request.url)
            else:
                # Create basic guide data structure if parse_marking_guide is not available
                guide_data = {
                    "filename": filename,
                    "questions": [],
                    "total_marks": 0,
                    "extraction_method": "none",
                    "processed_at": datetime.now().isoformat(),
                }
        except Exception as parse_error:
            logger.error(f"Error parsing guide: {str(parse_error)}")
            flash(f"Error parsing guide: {str(parse_error)}", "error")
            os.remove(file_path)
            return redirect(request.url)

        # Content validation and duplicate detection
        logger.info("🔍 Validating content and checking for duplicates...")
        try:
            content_validation_service = ContentValidationService()
            
            # Validate and check for duplicates
            validation_result = content_validation_service.validate_and_check_duplicates(
                file_path, 
                'marking_guide',
                user_id=get_current_user().id if get_current_user() else None,
                check_type='marking_guide'
            )
            
            if not validation_result['success']:
                logger.error(f"✗ Content validation failed: {validation_result.get('error', 'Unknown error')}")
                flash(f"Content validation failed: {validation_result['error']}", "error")
                os.remove(file_path)
                return redirect(request.url)
                
            # Check content quality
            content_quality = ValidationUtils.validate_content_quality(
                validation_result['text_content'],
                validation_result.get('confidence', 1.0)
            )
            
            # Handle duplicate detection based on policy
            duplicate_policy = 'warn'  # Can be made configurable
            duplicate_validation = ValidationUtils.validate_duplicate_policy(
                validation_result.get('duplicate_check', {}),
                duplicate_policy
            )
            
            if not duplicate_validation['success']:
                flash(duplicate_validation['message'], "error")
                os.remove(file_path)
                return redirect(request.url)
            elif duplicate_validation.get('warning'):
                flash(duplicate_validation['message'], "warning")
                
            # Show content quality warnings
            for warning in content_quality.get('warnings', []):
                flash(warning['message'], "warning")
                
        except Exception as validation_error:
            logger.error(f"Content validation error: {str(validation_error)}")
            flash(f"Content validation error: {str(validation_error)}", "error")
            os.remove(file_path)
            return redirect(request.url)

        # Store guide in database
        logger.info("Storing guide in database.")
        try:
            from src.database.models import MarkingGuide, User

            # Get current logged-in user
            current_user = get_current_user()
            if not current_user:
                flash("Error: User session expired. Please log in again.", "error")
                os.remove(file_path)
                return redirect(url_for("auth.login"))

            # Use validated metadata
            sanitized_data = metadata_validation['sanitized_data']
            guide_title = sanitized_data['title'] if sanitized_data['title'] else filename
            guide_description = sanitized_data['description']
            
            # Create enhanced description with extraction information
            questions_count = len(guide_data.get("questions", []))
            total_marks = guide_data.get("total_marks", 0.0)
            extraction_method = guide_data.get("extraction_method", "none")

            if extraction_method == "llm" and questions_count > 0:
                auto_description = f"LLM-extracted {questions_count} questions | Total marks: {total_marks}"
            elif extraction_method == "regex" and questions_count > 0:
                auto_description = f"Regex-extracted {questions_count} questions | Total marks: {total_marks}"
            else:
                auto_description = "No questions extracted"
                
            # Combine user description with auto description
            final_description = f"{guide_description} | {auto_description}" if guide_description else auto_description

            # Ensure we use the raw content from the parsed guide if available
            content_text = guide_data.get("raw_content") or validation_result.get('text_content', '')
            
            # Create marking guide record with content hash for duplicate detection
            marking_guide = MarkingGuide(
                user_id=current_user.id,
                title=guide_title,
                content_text=content_text,
                content_hash=validation_result['content_hash'],
                description=final_description,
                filename=filename,
                file_path=file_path,  # Keep the file path for now
                file_size=validation_result['file_size'],
                file_type=validation_result['file_type'],
                questions=guide_data.get("questions", []),
                total_marks=total_marks,
            )

            db.session.add(marking_guide)
            db.session.commit()
            guide_id = marking_guide.id

            # Store guide_id in session after successful upload
            session['guide_id'] = guide_id
            session.modified = True

            logger.info(f"Guide stored in database with ID: {guide_id}")
            _update_guide_uploaded_status(current_user.id)

        except Exception as storage_error:
            logger.error(f"Error storing guide in database: {str(storage_error)}")
            db.session.rollback()
            flash(f"Error storing guide: {str(storage_error)}", "error")
            os.remove(file_path)
            return redirect(request.url)

        logger.info(f"Guide uploaded successfully: {filename}")

        # Clean up temp file
        try:
            os.remove(file_path)
        except OSError as e:
            logger.warning(f"Could not remove temporary file {file_path}: {str(e)}")

        # Return appropriate response based on request type
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "status": "success",
                "success": True,
                "message": "Marking guide uploaded and processed successfully!"
            }), 200
        else:
            flash("Marking guide uploaded and processed successfully!", "success")
            return redirect(url_for("dashboard"))

    except Exception as e:
        logger.error(f"Error uploading guide: {str(e)}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "success": False,
                "error": "Error uploading guide. Please try again."
            }), 500
        else:
            flash("Error uploading guide. Please try again.", "error")
            return redirect(request.url)


@app.route("/upload-submission", methods=["GET", "POST"])
@login_required
def upload_submission():
    """Upload and process student submission."""
    from webapp.forms import UploadSubmissionForm
    
    # Check if guide is uploaded
    if not session.get('guide_uploaded'):
        return redirect(url_for('upload_guide'))
    
    # Check if a guide is selected for use
    if not session.get('guide_id'):
        flash('No marking guide selected. Please select a guide using "Use Guide" button first.', 'error')
        return redirect(url_for('dashboard'))
        
    form = UploadSubmissionForm()
    
    # If it's a GET request, render the template
    if request.method == 'GET':
        from flask_wtf.csrf import generate_csrf
        guide_id = session.get('guide_id')
        return render_template('upload_submission.html', form=form, guide_id=guide_id, csrf_token=generate_csrf())

    # For POST requests, check if it's an AJAX request or regular form submission
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    
    # Validate that a guide is selected for use (for both AJAX and form submissions)
    if not session.get('guide_id'):
        error_message = 'No marking guide selected. Please select a guide using "Use Guide" button first.'
        if is_ajax:
            return jsonify({"success": False, "error": error_message, "code": "NO_GUIDE_SELECTED"}), 400
        flash(error_message, 'error')
        return redirect(url_for('dashboard'))
    
    # For regular form submissions, validate the form
    if not is_ajax and form.validate_on_submit():
        file = form.file.data
        # Process file upload here using form data
        # ...
    
    # For AJAX requests or when form validation fails, process files manually
    try:
        logger.info(f"Upload submission endpoint called - Method: {request.method}, AJAX: {is_ajax}")
        logger.info(f"Request form data: {dict(request.form)}")
        logger.info(f"Request files: {list(request.files.keys())}")

        # Try multiple possible file input names
        files = request.files.getlist("submission_files") or request.files.getlist("file")
        if not files or all(f.filename == "" for f in files):
            if (
                request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.content_type == "application/json"
            ):
                return jsonify({"success": False, "error": "No files selected."}), 400
            flash("No files selected.", "error")
            return redirect(request.url)

        temp_dir = str(config.files.temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

        uploaded_count = 0
        failed_count = 0
        submissions_data = session.get("submissions", [])
        
        # Track results for multiple file processing
        processing_results = []
        file_errors = []

        # Import validation utilities
        from src.utils.validation_utils import ValidationUtils
        from src.services.content_validation_service import ContentValidationService
        
        # Get submission metadata from form and session
        student_name = request.form.get('student_name', '').strip()
        student_id = request.form.get('student_id', '').strip()
        # Get marking guide ID from session (the currently selected guide)
        marking_guide_id = session.get('guide_id', '').strip()
        
        # Validate submission metadata if provided
        if student_name or student_id or marking_guide_id:
            metadata_validation = ValidationUtils.validate_submission_metadata(
                student_name, student_id, marking_guide_id
            )
            if not metadata_validation['success']:
                error_messages = [issue['message'] for issue in metadata_validation['issues']]
                if (
                    request.headers.get("X-Requested-With") == "XMLHttpRequest"
                    or request.content_type == "application/json"
                ):
                    return jsonify({
                        "success": False, 
                        "error": "; ".join(error_messages)
                    }), 400
                for message in error_messages:
                    flash(message, "error")
                return redirect(request.url)

        for file in files:
            filename = secure_filename(file.filename) if file.filename else "unknown_file"
            
            # Comprehensive file validation
            file_validation = ValidationUtils.validate_file_upload(file)
            if not file_validation['success']:
                failed_count += 1
                file_errors.append({
                    'filename': filename,
                    'error': file_validation['error'],
                    'type': 'validation_error'
                })
                logger.warning(f"File validation failed for {filename}: {file_validation['error']}")
                continue

            file_path = os.path.join(
                temp_dir, f"submission_{uuid.uuid4().hex}_{filename}"
            )
            try:
                file.save(file_path)

                answers = {}
                raw_text = ""
                error = None

                if "parse_student_submission" in globals():
                    answers, raw_text, error = parse_student_submission(file_path)

                if error:
                    failed_count += 1
                    file_errors.append({
                        'filename': filename,
                        'error': f"Error processing {filename}: {error}",
                        'type': 'processing_error'
                    })
                    logger.error(f"Error processing {filename}: {error}")
                    os.remove(file_path)
                    continue
                elif not answers and not raw_text:
                    error = "No content could be extracted from the file."

                logger.info(
                    f"Before storing in session - filename: {filename}, raw_text length: {len(raw_text) if raw_text else 0}, answers keys: {list(answers.keys()) if answers else 'None'}, parse_submission error: {error}"
                )


                submission_id = str(uuid.uuid4())

                # Content validation and duplicate detection
                try:
                    content_validation_service = ContentValidationService()
                    
                    # Get file extension for validation
                    file_extension = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                    
                    # Debug logging
                    logger.info(f"Content validation - file: {filename}, extension: {file_extension}, raw_text length: {len(raw_text) if raw_text else 0}")
                    
                    # Validate and check for duplicates - pass extracted text if available
                    validation_result = content_validation_service.validate_and_check_duplicates(
                        file_path, 
                        file_extension,
                        user_id=get_current_user().id if get_current_user() else None,
                        check_type='submission',
                        marking_guide_id=marking_guide_id if marking_guide_id else None,
                        extracted_text=raw_text if raw_text else None
                    )
                    
                    logger.info(f"Content validation result: success={validation_result.get('success')}, error={validation_result.get('error')}")
                    
                    if not validation_result['success']:
                        if (
                            request.headers.get("X-Requested-With") == "XMLHttpRequest"
                            or request.content_type == "application/json"
                        ):
                            return jsonify({
                                "success": False,
                                "error": f"Content validation failed for {filename}: {validation_result['error']}"
                            }), 400
                        flash(f"Content validation failed for {filename}: {validation_result['error']}", "error")
                        failed_count += 1
                        os.remove(file_path)
                        continue
                        
                    # Check content quality - use extracted text if available, otherwise validation result text
                    text_for_quality_check = raw_text if raw_text else validation_result['text_content']
                    content_quality = ValidationUtils.validate_content_quality(
                        text_for_quality_check,
                        validation_result.get('confidence', 1.0)
                    )
                    
                    # Handle duplicate detection based on policy
                    duplicate_policy = 'warn'  # Can be made configurable
                    duplicate_validation = ValidationUtils.validate_duplicate_policy(
                        validation_result.get('duplicate_check', {}),
                        duplicate_policy
                    )
                    
                    if not duplicate_validation['success']:
                        if (
                            request.headers.get("X-Requested-With") == "XMLHttpRequest"
                            or request.content_type == "application/json"
                        ):
                            return jsonify({
                                "success": False,
                                "error": f"Duplicate detected for {filename}: {duplicate_validation['message']}"
                            }), 400
                        flash(f"Duplicate detected for {filename}: {duplicate_validation['message']}", "error")
                        failed_count += 1
                        os.remove(file_path)
                        continue
                    elif duplicate_validation.get('warning'):
                        logger.warning(f"Duplicate warning for {filename}: {duplicate_validation['message']}")
                        
                    # Log content quality warnings
                    for warning in content_quality.get('warnings', []):
                        logger.warning(f"Content quality warning for {filename}: {warning['message']}")
                        
                except Exception as validation_error:
                    logger.error(f"Content validation error for {filename}: {str(validation_error)}")
                    if (
                        request.headers.get("X-Requested-With") == "XMLHttpRequest"
                        or request.content_type == "application/json"
                    ):
                        return jsonify({
                            "success": False,
                            "error": f"Validation error for {filename}: {str(validation_error)}"
                        }), 400
                    flash(f"Validation error for {filename}: {str(validation_error)}", "error")
                    failed_count += 1
                    os.remove(file_path)
                    continue

                # Try to store in database first, fallback to session
                database_storage_success = False
                try:
                    current_user = get_current_user()
                    if current_user:
                        # Use validated metadata
                        sanitized_metadata = metadata_validation['sanitized_data'] if 'metadata_validation' in locals() else {
                            'student_name': student_name,
                            'student_id': student_id,
                            'marking_guide_id': marking_guide_id
                        }

                        # Store in database with all required fields including content hash
                        submission = Submission(
                            user_id=current_user.id,
                            student_name=sanitized_metadata['student_name'] or None,
                            student_id=sanitized_metadata['student_id'] or None,
                            marking_guide_id=sanitized_metadata['marking_guide_id'] or None,
                            filename=filename,
                            file_path=file_path,  # Store the path
                            file_size=validation_result['file_size'],
                            file_type=validation_result['file_type'],
                            content_text=validation_result['text_content'],
                            content_hash=validation_result['content_hash'],
                            answers=answers,
                            ocr_confidence=validation_result.get('confidence', 1.0),
                            processing_status="completed",
                            archived=False,  # Add archived field with default value
                        )
                        db.session.add(submission)
                        db.session.commit()
                        submission_id = str(submission.id)
                        database_storage_success = True
                        logger.info(
                            f"Stored submission in database with ID: {submission_id}"
                        )
                    else:
                        logger.error("No current user found - cannot save to database")
                        raise Exception("Authentication required for database storage")

                except Exception as storage_error:
                    logger.error(f"Database storage failed: {str(storage_error)}")
                    # Rollback any partial transaction
                    try:
                        db.session.rollback()
                    except:
                        pass
                    
                    # Return error response for failed database storage
                    if (
                        request.headers.get("X-Requested-With") == "XMLHttpRequest"
                        or request.content_type == "application/json"
                    ):
                        return jsonify({
                            "success": False,
                            "error": f"Failed to save submission to database: {str(storage_error)}"
                        }), 500
                    flash(f"Failed to save submission to database: {str(storage_error)}", "error")
                    failed_count += 1
                    os.remove(file_path)
                    continue
                
                # Only proceed if database storage was successful
                if not database_storage_success:
                    logger.error("Database storage was not successful")
                    failed_count += 1
                    os.remove(file_path)
                    continue

                uploaded_count += 1

                activity = session.get("recent_activity", [])
                activity.insert(
                    0,
                    {
                        "type": "submission_upload",
                        "message": f"Uploaded submission: {filename}",
                        "timestamp": datetime.now().isoformat(),
                        "icon": "upload",
                    },
                )
                session["recent_activity"] = activity[:10]

            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                flash(f"Error processing {filename}: {str(e)}", "error")
                failed_count += 1
            finally:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        logger.warning(
                            f"Could not remove temporary file {file_path}: {str(e)}"
                        )

        if uploaded_count > 0:
            flash(
                f"{uploaded_count} submission(s) uploaded and processed successfully!",
                "success",
            )
            logger.info(f"{uploaded_count} submission(s) uploaded successfully.")
            
            # Sync submission counts in session with database for consistency
            current_user = get_current_user()
            if current_user:
                sync_session_submission_counts(current_user.id)
            else:
                # Fallback to manual update if user not available
                current_total = session.get("total_submissions", 0)
                current_processed = session.get("processed_submissions", 0)
                session["total_submissions"] = current_total + uploaded_count
                session["processed_submissions"] = current_processed + uploaded_count  # All uploads are marked as processed
                session.modified = True
                logger.info(f"Updated session: total_submissions={session['total_submissions']}, processed_submissions={session['processed_submissions']}")
            
        if failed_count > 0:
            flash(
                f"{failed_count} submission(s) failed to upload or process. Check logs for details.",
                "error",
            )

        # Return JSON response for AJAX requests (batch processing)
        if (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.content_type == "application/json"
        ):
            response_data = {
                "status": "success" if uploaded_count > 0 else "partial_failure" if failed_count > 0 else "failure",
                "success": uploaded_count > 0,
                "uploaded_count": uploaded_count,
                "failed_count": failed_count,
                "total_files": len(files),
                "message": f"{uploaded_count} submission(s) uploaded successfully" + (f", {failed_count} failed" if failed_count > 0 else "")
            }
            
            # Include detailed error information for failed files
            if file_errors:
                response_data["errors"] = file_errors
                response_data["detailed_message"] = f"Successfully processed {uploaded_count} files. {failed_count} files failed: " + "; ".join([f"{err['filename']}: {err['error']}" for err in file_errors[:3]]) + ("..." if len(file_errors) > 3 else "")
            
            return jsonify(response_data), 200

        return redirect(url_for("dashboard"))

    except RequestEntityTooLarge:
        if (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.content_type == "application/json"
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"File too large. Max size is {config.max_file_size_mb}MB.",
                    }
                ),
                413,
            )
        flash(f"File too large. Max size is {config.max_file_size_mb}MB.", "error")
        return redirect(request.url)
    except Exception as e:
        logger.error(f"Error uploading submission: {str(e)}")
        if (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.content_type == "application/json"
        ):
            return jsonify({"success": False, "error": "Internal server error"}), 500
        flash("Error uploading submission. Please try again.", "error")
        return redirect(request.url)


@app.route("/submissions")
@login_required
def view_submissions():
    """View all submissions from both database and session."""
    try:
        submissions = []

        # Get current user
        current_user = get_current_user()

        # Get submissions from database first
        if current_user:
            try:
                from src.database.models import Submission

                db_submissions = (
                    Submission.query.filter_by(user_id=current_user.id)
                    .order_by(Submission.created_at.desc())
                    .all()
                )

                for submission in db_submissions:
                    submissions.append(
                        {
                            "id": str(submission.id),
                            "filename": submission.filename,
                            "uploaded_at": submission.created_at.isoformat(),
                            "processed": submission.processed,
                            "size_mb": (
                                round(submission.file_size / (1024 * 1024), 2)
                                if submission.file_size
                                else 0
                            ),
                            "source": "database",
                        }
                    )
                logger.info(f"Loaded {len(db_submissions)} submissions from database")
                # Update session with database submissions for UI visibility
                session["submissions"] = [s.to_dict() for s in db_submissions]
                # Sync session counts with database for consistency
                sync_session_submission_counts(current_user.id)
            except Exception as db_error:
                logger.warning(f"Error loading database submissions: {str(db_error)}")

        logger.info(f"Total submissions to display: {len(submissions)}")

        context = {"page_title": "Submissions", "submissions": submissions}
        return render_template("submissions.html", **context)
    except Exception as e:
        logger.error(f"Error viewing submissions: {str(e)}")
        flash("Error loading submissions. Please try again.", "error")
        return redirect(url_for("dashboard"))


def sync_session_submission_counts(current_user_id):
    """Synchronize session submission counts with database to prevent UI inconsistencies."""
    try:
        from src.database.models import Submission
        
        # Get accurate counts from database
        submission_stats = (
            db.session.query(
                db.func.count(Submission.id).label("total"),
                db.func.count(
                    db.case((Submission.processed == True, 1))
                ).label("processed"),
            )
            .filter(Submission.user_id == current_user_id)
            .filter_by(archived=False)
            .first()
        )
        
        total_submissions = submission_stats.total if submission_stats else 0
        processed_submissions = submission_stats.processed if submission_stats else 0
        
        # Update session with accurate counts
        session["total_submissions"] = total_submissions
        session["processed_submissions"] = processed_submissions
        session.modified = True
        
        logger.info(f"Synced session counts: total={total_submissions}, processed={processed_submissions}")
        return total_submissions, processed_submissions
        
    except Exception as e:
        logger.error(f"Error syncing session submission counts: {str(e)}")
        return session.get("total_submissions", 0), session.get("processed_submissions", 0)


def get_letter_grade(score):
    """Convert numerical score to letter grade."""
    if score >= 90:
        return 'A'
    elif score >= 80:
        return 'B'
    elif score >= 70:
        return 'C'
    elif score >= 60:
        return 'D'
    else:
        return 'F'

@app.route("/processing")
@login_required
def processing():
    """Show the processing page with real-time progress updates."""
    # Get progress_id from query parameter or session
    progress_id = request.args.get('progress_id') or session.get('current_progress_id')
    
    if not progress_id:
        flash('No processing task found.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('processing.html')


@app.route("/unified-processing")
@login_required
def unified_processing():
    """Show the unified AI processing page with enhanced real-time progress tracking."""
    # Get progress_id from query parameter or session
    progress_id = request.args.get('progress_id') or session.get('current_progress_id')
    
    if not progress_id:
        flash('No processing task found.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('unified_processing.html')


@app.route("/enhanced-processing")
@login_required
def enhanced_processing():
    """Show the enhanced LLM-driven processing pipeline interface."""
    from flask_wtf.csrf import generate_csrf
    return render_template(
        'enhanced_processing.html', 
        page_title="Enhanced AI Processing Pipeline",
        csrf_token=generate_csrf()
    )


@app.route("/results")
@login_required
def view_results():
    """View grading results."""
    try:
        # Check if grouped view is requested
        grouped_view = request.args.get('grouped', 'false').lower() == 'true'
        
        # Add timestamp for data freshness tracking
        from src.database.models import GradingResult, MarkingGuide
        

        last_progress_id = session.get("last_grading_progress_id")
        last_grading_result = session.get('last_grading_result')
        guide_id = session.get('guide_id')
        
        logger.info(f"view_results: last_progress_id from session: {last_progress_id}")
        logger.info(f"view_results: session['last_grading_result'] is {last_grading_result}")
        logger.info(f"view_results: session['guide_id'] is {guide_id}")
        logger.info(f"view_results: grouped_view requested: {grouped_view}")
        
        # If last_grading_result is None, set it to True if we have a progress_id
        # This helps recover from situations where the session variable wasn't properly set
        if last_progress_id and last_grading_result is None:
            logger.info(f"Setting session['last_grading_result'] to True since we have a progress_id")
            session['last_grading_result'] = True
            session.modified = True
        
        # Handle grouped view
        if grouped_view:
            return render_grouped_results()
        
        # Allow access to results page even if no recent grading results, the template will handle the display.

        # Get grading results from database for the last processed batch
        guide_id = session.get('guide_id')
        if not guide_id:
            flash('No marking guide selected. Please upload or select a guide first.', 'warning')
            return redirect(url_for('dashboard'))

        # Get the latest results from the database
        # This ensures we always have the most up-to-date data
        # First try to get results for the specific progress_id
        all_grading_results = []
        if last_progress_id:
            all_grading_results = GradingResult.query.filter_by(
                progress_id=last_progress_id, marking_guide_id=guide_id
            ).order_by(GradingResult.updated_at.desc()).all()

        # If no results found with progress_id, get all results for the current guide
        if not all_grading_results:
            logger.info(f"No results found for progress_id {last_progress_id}, fetching all results for guide {guide_id}")
            all_grading_results = GradingResult.query.filter_by(
                marking_guide_id=guide_id
            ).order_by(GradingResult.updated_at.desc()).all()
        
        # Log the number of results found
        logger.info(
            f"view_results: Found {len(all_grading_results)} grading results for progress_id: {last_progress_id}"
        )
        # If no grading results, the template will display a message.

        # Record the timestamp when data was fetched
        data_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        grading_results = {}
        skipped_results = 0
        duplicate_results = 0

        for res in all_grading_results:
            # Check if submission exists
            if not res.submission:
                logger.warning(f"Skipping grading result {res.id} - no associated submission found")
                skipped_results += 1
                continue
            
            # Only keep the latest result per submission_id to avoid duplicates
            if res.submission_id in grading_results:
                # Compare timestamps and keep the more recent one
                existing_timestamp = grading_results[res.submission_id].get("updated_at", "")
                current_timestamp = res.updated_at.isoformat() if res.updated_at else ""
                
                if current_timestamp > existing_timestamp:
                    # Current result is newer, replace the existing one
                    duplicate_results += 1
                else:
                    # Existing result is newer or same, skip current one
                    duplicate_results += 1
                    continue
                
            grading_results[res.submission_id] = {
                "filename": res.submission.filename if res.submission else "Unknown",
                "status": "completed",
                "timestamp": res.created_at.isoformat() if res.created_at else "",
                "updated_at": res.updated_at.isoformat() if res.updated_at else "",
                "score": res.score,
                "percentage": res.percentage,
                "max_score": res.max_score,
                "feedback": res.feedback,
                "criteria_scores": res.detailed_feedback,
                "mappings": [],  # Mappings are part of the Mapping model, not directly in GradingResult
                "metadata": {},
            }
        
        logger.info(f"view_results: Processed {len(grading_results)} unique results, skipped {skipped_results} due to missing submissions, found {duplicate_results} duplicate results")

        # Calculate batch summary
        total_submissions = len(grading_results)
        scores = [result.get("score", 0) for result in grading_results.values()]
        avg_score = sum(scores) / len(scores) if scores else 0
        highest_score = max(scores) if scores else 0
        lowest_score = min(scores) if scores else 0

        # Grade distribution - calculate based on percentages
        grade_distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for submission_id, result in grading_results.items():
            score = result.get("score", 0)
            max_score = result.get("max_score", 100)
            percentage = result.get("percentage", 0)
            if percentage == 0 and max_score > 0:
                percentage = (score / max_score) * 100
            letter = get_letter_grade(percentage)[0]  # Get first character (A, B, C, D, F)
            if letter in grade_distribution:
                grade_distribution[letter] += 1

        # Format results for template
        results_list = []
        for submission_id, result in grading_results.items():
            # Get all grading results for this submission to count actual questions
            submission_grading_results = GradingResult.query.filter_by(
                submission_id=submission_id,
                marking_guide_id=guide_id
            ).all()
            
            # Extract detailed feedback data and build criteria_scores from all grading results
            criteria_scores = []
            strengths = []
            weaknesses = []
            suggestions = []
            total_score = 0
            total_max_score = 0
            
            # Process each grading result (one per question)
            for gr in submission_grading_results:
                detailed_feedback = gr.detailed_feedback or {}
                
                # Calculate percentage for this question
                points_earned = gr.score or 0
                points_possible = gr.max_score or 1
                percentage = (points_earned / points_possible * 100) if points_possible > 0 else 0
                
                # Get mapping information if available
                mapping = gr.mapping
                question_text = mapping.guide_question_text if mapping else "Question"
                student_answer = mapping.submission_answer if mapping else ""
                
                criteria_scores.append({
                    "question_id": mapping.guide_question_id if mapping else f"q_{len(criteria_scores)+1}",
                    "description": question_text,
                    "points_earned": points_earned,
                    "points_possible": points_possible,
                    "percentage": round(percentage, 1),
                    "feedback": gr.feedback or "",
                    "detailed_feedback": detailed_feedback,
                    "guide_answer": "",
                    "student_answer": student_answer,
                    "match_score": mapping.match_score if mapping else 0,
                    "match_reason": mapping.match_reason if mapping else ""
                })
                
                total_score += points_earned
                total_max_score += points_possible
                
                # Extract strengths, weaknesses, suggestions from detailed_feedback
                if isinstance(detailed_feedback, dict):
                    if "strengths" in detailed_feedback:
                        strengths.extend(detailed_feedback.get("strengths", []))
                    if "weaknesses" in detailed_feedback:
                        weaknesses.extend(detailed_feedback.get("weaknesses", []))
                    if "suggestions" in detailed_feedback:
                        suggestions.extend(detailed_feedback.get("suggestions", []))
                    elif "improvement_suggestions" in detailed_feedback:
                        suggestions.extend(detailed_feedback.get("improvement_suggestions", []))
            
            # Remove duplicates from feedback lists
            strengths = list(set(strengths))
            weaknesses = list(set(weaknesses))
            suggestions = list(set(suggestions))
            
            # If no criteria_scores found, create a default one
            if not criteria_scores:
                criteria_scores = [{
                    "question_id": "default",
                    "description": "Overall Assessment",
                    "points_earned": result.get("score", 0),
                    "points_possible": result.get("max_score", 100),
                    "feedback": result.get("feedback", "No detailed feedback available"),
                    "detailed_feedback": {},
                    "guide_answer": "",
                    "student_answer": "",
                    "match_score": 0,
                    "match_reason": ""
                }]
                total_score = result.get("score", 0)
                total_max_score = result.get("max_score", 100)
            
            # Update the result with corrected totals
            if total_max_score > 0:
                corrected_percentage = (total_score / total_max_score) * 100
                result["score"] = total_score
                result["max_score"] = total_max_score
                result["percentage"] = corrected_percentage
            
            # Calculate letter grade based on percentage, not raw score
            score = result.get("score", 0)
            max_score = result.get("max_score", 100)
            # Calculate percentage if not already stored or if stored percentage is 0
            percentage = result.get("percentage", 0)
            if percentage == 0 and max_score > 0:
                percentage = (score / max_score) * 100
            letter_grade = get_letter_grade(percentage)
            
            results_list.append(
                {
                    "submission_id": submission_id,
                    "filename": result.get("filename", "Unknown"),
                    "score": percentage,  # Use calculated percentage for display
                    "raw_score": score,  # Keep raw score for reference
                    "max_score": max_score,
                    "letter_grade": letter_grade,
                    "total_questions": len(criteria_scores),
                    "graded_at": result.get("timestamp", ""),
                    "criteria_scores": criteria_scores,
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "suggestions": suggestions,
                }
            )

        # Sort results by score (highest first)
        results_list.sort(key=lambda x: x["score"], reverse=True)

        # Create batch summary with last updated timestamp
        batch_summary = {
            "total_submissions": total_submissions,
            "average_score": round(avg_score, 1),
            "highest_score": highest_score,
            "lowest_score": lowest_score,
            "score_distribution": grade_distribution,
            "last_updated": data_timestamp,
        }
        
        context = {
            "page_title": "Grading Results",
            "has_results": bool(grading_results),
            "successful_grades": total_submissions,
            "batch_summary": batch_summary,
            "results_list": results_list,
        }
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Return JSON response for AJAX requests
            return jsonify({
                "success": True,
                "has_results": bool(grading_results),
                "results": results_list,
                "batch_summary": batch_summary,
                "last_updated": data_timestamp
            })

        # Return HTML response for normal requests
        return render_template("results.html", **context)

    except Exception as e:
        logger.error(f"Error viewing results: {str(e)}")
        flash("Error loading results. Please try again.", "error")
        return redirect(url_for("dashboard"))


def render_grouped_results():
    """Render results grouped by marking guide."""
    try:
        from src.database.models import GradingResult, MarkingGuide
        from sqlalchemy import func
        
        # Get all grading results with their associated marking guides for current user
        results_query = db.session.query(
            GradingResult,
            MarkingGuide.title.label('guide_title'),
            MarkingGuide.filename.label('guide_filename'),
            MarkingGuide.total_marks.label('guide_total_marks')
        ).join(
            MarkingGuide, GradingResult.marking_guide_id == MarkingGuide.id
        ).filter(
            MarkingGuide.user_id == current_user.id
        ).order_by(
            MarkingGuide.title,
            GradingResult.updated_at.desc()
        ).all()
        
        # Group results by marking guide
        grouped_results = {}
        total_submissions = 0
        all_scores = []
        
        for result, guide_title, guide_filename, guide_total_marks in results_query:
            guide_id = result.marking_guide_id
            
            if guide_id not in grouped_results:
                grouped_results[guide_id] = {
                    "guide_id": guide_id,
                    "guide_title": guide_title,
                    "guide_filename": guide_filename,
                    "guide_total_marks": guide_total_marks,
                    "results": [],
                    "summary": {
                        "total_submissions": 0,
                        "average_score": 0,
                        "highest_score": 0,
                        "lowest_score": 100
                    }
                }
            
            # Check if submission exists
            if not result.submission:
                continue
                
            # Only keep the latest result per submission_id to avoid duplicates
            existing_result = next(
                (r for r in grouped_results[guide_id]["results"] 
                 if r["submission_id"] == result.submission_id), None
            )
            
            if existing_result:
                # Compare timestamps and keep the more recent one
                existing_updated = datetime.fromisoformat(existing_result["updated_at"].replace('Z', '+00:00').replace('+00:00', ''))
                if result.updated_at > existing_updated:
                    # Remove the older result
                    grouped_results[guide_id]["results"].remove(existing_result)
                else:
                    # Skip this older result
                    continue
            
            # Get all grading results for this submission to count actual questions
            submission_grading_results = GradingResult.query.filter_by(
                submission_id=result.submission_id,
                marking_guide_id=guide_id
            ).all()
            
            # Build criteria_scores from all grading results for this submission
            criteria_scores = []
            strengths = []
            weaknesses = []
            suggestions = []
            total_score = 0
            total_max_score = 0
            
            # Process each grading result (one per question)
            for gr in submission_grading_results:
                detailed_feedback = gr.detailed_feedback or {}
                
                # Calculate percentage for this question
                points_earned = gr.score or 0
                points_possible = gr.max_score or 1
                percentage = (points_earned / points_possible * 100) if points_possible > 0 else 0
                
                # Get mapping information if available
                mapping = gr.mapping
                question_text = mapping.guide_question_text if mapping else "Question"
                student_answer = mapping.submission_answer if mapping else ""
                
                criteria_scores.append({
                    "question_id": mapping.guide_question_id if mapping else f"q_{len(criteria_scores)+1}",
                    "description": question_text,
                    "points_earned": points_earned,
                    "points_possible": points_possible,
                    "percentage": round(percentage, 1),
                    "feedback": gr.feedback or "",
                    "detailed_feedback": detailed_feedback,
                    "guide_answer": "",
                    "student_answer": student_answer,
                    "match_score": mapping.match_score if mapping else 0,
                    "match_reason": mapping.match_reason if mapping else ""
                })
                
                total_score += points_earned
                total_max_score += points_possible
                
                # Extract strengths, weaknesses, suggestions from detailed_feedback
                if isinstance(detailed_feedback, dict):
                    if "strengths" in detailed_feedback:
                        strengths.extend(detailed_feedback.get("strengths", []))
                    if "weaknesses" in detailed_feedback:
                        weaknesses.extend(detailed_feedback.get("weaknesses", []))
                    if "suggestions" in detailed_feedback:
                        suggestions.extend(detailed_feedback.get("suggestions", []))
                    elif "improvement_suggestions" in detailed_feedback:
                        suggestions.extend(detailed_feedback.get("improvement_suggestions", []))
            
            # Remove duplicates from feedback lists
            strengths = list(set(strengths))
            weaknesses = list(set(weaknesses))
            suggestions = list(set(suggestions))
            
            # If no criteria_scores found, create a default one
            if not criteria_scores:
                criteria_scores = [{
                    "question_id": "default",
                    "description": "Overall Assessment",
                    "points_earned": result.score,
                    "points_possible": result.max_score,
                    "percentage": result.percentage,
                    "feedback": result.feedback or "No detailed feedback available",
                    "detailed_feedback": {},
                    "guide_answer": "",
                    "student_answer": "",
                    "match_score": 0,
                    "match_reason": ""
                }]
                total_score = result.score
                total_max_score = result.max_score
            
            # Calculate corrected percentage based on actual totals
            corrected_percentage = (total_score / total_max_score * 100) if total_max_score > 0 else 0
            
            # Calculate letter grade using corrected percentage
            letter_grade = get_letter_grade(corrected_percentage)
            
            result_data = {
                "submission_id": result.submission_id,
                "filename": result.submission.filename,
                "score": corrected_percentage,
                "raw_score": total_score,
                "max_score": total_max_score,
                "letter_grade": letter_grade,
                "total_questions": len(criteria_scores),
                "graded_at": result.created_at.isoformat() if result.created_at else "",
                "updated_at": result.updated_at.isoformat() if result.updated_at else "",
                "criteria_scores": criteria_scores,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "suggestions": suggestions,
                "feedback": result.feedback
            }
            
            grouped_results[guide_id]["results"].append(result_data)
            all_scores.append(corrected_percentage)
            total_submissions += 1
        
        # Calculate summaries for each guide
        for guide_data in grouped_results.values():
            results = guide_data["results"]
            if results:
                scores = [r["score"] for r in results]
                guide_data["summary"] = {
                    "total_submissions": len(results),
                    "average_score": round(sum(scores) / len(scores), 1),
                    "highest_score": max(scores),
                    "lowest_score": min(scores)
                }
                
                # Sort results within each guide by score (highest first)
                guide_data["results"].sort(key=lambda x: x["score"], reverse=True)
        
        # Convert to list format and sort by guide title
        grouped_results_list = sorted(grouped_results.values(), key=lambda x: x["guide_title"])
        
        # Calculate overall summary
        overall_summary = {
            "total_submissions": total_submissions,
            "total_guides": len(grouped_results_list),
            "average_score": round(sum(all_scores) / len(all_scores), 1) if all_scores else 0,
            "highest_score": max(all_scores) if all_scores else 0,
            "lowest_score": min(all_scores) if all_scores else 0,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        context = {
            "page_title": "Grading Results - Grouped by Guide",
            "has_results": bool(grouped_results_list),
            "grouped_results": grouped_results_list,
            "overall_summary": overall_summary,
            "grouped_view": True
        }
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "success": True,
                "has_results": bool(grouped_results_list),
                "grouped_results": grouped_results_list,
                "overall_summary": overall_summary
            })
        
        # Return HTML response for normal requests
        return render_template("results_grouped.html", **context)
        
    except Exception as e:
        logger.error(f"Error rendering grouped results: {str(e)}")
        flash("Error loading grouped results. Please try again.", "error")
        return redirect(url_for("dashboard"))





@app.route("/api/process-ai-grading", methods=["POST"])
@csrf.exempt
def process_ai_grading():
    max_questions = request.json.get("max_questions", None)
    """API endpoint to process unified AI-powered mapping and grading with progress tracking."""
    try:
        # Get the currently selected guide from session instead of request
        session_guide_id = session.get("guide_id")
        if not session_guide_id:
            return jsonify({
                "error": "No marking guide selected. Please select a guide using 'Use Guide' button first.",
                "code": "NO_GUIDE_SELECTED"
            }), 400
            
        # Still get submission_ids from request as these can vary
        submission_ids = request.json.get("submission_ids", [])
        if not submission_ids:
            return jsonify({"error": "Missing submission IDs"}), 400

        # Use the session guide_id instead of request guide_id
        guide = MarkingGuide.query.get(session_guide_id)
        if not guide:
            return jsonify({"error": "Selected marking guide not found"}), 404
            
        # Verify guide is not currently in use
        if is_guide_in_use(session_guide_id):
            return jsonify({
                "error": "Marking guide is currently being used for processing. Please wait for current operations to complete.",
                "code": "GUIDE_IN_USE"
            }), 409

        submissions = Submission.query.filter(Submission.id.in_(submission_ids)).all()
        if not submissions:
            return jsonify({"error": "No submissions found for the provided IDs"}), 404

        # Check if services are available
        if not mapping_service:
            return jsonify({"error": "AI services not available"}), 503

        # Process AI grading (mapping + grading combined)
        grading_results = {}
        successful_gradings = 0
        failed_gradings = 0

        # Get guide content from multiple sources
        guide_content = guide.content_text

        if not guide_content:
            return jsonify({"error": "Guide content not available"}), 400

        # Process each submission with combined AI mapping and grading
        for submission in submissions:
            submission_id = submission.get("id")
            if not submission_id:
                continue

            try:
                # Get submission data from database
                db_submission = next(
                    (s for s in submissions if s.id == submission_id), None
                )
                if not db_submission:
                    logger.warning(
                        f"No data found for submission {submission_id} in the provided list."
                    )
                    failed_gradings += 1
                    continue

                submission_data = {
                    "filename": db_submission.filename,
                    "content": db_submission.content_text,
                    "answers": db_submission.answers,
                }

                if not submission_data:
                    try:
                        db_submission = Submission.query.get(submission_id)
                        if db_submission:
                            submission_data = {
                                "filename": db_submission.filename,
                                "content": db_submission.content_text,
                                "answers": db_submission.answers,
                            }
                    except Exception as e:
                        logger.warning(
                            f"Could not retrieve submission from database: {str(e)}"
                        )

                if not submission_data:
                    logger.warning(f"No data found for submission {submission_id}")
                    failed_gradings += 1
                    continue

                # Get submission content
                submission_content = submission_data.get("content", "")
                # If content is empty but answers exist, convert answers to a string representation
                if not submission_content and submission_data.get("answers"):
                    # Check if answers is already a string (e.g., from a previous JSON.dumps)
                    if isinstance(submission_data["answers"], str):
                        submission_content = submission_data["answers"]
                    else:
                        # If it's a dict/JSON object, convert it to a string
                        try:
                            submission_content = json.dumps(submission_data["answers"])
                        except TypeError as e:
                            logger.error(f"Error converting answers to JSON string: {e}")
                            submission_content = ""
                elif not submission_content and not submission_data.get("answers"):
                    logger.warning(f"Submission {submission_id} has no content and no answers.")
                    failed_gradings += 1
                    continue

                if not submission_content:
                    logger.warning(f"No content found for submission {submission_id}")
                    failed_gradings += 1
                    continue

                # Use grading service for combined mapping and grading
                try:
                    logger.info(
                        f"Starting AI processing for submission {submission_id}"
                    )

                    # The grading service internally handles mapping and grading
                    grading_result, grading_error = grading_service.grade_submission(
                        guide_content, submission_content, max_questions=max_questions
                    )

                    if grading_error:
                        logger.error(
                            f"AI grading failed for submission {submission_id}: {grading_error}"
                        )
                        failed_gradings += 1
                        continue

                    if grading_result and grading_result.get("status") == "success":
                        # Store comprehensive grading results
                        grading_results[submission_id] = {
                            "filename": submission.get("filename", "Unknown"),
                            "status": "completed",
                            "timestamp": datetime.now().isoformat(),
                            "score": grading_result.get("score", 0),
                            "percentage": grading_result.get("percentage", 0),
                            "max_score": grading_result.get("max_score", 0),
                            "feedback": grading_result.get("feedback", ""),
                            "criteria_scores": grading_result.get(
                                "criteria_scores", []
                            ),
                            "mappings": grading_result.get("mappings", []),
                            "metadata": grading_result.get("metadata", {}),
                        }
                        # Save grading result to database
                        try:
                            new_grading_result = GradingResult(
                                submission_id=submission_id,
                                status=res.get("status", "error"),
                                mapping_id=grading_result.get(
                                    "mapping_id"
                                ),  # Assuming mapping_id is returned
                                score=grading_result.get("score", 0),
                                max_score=grading_result.get("max_score", 0),
                                percentage=grading_result.get("percentage", 0),
                                feedback=grading_result.get("feedback", ""),
                                detailed_feedback=grading_result.get(
                                    "criteria_scores", []
                                ),  # Or a more appropriate field
                            )
                            db.session.add(new_grading_result)
                            db.session.commit()
                            successful_gradings += 1
                            logger.info(
                                f"AI processing completed for {submission_id}: {grading_result.get('percentage', 0)}%"
                            )
                        except Exception as db_e:
                            db.session.rollback()
                            logger.error(
                                f"Database error saving grading result for {submission_id}: {str(db_e)}"
                            )
                            failed_gradings += 1
                            continue
                    else:
                        logger.error(
                            f"Invalid grading result for submission {submission_id}"
                        )
                        failed_gradings += 1

                except Exception as e:
                    logger.error(
                        f"Error in AI processing for submission {submission_id}: {str(e)}"
                    )
                    failed_gradings += 1
                    continue

            except Exception as e:
                logger.error(f"Error processing submission {submission_id}: {str(e)}")
                failed_gradings += 1
                continue

        # Calculate overall statistics
        total_score = sum(result.get("score", 0) for result in grading_results.values())
        total_max_score = sum(
            result.get("max_score", 0) for result in grading_results.values()
        )
        average_percentage = (
            sum(result.get("percentage", 0) for result in grading_results.values())
            / len(grading_results)
            if grading_results
            else 0
        )

        # Add to recent activity
        activity = session.get("recent_activity", [])
        activity.insert(
            0,
            {
                "type": "ai_grading_complete",
                "message": f"AI processing completed: {successful_gradings} successful, {failed_gradings} failed",
                "timestamp": datetime.now().isoformat(),
                "icon": "check",
            },
        )
        session["recent_activity"] = activity[:10]

        return jsonify(
            {
                "success": True,
                "message": f"AI processing completed: {successful_gradings} successful, {failed_gradings} failed",
                "results": grading_results,
                "summary": {
                    "successful": successful_gradings,
                    "failed": failed_gradings,
                    "total": len(submissions),
                    "total_score": total_score,
                    "total_max_score": total_max_score,
                    "average_percentage": round(average_percentage, 1),
                },
            }
        )

    except Exception as e:
        logger.error(f"Error in process_ai_grading: {str(e)}")
        return jsonify({"error": f"AI processing failed: {str(e)}"}), 500


@app.route("/api/process-unified-ai", methods=["POST"])
@login_required
@csrf.exempt
def process_unified_ai():
    """API endpoint for unified AI processing with real-time progress tracking."""
    try:
        logger.info("Starting unified AI processing endpoint")

        # Get request data
        data = request.get_json()

        # Check session data with detailed logging
        guide_uploaded = session.get("guide_uploaded", False)
        submissions = session.get("submissions", [])
        guide_data = session.get("guide_data")
        guide_content = session.get("guide_raw_content", "")

        logger.info(f"Session data check:")
        logger.info(f"  - guide_uploaded: {guide_uploaded}")
        logger.info(f"  - submissions count: {len(submissions)}")
        logger.info(f"  - guide_data available: {guide_data is not None}")
        logger.info(f"  - guide_content length: {len(guide_content)}")

        # Check if we have the minimum required data
        if not guide_uploaded and not guide_data:
            logger.warning("No guide uploaded or available in session")
            return (
                jsonify(
                    {
                        "error": "No marking guide available. Please upload a marking guide first.",
                        "details": "guide_not_uploaded",
                        "code": "GUIDE_MISSING"
                    }
                ),
                400,
            )

        if not submissions or len(submissions) == 0:
            logger.warning("No submissions available in session")
            return (
                jsonify(
                    {
                        "error": "No submissions available. Please upload submissions first.",
                        "details": "no_submissions",
                        "code": "SUBMISSIONS_MISSING"
                    }
                ),
                400,
            )

        # Get guide and submissions from session or storage
        guide_id = session.get("guide_id")
        submissions = session.get("submissions", [])


        
        if not guide_id:
            logger.warning("No guide selected in session")
            return jsonify({
                "error": "No marking guide selected. Please select a guide using 'Use Guide' button first.",
                "code": "NO_GUIDE_SELECTED"
            }), 400
            
        if not submissions:
            logger.warning("submissions are missing from session, attempting to recover from database")
            # Try to get submissions for the current user as fallback
            current_user = get_current_user()
            if current_user:
                db_submissions = Submission.query.filter_by(user_id=current_user.id).order_by(Submission.created_at.desc()).all()
                if db_submissions:
                    submissions = [s.to_dict() for s in db_submissions]
                    session['submissions'] = submissions
                    session.modified = True
                    logger.info(f"Recovered {len(submissions)} submissions from database")
                else:
                    logger.warning("No submissions found in database for current user")
                    return jsonify({
                        "error": "No submissions found. Please upload submissions first.",
                        "code": "NO_SUBMISSIONS_FOUND"
                    }), 400
            else:
                logger.warning("Current user not found when recovering submissions")
                return jsonify({
                    "error": "Authentication required. Please log in again.",
                    "code": "AUTH_REQUIRED"
                }), 401

        # Retrieve guide from database to ensure we have the latest content
        guide = MarkingGuide.query.get(guide_id)
        if not guide:
            logger.warning(f"Marking guide with ID {guide_id} not found in DB.")
            return jsonify({
                "error": "Marking guide not found.",
                "code": "GUIDE_NOT_FOUND"
            }), 404
            
        # Verify guide is not currently in use
        if is_guide_in_use(guide_id):
            logger.warning(f"Attempted to process guide {guide_id} while it's in use")
            return jsonify({
                "error": "Marking guide is currently being used for processing. Please wait for current operations to complete.",
                "code": "GUIDE_IN_USE"
            }), 409

        # Construct guide_data from the retrieved guide object
        guide_data = {
            "raw_content": guide.content_text,  # Use content_text from DB
            "filename": guide.filename,
            "questions": guide.questions,
            "total_marks": guide.total_marks,
            "extraction_method": "db_retrieval",
            "processed_at": datetime.now().isoformat(),
        }
        guide_content = guide.content_text # Ensure guide_content is directly from DB

        # Check if services are available with detailed status
        service_status = get_service_status()
        if not mapping_service:
            logger.error("Mapping service not available")
            return jsonify({
                "error": "AI services not available",
                "details": "mapping_service_unavailable",
                "service_status": service_status,
                "code": "SERVICE_UNAVAILABLE"
            }), 503

        if not guide_content:
            logger.warning("Marking guide content is empty after retrieval from DB.")
            return (
                jsonify(
                    {
                        "error": "Marking guide content is empty. Please ensure the guide was processed correctly.",
                        "details": "guide_content_empty",
                        "code": "GUIDE_CONTENT_EMPTY"
                    }
                ),
                400,
            )

        logger.info(
            f"Starting unified AI processing for {len(submissions)} submissions"
        )

        # Initialize unified AI service with error handling
        try:
            logger.info("Importing unified AI services...")
            from src.services.unified_ai_service import UnifiedAIService as ConsolidatedUnifiedAIService
            # Alias for backward compatibility
            UnifiedAIService = ConsolidatedUnifiedAIService
            from src.services.progress_tracker import progress_tracker

            logger.info("Services imported successfully")

            unified_ai_service = UnifiedAIService(
                mapping_service=mapping_service,
                grading_service=(
                    grading_service if "grading_service" in globals() else None
                ),
                llm_service=llm_service if "llm_service" in globals() else None,
            )
            logger.info("Unified AI service created successfully")
        except ImportError as e:
            logger.error(f"Failed to import unified AI services: {str(e)}")
            return jsonify({
                "error": f"Service import failed: {str(e)}",
                "code": "IMPORT_ERROR"
            }), 500
        except Exception as e:
            logger.error(f"Failed to create unified AI service: {str(e)}")
            return jsonify({
                "error": f"Service creation failed: {str(e)}",
                "code": "SERVICE_CREATION_ERROR"
            }), 500

        # Process with unified AI service with detailed error handling
        try:
            session_id = session.sid  # Use SecureFlaskSession's sid property
            logger.info(f"Creating progress session for {len(submissions)} submissions")
            progress_id = None # Initialize to None
            try:
                progress_id = progress_tracker.create_session(session_id, len(submissions))
                logger.info(f"Progress session created: {progress_id}")
            except Exception as e:
                logger.error(f"Error creating progress session: {str(e)}")
                return jsonify({
                    "error": f"Failed to create progress session: {str(e)}",
                    "code": "PROGRESS_SESSION_ERROR"
                }), 500

            # Store progress ID in session for frontend polling
            session["current_progress_id"] = progress_id

            # Create progress callback
            progress_callback = progress_tracker.create_progress_callback(progress_id)
            logger.info("Progress callback created")

            logger.info("Starting unified AI processing...")
            result, error = unified_ai_service.process_unified_ai_grading(
                marking_guide_content=guide_data,
                submissions=submissions,
                progress_callback=progress_callback,
            )
            logger.info("Unified AI processing completed")

            if error:
                logger.error(f"Unified AI processing returned error: {error}")
                # Mark progress as failed
                if progress_id:
                    progress_tracker.complete_session(progress_id, success=False, message=error)
                return jsonify({
                    "error": error,
                    "code": "PROCESSING_ERROR"
                }), 500

            # Save results to database
            from src.database.models import GradingResult, Mapping, Submission, db

            for res in result.get("results", []):
                submission_id = res.get("submission_id")
                submission = Submission.query.get(submission_id)
                if not submission:
                    logger.warning(
                        f"Submission with ID {submission_id} not found for saving results. Skipping."
                    )
                    continue

                guide_id = session.get("guide_id") # Retrieve guide_id from session

                # Update submission processing status based on AI grading result
                # This ensures the frontend accurately reflects the grading outcome
                submission.processing_status = res.get("status", "error")
                if submission.processing_status == "completed":
                    submission.processed = True

                # Process individual mappings and their grading results
                for mapping_data in res.get("mappings", []):
                    # Create and save Mapping object
                    new_mapping = Mapping(
                        submission_id=submission_id,
                        guide_question_id=mapping_data.get("guide_id"),
                        guide_question_text=mapping_data.get("guide_text"),
                        submission_answer=mapping_data.get("submission_answer"),
                        max_score=mapping_data.get("max_score"),
                        match_score=mapping_data.get("match_score"),
                        match_reason=mapping_data.get("match_reason"),
                        mapping_method="llm",  # Assuming LLM is the method
                    )
                    db.session.add(new_mapping)
                    db.session.flush()  # Flush to get the ID for the new_mapping

                    # Create and save GradingResult object for this mapping
                    grading_result = GradingResult(
                        submission_id=submission_id,
                        marking_guide_id=guide_id,
                        mapping_id=new_mapping.id,
                        score=mapping_data.get("grade_score", 0),
                        max_score=mapping_data.get("max_score", 0),
                        percentage=mapping_data.get("percentage", 0),
                        feedback=mapping_data.get("feedback", ""),
                        detailed_feedback=mapping_data.get("detailed_feedback", {}),
                        progress_id=session[
                            "current_progress_id"
                        ],  # Link to the progress session
                        confidence=mapping_data.get("confidence", 0.0),
                        grading_method="llm",
                    )
                    db.session.add(grading_result)

            # After processing all results for the batch, commit all changes
            db.session.commit()

            # After committing, refresh the session's submissions to reflect the updated status
            # This ensures the UI gets the latest data on page reload

            # Re-fetch recent submissions to ensure session data is fresh
            if current_user.is_authenticated:
                recent_submissions = (
                    Submission.query.filter_by(user_id=current_user.id)
                    .order_by(Submission.created_at.desc())
                        .all()
                )
                session["submissions"] = [s.to_dict() for s in recent_submissions]
                
                # Refresh session statistics to update dashboard counters
                refresh_session_statistics(current_user.id)

            progress_tracker.complete_session(progress_id, success=True)

            # Update session variables for results page
            if progress_id:
                session['last_grading_progress_id'] = progress_id
                session['last_grading_result'] = True
                session['guide_id'] = guide_id
                session.modified = True  # Mark session as modified to ensure changes are saved
                logger.info(f"Updated session with progress_id {progress_id}, last_grading_result=True, and guide_id={guide_id}")
            else:
                logger.warning("progress_id was None, not updating session with last_grading_progress_id.")

        except Exception as e:
            db.session.rollback()
            logger.error(
                f"Error during unified AI processing or saving results: {str(e)}"
            )
            if progress_id:
                logger.info(f"Attempting to complete session {progress_id} with failure.")
                progress_tracker.complete_session(
                    progress_id, success=False, message=f"Processing failed: {str(e)}"
                )
            else:
                logger.warning("progress_id was None in exception handler, cannot complete session.")
            return jsonify({
                "error": f"Processing failed: {str(e)}",
                "code": "PROCESSING_EXCEPTION"
            }), 500
        finally:
            pass  # The complete_session is already called in try/except blocks

        return (
            jsonify(
                {
                    "success": True,
                    "progress_id": progress_id,
                    "summary": result.get("summary"),
                    "message": "AI processing started successfully"
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error in process_unified_ai: {str(e)}")
        return jsonify({
            "error": f"Unified AI processing failed: {str(e)}",
            "code": "GENERAL_ERROR"
        }), 500


@app.route("/api/progress/<progress_id>", methods=["GET"])
@csrf.exempt
def get_progress(progress_id):
    """Get progress for a specific processing session."""
    try:
        from src.services.progress_tracker import progress_tracker

        if not progress_id:
            return jsonify({"success": False, "error": "Progress ID is required"}), 400
            
        progress = progress_tracker.get_progress(progress_id)
        
        if not progress:
            return jsonify({"success": False, "error": "Progress not found"}), 404
            
        return jsonify({
            "success": True,
            "progress": progress
        })

    except Exception as e:
        logger.error(f"Error getting progress for {progress_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to get progress: {str(e)}"
        }), 500

@app.route("/api/progress/<progress_id>/history", methods=["GET"])
@csrf.exempt
def get_progress_history(progress_id):
    """Get progress history for a specific processing session."""
    try:
        from src.services.progress_tracker import progress_tracker
        
        if not progress_id:
            return jsonify({"success": False, "error": "Progress ID is required"}), 400

        history = progress_tracker.get_progress_history(progress_id)

        if not history:
            return jsonify({"success": False, "error": "Progress history not found"}), 404
            
        return jsonify({
                "success": True,
            "history": history
        })

    except Exception as e:
        logger.error(f"Error getting progress history for {progress_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to get progress history: {str(e)}"
        }), 500


@app.route("/api/cache/stats", methods=["GET"])
@csrf.exempt
def get_cache_stats():
    """Get cache statistics from AI services."""
    try:
        stats = {}
        
        # Get unified AI service cache stats
        if 'unified_ai_service' in globals() and unified_ai_service:
            stats['unified_ai_service'] = unified_ai_service.get_cache_stats()
        
        # Get LLM service cache stats if available
        if 'llm_service' in globals() and llm_service and hasattr(llm_service, '_response_cache'):
            stats['llm_service'] = {
                'response_cache_size': len(llm_service._response_cache)
            }
        
        return jsonify({
            "success": True,
            "cache_stats": stats,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to get cache stats: {str(e)}"
        }), 500


@app.route("/api/cache/clear", methods=["POST"])
@csrf.exempt
def clear_cache():
    """Clear AI service caches."""
    try:
        cache_type = request.json.get('cache_type', 'all') if request.json else 'all'
        cleared_caches = []
        
        # Clear unified AI service caches
        if 'unified_ai_service' in globals() and unified_ai_service:
            if cache_type in ['all', 'unified_ai']:
                unified_ai_service.clear_cache()
                cleared_caches.append('unified_ai_service')
            elif cache_type == 'guide_type':
                unified_ai_service.clear_guide_type_cache()
                cleared_caches.append('unified_ai_service.guide_type')
            elif cache_type == 'content':
                unified_ai_service.clear_content_cache()
                cleared_caches.append('unified_ai_service.content')
        
        # Clear LLM service cache if available
        if cache_type in ['all', 'llm'] and 'llm_service' in globals() and llm_service and hasattr(llm_service, '_response_cache'):
            llm_service._response_cache.clear()
            cleared_caches.append('llm_service.response_cache')
        
        return jsonify({
            "success": True,
            "message": f"Cleared caches: {', '.join(cleared_caches)}",
            "cleared_caches": cleared_caches,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to clear cache: {str(e)}"
        }), 500


def get_letter_grade(score):
    """Convert numeric score to letter grade."""
    if score >= 97:
        return "A+"
    elif score >= 93:
        return "A"
    elif score >= 90:
        return "A-"
    elif score >= 87:
        return "B+"
    elif score >= 83:
        return "B"
    elif score >= 80:
        return "B-"
    elif score >= 77:
        return "C+"
    elif score >= 73:
        return "C"
    elif score >= 70:
        return "C-"
    elif score >= 67:
        return "D+"
    elif score >= 63:
        return "D"
    elif score >= 60:
        return "D-"
    else:
        return "F"


# Additional routes for enhanced functionality
@app.route("/marking-guides")
@login_required
def marking_guides():
    """View marking guide library with optimized performance and authentication."""
    try:
        guides = []

        # Get stored guides from database (optimized)
        try:
            from src.database.models import MarkingGuide

            current_user = get_current_user()
            if current_user:
                # Use efficient database query
                db_guides = (
                    MarkingGuide.query.filter_by(
                        user_id=current_user.id, is_active=True
                    )
                    .order_by(MarkingGuide.created_at.desc())
                    .limit(50)
                    .all()
                )

                for guide in db_guides:
                    guide_data = {
                        "id": str(guide.id),  # Ensure ID is a string
                        "name": guide.title,  # For backward compatibility
                        "title": guide.title,  # Primary field
                        "filename": guide.filename,
                        "description": guide.description
                        or f"Database guide - {guide.title}",
                        "questions": guide.questions or [],
                        "total_marks": guide.total_marks or 0,
                        "extraction_method": "database",
                        "created_at": guide.created_at.isoformat(),
                        "created_by": current_user.username,
                        "is_session_guide": False,
                    }
                    guides.append(guide_data)

                logger.info(f"Loaded {len(db_guides)} guides from database")
        except Exception as db_error:
            logger.error(f"Error loading guides from database: {str(db_error)}")

        # Calculate statistics
        total_guides = len(guides)
        total_questions = sum(len(guide.get("questions", [])) for guide in guides)
        total_marks_all = sum(guide.get("total_marks", 0) for guide in guides)

        # Get extraction method statistics
        extraction_methods = {}
        for guide in guides:
            method = guide.get("extraction_method", "unknown")
            extraction_methods[method] = extraction_methods.get(method, 0) + 1

        # Ensure all guides have proper fields and valid IDs
        valid_guides = []
        for guide in guides:
            if "extraction_method" not in guide or not guide["extraction_method"]:
                guide["extraction_method"] = "unknown"

            # Ensure ID is valid and not None
            if not guide.get("id") or guide["id"] in [None, "None", ""]:
                logger.warning(f"Guide with invalid ID found, skipping: {guide}")
                continue  # Skip guides with invalid IDs

            # Ensure title/name exists
            if not guide.get("title") and not guide.get("name"):
                guide["title"] = guide.get("filename", "Untitled Guide")
                guide["name"] = guide["title"]

            # Sanitize text fields to prevent JSON parsing issues
            def sanitize_text(text):
                if not text:
                    return text
                # Remove control characters that can break JSON
                # Remove control characters except tab, newline, and carriage return
                # Using a loop for character-by-character check instead of regex
                cleaned_text = []
                for char_code in str(text).encode("utf-8"):
                    if char_code >= 32 or char_code in (
                        9,
                        10,
                        13,
                    ):  # Allow tab (9), newline (10), carriage return (13)
                        cleaned_text.append(chr(char_code))
                text = "".join(cleaned_text)
                return text

            # Sanitize all text fields
            guide["title"] = sanitize_text(guide.get("title", ""))
            guide["name"] = sanitize_text(guide.get("name", ""))
            guide["filename"] = sanitize_text(guide.get("filename", ""))
            guide["description"] = sanitize_text(guide.get("description", ""))
            guide["created_by"] = sanitize_text(guide.get("created_by", ""))

            # Sanitize questions if they exist
            if guide.get("questions"):
                for question in guide["questions"]:
                    if isinstance(question, dict):
                        for key, value in question.items():
                            if isinstance(value, str):
                                question[key] = sanitize_text(value)

            valid_guides.append(guide)

        guides = valid_guides  # Use only valid guides

        context = {
            "page_title": "Marking Guide Library",
            "guides": guides,
            "saved_guides": guides,  # Template expects this variable
            "current_guide": session.get("guide_filename", None),
            "statistics": {
                "total_guides": total_guides,
                "total_questions": total_questions,
                "total_marks": total_marks_all,
                "extraction_methods": extraction_methods,
            },
        }

        return render_template("marking_guides.html", **context)
    except Exception as e:
        logger.error(f"Error loading guide library: {str(e)}")
        flash("Error loading guide library. Please try again.", "error")
        return redirect(url_for("dashboard"))


@app.route("/create-guide")
def create_guide():
    """Create new marking guide."""
    try:
        context = {"page_title": "Create Marking Guide"}
        return render_template("create_guide.html", **context)
    except Exception as e:
        logger.error(f"Error loading create guide page: {str(e)}")
        flash("Error loading create guide page. Please try again.", "error")
        return redirect(url_for("dashboard"))


@app.route("/guide/<guide_id>")
@login_required
def view_guide_content(guide_id):
    """View detailed content of a specific marking guide"""
    try:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            flash("Please log in to view guides", "error")
            return redirect(url_for("auth.login"))

        # Get guide from database
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            flash("Marking guide not found", "error")
            return redirect(url_for("marking_guides"))

        # Prepare context for template
        context = {
            "page_title": f"Guide: {guide.title}",
            "guide": guide,
            "filename": guide.filename,
            "raw_content": guide.content_text or "No content available",
            "questions": guide.questions or [],
            "total_marks": guide.total_marks or 0,
            "created_at": guide.created_at.isoformat() if guide.created_at else None,
        }

        return render_template("guide_content.html", **context)

    except Exception as e:
        logger.error(f"Error viewing guide content: {str(e)}")
        flash("Error loading guide content. Please try again.", "error")
        return redirect(url_for("marking_guides"))


@app.route("/use_guide/<guide_id>")
@login_required
def use_guide(guide_id):
    """Set active marking guide for the session and enable dashboard components"""
    try:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            flash("Please log in to use guides", "error")
            return redirect(url_for("auth.login"))

        # Get guide from database
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            flash("Marking guide not found", "error")
            return redirect(url_for("marking_guides"))

        # Set comprehensive session data for dashboard activation
        session["guide_id"] = guide.id
        _update_guide_uploaded_status(
            current_user.id
        )  # Critical for dashboard component activation
        session["guide_filename"] = guide.filename or guide.title
        session["guide_content"] = guide.content_text or ""
        session["guide_raw_content"] = guide.content_text or ""

        # Set guide data structure for AI processing
        session["guide_data"] = {
            "filename": guide.filename or guide.title,
            "questions": guide.questions or [],
            "total_marks": guide.total_marks or 0,
            "extraction_method": "database",
            "processed_at": (
                guide.created_at.isoformat()
                if guide.created_at
                else datetime.now().isoformat()
            ),
        }

        # Set current guide for backward compatibility
        session["current_guide"] = {
            "id": guide.id,
            "name": guide.title,
            "description": guide.description,
            "total_marks": guide.total_marks,
        }

        session.modified = True

        # Add to recent activity
        activity = session.get("recent_activity", [])
        activity.insert(
            0,
            {
                "type": "guide_loaded",
                "message": f"Loaded marking guide: {guide.title}",
                "timestamp": datetime.now().isoformat(),
                "icon": "check",
            },
        )
        session["recent_activity"] = activity[:10]

        logger.info(f"Guide loaded successfully: {guide.title} (ID: {guide.id})")
        flash(
            f'Marking guide "{guide.title}" loaded successfully! Dashboard components are now active.',
            "success",
        )
        return redirect(url_for("dashboard"))

    except SQLAlchemyError as e:
        logger.error(f"Database error in use_guide: {str(e)}")
        flash("Error accessing guide database", "error")
        return redirect(url_for("marking_guides"))
    except Exception as e:
        logger.error(f"Unexpected error in use_guide: {str(e)}")
        flash("An unexpected error occurred", "error")
        return redirect(url_for("marking_guides"))


@app.route("/clear-session-guide", methods=["GET", "POST"])
@login_required
def clear_session_guide():
    """Clear the current session guide and related grading data."""
    try:
        # Clear guide-related session variables
        session.pop("guide_data", None)
        session.pop("guide_filename", None)
        session.pop("guide_raw_content", None)
        session.pop("guide_uploaded", None)
        session.pop("guide_id", None)
        
        # Clear grading-related session variables
        session.pop("last_grading_progress_id", None)
        session.pop("last_grading_result", None)
        session.modified = True
        flash("Session guide cleared successfully.", "success")
        return redirect(url_for("marking_guides"))
    except Exception as e:
        logger.error(f"Error clearing session guide: {str(e)}")
        flash("Error clearing session guide. Please try again.", "error")
        return redirect(url_for("marking_guides"))


@app.route("/reprocess-submissions")
@login_required
def reprocess_submissions():
    """Reprocess submissions with empty content_text fields."""
    try:
        from src.database.models import Submission
        
        current_user = get_current_user()
        if not current_user:
            flash("Authentication required.", "error")
            return redirect(url_for("login"))
        
        # Find submissions with empty or null content_text
        submissions_to_process = Submission.query.filter(
            Submission.user_id == current_user.id,
            db.or_(
                Submission.content_text.is_(None),
                Submission.content_text == ""
            )
        ).all()
        
        if not submissions_to_process:
            flash("No submissions need reprocessing.", "info")
            return redirect(url_for("view_submissions"))
        
        processed_count = 0
        failed_count = 0
        
        for submission in submissions_to_process:
            try:
                if submission.file_path and os.path.exists(submission.file_path):
                    # Reprocess the file
                    answers, raw_text, error = parse_student_submission(submission.file_path)
                    
                    if raw_text and not error:
                        submission.content_text = raw_text
                        if answers:
                            submission.answers = answers
                        processed_count += 1
                        logger.info(f"Reprocessed submission {submission.id}: {len(raw_text)} characters extracted")
                    else:
                        failed_count += 1
                        logger.warning(f"Failed to reprocess submission {submission.id}: {error}")
                else:
                    failed_count += 1
                    logger.warning(f"File not found for submission {submission.id}: {submission.file_path}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Error reprocessing submission {submission.id}: {str(e)}")
        
        if processed_count > 0:
            db.session.commit()
            flash(f"Successfully reprocessed {processed_count} submission(s).", "success")
        
        if failed_count > 0:
            flash(f"{failed_count} submission(s) could not be reprocessed.", "warning")
        
        return redirect(url_for("view_submissions"))
        
    except Exception as e:
        logger.error(f"Error in reprocess_submissions: {str(e)}")
        flash("An error occurred while reprocessing submissions.", "error")
        return redirect(url_for("view_submissions"))


@app.route("/view-submission/<submission_id>")
@login_required
def view_submission_content(submission_id):
    """View content of a specific submission."""
    try:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            flash("Please log in to view submissions", "error")
            return redirect(url_for("auth.login"))

        # Get submission from database
        try:
            submission = Submission.query.filter_by(
                id=submission_id,
                user_id=current_user.id
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching submission: {str(e)}")
            flash("Error retrieving submission", "error")
            return redirect(url_for("view_submissions"))

        if not submission:
            logger.warning(f"Submission {submission_id} not found")
            flash("Submission not found", "error")
            return redirect(url_for("view_submissions"))

        # Get related grading results
        grading_results = GradingResult.query.filter_by(
            submission_id=submission_id
        ).all()

        # Handle file_size safely - it might be None or not exist in older database records
        # despite being defined as non-nullable in the current model
        file_size_kb = 0
        try:
            if hasattr(submission, 'file_size') and submission.file_size is not None:
                file_size_kb = round(submission.file_size / 1024, 1)
        except (AttributeError, TypeError) as e:
            logger.warning(f"Could not process file_size for submission {submission_id}: {str(e)}")

        # Extract raw text and answers if available
        raw_text = ""
        extracted_answers = {}
        try:
            if hasattr(submission, 'content_text') and submission.content_text:
                raw_text = submission.content_text
            if hasattr(submission, 'answers') and submission.answers:
                extracted_answers = submission.answers
        except (AttributeError, TypeError) as e:
            logger.warning(f"Could not process text content for submission {submission_id}: {str(e)}")

        context = {
            "page_title": f'Submission: {submission.filename}',
            "submission": submission,
            "grading_results": grading_results,
            "file_size_kb": file_size_kb,
            # Add these variables for direct access in the template
            "filename": submission.filename,
            "uploaded_at": submission.created_at.strftime("%Y-%m-%d %H:%M:%S") if submission.created_at else "",
            "processed": submission.processed,
            "submission_id": submission_id,
            "raw_text": raw_text,
            "extracted_answers": extracted_answers
        }
        return render_template("submission_content.html", **context)
    except Exception as e:
        logger.error(f"Error viewing submission content: {str(e)}")
        flash("Error loading submission content. Please try again.", "error")
        return redirect(url_for("view_submissions"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    """Application settings page."""
    try:
        # Get current settings from environment variables
        current_max_file_size = int(os.getenv("MAX_FILE_SIZE_MB", "16"))
        current_formats = os.getenv(
            "SUPPORTED_FORMATS",
            ".pdf,.docx,.doc,.jpg,.jpeg,.png,.tiff,.bmp,.gif"
        ).split(",")
        
        # Get API keys and configuration from environment variables
        current_llm_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        current_llm_model = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
        current_llm_seed = os.getenv("DEEPSEEK_SEED", "42")
        current_ocr_api_key = os.getenv("HANDWRITING_OCR_API_KEY", "")
        current_ocr_api_url = os.getenv("HANDWRITING_OCR_API_URL", "https://www.handwritingocr.com/api/v3")
        
        # Get UI settings from environment variables
        current_notification_level = os.getenv("NOTIFICATION_LEVEL", "all")
        current_theme = os.getenv("THEME", "light")
        current_language = os.getenv("LANGUAGE", "en")
        
        # Default settings
        default_settings = {
            "max_file_size": current_max_file_size,
            "allowed_formats": current_formats,
            "auto_process": True,
            "save_temp_files": False,
            "notification_level": current_notification_level,
            "theme": current_theme,
            "language": current_language,
            "llm_api_key": current_llm_api_key,
            "llm_model": current_llm_model,
            "llm_seed": current_llm_seed,
            # "llm_token_limit": current_llm_token_limit,  # Token limits removed
            "ocr_api_key": current_ocr_api_key,
            "ocr_api_url": current_ocr_api_url,
        }

        # Available options
        available_formats = [
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
            ".tiff",
            ".bmp",
            ".gif",
        ]
        notification_levels = [
            {"value": "all", "label": "All Notifications"},
            {"value": "important", "label": "Important Only"},
            {"value": "errors", "label": "Errors Only"},
            {"value": "none", "label": "No Notifications"},
        ]
        themes = [
            {"value": "light", "label": "Light Theme"},
            {"value": "dark", "label": "Dark Theme"},
            {"value": "auto", "label": "Auto (System)"},
        ]
        languages = [
            {"value": "en", "label": "English"},
            {"value": "es", "label": "Spanish"},
            {"value": "fr", "label": "French"},
            {"value": "de", "label": "German"},
        ]
        
        # Handle form submission
        if request.method == "POST":
            try:
                # Get form data
                max_file_size = request.form.get("max_file_size", "16")
                allowed_formats = request.form.getlist("allowed_formats")
                llm_api_key = request.form.get("llm_api_key", "")
                llm_model = request.form.get("llm_model", "deepseek-reasoner")
                llm_seed = request.form.get("llm_seed", "42")
                # llm_token_limit = request.form.get("llm_token_limit", "2048")  # Token limits removed
                ocr_api_key = request.form.get("ocr_api_key", "")
                ocr_api_url = request.form.get("ocr_api_url", "https://www.handwritingocr.com/api/v3")
                
                # Get UI settings
                notification_level = request.form.get("notification_level", "all")
                theme = request.form.get("theme", "light")
                language = request.form.get("language", "en")
                
                # Validate form data
                if not allowed_formats:
                    flash("Please select at least one file format.", "error")
                    return redirect(url_for("settings"))
                
                # Find .env file
                dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
                
                # Update .env file
                import dotenv
                
                # Update MAX_FILE_SIZE_MB
                dotenv.set_key(dotenv_path, "MAX_FILE_SIZE_MB", max_file_size)
                os.environ["MAX_FILE_SIZE_MB"] = max_file_size
                
                # Update SUPPORTED_FORMATS
                # Ensure each format has a leading dot
                normalized_formats = []
                for fmt in allowed_formats:
                    fmt = fmt.strip()
                    if fmt:
                        if not fmt.startswith("."):
                            fmt = "." + fmt
                        normalized_formats.append(fmt)
                
                formats_str = ",".join(normalized_formats)
                dotenv.set_key(dotenv_path, "SUPPORTED_FORMATS", formats_str)
                os.environ["SUPPORTED_FORMATS"] = formats_str
                
                # Update LLM configuration
                dotenv.set_key(dotenv_path, "DEEPSEEK_API_KEY", llm_api_key)
                os.environ["DEEPSEEK_API_KEY"] = llm_api_key
                
                dotenv.set_key(dotenv_path, "DEEPSEEK_MODEL", llm_model)
                os.environ["DEEPSEEK_MODEL"] = llm_model
                
                dotenv.set_key(dotenv_path, "DEEPSEEK_SEED", llm_seed)
                os.environ["DEEPSEEK_SEED"] = llm_seed
                
                # dotenv.set_key(dotenv_path, "DEEPSEEK_TOKEN_LIMIT", llm_token_limit)  # Token limits removed
                # os.environ["DEEPSEEK_TOKEN_LIMIT"] = llm_token_limit  # Token limits removed
                
                # Update OCR configuration
                dotenv.set_key(dotenv_path, "HANDWRITING_OCR_API_KEY", ocr_api_key)
                os.environ["HANDWRITING_OCR_API_KEY"] = ocr_api_key
                
                dotenv.set_key(dotenv_path, "HANDWRITING_OCR_API_URL", ocr_api_url)
                os.environ["HANDWRITING_OCR_API_URL"] = ocr_api_url
                
                # Update UI settings
                dotenv.set_key(dotenv_path, "NOTIFICATION_LEVEL", notification_level)
                os.environ["NOTIFICATION_LEVEL"] = notification_level
                
                dotenv.set_key(dotenv_path, "THEME", theme)
                os.environ["THEME"] = theme
                
                dotenv.set_key(dotenv_path, "LANGUAGE", language)
                os.environ["LANGUAGE"] = language
                
                # Reload configuration
                try:
                    from src.config.config_manager import ConfigManager
                    # Use the reload method instead of creating a new instance
                    config_manager = ConfigManager()
                    config_manager.reload()
                except ImportError:
                    logger.warning("ConfigManager not found, skipping config reload")
                except Exception as config_error:
                    logger.error(f"Error reloading ConfigManager: {str(config_error)}")
                
                # Reload UnifiedConfig to update supported_formats
                try:
                    from src.config.unified_config import UnifiedConfig, load_dotenv
                    # Reload environment variables to ensure we get the latest values
                    load_dotenv(override=True)
                    global config
                    config = UnifiedConfig()
                    logger.info("UnifiedConfig reloaded with updated settings")
                except ImportError:
                    logger.warning("UnifiedConfig not found, skipping config reload")
                except Exception as config_error:
                    logger.error(f"Error reloading UnifiedConfig: {str(config_error)}")
                
                # Reinitialize services with new API keys
                if "ocr_service" in globals() and ocr_api_key:
                    global ocr_service
                    ocr_service = OCRService(api_key=ocr_api_key, enable_fallback=False)
                    logger.info("OCR service reinitialized with new API key")
                
                if "llm_service" in globals() and llm_api_key:
                    global llm_service, mapping_service, grading_service
                    llm_service = LLMService(api_key=llm_api_key, model=llm_model, seed=int(llm_seed))
                    mapping_service = MappingService(llm_service=llm_service)
                    grading_service = GradingService(llm_service=llm_service, mapping_service=mapping_service)
                    logger.info("LLM services reinitialized with new API key and seed")
                
                flash("Settings updated successfully.", "success")
                return redirect(url_for("settings"))
            except Exception as e:
                logger.error(f"Error updating settings: {str(e)}")
                flash(f"Error updating settings: {str(e)}", "error")
                return redirect(url_for("settings"))

        # Check if config is available
        config_obj = None
        try:
            # Try to access the global config object
            if 'config' in globals():
                config_obj = globals()['config']
            else:
                # Try to create a new config object if not available
                try:
                    from src.config.unified_config import UnifiedConfig
                    config_obj = UnifiedConfig()
                    logger.info("Created new UnifiedConfig object for settings page")
                except ImportError:
                    logger.warning("UnifiedConfig not available, settings will be limited")
                except Exception as config_error:
                    logger.warning(f"Could not create UnifiedConfig: {str(config_error)}")
        except Exception as config_access_error:
            logger.warning(f"Error accessing config: {str(config_access_error)}")
        
        # Get service status and storage stats with error handling
        try:
            service_status = get_service_status()
        except Exception as e:
            logger.warning(f"Could not get service status: {e}")
            service_status = {}
            
        try:
            storage_stats = get_storage_stats()
        except Exception as e:
            logger.warning(f"Could not get storage stats: {e}")
            storage_stats = {
                "temp_size_mb": 0.0,
                "output_size_mb": 0.0,
                "total_size_mb": 0.0,
                "max_size_mb": 160.0,
            }

        context = {
            "page_title": "Settings",
            "settings": default_settings,
            "available_formats": available_formats,
            "notification_levels": notification_levels,
            "themes": themes,
            "languages": languages,
            "service_status": service_status,
            "storage_stats": storage_stats,
            "config": config_obj,  # Pass the config object to the template (might be None)
        }
        return render_template("settings.html", **context)
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        flash("Error loading settings. Please try again.", "error")
        return redirect(url_for("dashboard"))


# Duplicate export_results function removed - using the more complete version below


@app.route("/delete-guide/<guide_id>")
@login_required
def delete_guide(guide_id):
    """Delete a marking guide (legacy route for backward compatibility)."""
    try:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            flash("Please log in to delete guides", "error")
            return redirect(url_for("auth.login"))

        # Get guide from database
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            flash("Marking guide not found", "error")
            return redirect(url_for("marking_guides"))

        # Store guide name for flash message
        guide_name = guide.title

        # Check if this guide is currently active in session
        current_guide_id = session.get("guide_id")
        was_active_guide = str(current_guide_id) == str(guide_id)

        # Delete related records first to avoid foreign key constraint violations
        # Import required models
        from src.database.models import GradingSession, Mapping
        
        # Delete grading sessions related to this guide
        GradingSession.query.filter_by(marking_guide_id=guide_id).delete()
        
        # Delete grading results related to this guide
        GradingResult.query.filter_by(marking_guide_id=guide_id).delete()
        
        # Delete submissions related to this guide (and their mappings will be deleted via cascade)
        submissions = Submission.query.filter_by(marking_guide_id=guide_id).all()
        for submission in submissions:
            # Delete mappings for this submission
            Mapping.query.filter_by(submission_id=submission.id).delete()
            # Delete grading results for this submission
            GradingResult.query.filter_by(submission_id=submission.id).delete()
            # Delete the submission
            db.session.delete(submission)
        
        # Now delete the guide
        db.session.delete(guide)
        db.session.commit()

        # Clear session if this was the active guide
        if was_active_guide:
            # Clear guide-related session variables
            session.pop("guide_id", None)
            session.pop("guide_uploaded", None)
            session.pop("guide_filename", None)
            session.pop("guide_data", None)
            
            # Clear grading-related session variables
            session.pop("last_grading_progress_id", None)
            session.pop("last_grading_result", None)
            
            session.modified = True
            logger.info(f"Cleared active guide and related grading data from session: {guide_name}")

        # After deletion, update guide_uploaded status
        _update_guide_uploaded_status(current_user.id)
        if not session.get("guide_uploaded", True):
            flash(
                f'Active guide "{guide_name}" deleted and cleared from session',
                "warning",
            )
        else:
            flash(f'Marking guide "{guide_name}" deleted successfully', "success")

        logger.info(f"Guide deleted successfully: {guide_name} (ID: {guide_id})")
        return redirect(url_for("marking_guides"))

    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_guide: {str(e)}")
        db.session.rollback()
        flash("Error deleting guide from database", "error")
        return redirect(url_for("marking_guides"))
    except Exception as e:
        logger.error(f"Unexpected error in delete_guide: {str(e)}")
        flash("An unexpected error occurred while deleting the guide", "error")
        return redirect(url_for("marking_guides"))


@app.route("/api/delete-guide", methods=["POST"])
@csrf.exempt
@login_required
def api_delete_guide():
    """AJAX endpoint to delete a marking guide."""
    try:
        # Get guide ID from request
        data = request.get_json()
        if not data or "guide_id" not in data:
            return jsonify({"success": False, "error": "Guide ID is required"}), 400

        guide_id = data["guide_id"]

        # Get current user
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        # Get guide from database
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            return jsonify({"success": False, "error": "Marking guide not found"}), 404

        # Store guide name for response
        guide_name = guide.title

        # Check if this guide is currently active in session
        current_guide_id = session.get("guide_id")
        was_active_guide = str(current_guide_id) == str(guide_id)

        # Delete related records first to avoid foreign key constraint violations
        # Import required models
        from src.database.models import GradingSession, Mapping
        
        # Delete grading sessions related to this guide
        GradingSession.query.filter_by(marking_guide_id=guide_id).delete()
        
        # Delete grading results related to this guide
        GradingResult.query.filter_by(marking_guide_id=guide_id).delete()
        
        # Delete submissions related to this guide (and their mappings will be deleted via cascade)
        submissions = Submission.query.filter_by(marking_guide_id=guide_id).all()
        for submission in submissions:
            # Delete mappings for this submission
            Mapping.query.filter_by(submission_id=submission.id).delete()
            # Delete grading results for this submission
            GradingResult.query.filter_by(submission_id=submission.id).delete()
            # Delete the submission
            db.session.delete(submission)
        
        # Now delete the guide
        db.session.delete(guide)
        db.session.commit()

        # Clear session if this was the active guide
        if was_active_guide:
            # Clear guide-related session variables
            session.pop("guide_id", None)
            session.pop("guide_uploaded", None)
            session.pop("guide_filename", None)
            session.pop("guide_data", None)
            
            # Clear grading-related session variables
            session.pop("last_grading_progress_id", None)
            session.pop("last_grading_result", None)
            
            session.modified = True
            logger.info(f"Cleared active guide and related grading data from session: {guide_name}")

        logger.info(
            f"Guide deleted successfully via API: {guide_name} (ID: {guide_id})"
        )

        # After deletion, update guide_uploaded status
        _update_guide_uploaded_status(current_user.id)

        return jsonify(
            {
                "success": True,
                "message": f'Marking guide "{guide_name}" deleted successfully',
                "guide_id": guide_id,
                "guide_name": guide_name,
                "was_active_guide": was_active_guide,  # Tell frontend if this was the active guide
            }
        )

    except SQLAlchemyError as e:
        logger.error(f"Database error in api_delete_guide: {str(e)}")
        db.session.rollback()
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Database error occurred while deleting guide",
                }
            ),
            500,
        )
    except Exception as e:
        logger.error(f"Unexpected error in api_delete_guide: {str(e)}")
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500


@app.route("/api/service-status")
@csrf.exempt
def api_service_status():
    """API endpoint to check service status asynchronously."""
    try:
        status = get_service_status()
        return jsonify({"success": True, "status": status, "timestamp": time.time()})
    except Exception as e:
        logger.error(f"Error getting service status: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "status": {
                        "ocr_status": False,
                        "llm_status": False,
                        "storage_status": False,
                        "config_status": True,
                    },
                }
            ),
            500,
        )


@app.route("/api/delete-submission", methods=["POST"])
@csrf.exempt
def delete_submission():
    """API endpoint to delete a submission."""
    try:
        logger.info(f"Delete submission request - Headers: {request.headers}")
        logger.info(f"Delete submission request - Data: {request.data}")
        submission_id = request.json.get("submission_id")
        if not submission_id:
            logger.warning("Delete submission: No submission_id provided.")
            return (
                jsonify({"success": False, "message": "No submission ID provided."}),
                400,
            )

        current_user = get_current_user()
        if not current_user:
            logger.warning(
                f"Delete submission: Unauthorized attempt from IP: {request.remote_addr}"
            )
            return (
                jsonify({"success": False, "message": "Authentication required."}),
                401,
            )

        try:
            submission = Submission.query.filter_by(
                id=submission_id, user_id=current_user.id
            ).first()
            if submission:
                db.session.delete(submission)
                db.session.commit()
                logger.info(
                    f"Submission {submission_id} deleted successfully from database for user {current_user.id}."
                )
                add_recent_activity(
                    "submission_deleted",
                    f"Submission {submission_id[:8]}... deleted.",
                    "trash",
                )
                
                # Update session data after deletion
                # Re-fetch recent submissions to ensure session data is fresh
                recent_submissions = (
                    Submission.query.filter_by(user_id=current_user.id)
                    .order_by(Submission.created_at.desc())
                    .all()
                )
                session["submissions"] = [s.to_dict() for s in recent_submissions]
                
                # Update submission counts in session
                submission_stats = (
                    db.session.query(
                        db.func.count(Submission.id).label("total"),
                        db.func.count(
                            db.case((Submission.processing_status == "completed", 1))
                        ).label("processed"),
                    )
                    .filter(Submission.user_id == current_user.id)
                    .filter_by(archived=False)
                    .first()
                )

                session["total_submissions"] = submission_stats.total if submission_stats else 0
                session["processed_submissions"] = submission_stats.processed if submission_stats else 0
                session.modified = True  # Mark session as modified to ensure changes are saved
                
                return jsonify(
                    {"success": True, "message": "Submission deleted successfully."}
                )
            else:
                logger.warning(
                    f"Submission {submission_id} not found or unauthorized for user {current_user.id}."
                )
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Submission not found or unauthorized.",
                        }
                    ),
                    404,
                )

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error deleting submission {submission_id} for user {current_user.id}: {str(e)}"
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Database error occurred while deleting submission.",
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Error deleting submission: {str(e)}")
        return jsonify({"success": False, "message": "Internal server error."}), 500


@app.route("/api/results-grouped", methods=["GET"])
@login_required
def get_grouped_results():
    """API endpoint to get grading results grouped by marking guide."""
    try:
        from src.database.models import GradingResult, MarkingGuide
        from sqlalchemy import func
        
        # Get all grading results with their associated marking guides
        results_query = db.session.query(
            GradingResult,
            MarkingGuide.title.label('guide_title'),
            MarkingGuide.filename.label('guide_filename'),
            MarkingGuide.total_marks.label('guide_total_marks')
        ).join(
            MarkingGuide, GradingResult.marking_guide_id == MarkingGuide.id
        ).filter(
            MarkingGuide.user_id == current_user.id
        ).order_by(
            MarkingGuide.title,
            GradingResult.updated_at.desc()
        ).all()
        
        # Group results by marking guide
        grouped_results = {}
        
        for result, guide_title, guide_filename, guide_total_marks in results_query:
            guide_id = result.marking_guide_id
            
            if guide_id not in grouped_results:
                grouped_results[guide_id] = {
                    "guide_id": guide_id,
                    "guide_title": guide_title,
                    "guide_filename": guide_filename,
                    "guide_total_marks": guide_total_marks,
                    "results": [],
                    "summary": {
                        "total_submissions": 0,
                        "average_score": 0,
                        "highest_score": 0,
                        "lowest_score": 100
                    }
                }
            
            # Check if submission exists
            if not result.submission:
                continue
                
            # Only keep the latest result per submission_id to avoid duplicates
            existing_result = next(
                (r for r in grouped_results[guide_id]["results"] 
                 if r["submission_id"] == result.submission_id), None
            )
            
            if existing_result:
                # Compare timestamps and keep the more recent one
                if result.updated_at > datetime.fromisoformat(existing_result["updated_at"].replace('Z', '+00:00')):
                    # Remove the older result
                    grouped_results[guide_id]["results"].remove(existing_result)
                else:
                    # Skip this older result
                    continue
            
            # Parse detailed feedback for question breakdown
            detailed_feedback = result.detailed_feedback or {}
            criteria_scores = []
            
            if detailed_feedback and isinstance(detailed_feedback, dict):
                if "criteria_scores" in detailed_feedback:
                    criteria_scores = detailed_feedback.get("criteria_scores", [])
                elif "mappings" in detailed_feedback:
                    mappings = detailed_feedback.get("mappings", [])
                    for mapping in mappings:
                        if isinstance(mapping, dict):
                            points_earned = mapping.get("grade_score", 0)
                            points_possible = mapping.get("max_score", 1)
                            percentage = (points_earned / points_possible * 100) if points_possible > 0 else 0
                            
                            criteria_scores.append({
                                "question_id": mapping.get("guide_id", ""),
                                "description": mapping.get("guide_text", "Question"),
                                "points_earned": points_earned,
                                "points_possible": points_possible,
                                "percentage": round(percentage, 1),
                                "feedback": mapping.get("feedback", "")
                            })
            
            # If no criteria_scores found, create a default one
            if not criteria_scores:
                criteria_scores = [{
                    "question_id": "default",
                    "description": "Overall Assessment",
                    "points_earned": result.score,
                    "points_possible": result.max_score,
                    "percentage": result.percentage,
                    "feedback": result.feedback or "No detailed feedback available"
                }]
            
            # Calculate letter grade
            letter_grade = get_letter_grade(result.percentage)
            
            result_data = {
                "submission_id": result.submission_id,
                "filename": result.submission.filename,
                "score": result.percentage,
                "raw_score": result.score,
                "max_score": result.max_score,
                "letter_grade": letter_grade,
                "total_questions": len(criteria_scores),
                "graded_at": result.created_at.isoformat() if result.created_at else "",
                "updated_at": result.updated_at.isoformat() if result.updated_at else "",
                "criteria_scores": criteria_scores,
                "feedback": result.feedback
            }
            
            grouped_results[guide_id]["results"].append(result_data)
        
        # Calculate summaries for each guide
        for guide_data in grouped_results.values():
            results = guide_data["results"]
            if results:
                scores = [r["score"] for r in results]
                guide_data["summary"] = {
                    "total_submissions": len(results),
                    "average_score": round(sum(scores) / len(scores), 1),
                    "highest_score": max(scores),
                    "lowest_score": min(scores)
                }
        
        # Convert to list format for frontend
        response_data = list(grouped_results.values())
        
        return jsonify({
            "success": True,
            "grouped_results": response_data,
            "total_guides": len(response_data),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    except Exception as e:
        logger.error(f"Error fetching grouped results: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch grouped results"}), 500


@app.route("/api/delete-grading-result", methods=["POST"])
@csrf.exempt
def delete_grading_result():
    """API endpoint to delete a grading result."""
    try:
        grading_result_id = request.json.get("grading_result_id")
        if not grading_result_id:
            logger.warning("Delete grading result: No grading_result_id provided.")
            return (
                jsonify(
                    {"success": False, "message": "No grading result ID provided."}
                ),
                400,
            )

        grading_result = GradingResult.query.get(grading_result_id)
        if grading_result:
            db.session.delete(grading_result)
            db.session.commit()
            logger.info(
                f"Grading result {grading_result_id} deleted successfully from database."
            )
            add_recent_activity(
                "grading_result_deleted",
                f"Grading result {grading_result_id[:8]}... deleted.",
                "trash",
            )
            return jsonify(
                {"success": True, "message": "Grading result deleted successfully."}
            )
        else:
            logger.warning(
                f"Grading result {grading_result_id} not found for deletion."
            )
            return (
                jsonify({"success": False, "message": "Grading result not found."}),
                404,
            )

    except Exception as e:
        logger.error(f"Error deleting grading result: {str(e)}")
        return jsonify({"success": False, "message": "Internal server error."}), 500


# Duplicate route removed - using /api/cache/clear instead


# Duplicate route removed - using earlier /api/cache/stats definition


# Flask-Limiter removed - no limits on LLM functions
# limiter = Limiter(key_func=get_remote_address)
# limiter.init_app(app)

@app.route('/cache-management')
@login_required
def cache_management():
    """Cache management interface for AI optimization monitoring"""
    return render_template('cache_management.html')

@app.route('/api/health')
def health_check():
    """Health check for DB, Redis, Celery, and SocketIO."""
    status = {'db': False, 'redis': False, 'celery': False, 'socketio': False}
    errors = {}
    # DB check
    try:
        db.session.execute('SELECT 1')
        status['db'] = True
    except Exception as e:
        errors['db'] = str(e)
    # Redis check - removed
    status['redis'] = True  # Always true since Redis is no longer used
    # Celery check
    try:
        from src.services.background_tasks import celery_app
        i = celery_app.control.inspect()
        active = i.active()
        if active is not None:
            status['celery'] = True
    except Exception as e:
        errors['celery'] = str(e)
    # SocketIO check
    try:
        if socketio.server is not None:
            status['socketio'] = True
    except Exception as e:
        errors['socketio'] = str(e)
    ok = all(status.values())
    return jsonify({'ok': ok, 'status': status, 'errors': errors}), (200 if ok else 503)

# Rate limiting removed from background job endpoints
@app.route("/api/start-background-ocr", methods=["POST"])
@login_required
@csrf.exempt
def start_background_ocr():
    # ... existing code ...
    pass

@app.route("/api/start-background-grading", methods=["POST"])
@login_required
@csrf.exempt
def start_background_grading():
    # ... existing code ...
    pass

@app.route("/api/download-report/<submission_id>")
@login_required
@csrf.exempt
def download_report(submission_id):
    # ... existing code ...
    pass

# Dashboard stats API
@app.route("/api/dashboard-stats", methods=["GET"])
@login_required
def dashboard_stats():
    """Get dashboard statistics."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        # Get submission counts
        total_submissions, processed_submissions = sync_session_submission_counts(current_user.id)
        
        # Get last score
        from src.database.models import GradingResult, Submission
        avg_result = (
            db.session.query(db.func.avg(GradingResult.percentage))
            .join(Submission, GradingResult.submission_id == Submission.id)
            .filter(Submission.user_id == current_user.id)
            .scalar()
        )
        last_score = round(avg_result, 1) if avg_result else 0
        
        # Update session
        session["last_score"] = last_score
        session.modified = True
        
        # Get service status
        service_status = get_service_status()
        
        return jsonify({
            "success": True,
            "stats": {
                "totalSubmissions": total_submissions,
                "processedSubmissions": processed_submissions,
                "lastScore": last_score,
                "serviceStatus": service_status
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# Supported formats API
@app.route("/api/upload/supported-formats", methods=["GET"])
@login_required
def get_supported_formats():
    """Get list of supported file formats for upload."""
    try:
        # Get allowed file types from config
        allowed_types = getattr(config, 'ALLOWED_FILE_TYPES', [
            ".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"
        ])
        
        max_file_size = getattr(config, 'MAX_FILE_SIZE', 20971520)  # 20MB default
        
        return jsonify({
            "success": True,
            "data": {
                "supportedFormats": allowed_types,
                "maxFileSize": max_file_size,
                "maxFileSizeFormatted": f"{max_file_size // (1024*1024)}MB"
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting supported formats: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# Submission details API
@app.route("/api/submission-details/<submission_id>", methods=["GET"])
@login_required
def submission_details(submission_id):
    """Get detailed information about a submission."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        from src.database.models import Submission, GradingResult
        
        # Get submission
        submission = Submission.query.filter_by(
            id=submission_id, 
            user_id=current_user.id
        ).first()
        
        if not submission:
            return jsonify({"success": False, "error": "Submission not found"}), 404
        
        # Get grading result if available
        grading_result = GradingResult.query.filter_by(submission_id=submission_id).first()
        
        details = {
            "filename": submission.filename,
            "status": "Processed" if submission.processed else "Pending",
            "uploaded_at": submission.created_at.strftime("%Y-%m-%d %H:%M") if submission.created_at else "Unknown",
            "score": grading_result.percentage if grading_result else None,
            "ocr_status": "Completed" if submission.text_content else "Pending",
            "ai_status": "Completed" if grading_result else "Pending",
            "question_count": len(grading_result.question_results) if grading_result and hasattr(grading_result, 'question_results') else 0,
            "feedback": grading_result.feedback if grading_result else None
        }
        
        return jsonify({
            "success": True,
            "details": details
        })
        
    except Exception as e:
        logger.error(f"Error getting submission details: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# Submission statuses API
@app.route("/api/submission-statuses", methods=["GET"])
@login_required
def submission_statuses():
    """Get status of all submissions."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        from src.database.models import Submission
        
        submissions = Submission.query.filter_by(user_id=current_user.id).all()
        
        submission_data = []
        for submission in submissions:
            # Use processing_status if available, otherwise fall back to processed boolean
            status = submission.processing_status or ('completed' if submission.processed else 'pending')
            
            submission_data.append({
                "id": submission.id,
                "filename": submission.filename,
                "processing_status": status,
                "created_at": submission.created_at.strftime("%Y-%m-%d %H:%M") if submission.created_at else "Unknown"
            })
        
        return jsonify({
            "success": True,
            "submissions": submission_data
        })
        
    except Exception as e:
        logger.error(f"Error getting submission statuses: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/update-submission-status", methods=["POST"])
@login_required
def update_submission_status():
    """Update submission processing status."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        data = request.get_json()
        submission_id = data.get('submission_id')
        new_status = data.get('status')
        
        if not submission_id or not new_status:
            return jsonify({"success": False, "error": "Missing submission_id or status"}), 400
            
        valid_statuses = ['pending', 'processing', 'completed', 'failed']
        if new_status not in valid_statuses:
            return jsonify({"success": False, "error": f"Invalid status. Must be one of: {valid_statuses}"}), 400

        from src.database.models import Submission
        
        submission = Submission.query.filter_by(
            id=submission_id, 
            user_id=current_user.id
        ).first()
        
        if not submission:
            return jsonify({"success": False, "error": "Submission not found"}), 404
            
        # Update status
        submission.processing_status = new_status
        if new_status == 'completed':
            submission.processed = True
        elif new_status in ['pending', 'processing']:
            submission.processed = False
            
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Submission status updated to {new_status}",
            "submission": {
                "id": submission.id,
                "filename": submission.filename,
                "processing_status": submission.processing_status,
                "processed": submission.processed
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating submission status: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

        return jsonify({"success": False, "error": str(e)}), 500


# Export results API
@app.route("/api/export-results", methods=["GET", "POST"])
@login_required
def export_results():
    """Export grading results."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        from src.database.models import GradingResult, Submission
        import json
        import os
        from datetime import datetime
        
        # Get all grading results for the user
        results = (
            db.session.query(GradingResult, Submission)
            .join(Submission, GradingResult.submission_id == Submission.id)
            .filter(Submission.user_id == current_user.id)
            .all()
        )
        
        if not results:
            return jsonify({"success": False, "error": "No results to export"}), 400
        
        # Prepare export data
        export_data = {
            "export_date": datetime.now().isoformat(),
            "user_id": current_user.id,
            "total_submissions": len(results),
            "results": []
        }
        
        for grading_result, submission in results:
            result_data = {
                "submission_id": submission.id,
                "filename": submission.filename,
                "score": grading_result.percentage,
                "letter_grade": grading_result.letter_grade,
                "graded_at": grading_result.created_at.isoformat() if grading_result.created_at else None,
                "feedback": grading_result.feedback
            }
            export_data["results"].append(result_data)
        
        # Save to file
        export_filename = f"results_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_path = os.path.join("output", export_filename)
        
        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return jsonify({
            "success": True,
            "message": "Results exported successfully",
            "download_url": f"/download/{export_filename}",
            "filename": export_filename
        })
        
    except Exception as e:
        logger.error(f"Error exporting results: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# Download exported file
@app.route("/download/<filename>")
@login_required
def download_file(filename):
    """Download exported file."""
    try:
        from flask import send_from_directory
        return send_from_directory("output", filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({"error": "File not found"}), 404


# Marking guide usage status API
@app.route("/api/guide-usage-status", methods=["GET"])
@login_required
def guide_usage_status():
    """Check if marking guide is set to be used."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        from src.database.models import MarkingGuide
        
        # Get the current guide
        guide = MarkingGuide.query.filter_by(user_id=current_user.id).first()
        
        guide_status = {
            "guide_exists": guide is not None,
            "guide_enabled": guide.enabled if guide else False,
            "guide_filename": guide.filename if guide else None,
            "guide_uploaded_at": guide.created_at.isoformat() if guide and guide.created_at else None
        }
        
        return jsonify({
            "success": True,
            "guide_status": guide_status
        })
        
    except Exception as e:
        logger.error(f"Error checking guide usage status: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# Enhanced Processing API Endpoints
@app.route("/api/enhanced-processing/start", methods=["POST"])
@login_required
@csrf.exempt
def start_enhanced_processing():
    """Start the enhanced LLM-driven processing pipeline with specific marking guide."""
    try:
        import uuid
        from datetime import datetime
        
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        
        # Get current user
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "User not authenticated"}), 401
        
        # Get request data
        data = request.get_json() or {}
        marking_guide_id = data.get('marking_guide_id') or session.get('guide_id')
        
        # Debug logging
        app.logger.info(f"Enhanced processing request data: {data}")
        app.logger.info(f"Marking guide ID from request: {data.get('marking_guide_id')}")
        app.logger.info(f"Marking guide ID from session: {session.get('guide_id')}")
        app.logger.info(f"Final marking guide ID: {marking_guide_id}")
        
        if not marking_guide_id:
            return jsonify({
                "success": False, 
                "error": "No marking guide selected. Please select a marking guide first."
            }), 400
        
        # Load the specific marking guide
        marking_guide = MarkingGuide.query.filter_by(
            id=marking_guide_id, 
            user_id=user_id
        ).first()
        
        if not marking_guide:
            return jsonify({
                "success": False, 
                "error": "Selected marking guide not found or access denied."
            }), 404
        
        # Get submission IDs from request or use all submissions for the guide
        submission_ids = data.get('submission_ids', [])
        
        if submission_ids:
            # Load specific submissions
            submissions = Submission.query.filter(
                Submission.id.in_(submission_ids),
                Submission.marking_guide_id == marking_guide_id,
                Submission.user_id == user_id
            ).all()
        else:
            # Load all submissions for this marking guide
            submissions = Submission.query.filter_by(
                marking_guide_id=marking_guide_id,
                user_id=user_id
            ).all()
        
        if not submissions:
            return jsonify({
                "success": False, 
                "error": f"No submissions found for marking guide '{marking_guide.filename}'. Please upload submissions first."
            }), 400
        
        # Initialize progress tracking
        progress_data = {
            "task_id": task_id,
            "status": "started",
            "progress": 0,
            "current_step": "Initializing enhanced processing pipeline",
            "message": f"Starting LLM-driven workflow for guide: {marking_guide.filename}",
            "started_at": datetime.utcnow().isoformat(),
            "marking_guide_id": marking_guide_id,
            "marking_guide_name": marking_guide.filename,
            "submissions_count": len(submissions)
        }
        
        # Store progress in app storage (works better with background threads)
        if not hasattr(app, 'enhanced_progress'):
            app.enhanced_progress = {}
        app.enhanced_progress[task_id] = progress_data
        
        # Start background processing with specific guide
        import threading
        thread = threading.Thread(
            target=process_enhanced_pipeline_with_context, 
            args=(task_id, user_id, marking_guide_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": f"Enhanced processing started for '{marking_guide.filename}'"
        })
        
    except Exception as e:
        logger.error(f"Error starting enhanced processing: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/enhanced-processing/progress/<task_id>", methods=["GET"])
@login_required
@csrf.exempt
def get_enhanced_processing_progress(task_id):
    """Get progress of enhanced processing task."""
    try:
        # Get progress from app storage (in production, use Redis or database)
        if not hasattr(app, 'enhanced_progress'):
            app.enhanced_progress = {}
        
        progress_data = app.enhanced_progress.get(task_id)
        
        if not progress_data:
            # Fallback to session for backwards compatibility
            progress_key = f"enhanced_progress_{task_id}"
            progress_data = session.get(progress_key)
            
        if not progress_data:
            return jsonify({
                "success": False,
                "error": "Task not found or expired"
            }), 404
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "status": progress_data.get("status", "unknown"),
            "progress": progress_data.get("progress", 0),
            "current_step": progress_data.get("current_step", "Processing"),
            "message": progress_data.get("message", "Processing..."),
            "results": progress_data.get("results", {})
        })
        
    except Exception as e:
        logger.error(f"Error getting enhanced processing progress: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


def perform_intelligent_grading(llm_service, guide_type, guide_items, submission_data, total_points, max_questions_to_answer=None):
    """Perform intelligent grading of a submission against marking guide items.
    
    Args:
        llm_service: LLM service instance
        guide_type: Type of guide (QUESTION_ONLY, ANSWER_ONLY, MIXED)
        guide_items: List of guide items with questions/answers
        submission_data: Dict with submission content and metadata
        total_points: Total points available
        max_questions_to_answer: Maximum questions to grade (optional)
        
    Returns:
        Dict with grading results
    """
    try:
        # Limit questions if max_questions_to_answer is specified
        items_to_grade = guide_items
        if max_questions_to_answer and len(guide_items) > max_questions_to_answer:
            items_to_grade = guide_items[:max_questions_to_answer]
            logger.info(f"Limiting grading to {max_questions_to_answer} questions out of {len(guide_items)}")
        
        # Create simplified grading prompt that's more likely to return valid JSON
        system_prompt = """You are an expert exam grader. You must respond with valid JSON only. 
Do not include any text before or after the JSON. The JSON must be properly formatted and complete."""

        # Calculate points per item for fallback
        points_per_item = total_points // len(items_to_grade) if items_to_grade else total_points
        
        grading_prompt = f"""Grade this student submission against the marking guide. Return ONLY valid JSON.

MARKING GUIDE:
{chr(10).join([f"Item {item['item_number']}: {item.get('question', item.get('answer', 'Assessment item'))} (Points: {item.get('points', points_per_item)})" for item in items_to_grade])}

STUDENT SUBMISSION:
Student: {submission_data.get('student_name', 'Unknown')}
Content: {submission_data['content']}

Return this exact JSON structure:
{{
    "total_score": 0,
    "max_possible_score": {total_points},
    "percentage": 0.0,
    "overall_feedback": "Brief overall assessment",
    "question_grades": [
        {{
            "question_number": 1,
            "points_awarded": 0,
            "max_points": {points_per_item},
            "feedback": "Brief feedback"
        }}
    ]
}}"""
        
        # Get grading response from LLM
        grading_response = llm_service.generate_response(
            system_prompt=system_prompt,
            user_prompt=grading_prompt,
            temperature=0.1
        )
        
        # Parse the response with better error handling
        import json
        import re
        
        try:
            # Clean the response - remove any text before/after JSON
            cleaned_response = grading_response.strip()
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if json_match:
                cleaned_response = json_match.group(0)
            
            grading_result = json.loads(cleaned_response)
            
            # Validate required fields
            if 'total_score' not in grading_result:
                grading_result['total_score'] = 0
            if 'max_possible_score' not in grading_result:
                grading_result['max_possible_score'] = total_points
            if 'percentage' not in grading_result:
                grading_result['percentage'] = 0.0
            if 'overall_feedback' not in grading_result:
                grading_result['overall_feedback'] = "Grading completed"
            if 'question_grades' not in grading_result:
                grading_result['question_grades'] = []
                
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw LLM response: {grading_response[:500]}...")
            
            # Create a fallback grading result with partial credit
            estimated_score = min(total_points * 0.5, 50)  # Give 50% or 50 points, whichever is lower
            grading_result = {
                'total_score': estimated_score,
                'max_possible_score': total_points,
                'percentage': (estimated_score / total_points * 100) if total_points > 0 else 0,
                'overall_feedback': f"Automated grading completed. Raw response could not be parsed as JSON.",
                'question_grades': [{
                    'question_number': 1,
                    'points_awarded': estimated_score,
                    'max_points': total_points,
                    'feedback': 'Partial credit awarded due to parsing error'
                }]
            }
        
        # Add submission metadata
        grading_result['submission_id'] = submission_data['id']
        grading_result['submission_filename'] = submission_data['filename']
        grading_result['student_name'] = submission_data.get('student_name', 'Unknown')
        
        # Ensure percentage is calculated
        if grading_result['max_possible_score'] > 0:
            grading_result['percentage'] = (grading_result['total_score'] / grading_result['max_possible_score']) * 100
        else:
            grading_result['percentage'] = 0.0
        
        # Create feedback summary
        feedback_parts = []
        if grading_result.get('overall_feedback'):
            feedback_parts.append(grading_result['overall_feedback'])
        
        if grading_result.get('strengths'):
            feedback_parts.append(f"Strengths: {', '.join(grading_result['strengths'])}")
        
        if grading_result.get('areas_for_improvement'):
            feedback_parts.append(f"Areas for improvement: {', '.join(grading_result['areas_for_improvement'])}")
        
        grading_result['feedback'] = '\n\n'.join(feedback_parts)
        
        return grading_result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse grading response as JSON: {e}")
        # Return fallback result
        return {
            'submission_id': submission_data['id'],
            'submission_filename': submission_data['filename'],
            'student_name': submission_data.get('student_name', 'Unknown'),
            'total_score': 0,
            'max_possible_score': total_points,
            'percentage': 0.0,
            'feedback': f"Grading failed due to response parsing error: {str(e)}",
            'question_grades': [],
            'overall_feedback': "Unable to complete grading due to technical error"
        }
        
    except Exception as e:
        logger.error(f"Error in intelligent grading: {e}")
        # Return fallback result
        return {
            'submission_id': submission_data['id'],
            'submission_filename': submission_data['filename'],
            'student_name': submission_data.get('student_name', 'Unknown'),
            'total_score': 0,
            'max_possible_score': total_points,
            'percentage': 0.0,
            'feedback': f"Grading failed: {str(e)}",
            'question_grades': [],
            'overall_feedback': "Unable to complete grading due to technical error"
        }


def process_enhanced_pipeline_with_context(task_id, user_id, marking_guide_id=None):
    """Wrapper function to run enhanced pipeline with Flask application context."""
    try:
        logger.info(f"Starting enhanced processing pipeline with context for task {task_id}, guide {marking_guide_id}")
        with app.app_context():
            process_enhanced_pipeline(task_id, user_id, marking_guide_id)
        logger.info(f"Enhanced processing pipeline completed for task {task_id}")
    except Exception as e:
        logger.error(f"Error in enhanced processing pipeline wrapper: {str(e)}")
        # Update error progress even if context fails
        try:
            with app.app_context():
                error_progress = {
                    "task_id": task_id,
                    "status": "failed",
                    "progress": 0,
                    "current_step": "Error",
                    "message": f"Processing failed: {str(e)}",
                    "error": str(e),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                if not hasattr(app, 'enhanced_progress'):
                    app.enhanced_progress = {}
                app.enhanced_progress[task_id] = error_progress
        except Exception as context_error:
            logger.error(f"Failed to update error progress: {str(context_error)}")

def process_enhanced_pipeline(task_id, user_id, marking_guide_id=None):
    """Enhanced processing pipeline with intelligent marking guide analysis and best-score grading."""
    try:
        import time
        from datetime import datetime
        
        def update_progress(progress, step, message):
            """Helper to update progress with real-time updates."""
            progress_data = {
                "task_id": task_id,
                "status": "processing",
                "progress": min(progress, 100),
                "current_step": step,
                "message": message,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if not hasattr(app, 'enhanced_progress'):
                app.enhanced_progress = {}
            app.enhanced_progress[task_id] = progress_data
            
            logger.info(f"Enhanced Processing: {progress}% - {step} - {message}")
        
        # PHASE 1: Load and analyze marking guide (5-15%)
        update_progress(5, "Loading Data", "Loading marking guide from database...")
        
        # Load the specific marking guide
        marking_guide = MarkingGuide.query.filter_by(
            id=marking_guide_id, 
            user_id=user_id
        ).first()
        
        if not marking_guide:
            raise Exception(f"Marking guide {marking_guide_id} not found")
        
        # Load associated submissions
        submissions = Submission.query.filter_by(
            marking_guide_id=marking_guide_id,
            user_id=user_id
        ).all()
        
        if not submissions:
            raise Exception(f"No submissions found for marking guide {marking_guide.filename}")
        
        update_progress(8, "Data Loaded", f"Loaded guide '{marking_guide.filename}' with {len(submissions)} submissions")
        
        # Initialize LLM service
        try:
            from src.services.consolidated_llm_service import ConsolidatedLLMService
            llm_service = ConsolidatedLLMService()
            
            if not llm_service.is_available():
                raise Exception("LLM service is not available")
                
            update_progress(10, "LLM Ready", "LLM service initialized and ready")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {str(e)}")
            raise Exception(f"LLM service initialization failed: {str(e)}")
        
        # PHASE 2: Analyze marking guide structure (15-30%)
        update_progress(15, "Analyzing Guide", f"Analyzing marking guide structure: {marking_guide.filename}")
        
        # Use pre-extracted content from database
        guide_content = marking_guide.content_text or ""
        if not guide_content:
            raise Exception(f"Marking guide '{marking_guide.filename}' has no extracted content. Please re-upload the marking guide.")
        
        # Use LLM to determine guide type and extract structure
        guide_analysis_prompt = f"""
Analyze this marking guide and determine its structure. Classify it as one of:
1. QUESTION_ONLY: Contains only questions without model answers
2. ANSWER_ONLY: Contains only model answers without explicit questions  
3. MIXED: Contains both questions and their corresponding answers

Then extract the structured content accordingly.

Marking Guide Content:
{guide_content}

Return a JSON response with this structure:
{{
    "guide_type": "QUESTION_ONLY|ANSWER_ONLY|MIXED",
    "total_items": <number>,
    "items": [
        {{
            "item_number": <number>,
            "question": "<question text if available>",
            "answer": "<answer text if available>",
            "points": <estimated points if mentioned>,
            "section": "<section name if applicable>"
        }}
    ],
    "grading_criteria": "<any specific grading instructions found>",
    "total_points": <total points if determinable>
}}
"""
        
        try:
            guide_analysis_response = llm_service.generate_response(
                system_prompt="You are an expert at analyzing educational marking guides and extracting their structure.",
                user_prompt=guide_analysis_prompt,
                temperature=0.1
            )
            
            import json
            guide_analysis = json.loads(guide_analysis_response)
            guide_type = guide_analysis.get("guide_type", "MIXED")
            guide_items = guide_analysis.get("items", [])
            total_points = guide_analysis.get("total_points", 100)
            
            logger.info(f"Guide analysis complete: Type={guide_type}, Items={len(guide_items)}, Points={total_points}")
            
        except Exception as e:
            logger.warning(f"Guide analysis failed, using fallback: {str(e)}")
            # Fallback: treat as mixed type
            guide_type = "MIXED"
            guide_items = [{"item_number": 1, "question": "General Assessment", "answer": guide_content, "points": 100}]
            total_points = 100
        
        update_progress(25, "Guide Analyzed", f"Guide type: {guide_type}, Found {len(guide_items)} items")
        
        # PHASE 3: Load submissions from database (30-50%)
        processed_submissions = []
        
        for i, submission in enumerate(submissions):
            progress = 30 + (20 * i / len(submissions))
            update_progress(int(progress), "Loading Submissions", f"Loading: {submission.filename}")
            
            # Use pre-extracted content from database
            submission_content = submission.content_text
            
            if not submission_content:
                logger.warning(f"No extracted content available for submission {submission.filename}. Skipping.")
                continue
                
            processed_submissions.append({
                'id': submission.id,
                'filename': submission.filename,
                'content': submission_content,
                'student_name': submission.student_name
            })
        
        update_progress(50, "Submissions Loaded", f"Loaded {len(processed_submissions)} submissions from database")
        
        # PHASE 4: Intelligent mapping and grading (50-90%)
        grading_results = []
        
        for i, submission_data in enumerate(processed_submissions):
            progress = 50 + (40 * i / len(processed_submissions))
            update_progress(int(progress), "AI Grading", f"Grading: {submission_data['filename']}")
            
            try:
                # Create comprehensive grading prompt based on guide type
                grading_result = perform_intelligent_grading(
                    llm_service, 
                    guide_type, 
                    guide_items, 
                    submission_data, 
                    total_points,
                    marking_guide.max_questions_to_answer
                )
                
                if grading_result:
                    grading_results.append(grading_result)
                    logger.info(f"Successfully graded {submission_data['filename']}: {grading_result['total_score']}/{grading_result['max_possible_score']}")
                
            except Exception as grading_error:
                logger.error(f"Grading failed for {submission_data['filename']}: {grading_error}")
                continue
        
        update_progress(90, "Saving Results", "Saving grading results to database...")
        
        # PHASE 5: Save results to database (90-100%)
        saved_count = 0
        for result in grading_results:
            try:
                # Create GradingResult record
                grading_record = GradingResult(
                    submission_id=result['submission_id'],
                    marking_guide_id=marking_guide_id,
                    score=result['total_score'],
                    max_score=result['max_possible_score'],
                    percentage=result['percentage'],
                    feedback=result['feedback'],
                    detailed_feedback={
                        'question_grades': result.get('question_grades', []),
                        'guide_type': guide_type,
                        'task_id': task_id,
                        'grading_method': 'enhanced_llm_processing',
                        'overall_feedback': result.get('overall_feedback', ''),
                        'strengths': result.get('strengths', []),
                        'areas_for_improvement': result.get('areas_for_improvement', [])
                    },
                    grading_method='enhanced_llm',
                    confidence=0.85
                )
                
                db.session.add(grading_record)
                saved_count += 1
                
            except Exception as save_error:
                logger.error(f"Failed to save result for submission {result['submission_id']}: {save_error}")
        
        # Commit all results
        db.session.commit()
        
        update_progress(100, "Complete", f"Enhanced processing completed! Graded {saved_count} submissions")
        
        # Update final progress
        final_progress = {
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "current_step": "Complete",
            "message": f"Successfully processed {saved_count} submissions using {guide_type} marking guide",
            "results": {
                "guide_type": guide_type,
                "guide_items_count": len(guide_items),
                "submissions_processed": len(processed_submissions),
                "results_saved": saved_count,
                "total_points": total_points
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if not hasattr(app, 'enhanced_progress'):
            app.enhanced_progress = {}
        app.enhanced_progress[task_id] = final_progress
        
        logger.info(f"Enhanced processing completed for task {task_id}: {saved_count} results saved")

    except Exception as e:
        logger.error(f"Error in enhanced processing pipeline: {str(e)}")
        
        # Update error progress
        error_progress = {
            "task_id": task_id,
            "status": "failed",
            "progress": 0,
            "current_step": "Error",
            "message": f"Processing failed: {str(e)}",
            "error": str(e),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if not hasattr(app, 'enhanced_progress'):
            app.enhanced_progress = {}
        app.enhanced_progress[task_id] = error_progress


# ... audit all endpoints for @login_required and permission checks ...


def shutdown_handler(signum=None, frame=None):
    """Handle graceful shutdown of the application."""
    logger.info("Shutdown signal received, cleaning up...")
    
    try:
        # Stop file cleanup service if it exists
        if 'file_cleanup_service' in globals() and file_cleanup_service:
            file_cleanup_service.stop_scheduled_cleanup()
            logger.info("File cleanup service stopped")
    except Exception as e:
        logger.error(f"Error stopping file cleanup service: {e}")
    
    try:
        # Stop any other background services
        if 'performance_optimizer' in globals():
            # Add any cleanup for performance optimizer if needed
            pass
    except Exception as e:
        logger.error(f"Error stopping performance optimizer: {e}")
    
    logger.info("Application shutdown complete")
    sys.exit(0)

if __name__ == "__main__":
    logger.info("Starting Exam Grader Web Application...")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    # Register atexit handler as backup
    atexit.register(shutdown_handler)

    # Get configuration values
    host = getattr(config, "HOST", "127.0.0.1")
    port = getattr(config, "PORT", 5000)
    debug = getattr(config, "DEBUG", False)

    logger.info(create_startup_summary(host=host, port=port))
    logger.info(f"Debug mode: {debug}")

    try:
        # Use socketio.run() instead of app.run() for proper signal handling
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        shutdown_handler()
    except Exception as e:
        logger.error(f"Application error: {e}")
        shutdown_handler()

# Global cleanup function for graceful shutdown
def cleanup_services():
    """Clean up all services and connections for graceful shutdown."""
    try:
        logger.info("🧹 Starting service cleanup...")
        
        # Stop file cleanup service
        if 'file_cleanup_service' in globals() and file_cleanup_service:
            try:
                file_cleanup_service.stop_scheduled_cleanup()
                logger.info("✅ File cleanup service stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping file cleanup service: {e}")
        
        # Close SocketIO connections
        try:
            if 'socketio' in globals() and socketio:
                try:
                    # Disconnect all clients gracefully
                    if hasattr(socketio, 'server') and socketio.server:
                        # Get all connected clients and disconnect them
                        try:
                            # Disconnect all clients
                            for sid in list(socketio.server.manager.get_participants(namespace='/')):
                                socketio.server.disconnect(sid)
                        except:
                            # Fallback: try to shutdown the server directly
                            if hasattr(socketio.server, 'shutdown'):
                                socketio.server.shutdown()
                        logger.info("✅ SocketIO connections closed")
                    else:
                        logger.info("✅ SocketIO server not active")
                except Exception as inner_e:
                    logger.warning(f"⚠️ SocketIO cleanup fallback: {inner_e}")
                    # Try alternative cleanup
                    try:
                        if hasattr(socketio, 'server') and socketio.server:
                            socketio.server.shutdown()
                    except:
                        pass
                    logger.info("✅ SocketIO cleanup attempted")
        except Exception as e:
            logger.error(f"❌ Error closing SocketIO: {e}")
        
        # Close database connections
        try:
            if 'db' in globals() and db:
                try:
                    # Try with app context first
                    with app.app_context():
                        db.session.close()
                        db.engine.dispose()
                except RuntimeError:
                    # If app context not available, try direct cleanup
                    try:
                        db.session.close()
                    except:
                        pass
                    try:
                        db.engine.dispose()
                    except:
                        pass
                logger.info("✅ Database connections closed")
        except Exception as e:
            logger.error(f"❌ Error closing database: {e}")
        
        # Stop background threads
        try:
            for thread in threading.enumerate():
                if thread != threading.current_thread() and thread.daemon:
                    logger.info(f"🧵 Stopping daemon thread: {thread.name}")
                    # Give threads a moment to finish
                    thread.join(timeout=1.0)
                    # Force stop if still alive
                    if thread.is_alive():
                        logger.warning(f"🧵 Force stopping thread: {thread.name}")
        except Exception as e:
            logger.error(f"❌ Error stopping threads: {e}")
        
        logger.info("✅ Service cleanup completed")
        
        # Force exit after cleanup
        try:
            import os
            os._exit(0)
        except:
            pass
        
    except Exception as e:
        logger.error(f"❌ Error during service cleanup: {e}")

# Register cleanup function to run on exit
atexit.register(cleanup_services)

# Add signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"🛑 Received signal {signum}, initiating shutdown...")
    cleanup_services()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Shutdown endpoint for graceful shutdown
@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Endpoint to trigger graceful shutdown."""
    try:
        logger.info("🛑 Shutdown endpoint called")
        
        # Trigger cleanup
        cleanup_services()
        
        # Shutdown the Flask development server
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            logger.warning("Not running with the Werkzeug Server")
            return jsonify({'status': 'error', 'message': 'Not running with Werkzeug server'}), 500
        
        func()
        logger.info("✅ Server shutdown initiated")
        return jsonify({'status': 'success', 'message': 'Server shutting down...'})
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500