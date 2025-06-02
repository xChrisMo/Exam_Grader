#!/usr/bin/env python3
"""
Exam Grader Installation Script
Automated setup for the Exam Grader application with dependency management.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_colored(message, color=Colors.OKBLUE):
    """Print colored message to terminal."""
    print(f"{color}{message}{Colors.ENDC}")


def print_header(message):
    """Print header message."""
    print_colored(f"\n{'='*60}", Colors.HEADER)
    print_colored(f"🚀 {message}", Colors.HEADER)
    print_colored(f"{'='*60}", Colors.HEADER)


def print_success(message):
    """Print success message."""
    print_colored(f"✅ {message}", Colors.OKGREEN)


def print_warning(message):
    """Print warning message."""
    print_colored(f"⚠️  {message}", Colors.WARNING)


def print_error(message):
    """Print error message."""
    print_colored(f"❌ {message}", Colors.FAIL)


def run_command(command, description="", check=True):
    """Run a shell command with error handling."""
    if description:
        print_colored(f"🔄 {description}...", Colors.OKCYAN)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {command}")
        if e.stderr:
            print_error(f"Error: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    print_header("Checking Python Version")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 3.8+ required. Current version: {version.major}.{version.minor}")
        return False
    
    print_success(f"Python {version.major}.{version.minor}.{version.micro} ✓")
    return True


def check_virtual_environment():
    """Check if running in virtual environment."""
    print_header("Checking Virtual Environment")
    
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_success("Running in virtual environment ✓")
        return True
    else:
        print_warning("Not running in virtual environment")
        print_colored("Recommendation: Create and activate a virtual environment", Colors.WARNING)
        print_colored("python -m venv exam_grader_env", Colors.OKCYAN)
        print_colored("source exam_grader_env/bin/activate  # Linux/Mac", Colors.OKCYAN)
        print_colored("exam_grader_env\\Scripts\\activate     # Windows", Colors.OKCYAN)
        
        response = input("\nContinue anyway? (y/N): ").lower().strip()
        return response == 'y'


def install_dependencies():
    """Install Python dependencies."""
    print_header("Installing Dependencies")
    
    # Upgrade pip first
    if not run_command("python -m pip install --upgrade pip", "Upgrading pip"):
        print_warning("Failed to upgrade pip, continuing...")
    
    # Install main dependencies
    if not run_command("pip install -r requirements.txt", "Installing main dependencies"):
        print_error("Failed to install dependencies")
        return False
    
    print_success("Dependencies installed successfully ✓")
    return True


def create_directories():
    """Create necessary directories."""
    print_header("Creating Directories")
    
    directories = [
        "temp",
        "output", 
        "uploads",
        "logs",
        "tests/reports"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print_success(f"Created directory: {directory}")
    
    return True


def setup_environment_file():
    """Setup environment configuration file."""
    print_header("Setting Up Environment Configuration")
    
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if env_file.exists():
        print_warning(".env file already exists")
        response = input("Overwrite? (y/N): ").lower().strip()
        if response != 'y':
            print_colored("Skipping environment setup", Colors.OKCYAN)
            return True
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print_success("Created .env file from template")
        print_warning("Please edit .env file with your configuration:")
        print_colored("- Set SECRET_KEY to a secure random string", Colors.WARNING)
        print_colored("- Configure API keys if needed", Colors.WARNING)
        print_colored("- Adjust file size limits and paths", Colors.WARNING)
    else:
        print_error("env.example file not found")
        return False
    
    return True


def run_tests():
    """Run basic tests to verify installation."""
    print_header("Running Tests")
    
    # Check if pytest is available
    if not run_command("python -m pytest --version", check=False):
        print_warning("pytest not available, skipping tests")
        return True
    
    # Run security tests
    if Path("tests/test_security.py").exists():
        if run_command("python -m pytest tests/test_security.py -v", "Running security tests"):
            print_success("Security tests passed ✓")
        else:
            print_warning("Some security tests failed")
    
    return True


def display_next_steps():
    """Display next steps for the user."""
    print_header("Installation Complete!")
    
    print_colored("🎉 Exam Grader has been installed successfully!", Colors.OKGREEN)
    print_colored("\nNext steps:", Colors.OKBLUE)
    print_colored("1. Edit .env file with your configuration", Colors.OKCYAN)
    print_colored("2. Start the application:", Colors.OKCYAN)
    print_colored("   python run_app.py", Colors.BOLD)
    print_colored("3. Open your browser to: http://127.0.0.1:5000", Colors.OKCYAN)
    
    print_colored("\nOptional:", Colors.OKBLUE)
    print_colored("- Run tests: python -m pytest", Colors.OKCYAN)
    print_colored("- Check health: curl http://127.0.0.1:5000/health", Colors.OKCYAN)
    print_colored("- View documentation: README.md", Colors.OKCYAN)
    
    print_colored(f"\n{'='*60}", Colors.OKGREEN)


def main():
    """Main installation function."""
    print_colored("🚀 Exam Grader Installation Script", Colors.HEADER)
    print_colored("This script will install and configure the Exam Grader application.\n", Colors.OKBLUE)
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    if not check_virtual_environment():
        sys.exit(1)
    
    # Installation steps
    steps = [
        ("Installing dependencies", install_dependencies),
        ("Creating directories", create_directories),
        ("Setting up environment", setup_environment_file),
        ("Running tests", run_tests),
    ]
    
    for description, func in steps:
        try:
            if not func():
                print_error(f"Failed: {description}")
                sys.exit(1)
        except KeyboardInterrupt:
            print_error("\nInstallation cancelled by user")
            sys.exit(1)
        except Exception as e:
            print_error(f"Unexpected error during {description}: {str(e)}")
            sys.exit(1)
    
    display_next_steps()


if __name__ == "__main__":
    main()
