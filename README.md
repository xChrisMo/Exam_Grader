# Automated Engineering Grading App

An AI-powered system for automated grading of engineering exam submissions.

## Project Structure

```
grading_app/
├── src/
│   ├── parsing/
│   │   ├── parse_guide.py
│   │   └── parse_submission.py
│   ├── grading/
│   │   ├── answer_matcher.py
│   │   └── ai_grader.py
│   ├── output/
│   │   ├── report_generator.py
│   │   └── csv_exporter.py
│   └── web/
│       └── app.py
├── tests/
├── config/
│   └── .env.example
└── data/
    ├── guides/
    └── submissions/
```

## Setup

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp config/.env.example config/.env
```

## Usage

### CLI Mode

```bash
python src/main.py --guide path/to/guide.docx --submission path/to/submission.pdf
```

### Web UI

```bash
streamlit run src/web/app.py
```

## Features

- Marking guide parsing (DOCX/PDF)
- Student submission parsing (text/OCR)
- AI-powered answer grading
- Detailed feedback generation
- CSV/JSON report export
- Web interface (optional)

## Development

Run tests:

```bash
pytest tests/
```

## License

MIT License
