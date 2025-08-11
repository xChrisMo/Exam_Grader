@echo off
echo ========================================
echo  Exam Grader - Extended Timeout Mode
echo ========================================
echo.
echo Starting application with optimized settings for AI processing...
echo - Request timeout: 10 minutes
echo - Optimized for long-running grading operations
echo - Enhanced error handling and recovery
echo.

REM Set environment variables for extended timeouts
set USE_WAITRESS=true
set REQUEST_TIMEOUT=600
set SOCKET_TIMEOUT=600
set DEBUG=false

REM Start the application
python run_with_timeout.py

pause