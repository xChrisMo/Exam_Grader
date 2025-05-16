# Exam Grader Installation Guide

This guide will help you install and run the Exam Grader application on a new PC.

## System Requirements

- Windows, macOS, or Linux
- Python 3.8 or higher
- Internet connection for API access

## Installation Steps

### Method 1: Using the Setup Script (Recommended for Windows)

1. Copy the entire Exam Grader folder to your PC
2. Double-click the `setup_and_run.bat` file
3. The script will:
   - Create a virtual environment
   - Install all required dependencies
   - Start the application

### Method 2: Manual Installation

1. Copy the entire Exam Grader folder to your PC
2. Open a command prompt or terminal in the Exam Grader folder
3. Create a virtual environment:
   ```
   python -m venv venv
   ```
4. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
5. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
6. Run the application:
   ```
   python run_app.py
   ```

## Troubleshooting

### "Client._init_() got an unexpected keyword argument 'proxies'" Error

If you encounter this error, it means there's an issue with the OpenAI library version. The application has been patched to use a compatible version (0.28.1), but if you still encounter this error:

1. Make sure you're using the virtual environment created by the setup script
2. Try manually installing the correct OpenAI version:
   ```
   pip uninstall -y openai
   pip install openai==0.28.1
   ```
3. Restart the application

### OCR Service Not Available

The OCR service requires an API key. If you see a message that the OCR service is not available:

1. Create a `.env` file in the Exam Grader folder if it doesn't exist
2. Add your OCR API key to the `.env` file:
   ```
   HANDWRITING_OCR_API_KEY=your_api_key_here
   ```
3. Restart the application

### LLM Service Not Available

The LLM service (DeepSeek) requires an API key. If you see a message that the LLM service is not available:

1. Create a `.env` file in the Exam Grader folder if it doesn't exist
2. Add your DeepSeek API key to the `.env` file:
   ```
   DEEPSEEK_API_KEY=your_api_key_here
   ```
3. Restart the application

## Configuration

You can configure the application by editing the `.env` file. Here are some important settings:

```
# Web Interface Configuration
HOST=127.0.0.1
PORT=8501

# File Processing Configuration
MAX_FILE_SIZE_MB=20
SUPPORTED_FORMATS=.txt,.docx,.pdf,.jpg,.jpeg,.png,.tiff,.bmp,.gif
```

## Getting Help

If you encounter any issues not covered in this guide, please contact the development team for assistance.
