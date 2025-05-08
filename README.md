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
   python web/app.py
   ```

5. Access the web interface at `http://localhost:8501`

## Usage Guide

### Step 1: Upload Marking Guide
- Upload your marking guide document (DOCX or TXT format)
- The system will extract criteria, questions, and mark allocations

### Step 2: Upload Student Submission
- Upload a student's submission (PDF, DOCX, images, or TXT)
- OCR will automatically extract text from images or scanned documents

### Step 3: Map Submission to Criteria
- Click "Map Submission to Criteria" to analyze how the submission addresses each criterion
- View the mapping to see which parts of the submission match each criterion
- Identify unmapped criteria and submission sections

### Step 4: Grade Submission
- Click "Grade Submission" to evaluate the submission against the marking guide
- Review detailed feedback and scores for each criterion
- Export results as needed

## Architecture

The application follows a modular architecture:

- `src/parsing/`: Document parsing modules
- `src/services/`: Core services (OCR, LLM, grading, mapping)
- `src/storage/`: Storage services for caching results
- `web/`: Web interface using Flask
- `utils/`: Utility functions and helpers

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
- OCR libraries for text extraction
- Flask for the web framework
