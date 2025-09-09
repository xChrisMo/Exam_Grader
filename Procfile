web: python run_app.py
release: chmod +x install_tesseract.sh && ./install_tesseract.sh && python clear_secrets.py && python check_ocr_status.py && python -c "import sys; sys.path.insert(0, '.'); from webapp.app import app; from src.database.models import db; app.app_context().push(); db.create_all(); print('Database tables created successfully')"
