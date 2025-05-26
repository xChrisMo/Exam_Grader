# Exam Grader Web Application

A modern, AI-powered web interface for automated exam grading using DeepSeek AI.

## 🚀 Features

- **Modern Dashboard** - Clean, intuitive interface with real-time updates
- **Drag & Drop Upload** - Easy file upload for marking guides and submissions
- **Real-time Processing** - Live progress updates via WebSocket connections
- **Detailed Results** - Comprehensive grading reports with feedback
- **Multi-format Support** - PDF, DOCX, TXT, and image files
- **Responsive Design** - Works on desktop, tablet, and mobile devices
- **Settings Management** - Configurable grading parameters and API settings

## 📋 Prerequisites

- Python 3.11 or higher
- DeepSeek API key (get from [DeepSeek Platform](https://platform.deepseek.com/))
- Modern web browser (Chrome, Firefox, Safari, Edge)

## 🛠️ Installation

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd Exam_Grader
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env file with your settings
   ```

4. **Configure your DeepSeek API key**:
   - Open the web application
   - Go to Settings → API Settings
   - Enter your DeepSeek API key

## 🚀 Quick Start

### Development Mode

```bash
# Start the web application
python run_web.py

# Or with custom settings
python run_web.py --host 0.0.0.0 --port 8080 --debug
```

### Production Mode

```bash
# Start with Gunicorn (recommended for production)
python run_web.py --production --workers 4

# Or use the Flask app directly
python app.py
```

The application will be available at:
- **Local**: http://127.0.0.1:5000
- **Network**: http://0.0.0.0:5000 (if using --host 0.0.0.0)

## 📖 Usage Guide

### 1. Dashboard
- View recent grading results
- Quick access to all features
- System statistics and overview

### 2. Upload Files
- **Marking Guide**: Upload your rubric or marking criteria (PDF, DOCX, TXT)
- **Student Submission**: Upload the exam to be graded (PDF, DOCX, TXT, images)
- **Processing Options**: Configure feedback detail level and analysis options

### 3. Real-time Processing
- Watch live progress as your submission is processed
- Stages: Upload → Parse → Analyze → Grade → Complete
- Estimated processing time: 2-5 minutes depending on file size

### 4. View Results
- Detailed grading breakdown by criteria
- Overall score and grade
- Comprehensive feedback and improvement suggestions
- Download reports in multiple formats

### 5. Settings
- **General**: Application preferences and display options
- **Grading**: Configure grading scales and feedback levels
- **API**: DeepSeek API configuration and testing
- **Storage**: File management and cleanup options
- **Security**: Access control and security settings

## 🔧 Configuration

### Environment Variables

Key environment variables in `.env`:

```bash
# Web Server
HOST=127.0.0.1
PORT=5000
SECRET_KEY=your-secret-key-here
DEBUG=True

# File Processing
MAX_FILE_SIZE_MB=10
TEMP_DIR=temp
OUTPUT_DIR=output

# API Configuration
DEEPSEEK_API_KEY=your-api-key-here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TEMPERATURE=0.1
```

### Web-specific Settings

The web application includes additional configuration options:

- **Session Management**: Secure session handling with Flask-Session
- **File Upload Limits**: Configurable maximum file sizes
- **Real-time Updates**: WebSocket support for live progress
- **CORS Support**: Cross-origin resource sharing for API access

## 🎨 User Interface

### Design Features
- **Bootstrap 5** - Modern, responsive framework
- **Bootstrap Icons** - Comprehensive icon library
- **Custom CSS** - Enhanced styling with animations and transitions
- **Dark Mode Support** - Automatic system theme detection
- **Accessibility** - WCAG compliant design with keyboard navigation

### Browser Support
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 🔒 Security

### Built-in Security Features
- **CSRF Protection** - Cross-site request forgery prevention
- **Secure Sessions** - Encrypted session management
- **File Validation** - Strict file type and size validation
- **Rate Limiting** - API request throttling
- **Input Sanitization** - XSS prevention

### Production Security
For production deployment:
1. Use HTTPS with SSL certificates
2. Set strong SECRET_KEY
3. Configure firewall rules
4. Enable rate limiting
5. Regular security updates

## 📊 Monitoring

### Logging
- Application logs: `logs/app.log`
- Access logs: `logs/access.log` (production)
- Error logs: `logs/error.log` (production)

### Health Checks
- Application status: `/health` (coming soon)
- API connectivity: Settings → API → Test Connection

## 🚀 Deployment

### Docker (Recommended)
```bash
# Build image
docker build -t exam-grader-web .

# Run container
docker run -p 5000:5000 -v $(pwd)/.env:/app/.env exam-grader-web
```

### Traditional Deployment
```bash
# Install production dependencies
pip install gunicorn eventlet

# Run with Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class eventlet app:create_app()
```

### Cloud Platforms
- **Heroku**: Use `Procfile` with Gunicorn
- **AWS**: Deploy with Elastic Beanstalk or ECS
- **Google Cloud**: Use App Engine or Cloud Run
- **Azure**: Deploy with App Service

## 🛠️ Development

### Project Structure
```
├── app.py                 # Main Flask application
├── run_web.py            # Application launcher
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── dashboard.html    # Main dashboard
│   ├── upload.html       # File upload page
│   ├── results.html      # Results display
│   └── settings.html     # Settings page
├── static/               # Static assets
│   ├── css/             # Stylesheets
│   ├── js/              # JavaScript files
│   └── images/          # Images and icons
└── src/                 # Backend modules
```

### Adding Features
1. Create new routes in `app.py`
2. Add templates in `templates/`
3. Include JavaScript in `static/js/`
4. Update navigation in `base.html`

## 🐛 Troubleshooting

### Common Issues

**Port already in use**:
```bash
python run_web.py --port 8080
```

**Missing dependencies**:
```bash
pip install -r requirements.txt
```

**API connection failed**:
- Check your DeepSeek API key
- Verify internet connection
- Test API in Settings page

**File upload errors**:
- Check file size limits
- Verify file format support
- Ensure sufficient disk space

### Debug Mode
```bash
python run_web.py --debug
```

## 📞 Support

- **Documentation**: Check the main README.md
- **Issues**: Report bugs via GitHub issues
- **API Documentation**: [DeepSeek API Docs](https://platform.deepseek.com/api-docs)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Happy Grading! 🎓**
