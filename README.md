# Exam Grader Application

An AI-powered assessment platform for grading exams and providing detailed feedback.

## Setup and Installation

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the application: `python run_app.py`

## Environment Configuration

Create a `.env` file in the project root or in the `instance/` directory with the following variables:

```
HOST=127.0.0.1
PORT=8501
DEBUG=True
MAX_FILE_SIZE_MB=20
HANDWRITING_OCR_API_KEY=your_ocr_api_key
DEEPSEEK_API_KEY=your_llm_api_key
```

## Dependencies

The application uses the following key dependencies:

- Flask 2.3.x: Web framework
- Flask-Babel 2.0.0: Internationalization support
- Flask-SQLAlchemy: Database ORM
- PyMuPDF: PDF processing
- OpenAI: AI integration

## Known Compatibility Issues

### Flask and Flask-Babel Compatibility

There is a compatibility issue between Flask 3.x and Flask-Babel 2.0.0. The application is currently configured to use Flask 2.3.x to maintain compatibility with Flask-Babel 2.0.0.

#### Issue Details

Flask 3.0 changed how extensions register functions like `localeselector`. The `@babel.localeselector` decorator used in Flask-Babel 2.0.0 is not compatible with Flask 3.0+.

#### Current Solution

The application uses a two-step initialization pattern for Flask-Babel and manually sets the locale selector function:

```python
# Initialize Babel without using the decorator
babel = Babel()
babel.init_app(app)

# Define locale selector function
def get_locale():
    return 'en'

# Manually set the locale selector
babel.locale_selector_func = get_locale
```

#### Future Upgrades

If upgrading to Flask 3.x in the future, the initialization should be changed to use the new API:

```python
babel = Babel()
babel.init_app(app, locale_selector=get_locale)
```

Alternatively, wait for a Flask-Babel update that supports Flask 3.x.

## License

[MIT License](LICENSE)