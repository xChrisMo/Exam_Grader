@echo off
echo Stopping Exam Grader server gracefully...

REM First try graceful shutdown by finding and sending SIGTERM to the specific process
echo Looking for Exam Grader processes...

REM Kill processes by command line (more specific)
for /f "tokens=2" %%i in ('wmic process where "CommandLine like '%%run_app.py%%'" get ProcessId /format:table ^| findstr /r "[0-9]"') do (
    echo Gracefully stopping Exam Grader process %%i
    taskkill /pid %%i >nul 2>&1
    timeout /t 3 >nul
    taskkill /f /pid %%i >nul 2>&1
)

REM Kill processes by command line (Flask app)
for /f "tokens=2" %%i in ('wmic process where "CommandLine like '%%exam_grader_app%%'" get ProcessId /format:table ^| findstr /r "[0-9]"') do (
    echo Gracefully stopping Flask process %%i
    taskkill /pid %%i >nul 2>&1
    timeout /t 3 >nul
    taskkill /f /pid %%i >nul 2>&1
)

REM Kill any processes using the default ports
echo Checking for processes using ports 8501 and 5000...
for /f "tokens=5" %%i in ('netstat -ano ^| findstr :8501') do (
    echo Terminating process using port 8501: %%i
    taskkill /f /pid %%i >nul 2>&1
)

for /f "tokens=5" %%i in ('netstat -ano ^| findstr :5000') do (
    echo Terminating process using port 5000: %%i
    taskkill /f /pid %%i >nul 2>&1
)

echo Server stopped.
pause