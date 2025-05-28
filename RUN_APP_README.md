# 🚀 Exam Grader Application Runner

This directory contains multiple ways to run the Exam Grader Flask application with comprehensive setup checking and error handling.

## 📁 Files Overview

- **`run_app.py`** - Main Python runner with full feature set
- **`run_app.bat`** - Windows batch file for easy startup
- **`run_app.sh`** - Unix/Linux/macOS shell script
- **`RUN_APP_README.md`** - This documentation file

## 🎯 Quick Start

### Windows Users
```bash
# Double-click or run from command prompt
run_app.bat

# Or with Python directly
python run_app.py
```

### Unix/Linux/macOS Users
```bash
# Make executable and run
chmod +x run_app.sh
./run_app.sh

# Or with Python directly
python3 run_app.py
```

## 🔧 Advanced Usage

### Command Line Options

```bash
# Basic usage
python run_app.py

# Custom host and port
python run_app.py --host 0.0.0.0 --port 8080

# Production mode (no debug)
python run_app.py --no-debug

# Install requirements first
python run_app.py --install

# Check setup only (don't run)
python run_app.py --check

# Get help
python run_app.py --help
```

### Common Scenarios

#### First Time Setup
```bash
# Check if everything is ready
python run_app.py --check

# Install requirements if needed
python run_app.py --install

# Run the application
python run_app.py
```

#### Development Mode
```bash
# Run with debug mode (default)
python run_app.py

# Run on all interfaces for testing
python run_app.py --host 0.0.0.0
```

#### Production Mode
```bash
# Run without debug mode
python run_app.py --no-debug --host 0.0.0.0 --port 80
```

## ✅ What the Runner Does

### System Checks
- ✅ **Python Version** - Ensures Python 3.8+
- ✅ **Virtual Environment** - Warns if not using venv
- ✅ **Dependencies** - Checks required packages
- ✅ **Directory Structure** - Creates necessary folders
- ✅ **Environment Setup** - Sets Flask environment variables

### Automatic Setup
- 📁 **Creates Directories**: `temp/`, `output/`, `logs/`, `webapp/static/uploads/`
- 🔧 **Sets Environment**: `FLASK_APP`, `FLASK_ENV`
- 📦 **Installs Packages**: When using `--install` flag
- 🛣️ **Path Management**: Adds project root to Python path

### Error Handling
- 🚨 **Port Conflicts** - Suggests alternative ports
- 🔍 **Missing Dependencies** - Clear installation instructions
- 📝 **Import Errors** - Helpful debugging information
- ⌨️ **Graceful Shutdown** - Handles Ctrl+C properly

## 🌐 Access Points

Once running, access the application at:

- **Main Dashboard**: http://127.0.0.1:5000
- **Upload Guide**: http://127.0.0.1:5000/upload-guide
- **Upload Submission**: http://127.0.0.1:5000/upload-submission
- **Guide Library**: http://127.0.0.1:5000/marking-guides
- **Settings**: http://127.0.0.1:5000/settings

## 🔧 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Try a different port
python run_app.py --port 5001
```

#### Missing Dependencies
```bash
# Install requirements
python run_app.py --install

# Or manually
pip install -r webapp/requirements.txt
```

#### Python Version Issues
```bash
# Check Python version
python --version

# Use Python 3 explicitly
python3 run_app.py
```

#### Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Unix/Linux/macOS)
source venv/bin/activate

# Then run
python run_app.py
```

### Debug Mode

The runner includes comprehensive logging:

```bash
# Check setup without running
python run_app.py --check

# This will show:
# ✅ Python version: 3.9.0
# ⚠️  Warning: Not running in a virtual environment
# ✅ Project root: /path/to/project
# ✅ FLASK_APP: webapp.exam_grader_app
# ✅ Created necessary directories
# ✅ All required dependencies are installed
```

## 🎨 Features

### Smart Detection
- Automatically detects Python command (`python` vs `python3`)
- Checks for virtual environment activation
- Validates project structure

### Cross-Platform
- Works on Windows, macOS, and Linux
- Provides platform-specific scripts
- Handles path differences automatically

### Developer Friendly
- Colored output for better readability
- Comprehensive error messages
- Helpful suggestions for common issues

## 📋 Requirements

- **Python**: 3.8 or higher
- **Flask**: 2.0+
- **Dependencies**: Listed in `webapp/requirements.txt`

## 🚀 Production Deployment

For production deployment, consider:

```bash
# Run without debug mode
python run_app.py --no-debug --host 0.0.0.0 --port 80

# Or use a production WSGI server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:80 webapp.exam_grader_app:app
```

---

**Happy Grading! 📚✨**
