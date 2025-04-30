# Configuration Guide

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# DeepSeek API Configuration
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions

# OCR Configuration
TESSERACT_CMD_PATH=/usr/bin/tesseract  # Path to tesseract executable

# Application Settings
OUTPUT_DIR=output
TEMP_DIR=temp
LOG_LEVEL=INFO

# Grading Settings
SIMILARITY_THRESHOLD=0.8
OCR_CONFIDENCE_THRESHOLD=0.7
MAX_TOKENS=1000
TEMPERATURE=0.0
```

## Required Dependencies

1. Python 3.10 or higher
2. Tesseract OCR (for handwritten text recognition)
3. Required Python packages (install using `pip install -r requirements.txt`):
   - python-docx
   - PyMuPDF
   - streamlit
   - python-dotenv
   - pytesseract
   - Pillow
   - requests

## Directory Structure

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
├── output/          # Generated reports
├── temp/           # Temporary files
└── data/
    ├── guides/     # Sample marking guides
    └── submissions/ # Sample student submissions
```

## Usage

1. Set up your environment variables in `.env`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the web interface: `streamlit run src/web/app.py`

## File Formats

### Marking Guide

- DOCX or PDF format
- Questions should be numbered (e.g., "Q1", "Question 1")
- Mark allocations should be specified (e.g., "[marks: 10]")
- Model answers should follow each question

### Student Submissions

Supported formats:

- Text files (.txt)
- Word documents (.docx)
- PDF files (.pdf)
- Images (.jpg, .jpeg, .png, .bmp)

## Output

The application generates:

1. Individual student reports (JSON and CSV)
2. Class summary report (JSON and CSV)
3. Detailed feedback for each answer
4. Grading confidence scores
