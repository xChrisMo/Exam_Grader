# Exam Grader

An AI-powered application for educators to grade student exam submissions against marking guides using DeepSeek LLM.

## Features

### Document Processing

- **Document Parsing**: Upload and parse marking guides and student submissions in various formats (PDF, Word, images, text)
- **OCR Processing**: Extract text from image-based submissions automatically

### AI-Powered Grading

- **Marking Guide Analysis**: Extract questions, criteria, and mark allocation
- **LLM Integration**: Utilize DeepSeek's LLM for intelligent analysis
- **Detailed Feedback**: Generate per-criterion feedback with justifications

### Criteria Mapping

- **Submission-to-Criteria Mapping**: Map specific parts of student submissions to each marking criterion
- **Confidence Scoring**: Evaluate how well each submission section addresses the criteria
- **Gap Analysis**: Identify unmapped criteria and submission sections

### Web Interface

- **Intuitive Upload Flow**: Step-by-step process for uploading and analyzing documents
- **Visualized Results**: Clear presentation of grades and feedback
- **Responsive Design**: Works on desktop and mobile devices
- **Result Caching**: Store results to avoid redundant API calls

## Getting Started

### Prerequisites

- Python 3.8 or higher
- DeepSeek API key (set in `.env` file)
- Required Python packages (see `requirements.txt`)

### Installation

1. Clone the repository:

   ```
   git clone https://github.com/your-username/exam-grader.git
   cd exam-grader
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your DeepSeek API key:

   ```
   DEEPSEEK_API_KEY=your_api_key_here
   ```

4. Run the application:

   ```
   python run_app.py
   ```

## Usage Guide

### Core Application

The application provides a command-line interface and Python API for:

1. **Document Parsing**: Extract text from various file formats
2. **OCR Processing**: Convert handwritten content to text
3. **LLM Integration**: AI-powered grading and mapping
4. **Result Storage**: Cache and store grading results

### Supported File Formats

- **Documents**: PDF, DOCX, TXT
- **Images**: JPG, JPEG, PNG, TIFF, BMP, GIF (processed with OCR)

### Python API Usage

```python
from src.parsing.parse_submission import parse_student_submission
from src.services.llm_service import LLMService
from src.services.mapping_service import MappingService

# Parse a document
result, text, error = parse_student_submission('exam.pdf')
if not error:
    print(f'Extracted text: {text}')

# Use LLM service for grading
llm = LLMService()
# ... grading logic
```

## Running Tests

The project includes a comprehensive test suite to ensure all components work correctly:

```bash
# Run all tests
python -m unittest discover tests

# Run specific test modules
python -m unittest tests.test_services
python -m unittest tests.test_mapping_service
python -m unittest tests.test_answer_comparison
```

You can also run individual test files directly:

```bash
python tests/test_services.py
python tests/test_mapping_service.py
python tests/test_answer_comparison.py
```

## Project Structure

The application follows a modular architecture:

```
exam-grader/
├── src/                # Source code
│   ├── config/         # Configuration management
│   ├── parsing/        # Document parsing modules
│   ├── services/       # Core services (OCR, LLM, grading, mapping)
│   └── storage/        # Storage services for caching results
├── utils/              # Utility functions and helpers
├── temp/               # Runtime temporary files (auto-created)
├── logs/               # Application logs (auto-created)
├── output/             # Output files (auto-created)
├── results/            # Results storage (auto-created)
├── .env                # Environment variables
├── .env.example        # Environment configuration template
├── requirements.txt    # Python dependencies
├── pyproject.toml      # Project configuration
├── validate_setup.py   # Setup validation script
└── run_app.py          # Application entry point
```

## Key Components

### Mapping Service

The mapping service analyzes both the marking guide and student submission to create detailed mappings between criteria and submission sections. It uses the DeepSeek LLM to:

1. Identify individual criteria in the marking guide
2. Find relevant sections in the student submission that address each criterion
3. Assign confidence scores to indicate match quality
4. Track unmapped criteria and submission sections

### Grading Service

The grading service evaluates student submissions by:

1. Analyzing how well each criterion is addressed
2. Assigning scores based on the marking guide
3. Providing detailed feedback and justifications
4. Calculating overall grades and percentages

## License

[MIT License](LICENSE)

## Acknowledgements

- DeepSeek for providing the LLM API
- HandwritingOCR for text extraction from images
- Python community for excellent libraries
