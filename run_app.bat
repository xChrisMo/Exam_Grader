@echo off
echo Exam Grader - Web Application
echo --------------------------------
echo.

REM Check if Python is in PATH
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python not found in PATH.
    echo Please install Python and make sure it's in your PATH.
    echo.
    pause
    exit /b 1
)

REM Check for required dependencies
python -c "import flask" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing required packages...
    pip install flask markupsafe validators python-dotenv openai requests
    if %ERRORLEVEL% NEQ 0 (
        echo Error installing packages.
        pause
        exit /b 1
    )
)

echo Starting Exam Grader web application...
echo The application will be available at http://127.0.0.1:8501
echo.
echo Press Ctrl+C to stop the server.
echo.

python run_app.py

pause 