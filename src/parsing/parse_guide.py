import os
from typing import Dict, List, Tuple
import docx
import fitz  # PyMuPDF

class MarkingGuideParser:
    def __init__(self):
        self.questions: List[Dict] = []
        self.total_marks: int = 0

    def parse_docx(self, file_path: str) -> Tuple[List[Dict], int]:
        """Parse a DOCX marking guide file."""
        try:
            doc = docx.Document(file_path)
            self._process_docx_content(doc)
            return self.questions, self.total_marks
        except Exception as e:
            raise Exception(f"Error parsing DOCX file: {str(e)}")

    def parse_pdf(self, file_path: str) -> Tuple[List[Dict], int]:
        """Parse a PDF marking guide file."""
        try:
            doc = fitz.open(file_path)
            self._process_pdf_content(doc)
            return self.questions, self.total_marks
        except Exception as e:
            raise Exception(f"Error parsing PDF file: {str(e)}")

    def _process_docx_content(self, doc: docx.Document) -> None:
        """Process content from a DOCX document."""
        current_question = None
        current_marks = 0

        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue

            # Check for question number pattern (e.g., "Q1", "Question 1")
            if text.lower().startswith(('q', 'question')):
                if current_question:
                    self.questions.append(current_question)
                current_question = {
                    'number': self._extract_question_number(text),
                    'text': '',
                    'model_answer': '',
                    'marks': 0
                }
            elif '[marks:' in text.lower():
                marks = self._extract_marks(text)
                if current_question:
                    current_question['marks'] = marks
                    self.total_marks += marks
            elif current_question:
                if not current_question['text']:
                    current_question['text'] = text
                else:
                    current_question['model_answer'] += text + '\n'

        if current_question:
            self.questions.append(current_question)

    def _process_pdf_content(self, doc: fitz.Document) -> None:
        """Process content from a PDF document."""
        current_question = None
        current_marks = 0

        for page in doc:
            text = page.get_text()
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Similar logic to DOCX processing
                if line.lower().startswith(('q', 'question')):
                    if current_question:
                        self.questions.append(current_question)
                    current_question = {
                        'number': self._extract_question_number(line),
                        'text': '',
                        'model_answer': '',
                        'marks': 0
                    }
                elif '[marks:' in line.lower():
                    marks = self._extract_marks(line)
                    if current_question:
                        current_question['marks'] = marks
                        self.total_marks += marks
                elif current_question:
                    if not current_question['text']:
                        current_question['text'] = line
                    else:
                        current_question['model_answer'] += line + '\n'

        if current_question:
            self.questions.append(current_question)

    def _extract_question_number(self, text: str) -> str:
        """Extract question number from text."""
        import re
        match = re.search(r'[Qq](?:uestion)?\s*(\d+)', text)
        return match.group(1) if match else ""

    def _extract_marks(self, text: str) -> int:
        """Extract marks from text."""
        import re
        match = re.search(r'\[marks:\s*(\d+)\]', text.lower())
        return int(match.group(1)) if match else 0

def parse_marking_guide(file_path: str) -> Tuple[List[Dict], int]:
    """Main function to parse a marking guide file."""
    parser = MarkingGuideParser()
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.docx':
        return parser.parse_docx(file_path)
    elif ext == '.pdf':
        return parser.parse_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}") 