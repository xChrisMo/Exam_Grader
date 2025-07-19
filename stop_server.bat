@echo off
echo Stopping Exam Grader server...

REM Kill Python processes running the app
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo table /nh') do (
    echo Terminating Python process %%i
    taskkill /f /pid %%i >nul 2>&1
)

REM Also kill any processes using the default port
for /f "tokens=5" %%i in ('netstat -ano ^| findstr :8501') do (
    echo Terminating process using port 8501: %%i
    taskkill /f /pid %%i >nul 2>&1
)

echo Server stopped.
pause