# Technology Stack and Build System

## Core Technologies

### Backend
- **Python 3.8+**: Primary programming language
- **Flask 3.0+**: Web framework with blueprints architecture
- **SQLAlchemy 2.0+**: Database ORM with SQLite
- **Flask-Login**: User authentication and session management
- **Flask-WTF**: CSRF protection and form handling
- **Flask-SocketIO**: Real-time WebSocket communication

### Frontend
- **Jinja2**: Server-side templating engine
- **Tailwind CSS 3.4+**: Utility-first CSS framework
- **JavaScript (ES2020)**: Client-side interactivity
- **TypeScript**: Type-safe JavaScript development

### AI/ML Services
- **OpenAI API**: LLM services for grading
- **HandwritingOCR API**: Primary OCR service
- **Multiple OCR Fallbacks**: EasyOCR, PaddleOCR, TrOCR, Tesseract
- **DeepSeek API**: Alternative LLM provider

### Data Processing
- **pdf2image**: PDF to image conversion for OCR processing
- **python-docx**: Word document handling
- **Pillow**: Image processing
- **pandas/numpy**: Data analysis and export

## Build System and Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -e ".[dev]"
```

### Development Commands
```bash
# Start development server
python run_app.py
python webapp/app.py

# Start with specific configuration
HOST=127.0.0.1 PORT=8501 DEBUG=True python run_app.py

# Build CSS (Tailwind)
npm run build-css        # Development with watch
npm run build-css-prod   # Production minified
```

### Testing
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov=webapp --cov=utils

# Run specific test categories
python -m pytest -m unit
python -m pytest -m integration
python -m pytest -m "not slow"
```

### Database Management
```bash
# Initialize database
python -c "from webapp.app import app, db; app.app_context().push(); db.create_all()"

# Reset database (WARNING: deletes data)
python reset_database.py

# Create database
python create_db.py
```

### Code Quality
```bash
# Format code
black src/ webapp/ utils/
isort src/ webapp/ utils/

# Lint code
flake8 src/ webapp/ utils/
pylint src/ webapp/ utils/

# Type checking
mypy src/ webapp/ utils/

# Security scanning
bandit -r src/ webapp/ utils/
```

### Production Deployment
```bash
# Production server with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 webapp.app:app

# Docker build
docker build -t exam-grader .
docker run -p 8501:8501 exam-grader
```

## Configuration Management

### Environment Variables
- Copy `env.example` to `.env` for local development
- Required: `HANDWRITING_OCR_API_KEY`, `DEEPSEEK_API_KEY`
- Optional: `DATABASE_URL`, `SECRET_KEY`, `DEBUG`, `HOST`, `PORT`

### Configuration Files
- `config/`: JSON configuration files for different environments
- `src/config/unified_config.py`: Centralized configuration management
- `pyproject.toml`: Python project configuration and dependencies
- `tailwind.config.js`: CSS framework configuration
- `tsconfig.json`: TypeScript compiler options

## Package Management

### Python Dependencies
- **Core**: Flask ecosystem, SQLAlchemy, security libraries
- **AI/ML**: OpenAI, OCR engines, document processing
- **Development**: pytest, black, mypy, coverage tools
- **Optional**: Background tasks (Celery), PDF generation, analytics

### Node.js Dependencies
- **Tailwind CSS**: Utility-first CSS framework
- **Plugins**: Forms, typography extensions
- Minimal JavaScript build system for CSS processing

## Architecture Patterns

### Application Factory Pattern
- `webapp/app_factory.py`: Clean Flask app creation
- Modular blueprint registration
- Extension initialization
- Error handler setup

### Service Layer Architecture
- `src/services/`: Business logic services
- Dependency injection and service registry
- Background task processing
- Monitoring and health checks

### Configuration Management
- Unified configuration system
- Environment-specific settings
- Validation and type safety
- Hot-reload capabilities