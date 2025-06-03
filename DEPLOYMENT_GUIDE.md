# 🚀 Production Deployment Guide

## Overview
This guide covers deploying the enhanced Exam Grader application with all 20 critical fixes implemented. The application now includes comprehensive security, performance optimizations, and user experience improvements.

## 📋 Pre-Deployment Checklist

### ✅ Security Verification
- [ ] CSRF protection enabled for all forms and API endpoints
- [ ] Rate limiting configured for all routes
- [ ] Input sanitization implemented throughout
- [ ] File upload security measures in place
- [ ] Error messages don't expose sensitive information
- [ ] Session management properly configured

### ✅ Performance Verification
- [ ] Multi-level caching system operational
- [ ] File processing optimized for large files
- [ ] Memory-efficient handlers implemented
- [ ] Database connections properly pooled
- [ ] Static assets optimized and compressed

### ✅ Reliability Verification
- [ ] Comprehensive error handling in place
- [ ] Graceful degradation for service failures
- [ ] Proper logging configuration
- [ ] Health check endpoints functional
- [ ] Backup and recovery procedures tested

## 🔧 Environment Setup

### 1. System Requirements
```bash
# Minimum requirements
- Python 3.8+
- 4GB RAM (8GB recommended)
- 20GB disk space
- Redis (for caching)
- PostgreSQL/MySQL (for production storage)

# Recommended for production
- 8GB+ RAM
- SSD storage
- Load balancer
- Reverse proxy (nginx/Apache)
```

### 2. Environment Variables
Create a `.env` file with production settings:

```bash
# Application Settings
FLASK_ENV=production
SECRET_KEY=your-super-secure-secret-key-here
MAX_CONTENT_LENGTH=52428800  # 50MB

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/exam_grader
REDIS_URL=redis://localhost:6379/0

# Security Settings
CSRF_SECRET_KEY=another-secure-key-for-csrf
RATE_LIMIT_STORAGE_URL=redis://localhost:6379/1

# File Storage
UPLOAD_FOLDER=/var/app/uploads
TEMP_FOLDER=/var/app/temp
MAX_FILE_SIZE_MB=50

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/exam_grader/app.log

# External Services
OCR_SERVICE_URL=http://localhost:8001
LLM_SERVICE_URL=http://localhost:8002
```

### 3. Dependencies Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install production dependencies
pip install gunicorn redis psycopg2-binary
```

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/temp /app/uploads /app/logs

# Set permissions
RUN chmod +x /app/run.py

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "webapp.exam_grader_app:app"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://postgres:password@db:5432/exam_grader
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=exam_grader
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
```

## ⚙️ Web Server Configuration

### Nginx Configuration
```nginx
upstream exam_grader {
    server app:5000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=upload:10m rate=2r/s;

    client_max_body_size 50M;

    location / {
        proxy_pass http://exam_grader;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://exam_grader;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /upload-guide {
        limit_req zone=upload burst=5 nodelay;
        proxy_pass http://exam_grader;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## 📊 Monitoring & Logging

### 1. Application Monitoring
```python
# Add to your monitoring setup
from utils.logger import setup_logger
import psutil
import time

def monitor_application():
    """Monitor application health and performance."""
    logger = setup_logger('monitor')
    
    while True:
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        # Application metrics
        from utils.cache import Cache
        cache = Cache()
        cache_stats = cache.get_stats()
        
        from utils.rate_limiter import rate_limiter
        rate_stats = rate_limiter.get_stats()
        
        logger.info(f"System: CPU={cpu_percent}%, Memory={memory_percent}%, Disk={disk_percent}%")
        logger.info(f"Cache: Hit Rate={cache_stats.get('hit_rate', 0)}%")
        logger.info(f"Rate Limiting: Active IPs={rate_stats.get('active_ips', 0)}")
        
        time.sleep(60)  # Monitor every minute
```

### 2. Log Configuration
```python
# Production logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/exam_grader/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed'
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/exam_grader/error.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'formatter': 'detailed',
            'level': 'ERROR'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file', 'error_file']
    }
}
```

## 🔒 Security Hardening

### 1. SSL/TLS Configuration
```bash
# Generate SSL certificate (Let's Encrypt recommended)
certbot --nginx -d your-domain.com

# Or use self-signed for testing
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

### 2. Firewall Configuration
```bash
# UFW configuration
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 3. Application Security
```python
# Additional security middleware
from flask_talisman import Talisman

# Add to app initialization
Talisman(app, {
    'force_https': True,
    'strict_transport_security': True,
    'content_security_policy': {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data:",
    }
})
```

## 🚀 Deployment Steps

### 1. Prepare Server
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo pip3 install docker-compose

# Create application directory
sudo mkdir -p /var/app/exam_grader
sudo chown $USER:$USER /var/app/exam_grader
```

### 2. Deploy Application
```bash
# Clone repository
cd /var/app/exam_grader
git clone <your-repo-url> .

# Set up environment
cp .env.example .env
# Edit .env with production values

# Build and start services
docker-compose up -d

# Verify deployment
docker-compose ps
curl http://localhost/health
```

### 3. Post-Deployment Verification
```bash
# Check all services are running
docker-compose logs app
docker-compose logs nginx
docker-compose logs db
docker-compose logs redis

# Test application functionality
curl -X GET http://localhost/
curl -X GET http://localhost/api/cache/stats

# Monitor logs
tail -f logs/app.log
```

## 📈 Performance Tuning

### 1. Database Optimization
```sql
-- PostgreSQL optimizations
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
SELECT pg_reload_conf();
```

### 2. Redis Configuration
```bash
# Redis optimizations in redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### 3. Application Tuning
```python
# Gunicorn configuration
bind = "0.0.0.0:5000"
workers = 4  # 2 * CPU cores
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 120
keepalive = 5
```

## 🔄 Backup & Recovery

### 1. Database Backup
```bash
#!/bin/bash
# backup_db.sh
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec db pg_dump -U postgres exam_grader > backup_${DATE}.sql
aws s3 cp backup_${DATE}.sql s3://your-backup-bucket/
```

### 2. Application Backup
```bash
#!/bin/bash
# backup_app.sh
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf app_backup_${DATE}.tar.gz uploads/ logs/ .env
aws s3 cp app_backup_${DATE}.tar.gz s3://your-backup-bucket/
```

## 📞 Support & Maintenance

### Health Check Endpoint
The application includes a health check endpoint at `/health` that verifies:
- Database connectivity
- Redis connectivity
- Cache system status
- File system access
- Service availability

### Maintenance Tasks
- Daily: Check logs for errors
- Weekly: Review performance metrics
- Monthly: Update dependencies
- Quarterly: Security audit
- Annually: Disaster recovery test

### Troubleshooting
Common issues and solutions are documented in `TROUBLESHOOTING.md`.

For support, contact: [your-support-email]

## 🎯 Production Readiness Checklist

### Final Verification Steps
- [ ] All 20 critical fixes implemented and tested
- [ ] Integration tests passing
- [ ] Security scan completed
- [ ] Performance benchmarks met
- [ ] Monitoring systems operational
- [ ] Backup procedures tested
- [ ] Documentation updated
- [ ] Team training completed

### Go-Live Checklist
- [ ] DNS configured
- [ ] SSL certificates installed
- [ ] Load balancer configured
- [ ] Monitoring alerts set up
- [ ] Rollback plan prepared
- [ ] Support team notified
- [ ] User communication sent
