# Render.com Deployment Fixes

This document outlines the fixes applied to resolve deployment issues on Render.com.

## Issues Fixed

### 1. LLM API Authentication Error (401)
**Problem**: `Authentication Fails, Your api key: ****here is invalid`

**Solution**: 
- Added `LLM_API_KEY` environment variable to complement `DEEPSEEK_API_KEY`
- Updated environment configuration to support both variable names
- The LLM service now checks for both `LLM_API_KEY` and `DEEPSEEK_API_KEY`

**Required Environment Variables on Render.com**:
```
DEEPSEEK_API_KEY=your_actual_deepseek_api_key_here
LLM_API_KEY=your_actual_deepseek_api_key_here
```

### 2. Missing antiword Dependency
**Problem**: `WARNING - Missing optional dependencies: antiword ([Errno 2] No such file or directory: 'antiword')`

**Solution**:
- Improved error handling for antiword dependency
- Added graceful fallback when antiword is not available
- Updated dependency checking to use `which antiword` instead of `antiword --version`
- DOC file processing will now fall back to alternative methods when antiword is unavailable

**Note**: antiword is not available on Render.com by default. The application will work without it, but DOC file processing will use alternative methods.

### 3. CSRF Token Missing Error
**Problem**: `WARNING - CSRF error: 400 Bad Request: The CSRF session token is missing`

**Solution**:
- Added explicit CSRF token validation in the signup route
- Improved error handling for CSRF validation failures
- Enhanced CSRF token generation and validation

### 4. Registration Failed Error
**Problem**: `Registration failed. Please try again.` on Render.com

**Solution**:
- Fixed database table creation - tables are now properly created on startup
- Improved user ID generation using UUID instead of timestamp-based IDs
- Added database connectivity checks during registration
- Enhanced error handling with specific error messages for different failure types
- Added database initialization script for deployment platforms

## Environment Variables for Render.com

Set these environment variables in your Render.com dashboard:

### Required Variables
```
SECRET_KEY=your_32_character_secret_key_here_123456789
DEEPSEEK_API_KEY=your_actual_deepseek_api_key_here
LLM_API_KEY=your_actual_deepseek_api_key_here
DATABASE_URL=sqlite:///exam_grader.db
```

### Optional Variables (with defaults)
```
DEBUG=False
TESTING=False
HOST=0.0.0.0
PORT=10000
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://*.onrender.com,https://*.render.com
```

## Build Configuration

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
python run_app.py
```

## Dependencies Status

The application will now gracefully handle missing optional dependencies:

- ✅ **Available**: PyPDF2, pdfplumber, python-docx, docx2txt, striprtf, beautifulsoup4, chardet
- ⚠️ **Not Available**: antiword (will use fallback methods for DOC files)
- ✅ **Core Dependencies**: All required dependencies are available

## Testing the Deployment

1. **Check LLM Connectivity**: The application should no longer show 401 authentication errors
2. **Test File Upload**: Upload various file types to ensure processing works
3. **Test User Registration**: The signup form should work without CSRF errors
4. **Check Logs**: Monitor logs for any remaining warnings or errors

## Troubleshooting

### If LLM API still fails:
1. Verify your DeepSeek API key is valid and active
2. Check that both `DEEPSEEK_API_KEY` and `LLM_API_KEY` are set to the same value
3. Ensure your API key has sufficient credits/quota

### If CSRF errors persist:
1. Clear browser cache and cookies
2. Check that the SECRET_KEY is properly set
3. Verify the application is using HTTPS (required for secure cookies)

### If registration still fails:
1. Check the Render.com logs for database connection errors
2. Verify that the `DATABASE_URL` environment variable is set correctly
3. Ensure the database tables are created (check the release phase logs)
4. Try running the database initialization script manually: `python init_db.py`
5. Check for specific error messages in the registration form

### If file processing fails:
1. Check the logs for specific error messages
2. Verify file size limits are appropriate
3. Test with different file formats to identify which ones work

## Performance Notes

- The application will automatically fall back to available extraction methods
- DOC files will be processed using alternative methods when antiword is unavailable
- All core functionality remains available even with missing optional dependencies
