"""
Vercel Serverless Function Entry Point for Flask App
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up Vercel-specific environment
from api.vercel_config import setup_vercel_environment
setup_vercel_environment()

# Create a minimal Flask app for Vercel
from flask import Flask, jsonify, render_template_string, request, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)

# Basic configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'vercel-deployment-key')
app.config['WTF_CSRF_ENABLED'] = True

# Initialize extensions
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Basic routes
@app.route('/')
def index():
    return jsonify({
        'status': 'ok',
        'message': 'Exam Grader API is running on Vercel',
        'service': 'exam-grader',
        'environment': 'vercel'
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'ok',
        'service': 'exam-grader',
        'environment': 'vercel',
        'version': '2.1.2'
    })

@app.route('/dashboard')
def dashboard():
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Exam Grader - Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100">
        <div class="min-h-screen flex items-center justify-center">
            <div class="max-w-md w-full bg-white rounded-lg shadow-md p-6">
                <h1 class="text-2xl font-bold text-center text-gray-800 mb-4">
                    Exam Grader
                </h1>
                <div class="text-center">
                    <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
                        <strong>Status:</strong> Running on Vercel
                    </div>
                    <p class="text-gray-600 mb-4">
                        AI-powered educational assessment platform
                    </p>
                    <div class="space-y-2">
                        <a href="/api/health" class="block bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
                            Health Check
                        </a>
                        <p class="text-sm text-gray-500">
                            Version 2.1.2 - Deployed on Vercel
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(dashboard_html)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found',
        'available_endpoints': [
            '/',
            '/api/health',
            '/dashboard'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Internal server error',
        'error': str(error)
    }), 500

# User loader (minimal implementation)
@login_manager.user_loader
def load_user(user_id):
    return None  # Simplified for Vercel deployment

# Vercel expects the app to be available as 'app'
if __name__ == "__main__":
    app.run()