@echo off
setlocal

:: Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install/update dependencies
echo Checking dependencies...
pip install -r requirements.txt

:: Set development environment variables
set DEBUG=True
set LOG_LEVEL=DEBUG

echo Starting development server...
python web/app.py

:: Deactivate virtual environment on exit
deactivate 