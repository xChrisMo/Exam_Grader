@echo off
REM Quick Protection Commands

if "%1"=="start" (
    echo Starting file protection...
    python protect.py start
) else if "%1"=="stop" (
    echo Stopping file protection...
    python protect.py stop
) else if "%1"=="status" (
    echo Checking status...
    python protect.py status
) else if "%1"=="commit" (
    echo Committing changes safely...
    python protect.py commit %2 %3 %4 %5
) else (
    echo Usage: protect [start^|stop^|status^|commit]
    echo.
    echo   protect start    - Start monitoring files
    echo   protect stop     - Stop monitoring
    echo   protect status   - Show current status
    echo   protect commit   - Safely commit changes
)
