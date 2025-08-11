# Deployment Guide

## Quick Deploy to Render

### 1. Prepare Repository

1. **Fork or clone** this repository to your GitHub account
2. **Push your changes** to GitHub:
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

### 2. Deploy to Render

1. **Visit [Render Dashboard](https://dashboard.render.com)**
2. **Click "New +"** → **"Web Service"**
3. **Connect your GitHub repository**
4. **Configure the service:**
   - **Name**: `exam-grader` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run_app.py`

### 3. Environment Variables

Add these environment variables in Render:

**Required:**
```
HANDWRITING_OCR_API_KEY=your_ocr_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

**Optional (Render will auto-generate if not provided):**
```
SECRET_KEY=your_secret_key_here
DATABASE_URL=sqlite:///exam_grader.db
```

**System (auto-configured):**
```
PORT=10000
HOST=0.0.0.0
DEBUG=false
FLASK_ENV=production
```

### 4. Get API Keys

#### HandwritingOCR API Key
1. Visit [HandwritingOCR.com](https://www.handwritingocr.com)
2. Sign up for an account
3. Go to Dashboard → API Keys
4. Copy your API key

#### DeepSeek API Key
1. Visit [DeepSeek Platform](https://platform.deepseek.com)
2. Sign up for an account
3. Go to API Keys section
4. Create a new API key
5. Copy your API key

### 5. Deploy

1. **Click "Create Web Service"**
2. **Wait for deployment** (usually 2-5 minutes)
3. **Your app will be available** at `https://your-app-name.onrender.com`

## Alternative Deployment Options

### Deploy to Heroku

1. **Install Heroku CLI**
2. **Create Heroku app:**
   ```bash
   heroku create your-app-name
   ```
3. **Set environment variables:**
   ```bash
   heroku config:set HANDWRITING_OCR_API_KEY=your_key
   heroku config:set DEEPSEEK_API_KEY=your_key
   ```
4. **Deploy:**
   ```bash
   git push heroku main
   ```

### Deploy to Railway

1. **Visit [Railway.app](https://railway.app)**
2. **Connect GitHub repository**
3. **Add environment variables**
4. **Deploy automatically**

### Deploy to DigitalOcean App Platform

1. **Visit [DigitalOcean Apps](https://cloud.digitalocean.com/apps)**
2. **Create new app from GitHub**
3. **Configure build settings:**
   - Build Command: `pip install -r requirements.txt`
   - Run Command: `python run_app.py`
4. **Add environment variables**
5. **Deploy**

## Local Development

### Setup
```bash
git clone <your-repo-url>
cd exam-grader
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env
# Edit .env with your API keys
python run_app.py
```

### Environment Variables (.env file)
```env
HANDWRITING_OCR_API_KEY=your_ocr_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///exam_grader.db
HOST=127.0.0.1
PORT=5000
DEBUG=true
```

## Production Configuration

### Security Checklist
- ✅ Set `DEBUG=false` in production
- ✅ Use strong `SECRET_KEY`
- ✅ Enable HTTPS (handled by Render)
- ✅ Set proper CORS headers
- ✅ Use environment variables for secrets

### Performance Optimization
- ✅ Enable caching
- ✅ Use production WSGI server (gunicorn)
- ✅ Optimize database queries
- ✅ Enable compression

### Monitoring
- ✅ Health check endpoint: `/api/health`
- ✅ Application logs in Render dashboard
- ✅ Error tracking and reporting

## Troubleshooting

### Common Issues

**Build Fails:**
- Check `requirements.txt` is complete
- Ensure Python version compatibility

**App Won't Start:**
- Check environment variables are set
- Verify API keys are valid
- Check logs in Render dashboard

**Database Issues:**
- Database is created automatically on first run
- Check file permissions for SQLite

**API Errors:**
- Verify API keys are correct
- Check API service status
- Review rate limits

### Getting Help

1. **Check logs** in your deployment platform dashboard
2. **Review error messages** for specific issues
3. **Test locally** with same environment variables
4. **Check API service status** for external dependencies

## Scaling

### Horizontal Scaling
- Use multiple instances on Render Pro
- Implement session storage (Redis)
- Use external database (PostgreSQL)

### Performance Monitoring
- Monitor response times
- Track API usage
- Monitor memory usage
- Set up alerts for errors

## Backup and Recovery

### Database Backup
```bash
# Download database from Render
render exec your-service-name -- sqlite3 /opt/render/project/src/instance/exam_grader.db .dump > backup.sql
```

### Restore Database
```bash
# Upload and restore
cat backup.sql | render exec your-service-name -- sqlite3 /opt/render/project/src/instance/exam_grader.db
```