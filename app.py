#!/usr/bin/env python3
"""
Exam Grader Web Application

A Flask-based web interface for the Exam Grader application that provides
an intuitive dashboard for uploading marking guides and student submissions,
viewing grading results, and managing the grading process.
"""

import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Flask imports
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_session import Session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Application imports
from src.config.config_manager import ConfigManager
from src.parsing.parse_submission import parse_student_submission
from src.parsing.parse_guide import parse_marking_guide
from src.services.llm_service import LLMService
from src.services.grading_service import GradingService
from src.services.mapping_service import MappingService
from src.storage.results_storage import ResultsStorage
from utils.logger import setup_logger

# Initialize logger
logger = setup_logger(__name__)

class ExamGraderApp:
    """Main Flask application class for the Exam Grader web interface."""

    def __init__(self):
        """Initialize the Flask application and configure all components."""
        self.app = Flask(__name__)
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config

        # Configure Flask app
        self._configure_app()

        # Initialize extensions
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        CORS(self.app)
        Session(self.app)

        # Initialize services
        self._initialize_services()

        # Register routes
        self._register_routes()
        self._register_socketio_events()

        logger.info("Exam Grader web application initialized successfully")

    def _configure_app(self):
        """Configure Flask application settings."""
        self.app.config.update({
            'SECRET_KEY': self.config.secret_key,
            'MAX_CONTENT_LENGTH': self.config.max_file_size_mb * 1024 * 1024,
            'UPLOAD_FOLDER': os.path.join(self.config.temp_dir, 'uploads'),
            'SESSION_TYPE': 'filesystem',
            'SESSION_FILE_DIR': os.path.join(self.config.temp_dir, 'flask_session'),
            'SESSION_PERMANENT': False,
            'SESSION_USE_SIGNER': True,
            'SESSION_KEY_PREFIX': 'exam_grader:',
            'TEMPLATES_AUTO_RELOAD': self.config.debug,
            'DEBUG': self.config.debug
        })

        # Create required directories
        os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(self.app.config['SESSION_FILE_DIR'], exist_ok=True)

    def _initialize_services(self):
        """Initialize application services."""
        self.llm_service = LLMService()
        self.grading_service = GradingService(self.llm_service)
        self.mapping_service = MappingService(self.llm_service)
        self.results_storage = ResultsStorage()

        logger.info("Application services initialized")

    def _register_routes(self):
        """Register Flask routes."""

        @self.app.route('/')
        def index():
            """Professional dashboard page with advanced analytics."""
            return render_template('dashboard-professional.html',
                                 config=self.config,
                                 recent_results=self._get_recent_results())

        @self.app.route('/upload')
        def upload_page():
            """Professional upload page with enhanced drag-and-drop."""
            return render_template('upload-professional.html', config=self.config)

        @self.app.route('/results')
        def results_page():
            """Results page showing grading history."""
            return render_template('results.html',
                                 config=self.config,
                                 results=self._get_all_results())

        @self.app.route('/settings')
        def settings_page():
            """Settings and configuration page."""
            return render_template('settings.html', config=self.config)

        @self.app.route('/api/upload', methods=['POST'])
        def upload_files():
            """Handle file uploads via API."""
            try:
                if 'marking_guide' not in request.files or 'submission' not in request.files:
                    return jsonify({'error': 'Both marking guide and submission files are required'}), 400

                guide_file = request.files['marking_guide']
                submission_file = request.files['submission']

                if guide_file.filename == '' or submission_file.filename == '':
                    return jsonify({'error': 'No files selected'}), 400

                # Generate session ID for this upload
                session_id = str(uuid.uuid4())
                session['current_session'] = session_id

                # Save uploaded files
                guide_path = self._save_uploaded_file(guide_file, 'guide', session_id)
                submission_path = self._save_uploaded_file(submission_file, 'submission', session_id)

                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'guide_path': guide_path,
                    'submission_path': submission_path,
                    'message': 'Files uploaded successfully'
                })

            except RequestEntityTooLarge:
                return jsonify({'error': f'File too large. Maximum size is {self.config.max_file_size_mb}MB'}), 413
            except Exception as e:
                logger.error(f"Upload error: {str(e)}")
                return jsonify({'error': f'Upload failed: {str(e)}'}), 500

        @self.app.route('/api/process', methods=['POST'])
        def process_files():
            """Process uploaded files and start grading."""
            try:
                data = request.get_json()
                session_id = data.get('session_id')

                if not session_id:
                    return jsonify({'error': 'Session ID required'}), 400

                # Start processing in background
                self.socketio.start_background_task(self._process_files_background, session_id)

                return jsonify({
                    'success': True,
                    'message': 'Processing started',
                    'session_id': session_id
                })

            except Exception as e:
                logger.error(f"Processing error: {str(e)}")
                return jsonify({'error': f'Processing failed: {str(e)}'}), 500

        @self.app.errorhandler(404)
        def not_found(error):
            return render_template('error.html',
                                 error_code=404,
                                 error_message="Page not found"), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            return render_template('error.html',
                                 error_code=500,
                                 error_message="Internal server error"), 500

    def _register_socketio_events(self):
        """Register SocketIO event handlers."""

        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.info(f"Client connected: {request.sid}")
            emit('connected', {'message': 'Connected to Exam Grader'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info(f"Client disconnected: {request.sid}")

        @self.socketio.on('join_session')
        def handle_join_session(data):
            """Join a processing session room."""
            session_id = data.get('session_id')
            if session_id:
                join_room(session_id)
                emit('joined_session', {'session_id': session_id})
                logger.info(f"Client {request.sid} joined session {session_id}")

    def _save_uploaded_file(self, file, file_type: str, session_id: str) -> str:
        """Save an uploaded file and return the path."""
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{session_id}_{file_type}_{timestamp}_{filename}"

        file_path = os.path.join(self.app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(file_path)

        logger.info(f"Saved {file_type} file: {safe_filename}")
        return file_path

    def _get_recent_results(self, limit: int = 5) -> List[Dict]:
        """Get recent grading results for dashboard."""
        # This would typically query the results storage
        # For now, return empty list
        return []

    def _get_all_results(self) -> List[Dict]:
        """Get all grading results."""
        # This would typically query the results storage
        # For now, return empty list
        return []

    def _process_files_background(self, session_id: str):
        """Background task to process uploaded files."""
        try:
            # Emit progress updates
            self.socketio.emit('progress', {
                'session_id': session_id,
                'stage': 'parsing',
                'message': 'Parsing uploaded files...',
                'progress': 10
            }, room=session_id)

            # This would contain the actual processing logic
            # For now, simulate processing
            import time
            time.sleep(2)

            self.socketio.emit('progress', {
                'session_id': session_id,
                'stage': 'grading',
                'message': 'Grading submission...',
                'progress': 50
            }, room=session_id)

            time.sleep(3)

            self.socketio.emit('progress', {
                'session_id': session_id,
                'stage': 'complete',
                'message': 'Processing complete!',
                'progress': 100,
                'results': {'score': 85, 'feedback': 'Good work overall'}
            }, room=session_id)

        except Exception as e:
            logger.error(f"Background processing error: {str(e)}")
            self.socketio.emit('error', {
                'session_id': session_id,
                'message': f'Processing failed: {str(e)}'
            }, room=session_id)

    def run(self, host: str = None, port: int = None, debug: bool = None):
        """Run the Flask application."""
        host = host or self.config.host
        port = port or self.config.port
        debug = debug if debug is not None else self.config.debug

        logger.info(f"Starting Exam Grader web application on {host}:{port}")
        self.socketio.run(self.app, host=host, port=port, debug=debug)


def create_app() -> Flask:
    """Factory function to create Flask app instance."""
    exam_grader = ExamGraderApp()
    return exam_grader.app


if __name__ == '__main__':
    # Create and run the application
    exam_grader = ExamGraderApp()
    exam_grader.run()
