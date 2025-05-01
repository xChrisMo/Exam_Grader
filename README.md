# Exam Grader

An automated system for grading exams using OCR and natural language processing. The system supports processing handwritten submissions, PDF documents, and text files, providing automated grading based on predefined marking guides.

## Features

- Handwriting OCR support for multiple file formats
- Automated grading based on marking guides
- Web interface for easy submission management
- Caching system for improved performance
- Detailed feedback and scoring
- Support for multiple file formats:
  - Images (JPG, PNG, TIFF, BMP, GIF)
  - PDF documents
  - Word documents (DOCX)
  - Text files (TXT)

## Project Structure

```
exam_grader/
├── src/                  # Core application code
│   ├── config/          # Configuration management
│   ├── parsing/         # Document parsing and grading
│   ├── services/        # External service integrations
│   └── storage/         # Storage implementations
├── web/                 # Web interface
│   ├── static/         # Static assets
│   └── templates/      # HTML templates
├── utils/               # Utility modules
│   ├── cache.py        # Caching implementation
│   ├── logger.py       # Logging configuration
│   ├── retry.py        # Retry mechanism
│   └── validator.py    # Input validation
├── logs/               # Application logs
├── temp/               # Temporary files
│   └── uploads/       # Upload directory
└── output/             # Generated output files
```

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment tool (venv)
- Git

## Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd exam_grader
   ```

2. Create and activate a virtual environment:

   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create necessary directories:
   ```bash
   mkdir -p logs temp/uploads output
   ```

## Configuration

1. Create configuration file:

   ```bash
   cp config.env.example config.env
   ```

2. Configure the following settings in `config.env`:

   ```ini
   # API Configuration
   HANDWRITING_OCR_API_KEY=your_api_key_here
   OCR_API_BASE_URL=https://www.handwritingocr.com/api/v3

   # Application Settings
   DEBUG=False
   HOST=127.0.0.1
   PORT=8501
   SECRET_KEY=your-secret-key-here

   # Logging Configuration
   LOG_LEVEL=INFO
   MAX_LOG_SIZE_MB=10
   LOG_BACKUP_COUNT=5

   # File Upload Settings
   MAX_CONTENT_LENGTH_MB=20
   ALLOWED_EXTENSIONS=pdf,jpg,jpeg,png,gif,bmp,tiff,txt,docx

   # Cache Settings
   CACHE_TTL_HOURS=24
   MAX_CACHE_SIZE_MB=100
   CACHE_CLEANUP_THRESHOLD=0.9
   ```

3. Environment-specific settings:
   - Development: Set `DEBUG=True` for detailed error messages
   - Production: Set proper `SECRET_KEY` and disable debug mode

## Running the Application

1. Development mode:

   ```bash
   # Windows
   run_dev.bat

   # Linux/macOS
   python web/app.py
   ```

2. Production mode:
   ```bash
   export FLASK_ENV=production
   python web/app.py
   ```

The application will be available at `http://127.0.0.1:8501`

## Usage Guide

1. Prepare Marking Guide:

   - Create a marking guide document (DOCX or TXT format)
   - Include clear question numbers and model answers
   - Specify marks for each question

2. Upload Marking Guide:

   - Click "Upload Marking Guide" on the main page
   - Select your guide document
   - The system will parse and validate the guide

3. Process Submissions:

   - Click "Upload Submission" to process student work
   - Supported formats: PDF, images, DOCX, TXT
   - Maximum file size: 20MB

4. View Results:
   - Access processed submissions through the dashboard
   - View detailed feedback and scores
   - Export results if needed

## Troubleshooting

1. OCR Issues:

   - Ensure proper API key configuration
   - Check file format and size limits
   - Review logs in `logs/app.log`

2. Performance Issues:

   - Check cache configuration
   - Monitor disk space for logs and cache
   - Adjust cleanup thresholds if needed

3. Upload Errors:
   - Verify file permissions
   - Check upload directory exists
   - Ensure file size within limits

## Development

1. Code Style:

   ```bash
   # Format code
   black .

   # Sort imports
   isort .

   # Check style
   flake8
   ```

2. Type Checking:

   ```bash
   mypy .
   ```

3. Running Tests:
   ```bash
   pytest
   ```

## Maintenance

1. Log Management:

   - Logs are stored in `logs/app.log`
   - Rotated automatically when size exceeds 10MB
   - Keeps up to 5 backup files

2. Cache Cleanup:

   - Automatic cleanup when threshold reached
   - Manual cleanup through web interface
   - Cache expires after 24 hours by default

3. Temporary Files:
   - Automatically cleaned up after processing
   - Located in `temp/uploads`
   - Regular cleanup recommended

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For issues and feature requests, please use the issue tracker on GitHub.
