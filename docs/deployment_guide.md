# LLM Training Improvements Deployment Guide

This guide provides comprehensive instructions for deploying the LLM training improvements to your environment.

## Overview

The LLM training improvements include:
- Enhanced document processing with fallback mechanisms
- Model testing infrastructure
- System monitoring and health checks
- Improved error handling and recovery
- Performance optimizations
- Analytics and reporting capabilities

## Prerequisites

### System Requirements
- Python 3.8 or higher
- SQLite 3.x or PostgreSQL 12+
- At least 4GB RAM
- At least 10GB free disk space
- Write permissions to application directories

### Dependencies
- All Python packages listed in `requirements.txt`
- psutil for system monitoring
- Additional packages for specific features

## Pre-Deployment Checklist

1. **Backup Current System**
   ```bash
   # Create backup directory
   mkdir -p backups/pre_deployment_$(date +%Y%m%d_%H%M%S)
   
   # Backup database
   cp instance/exam_grader.db backups/pre_deployment_$(date +%Y%m%d_%H%M%S)/
   
   # Backup configuration
   cp -r config backups/pre_deployment_$(date +%Y%m%d_%H%M%S)/
   ```

2. **Verify System Health**
   ```bash
   # Check disk space
   df -h
   
   # Check memory usage
   free -h
   
   # Check running processes
   ps aux | grep python
   ```

3. **Test Database Connection**
   ```bash
   python -c "from webapp.app_factory import create_app; from src.database.models import db; app = create_app(); app.app_context().push(); db.session.execute('SELECT 1').fetchone(); print('Database OK')"
   ```

## Deployment Methods

### Method 1: Automated Deployment (Recommended)

Use the provided deployment script for automated deployment:

```bash
# For production environment
python scripts/deploy_llm_improvements.py --environment production

# For development environment
python scripts/deploy_llm_improvements.py --environment development

# Dry run (no changes made)
python scripts/deploy_llm_improvements.py --environment production --dry-run
```

### Method 2: Manual Deployment

If you prefer manual deployment or need to customize the process:

#### Step 1: Stop Services
```bash
# Stop web application (adjust for your setup)
sudo systemctl stop exam-grader-webapp
# or
pkill -f "python.*run_app.py"
```

#### Step 2: Update Dependencies
```bash
pip install -r requirements.txt --upgrade
```

#### Step 3: Run Database Migrations
```bash
python -c "
from migrations.add_llm_testing_enhancements import upgrade
upgrade()
print('Migrations completed')
"
```

#### Step 4: Update Configuration
```bash
# Copy new configuration templates if needed
cp config/deployment_production.json.template config/deployment_production.json
# Edit configuration as needed
```

#### Step 5: Start Services
```bash
# Start web application
sudo systemctl start exam-grader-webapp
# or
python run_app.py &
```

#### Step 6: Verify Deployment
```bash
# Check application health
curl http://localhost:5000/api/monitoring/health
```

## Configuration

### Environment-Specific Configuration

The deployment uses environment-specific configuration files:

- `config/deployment_production.json` - Production settings
- `config/deployment_development.json` - Development settings
- `config/deployment_testing.json` - Testing settings

### Key Configuration Options

```json
{
  "database_backup": true,
  "service_restart_timeout": 60,
  "health_check_timeout": 120,
  "rollback_on_failure": true,
  "monitoring": {
    "enabled": true,
    "check_interval": 30,
    "alert_thresholds": {
      "cpu_warning": 80,
      "cpu_critical": 95,
      "memory_warning": 85,
      "memory_critical": 95
    }
  }
}
```

### Monitoring Configuration

The system includes comprehensive monitoring. Configure thresholds in your deployment configuration:

```json
{
  "monitoring": {
    "alert_thresholds": {
      "cpu_warning": 80,
      "cpu_critical": 95,
      "memory_warning": 85,
      "memory_critical": 95,
      "disk_warning": 90,
      "disk_critical": 95,
      "response_time_warning_ms": 5000,
      "response_time_critical_ms": 10000
    }
  }
}
```

## Post-Deployment Verification

### 1. Health Checks
```bash
# Check overall system health
curl http://localhost:5000/api/monitoring/health

# Check specific service health
curl http://localhost:5000/api/monitoring/health-checks
```

### 2. Feature Verification
```bash
# Test document upload
curl -X POST -F "files=@test_document.txt" http://localhost:5000/api/llm/documents/upload

# Test monitoring endpoints
curl http://localhost:5000/api/monitoring/metrics
```

### 3. Database Verification
```bash
python -c "
from webapp.app_factory import create_app
from src.database.models import LLMModelTest, ProcessingMetrics
app = create_app()
with app.app_context():
    print(f'LLMModelTest table exists: {LLMModelTest.query.count() >= 0}')
    print(f'ProcessingMetrics table exists: {ProcessingMetrics.query.count() >= 0}')
"
```

## Rollback Procedures

If deployment fails or issues are discovered, use the rollback script:

### List Available Backups
```bash
python scripts/rollback_deployment.py --list-backups
```

### Perform Rollback
```bash
python scripts/rollback_deployment.py --backup-path backups/deployment_20250127_143022 --environment production
```

### Manual Rollback
If the automated rollback fails:

1. **Stop Services**
   ```bash
   sudo systemctl stop exam-grader-webapp
   ```

2. **Restore Database**
   ```bash
   cp backups/deployment_20250127_143022/exam_grader.db instance/
   ```

3. **Restore Configuration**
   ```bash
   cp -r backups/deployment_20250127_143022/config/* config/
   ```

4. **Start Services**
   ```bash
   sudo systemctl start exam-grader-webapp
   ```

## Troubleshooting

### Common Issues

#### 1. Database Migration Failures
```bash
# Check database integrity
python -c "
from webapp.app_factory import create_app
from src.database.models import db
app = create_app()
with app.app_context():
    try:
        db.session.execute('PRAGMA integrity_check').fetchall()
        print('Database integrity OK')
    except Exception as e:
        print(f'Database issue: {e}')
"
```

#### 2. Permission Issues
```bash
# Fix permissions
chmod -R 755 logs uploads temp instance
chown -R www-data:www-data logs uploads temp instance  # Adjust user as needed
```

#### 3. Service Start Failures
```bash
# Check logs
tail -f logs/app.log
tail -f deployment.log

# Check process status
ps aux | grep python
netstat -tlnp | grep :5000
```

#### 4. Memory Issues
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Clear cache if needed
echo 3 > /proc/sys/vm/drop_caches  # Requires root
```

### Log Files

Monitor these log files during and after deployment:

- `deployment.log` - Deployment process logs
- `rollback.log` - Rollback process logs
- `logs/app.log` - Application logs
- `logs/exam_grader_app_errors.log` - Error logs

### Performance Monitoring

Access the monitoring dashboard at:
```
http://your-server/monitoring/dashboard
```

Or use API endpoints:
```bash
# System metrics
curl http://localhost:5000/api/monitoring/metrics

# Performance dashboard
curl http://localhost:5000/api/monitoring/dashboard

# Active alerts
curl http://localhost:5000/api/monitoring/alerts
```

## Security Considerations

### 1. File Permissions
Ensure proper file permissions after deployment:
```bash
# Application files
chmod 644 *.py
chmod 755 scripts/*.py

# Sensitive files
chmod 600 .env .env.local
chmod 600 instance/secrets.enc

# Directories
chmod 755 logs uploads temp
chmod 700 instance
```

### 2. Database Security
- Ensure database files are not web-accessible
- Use strong database passwords if using PostgreSQL
- Regular database backups

### 3. Network Security
- Configure firewall rules
- Use HTTPS in production
- Implement rate limiting

## Maintenance

### Regular Tasks

1. **Monitor System Health**
   ```bash
   # Daily health check
   curl http://localhost:5000/api/monitoring/health
   ```

2. **Clean Up Old Backups**
   ```bash
   # Remove backups older than 30 days
   find backups/ -name "deployment_*" -mtime +30 -exec rm -rf {} \;
   ```

3. **Update Dependencies**
   ```bash
   # Monthly dependency updates
   pip list --outdated
   pip install -r requirements.txt --upgrade
   ```

4. **Log Rotation**
   ```bash
   # Rotate large log files
   logrotate -f /etc/logrotate.d/exam-grader
   ```

### Performance Optimization

1. **Database Optimization**
   ```bash
   # SQLite optimization
   python -c "
   from webapp.app_factory import create_app
   from src.database.models import db
   app = create_app()
   with app.app_context():
       db.session.execute('VACUUM')
       db.session.execute('ANALYZE')
       db.session.commit()
   "
   ```

2. **Cache Management**
   - Monitor cache hit rates
   - Clear cache if memory usage is high
   - Adjust cache timeouts based on usage patterns

## Support

### Getting Help

1. **Check Logs**: Always check application and deployment logs first
2. **System Status**: Use monitoring dashboard to identify issues
3. **Documentation**: Refer to feature-specific documentation
4. **Community**: Check project documentation and issues

### Reporting Issues

When reporting deployment issues, include:
- Environment details (OS, Python version, etc.)
- Deployment method used
- Error messages from logs
- System resource usage
- Steps to reproduce

## Appendix

### A. Environment Variables

Required environment variables:
```bash
# Database
DATABASE_URL=sqlite:///instance/exam_grader.db

# Security
SECRET_KEY=your-secret-key-here
SECURITY_PASSWORD_SALT=your-salt-here

# Monitoring (optional)
MONITORING_ENABLED=true
MONITORING_CHECK_INTERVAL=30
```

### B. Service Configuration

Example systemd service file (`/etc/systemd/system/exam-grader-webapp.service`):
```ini
[Unit]
Description=Exam Grader Web Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/exam_grader
Environment=PATH=/path/to/venv/bin
ExecStart=/path/to/venv/bin/python run_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### C. Nginx Configuration

Example nginx configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /static {
        alias /path/to/exam_grader/webapp/static;
    }
}
```

This completes the deployment guide for the LLM training improvements.