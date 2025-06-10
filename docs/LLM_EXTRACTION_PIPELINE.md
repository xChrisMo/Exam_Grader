# LLM-Powered Marking Guide Extraction Pipeline

## Overview

The Exam Grader application now includes an advanced LLM-powered extraction pipeline that intelligently processes marking guide documents after OCR parsing. This system uses artificial intelligence to accurately extract questions, scores, and metadata from marking guides, significantly improving the accuracy and reliability of the grading process.

## Features

### 🧠 **Intelligent Question Extraction**
- **Complete Question Text**: Extracts full question content, not just keywords
- **Question Numbering**: Preserves original numbering schemes (1, 2, 3 or I, II, III, etc.)
- **Sub-questions**: Identifies and structures sub-parts (1a, 1b, 2i, 2ii, etc.)
- **Context Awareness**: Understands question boundaries and relationships

### 📊 **Smart Score Detection**
- **Flexible Score Formats**: Recognizes "marks", "points", "pts", or numbers in parentheses
- **Automatic Calculation**: Computes total marks from individual question scores
- **Score Validation**: Ensures scores are numeric and reasonable
- **Missing Score Estimation**: Provides intelligent estimates when scores are unclear

### 🔍 **Metadata Extraction**
- **Extraction Confidence**: Provides confidence scores for extraction quality
- **Processing Notes**: Documents any assumptions or ambiguities encountered
- **Method Tracking**: Records whether LLM or fallback extraction was used
- **Timestamp Information**: Tracks when extraction was performed

## Architecture

### Pipeline Flow

```
1. File Upload → 2. OCR Parsing → 3. LLM Extraction → 4. Database Storage
     ↓               ↓               ↓                ↓
   PDF/Word      Raw Text      Structured Data    User-Specific
   Document      Content       (JSON Format)      Guide Library
```

### Components

#### 1. **GuideExtractionService** (`src/services/guide_extraction_service.py`)
- Main service class for LLM-powered extraction
- Handles LLM communication and response processing
- Provides fallback mechanisms for error cases
- Creates standardized data structures

#### 2. **Enhanced Upload Route** (`webapp/exam_grader_app.py`)
- Integrates LLM extraction into existing upload workflow
- Maintains backward compatibility with existing functionality
- Provides user feedback on extraction quality
- Stores enhanced data in database

#### 3. **Database Integration**
- User-specific guide storage with enhanced metadata
- Extraction method and confidence tracking
- Structured question data with scores and sub-questions
- Processing status and timestamp information

## Usage

### For Users

1. **Upload Marking Guide**: Use the existing upload interface
2. **Automatic Processing**: OCR extracts text, LLM analyzes structure
3. **Review Results**: Check extraction quality and question count
4. **Use in Grading**: Extracted questions are available for submission grading

### Success Messages

- **LLM Success**: "Marking guide uploaded successfully! Extracted 5 questions with 100 total marks using AI analysis."
- **Basic Success**: "Marking guide uploaded successfully! Found 3 questions with 75 total marks."
- **Fallback**: "Guide uploaded successfully, but advanced question extraction is not available."

## Data Structure

### Extracted Guide Data

```json
{
    "questions": [
        {
            "id": "q1",
            "number": "1",
            "text": "Complete question text here",
            "max_score": 10,
            "sub_questions": [
                {
                    "id": "q1a",
                    "number": "1a",
                    "text": "Sub-question text",
                    "max_score": 5
                }
            ]
        }
    ],
    "total_marks": 100,
    "metadata": {
        "num_questions": 5,
        "num_sub_questions": 8,
        "extraction_confidence": 0.95,
        "extraction_method": "llm_powered",
        "processing_notes": "Any relevant notes"
    }
}
```

### Database Storage

```python
MarkingGuide(
    user_id=current_user.id,
    title="Guide Title",
    description="Uploaded guide: filename.pdf | LLM-extracted 5 questions | Confidence: 95.0%",
    filename="filename.pdf",
    content_text="Raw OCR text...",
    questions=[...],  # Structured question data
    total_marks=100.0,
    processing_status='completed'
)
```

## Error Handling

### Graceful Degradation

1. **LLM Unavailable**: Falls back to basic extraction with manual patterns
2. **JSON Parse Error**: Uses manual extraction fallback
3. **OCR Failure**: Attempts text file reading as fallback
4. **Network Issues**: Provides appropriate error messages to users

### Validation

- **Required Fields**: Ensures all questions have ID, text, and score
- **Score Validation**: Verifies scores are numeric and reasonable
- **Structure Validation**: Checks data format and completeness
- **Confidence Scoring**: Provides quality assessment of extraction

## Configuration

### LLM Service Requirements

- **API Key**: DeepSeek API key in environment variables
- **Model**: Uses `deepseek-reasoner` model for analysis
- **Temperature**: Set to 0.0 for deterministic results
- **Timeout**: Configured for reasonable response times

### Fallback Behavior

When LLM service is unavailable:
- Uses pattern matching for basic question detection
- Provides lower confidence scores
- Still creates usable guide structures
- Maintains full application functionality

## Benefits

### For Educators

- **Time Saving**: Automatic question extraction eliminates manual data entry
- **Accuracy**: AI-powered analysis reduces human error
- **Consistency**: Standardized extraction across all guides
- **Flexibility**: Handles various marking guide formats and styles

### For Students

- **Better Feedback**: More accurate question mapping leads to better grading
- **Faster Results**: Automated processing speeds up grading workflow
- **Consistent Grading**: Standardized question structures ensure fair assessment

## Future Enhancements

### Planned Features

- **Multi-language Support**: Extract questions in different languages
- **Image Question Handling**: Process questions with embedded images
- **Custom Scoring Schemes**: Support for weighted or complex scoring
- **Batch Processing**: Handle multiple guides simultaneously

### Integration Opportunities

- **Learning Management Systems**: Direct integration with LMS platforms
- **Question Banks**: Export extracted questions to question databases
- **Analytics Dashboard**: Detailed extraction quality metrics
- **API Endpoints**: Programmatic access to extraction services

## Troubleshooting

### Common Issues

1. **Low Extraction Confidence**: Check guide formatting and clarity
2. **Missing Questions**: Verify question numbering is clear
3. **Incorrect Scores**: Ensure score values are explicitly stated
4. **LLM Timeout**: Check network connectivity and API key validity

### Support

For technical support or feature requests related to the LLM extraction pipeline, please refer to the main application documentation or contact the development team.
