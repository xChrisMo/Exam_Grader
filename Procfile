web: gunicorn --bind 0.0.0.0:$PORT --timeout 300 --workers 1 --worker-class gevent --worker-connections 1000 webapp.app:app
release: python -c "import sys; sys.path.insert(0, '.'); from webapp.app import app; from src.database.models import db; app.app_context().push(); db.create_all()"
