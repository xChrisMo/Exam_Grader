@echo off
REM Exam Grader Application Runner for Windows
REM Simple batch file to start the Flask application

echo ========================================
echo    Exam Grader Application Runner
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "run_app.py" (
    echo ERROR: run_app.py not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

REM Run the application
echo Starting Exam Grader Application...
echo.
python run_app.py %*

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo Application exited with an error
    pause
)
