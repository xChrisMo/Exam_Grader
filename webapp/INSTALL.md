# Installation Guide - Exam Grader Web Application

This guide will help you set up and run the Exam Grader web application on your system.

## Prerequisites

- **Python 3.8 or higher** (Python 3.11+ recommended)
- **pip** (Python package installer)
- **Web browser** (Chrome, Firefox, Safari, or Edge)

## Quick Start

### Option 1: Using Startup Scripts (Recommended)

#### Windows
1. Open Command Prompt or PowerShell
2. Navigate to the webapp directory:
   ```cmd
   cd path\to\Exam_Grader\webapp
   ```
3. Run the startup script:
   ```cmd
   start.bat
   ```

#### Linux/Mac
1. Open Terminal
2. Navigate to the webapp directory:
   ```bash
   cd path/to/Exam_Grader/webapp
   ```
3. Make the script executable and run it:
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

### Option 2: Manual Installation

#### Step 1: Install Python Dependencies

1. **Navigate to the webapp directory**:
   ```bash
   cd webapp
   ```

2. **Install Flask** (minimum requirement):
   ```bash
   pip install flask
   ```

3. **Or install all dependencies** (recommended):
   ```bash
   pip install -r requirements.txt
   ```

#### Step 2: Run the Application

Choose one of these methods:

**Method A: Direct execution**
```bash
python exam_grader_app.py
```

**Method B: Using the run script**
```bash
python run.py
```

**Method C: Using Flask CLI**
```bash
# Windows
set FLASK_APP=exam_grader_app.py
set FLASK_ENV=development
flask run

# Linux/Mac
export FLASK_APP=exam_grader_app.py
export FLASK_ENV=development
flask run
```

#### Step 3: Access the Application

Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

## Detailed Installation

### Virtual Environment (Recommended)

Using a virtual environment helps avoid conflicts with other Python projects:

1. **Create a virtual environment**:
   ```bash
   python -m venv exam_grader_env
   ```

2. **Activate the virtual environment**:
   
   **Windows:**
   ```cmd
   exam_grader_env\Scripts\activate
   ```
   
   **Linux/Mac:**
   ```bash
   source exam_grader_env/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python exam_grader_app.py
   ```

5. **Deactivate when done**:
   ```bash
   deactivate
   ```

### Dependencies

The application requires these Python packages:

**Core Requirements:**
- Flask 2.3.3+
- Werkzeug 2.3.7+
- Jinja2 3.1.2+

**Optional (for enhanced functionality):**
- python-magic (file type detection)
- gunicorn (production deployment)
- cryptography (enhanced security)

### System Requirements

**Minimum:**
- Python 3.8+
- 512MB RAM
- 100MB disk space
- Modern web browser

**Recommended:**
- Python 3.11+
- 1GB RAM
- 500MB disk space
- Chrome 90+ or Firefox 88+

## Configuration

The application uses fallback configuration when the main config system is not available:

- **Host**: 127.0.0.1 (localhost)
- **Port**: 5000
- **Debug Mode**: Enabled (development)
- **Max File Size**: 16MB
- **Supported File Types**: PDF, DOCX, DOC, JPG, JPEG, PNG, TIFF, BMP, GIF

## Troubleshooting

### Common Issues

#### 1. Python Not Found
```
'python' is not recognized as an internal or external command
```
**Solution**: Install Python from [python.org](https://python.org) and ensure it's added to your PATH.

#### 2. Flask Not Found
```
ModuleNotFoundError: No module named 'flask'
```
**Solution**: Install Flask using `pip install flask`

#### 3. Port Already in Use
```
OSError: [Errno 48] Address already in use
```
**Solution**: 
- Kill the existing process using the port
- Or change the port in `exam_grader_app.py` (line with `app.run(port=5000)`)

#### 4. Permission Denied (Linux/Mac)
```
Permission denied: './start.sh'
```
**Solution**: Make the script executable with `chmod +x start.sh`

#### 5. Template Not Found
```
TemplateNotFound: dashboard.html
```
**Solution**: Ensure you're running the application from the webapp directory

### Debug Mode

The application runs in debug mode by default, which provides:
- Detailed error messages in the browser
- Automatic reloading when code changes
- Interactive debugger for errors

To disable debug mode for production, edit `exam_grader_app.py`:
```python
app.run(debug=False)
```

### Logs and Debugging

- Check the terminal/command prompt for error messages
- Flask will display detailed error pages in debug mode
- Use browser developer tools (F12) to check for JavaScript errors

## Production Deployment

For production use, consider:

1. **Use a production WSGI server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 exam_grader_app:app
   ```

2. **Disable debug mode**
3. **Use environment variables for configuration**
4. **Set up proper logging**
5. **Use HTTPS with SSL certificates**

## Getting Help

If you encounter issues:

1. Check this troubleshooting guide
2. Verify all prerequisites are installed
3. Ensure you're in the correct directory
4. Check the terminal output for error messages
5. Try running the test application first: `python test_app.py`

## Next Steps

Once the application is running:

1. **Upload a Marking Guide**: Navigate to the "Marking Guide" section
2. **Upload Student Submissions**: Use the "Upload Submission" feature
3. **Process and Grade**: Use the AI processing features
4. **View Results**: Check the detailed grading results

## File Structure

After installation, your webapp directory should contain:

```
webapp/
├── exam_grader_app.py      # Main application
├── run.py                  # Development runner
├── test_app.py            # Test application
├── start.bat              # Windows startup script
├── start.sh               # Linux/Mac startup script
├── requirements.txt       # Python dependencies
├── README.md             # Application documentation
├── INSTALL.md            # This installation guide
├── static/               # CSS, JS, and other assets
│   ├── css/
│   ├── js/
│   └── favicon.ico
└── templates/            # HTML templates
    ├── layout.html
    ├── dashboard.html
    ├── upload_guide.html
    ├── upload_submission.html
    ├── submissions.html
    ├── results.html
    └── error.html
```

## Support

For additional support or questions about the Exam Grader system, refer to the main project documentation.
