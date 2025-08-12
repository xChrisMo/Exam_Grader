# Deploying Exam Grader to Vercel

This guide will help you deploy the Exam Grader application to Vercel using the Vercel CLI.

## Prerequisites

1. **Vercel CLI**: Install the Vercel CLI globally
   ```bash
   npm install -g vercel
   ```

2. **Vercel Account**: Sign up at [vercel.com](https://vercel.com) if you haven't already

3. **Environment Variables**: You'll need to set up the following environment variables in Vercel:
   - `OPENAI_API_KEY` (required for AI grading)
   - `HANDWRITING_OCR_API_KEY` (required for OCR processing)
   - `DEEPSEEK_API_KEY` (optional, alternative LLM provider)
   - `SECRET_KEY` (Flask secret key for sessions)

## Deployment Steps

### 1. Login to Vercel
```bash
vercel login
```

### 2. Deploy the Application
From the project root directory, run:
```bash
vercel
```

Follow the prompts:
- **Set up and deploy?** → Yes
- **Which scope?** → Select your account/team
- **Link to existing project?** → No (for first deployment)
- **Project name** → exam-grader (or your preferred name)
- **Directory** → ./ (current directory)
- **Override settings?** → No (we have vercel.json configured)

### 3. Set Environment Variables
After deployment, set up your environment variables:

```bash
# Set OpenAI API key
vercel env add OPENAI_API_KEY

# Set OCR API key
vercel env add HANDWRITING_OCR_API_KEY

# Set DeepSeek API key (optional)
vercel env add DEEPSEEK_API_KEY

# Set Flask secret key
vercel env add SECRET_KEY
```

When prompted, enter the values and select:
- **Environment**: Production, Preview, Development (or just Production)
- **Value**: Enter your actual API keys

### 4. Redeploy with Environment Variables
```bash
vercel --prod
```

## Configuration Files Created

The following files have been created for Vercel deployment:

- **`vercel.json`**: Main Vercel configuration
- **`api/index.py`**: Serverless function entry point
- **`api/vercel_config.py`**: Vercel-specific configuration
- **`requirements-vercel.txt`**: Optimized dependencies for serverless
- **`.vercelignore`**: Files to exclude from deployment

## Important Notes

### Database
- The app uses SQLite by default, which works in Vercel's serverless environment
- Database files are stored in the `/tmp` directory and are ephemeral
- For production, consider using a managed database service

### File Uploads
- Uploaded files are stored in `/tmp` and are ephemeral in serverless
- Consider using cloud storage (AWS S3, Vercel Blob) for persistent file storage

### Limitations
- Serverless functions have execution time limits (300 seconds max)
- Background tasks and long-running processes are disabled
- File system is read-only except for `/tmp`

### Monitoring
- Check deployment logs: `vercel logs`
- View function logs in Vercel dashboard
- Use the health check endpoint: `https://your-app.vercel.app/api/health`

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are in `requirements-vercel.txt`
2. **Database Errors**: Check that database initialization is working
3. **Timeout Errors**: Large file processing may exceed serverless limits
4. **Environment Variables**: Ensure all required API keys are set

### Debugging Commands

```bash
# Check deployment status
vercel ls

# View logs
vercel logs your-deployment-url

# Check environment variables
vercel env ls

# Remove deployment (if needed)
vercel remove your-project-name
```

## Production Considerations

For a production deployment, consider:

1. **Database**: Use PostgreSQL or MySQL with a service like PlanetScale or Supabase
2. **File Storage**: Use Vercel Blob or AWS S3 for file uploads
3. **Monitoring**: Set up error tracking with Sentry
4. **Caching**: Implement Redis for session storage and caching
5. **CDN**: Use Vercel's built-in CDN for static assets

## Alternative: Manual Deployment

If you prefer to deploy manually through the Vercel dashboard:

1. Push your code to GitHub
2. Connect your repository in the Vercel dashboard
3. Set environment variables in the dashboard
4. Deploy automatically on push

## Support

If you encounter issues:
- Check Vercel documentation: https://vercel.com/docs
- Review function logs in the Vercel dashboard
- Test locally with `vercel dev`