web: python run_app.py
release: python clear_secrets.py && python -c "import sys; sys.path.insert(0, '.'); from webapp.app import app; from src.database.models import db; app.app_context().push(); db.create_all(); print('Database tables created successfully')"
