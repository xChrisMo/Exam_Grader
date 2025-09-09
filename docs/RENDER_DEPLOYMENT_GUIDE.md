# Render.com Deployment Guide

This guide explains how to deploy the Exam Grader application to Render.com.

## Prerequisites

1. A Render.com account
2. Your application code pushed to a Git repository (GitHub, GitLab, or Bitbucket)

## Deployment Steps

### 1. Create a New Web Service

1. Log in to your Render.com dashboard
2. Click "New +" and select "Web Service"
3. Connect your Git repository
4. Configure the service:
   - **Name**: `exam-grader` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run_app.py`

### 2. Set Environment Variables

In your Render service dashboard, go to the "Environment" tab and add the following variables:

#### Required Environment Variables

```bash
# Generate a secure SECRET_KEY using the provided script
SECRET_KEY=your_generated_secret_key_here

# API Keys (replace with your actual keys)
DEEPSEEK_API_KEY=your_deepseek_api_key_here
HANDWRITING_OCR_API_KEY=your_handwriting_ocr_api_key_here

# LLM Configuration (unlimited usage)
LLM_REQUESTS_PER_MINUTE=1000
LLM_REQUESTS_PER_HOUR=10000
TIMEOUT_LLM_PROCESSING=1200
LLM_JSON_TIMEOUT=60.0

# Database (SQLite will be used by default)
DATABASE_URL=sqlite:///exam_grader.db

# Server Configuration
HOST=0.0.0.0
PORT=10000
DEBUG=False
ENVIRONMENT=production

# CORS Configuration (optional - defaults to allow all origins)
ALLOWED_ORIGINS=https://your-app-name.onrender.com,https://*.onrender.com
```

#### Optional Environment Variables

```bash
# Performance Settings
MAX_BATCH_WORKERS=5
BATCH_PROCESSING_SIZE=5
MAX_CONCURRENT_OPERATIONS=10

# Timeout Settings
TIMEOUT_OCR_PROCESSING=180
TIMEOUT_LLM_PROCESSING=600
TIMEOUT_FILE_PROCESSING=90

# Security Settings
SESSION_TIMEOUT=3600
MAX_CONCURRENT_SESSIONS=3
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_LEVEL=INFO
```

### 3. Generate a Secure SECRET_KEY

Run the provided script to generate a secure SECRET_KEY:

```bash
python generate_secret_key.py
```

Copy the generated key and set it as the `SECRET_KEY` environment variable in Render.

### 4. Deploy

1. Click "Create Web Service"
2. Render will automatically build and deploy your application
3. Monitor the build logs for any issues

## Troubleshooting

### Common Issues

#### SECRET_KEY Error
If you see "SECRET_KEY must be at least 32 characters long":
- Ensure you've set the `SECRET_KEY` environment variable in Render
- Use the `generate_secret_key.py` script to create a proper key
- The key should be at least 32 characters long

#### Build Failures
- Check that all dependencies are listed in `requirements.txt`
- Ensure Python version compatibility
- Review build logs for specific error messages

#### Runtime Errors
- Check application logs in the Render dashboard
- Verify all required environment variables are set
- Ensure API keys are valid and have proper permissions

### Environment Detection

The application automatically detects Render deployment using the `RENDER` environment variable and adjusts configuration accordingly:
- Sets host to `0.0.0.0`
- Uses the `PORT` environment variable
- Disables debug mode
- Enables production security settings

### CORS Configuration

The application supports configurable CORS (Cross-Origin Resource Sharing) settings:

- **Default behavior**: Allows all origins (`*`) for development
- **Production**: Set `ALLOWED_ORIGINS` to restrict access to specific domains
- **Render domains**: Automatically includes `*.onrender.com` and `*.render.com` in allowed origins

Example CORS configuration:
```bash
# Allow specific domains
ALLOWED_ORIGINS=https://your-app.onrender.com,https://yourdomain.com

# Allow all Render subdomains
ALLOWED_ORIGINS=https://*.onrender.com,https://*.render.com

# Allow all origins (default, less secure)
ALLOWED_ORIGINS=*
```

### LLM Configuration

The application is configured for unlimited LLM usage with the following settings:

- **Rate Limits**: 1000 requests per minute, 10000 requests per hour
- **Timeouts**: 20 minutes for LLM processing, 60 seconds for JSON parsing
- **File Size**: Up to 100MB files supported
- **Retry Logic**: 5 retry attempts with exponential backoff

These settings ensure that large documents and complex processing tasks can be handled without artificial limitations.

## Security Considerations

1. **Never commit sensitive data**: Keep API keys and SECRET_KEY out of your repository
2. **Use environment variables**: Store all sensitive configuration in Render's environment variables
3. **Regular key rotation**: Consider rotating your SECRET_KEY periodically
4. **Monitor access**: Use Render's monitoring features to track application usage

## Performance Optimization

For better performance on Render:
1. Enable caching in your environment variables
2. Optimize database queries
3. Use appropriate timeout values
4. Monitor resource usage in the Render dashboard

## Support

If you encounter issues:
1. Check the application logs in Render dashboard
2. Review this deployment guide
3. Check the main project documentation
4. Create an issue in the project repository
