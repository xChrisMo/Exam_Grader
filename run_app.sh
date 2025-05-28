#!/bin/bash
# Exam Grader Application Runner for Unix/Linux/macOS
# Simple shell script to start the Flask application

set -e  # Exit on any error

echo "========================================"
echo "   Exam Grader Application Runner"
echo "========================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

print_success() {
    echo -e "${GREEN}SUCCESS: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        print_error "Python is not installed or not in PATH"
        echo "Please install Python 3.8+ from https://python.org"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
echo "Found Python version: $PYTHON_VERSION"

# Check if we're in the right directory
if [ ! -f "run_app.py" ]; then
    print_error "run_app.py not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    print_warning "Virtual environment found but not activated"
    echo "Consider running: source venv/bin/activate"
    echo
elif [ -d ".venv" ]; then
    print_warning "Virtual environment found but not activated"
    echo "Consider running: source .venv/bin/activate"
    echo
fi

# Make the script executable if it isn't already
chmod +x "$0"

# Run the application
echo "Starting Exam Grader Application..."
echo
$PYTHON_CMD run_app.py "$@"

# Check exit status
if [ $? -ne 0 ]; then
    print_error "Application exited with an error"
    exit 1
else
    print_success "Application stopped successfully"
fi
