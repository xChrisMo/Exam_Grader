@echo off
REM Exam Grader Flask Web Application Startup Script for Windows
REM This script starts the Flask web application

echo.
echo ========================================
echo   Exam Grader Web Application
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo Python version:
python --version
echo.

REM Check if we're in the right directory
if not exist "exam_grader_app.py" (
    echo ERROR: exam_grader_app.py not found
    echo Please run this script from the webapp directory
    pause
    exit /b 1
)

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Flask not found. Installing dependencies...
    echo.
    pip install flask werkzeug jinja2
    if errorlevel 1 (
        echo ERROR: Failed to install Flask
        echo Please install manually: pip install flask
        pause
        exit /b 1
    )
)

echo Starting Exam Grader Web Application...
echo.
echo Dashboard will be available at: http://127.0.0.1:5000
echo Press Ctrl+C to stop the server
echo.
echo ========================================
echo.

REM Start the Flask application
python exam_grader_app.py

echo.
echo Application stopped.
pause
