# Exam Grader Deployment Guide

## 1. Environment Variables
- `FLASK_ENV=production`
- `SECRET_KEY=your-secret-key`
- `DATABASE_URL=postgresql://user:pass@host/dbname`
- `REDIS_URL=redis://localhost:6379/0`
- `CELERY_BROKER_URL=redis://localhost:6379/0`
- `CELERY_RESULT_BACKEND=redis://localhost:6379/0`
- `HANDWRITING_OCR_API_KEY=your-ocr-key`
- `LLM_API_KEY=your-llm-key`

## 2. Services
- **Flask App:**
  - Use `gunicorn` or `uwsgi` for WSGI serving.
  - Example: `gunicorn -k eventlet -w 1 webapp.exam_grader_app:app`
- **SocketIO:**
  - Use `eventlet` or `gevent` for async support.
  - Example: `gunicorn -k eventlet -w 1 webapp.exam_grader_app:app`
- **Celery Workers:**
  - Start with: `celery -A src.services.background_tasks.celery_app worker --loglevel=info --concurrency=4`
- **Redis:**
  - Use as broker and result backend for Celery and SocketIO message queue.
  - Secure Redis with a password and bind to localhost or use a firewall.

## 3. Recommended Settings
- Set `worker_max_tasks_per_child` in Celery to avoid memory leaks.
- Use `timeout` and `soft_time_limit` for long-running tasks.
- Use `Flask-Limiter` to prevent API abuse.
- Enable HTTPS in production.

## 4. Monitoring & Health
- Use `/api/health` endpoint for health checks.
- Monitor Celery, Redis, and DB logs.
- Set up alerts for failed jobs or unhealthy services.

## 5. Static Files
- Serve static files (JS, CSS, images) via a CDN or reverse proxy (e.g., Nginx).

## 6. Database Migrations
- Use Alembic or Flask-Migrate for schema changes.

## 7. Troubleshooting
- Check logs for errors (`logs/` directory, Celery, Redis, Gunicorn output).
- Use the manual QA checklist in `tests/manual_qa_checklist.md` for validation.

---

**For questions or issues, see the README or contact the system maintainer.** 