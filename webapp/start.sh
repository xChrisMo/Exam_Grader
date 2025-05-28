#!/bin/bash
# Exam Grader Flask Web Application Startup Script for Linux/Mac
# This script starts the Flask web application

echo ""
echo "========================================"
echo "   Exam Grader Web Application"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python is not installed"
        echo "Please install Python 3.8+ and try again"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "Python version:"
$PYTHON_CMD --version
echo ""

# Check if we're in the right directory
if [ ! -f "exam_grader_app.py" ]; then
    echo "ERROR: exam_grader_app.py not found"
    echo "Please run this script from the webapp directory"
    exit 1
fi

# Check if Flask is installed
$PYTHON_CMD -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Flask not found. Installing dependencies..."
    echo ""
    pip3 install flask werkzeug jinja2 || pip install flask werkzeug jinja2
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install Flask"
        echo "Please install manually: pip install flask"
        exit 1
    fi
fi

echo "Starting Exam Grader Web Application..."
echo ""
echo "Dashboard will be available at: http://127.0.0.1:5000"
echo "Press Ctrl+C to stop the server"
echo ""
echo "========================================"
echo ""

# Start the Flask application
$PYTHON_CMD exam_grader_app.py

echo ""
echo "Application stopped."
