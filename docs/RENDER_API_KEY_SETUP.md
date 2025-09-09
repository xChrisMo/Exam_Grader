# Render.com API Key Setup Guide

## Problem
Your Exam Grader application is showing this error on Render.com:
```
WARNING - Medium severity error: Error code: 401 - {'error': {'message': 'Authentication Fails, Your api key: ****here is invalid', 'type': 'authentication_error', 'param': None, 'code': 'invalid_request_error'}}
```

This means the application is using a placeholder API key instead of your real DeepSeek API key.

## Solution

### Step 1: Get Your DeepSeek API Key

1. Go to [DeepSeek Console](https://platform.deepseek.com/)
2. Sign in or create an account
3. Navigate to the API Keys section
4. Create a new API key
5. Copy the API key (it should look like `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

### Step 2: Set Environment Variable on Render.com

1. Go to your Render.com dashboard
2. Navigate to your Exam Grader service
3. Click on "Environment" tab
4. Add a new environment variable:
   - **Key**: `DEEPSEEK_API_KEY`
   - **Value**: Your actual API key (e.g., `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
5. Click "Save Changes"

### Step 3: Redeploy

1. Go to the "Manual Deploy" section
2. Click "Deploy latest commit"
3. Wait for deployment to complete

### Step 4: Verify

1. Check the deployment logs for:
   ```
   INFO - LLM service initialized successfully with model: deepseek-chat
   ```
2. Test the application by uploading a marking guide
3. The LLM processing should now work without 401 errors

## Alternative: Test Your API Key Locally

If you want to test your API key before deploying:

1. Create a `.env` file in your project root:
   ```bash
   DEEPSEEK_API_KEY=your_actual_api_key_here
   ```

2. Run the test script:
   ```bash
   python test_api_key.py
   ```

3. You should see:
   ```
   ✅ API key is valid and working!
   ```

## Troubleshooting

### Still Getting 401 Errors?

1. **Check the API key format**: It should start with `sk-` and be about 50+ characters long
2. **Verify the environment variable name**: Must be exactly `DEEPSEEK_API_KEY`
3. **Check DeepSeek account**: Ensure your account has credits and the API key is active
4. **Clear browser cache**: Sometimes old cached responses can cause issues

### API Key Not Loading?

1. **Check deployment logs**: Look for any errors during startup
2. **Verify environment variables**: In Render.com dashboard, ensure the variable is set correctly
3. **Redeploy**: Sometimes a fresh deployment is needed

### Getting "Service temporarily unavailable"?

This means the LLM service is working but there might be rate limits or temporary issues. Try again in a few minutes.

## Security Notes

- Never commit your API key to version control
- Use environment variables for all sensitive data
- Regularly rotate your API keys
- Monitor your API usage in the DeepSeek console

## Support

If you continue to have issues:

1. Check the deployment logs on Render.com
2. Verify your DeepSeek account status
3. Test the API key locally first
4. Contact support with specific error messages
