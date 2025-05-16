"""
Update script to fix the OpenAI client initialization issue.
This script updates the webapp to use the patched LLM service.
"""

import os
import shutil
import sys

def update_webapp():
    """Update the webapp to use the patched LLM service."""
    print("Updating webapp to use patched LLM service...")
    
    # Path to the webapp app.py file
    webapp_path = os.path.join("webapp", "app.py")
    
    # Check if the file exists
    if not os.path.exists(webapp_path):
        print(f"Error: {webapp_path} not found.")
        return False
    
    # Read the current content
    with open(webapp_path, "r") as f:
        content = f.read()
    
    # Replace the import statement
    updated_content = content.replace(
        "from src.services.llm_service import LLMService",
        "from src.services.llm_service_patched import LLMService"
    )
    
    # Write the updated content
    with open(webapp_path, "w") as f:
        f.write(updated_content)
    
    print(f"Updated {webapp_path} to use patched LLM service.")
    return True

def update_services_init():
    """Update the services __init__.py file to use the patched LLM service."""
    print("Updating services __init__.py to use patched LLM service...")
    
    # Path to the services __init__.py file
    services_init_path = os.path.join("src", "services", "__init__.py")
    
    # Check if the file exists
    if not os.path.exists(services_init_path):
        print(f"Error: {services_init_path} not found.")
        return False
    
    # Read the current content
    with open(services_init_path, "r") as f:
        content = f.read()
    
    # Replace the import statement
    updated_content = content.replace(
        "from src.services.llm_service import LLMService, LLMServiceError",
        "from src.services.llm_service_patched import LLMService, LLMServiceError"
    )
    
    # Write the updated content
    with open(services_init_path, "w") as f:
        f.write(updated_content)
    
    print(f"Updated {services_init_path} to use patched LLM service.")
    return True

def update_requirements():
    """Update the requirements.txt file to specify a compatible OpenAI version."""
    print("Updating requirements.txt to specify compatible OpenAI version...")
    
    # Path to the requirements.txt file
    requirements_path = "requirements.txt"
    
    # Check if the file exists
    if not os.path.exists(requirements_path):
        print(f"Error: {requirements_path} not found.")
        return False
    
    # Read the current content
    with open(requirements_path, "r") as f:
        content = f.read()
    
    # Replace the OpenAI version
    if "openai==" in content:
        updated_content = content.replace(
            "openai==1.3.0",
            "openai==0.28.1  # Using older version for compatibility"
        )
    else:
        # Add the OpenAI version if not found
        updated_content = content + "\nopenai==0.28.1  # Using older version for compatibility\n"
    
    # Write the updated content
    with open(requirements_path, "w") as f:
        f.write(updated_content)
    
    print(f"Updated {requirements_path} to specify compatible OpenAI version.")
    return True

def create_setup_script():
    """Create a setup script for easy installation."""
    print("Creating setup script...")
    
    # Path to the setup script
    setup_script_path = "setup_and_run.bat"
    
    # Content of the setup script
    setup_script_content = """@echo off
echo Exam Grader - Setup and Run
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

REM Create and activate virtual environment
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing required packages...
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo Error installing packages.
    pause
    exit /b 1
)

echo.
echo Dependencies installed successfully!
echo.

REM Run the application
echo Starting Exam Grader web application...
echo The application will be available at http://127.0.0.1:8501
echo.
echo Press Ctrl+C to stop the server.
echo.

python run_app.py

pause
"""
    
    # Write the setup script
    with open(setup_script_path, "w") as f:
        f.write(setup_script_content)
    
    print(f"Created {setup_script_path} for easy installation.")
    return True

def main():
    """Main function to update the application."""
    print("Starting update process...")
    
    # Update the webapp
    webapp_updated = update_webapp()
    
    # Update the services __init__.py
    services_init_updated = update_services_init()
    
    # Update the requirements.txt
    requirements_updated = update_requirements()
    
    # Create the setup script
    setup_script_created = create_setup_script()
    
    # Check if all updates were successful
    if webapp_updated and services_init_updated and requirements_updated and setup_script_created:
        print("\nUpdate completed successfully!")
        print("\nTo run the application on another PC:")
        print("1. Copy the entire Exam Grader folder to the new PC")
        print("2. Run setup_and_run.bat by double-clicking it")
        print("3. The script will create a virtual environment, install dependencies, and start the application")
    else:
        print("\nUpdate completed with errors. Please check the output above.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
