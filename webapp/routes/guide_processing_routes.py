"""
Guide Processing Routes

This module contains routes for processing marking guides with LLM
to extract questions and marking criteria.
"""

import os
import json
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from src.database.models import db, MarkingGuide
from src.services.consolidated_llm_service import ConsolidatedLLMService
from src.services.consolidated_ocr_service import ConsolidatedOCRService
from utils.logger import logger

guide_processing_bp = Blueprint('guide_processing', __name__)

# Initialize services
llm_service = ConsolidatedLLMService()
ocr_service = ConsolidatedOCRService()

@guide_processing_bp.route('/api/process-guide', methods=['POST'])
@login_required
def process_guide():
    """Process a marking guide to extract questions using LLM."""
    try:
        data = request.get_json()
        if not data or 'guide_id' not in data:
            return jsonify({'success': False, 'message': 'Guide ID is required'}), 400
        
        guide_id = data['guide_id']
        logger.info(f"Processing guide {guide_id} for user {current_user.id}")
        
        # Get the guide
        guide = MarkingGuide.query.filter_by(
            id=guide_id,
            user_id=current_user.id
        ).first()
        
        if not guide:
            logger.warning(f"Guide {guide_id} not found for user {current_user.id}")
            return jsonify({'success': False, 'message': 'Guide not found'}), 404
        
        if guide.questions and len(guide.questions) > 0:
            return jsonify({
                'success': True, 
                'message': 'Guide already processed',
                'questions': guide.questions,
                'total_marks': guide.total_marks
            })
        
        if not guide.content_text:
            content_text = extract_text_from_file(guide.file_path, guide.file_type)
            if not content_text:
                return jsonify({
                    'success': False, 
                    'message': 'Could not extract text from guide file'
                }), 400
            
            guide.content_text = content_text
        else:
            content_text = guide.content_text
        
        # Use LLM to extract questions
        questions_data = extract_questions_with_llm(content_text)
        
        if not questions_data:
            return jsonify({
                'success': False, 
                'message': 'Could not extract questions from guide content'
            }), 400
        
        # Calculate total marks
        total_marks = sum(q.get('marks', 0) for q in questions_data)
        
        # Update the guide
        guide.questions = questions_data
        guide.total_marks = total_marks
        
        db.session.commit()
        
        logger.info(f"Successfully processed guide {guide_id} - extracted {len(questions_data)} questions")
        
        return jsonify({
            'success': True,
            'message': f'Successfully extracted {len(questions_data)} questions',
            'questions': questions_data,
            'total_marks': total_marks
        })
        
    except Exception as e:
        logger.error(f"Error processing guide: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': f'Error processing guide: {str(e)}'
        }), 500

def extract_text_from_file(file_path: str, file_type: str) -> str:
    """Extract text content from a file."""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        # Handle different file types
        if file_type.lower() in ['pdf']:
            if ocr_service.is_available():
                result = ocr_service.extract_text(file_path)
                return result.get('text', '') if result else ''
            else:
                # Fallback: try to read PDF with PyPDF2
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as file:
                        reader = PyPDF2.PdfReader(file)
                        text = ''
                        for page in reader.pages:
                            text += page.extract_text() + '\n'
                        return text
                except ImportError:
                    logger.warning("PyPDF2 not available for PDF text extraction")
                    return None
        
        elif file_type.lower() in ['txt']:
            # Read text file directly
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        
        elif file_type.lower() in ['docx', 'doc']:
            try:
                from docx import Document
                doc = Document(file_path)
                text = ''
                for paragraph in doc.paragraphs:
                    text += paragraph.text + '\n'
                return text
            except ImportError:
                logger.warning("python-docx not available for Word document extraction")
                return None
        
        elif file_type.lower() in ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'gif']:
            if ocr_service.is_available():
                result = ocr_service.extract_text_from_image(file_path)
                return result if result else ''
            else:
                logger.warning("OCR service not available for image text extraction")
                return None
        
        else:
            logger.warning(f"Unsupported file type: {file_type}")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting text from file {file_path}: {e}")
        return None

def extract_questions_with_llm(content_text: str) -> list:
    """Extract questions from guide content using LLM."""
    try:
        if not llm_service.is_available():
            logger.error("LLM service not available for question extraction")
            return None
        
        system_prompt = """You are an expert at analyzing marking guides and exam papers to extract questions and marking criteria.

Your task is to analyze the provided marking guide content and extract all questions along with their marking criteria.

IMPORTANT: Look for actual exam questions, not examples, instructions, or sample text. Focus on:
- Questions that students need to answer
- Problems to be solved
- Tasks to be completed
- Essay prompts or discussion topics

For each question you find, extract:
1. Question number (if available)
2. Question text (the actual question students see)
3. Expected answer or marking criteria (how to grade the answer)
4. Marks allocated to the question

Return your response as a valid JSON array where each question is an object with these fields:
- "number": question number (string, e.g., "1", "2a", "3.1")
- "text": the actual question text that students see
- "criteria": marking criteria, expected answer, or grading rubric
- "marks": number of marks (integer)

Example format:
[
    {
        "number": "1",
        "text": "Define photosynthesis and explain its importance in ecosystems.",
        "criteria": "Definition should include light energy conversion to chemical energy. Importance should mention oxygen production and food chain foundation.",
        "marks": 10
    },
    {
        "number": "2a",
        "text": "Calculate the area of a circle with radius 5cm.",
        "criteria": "Use formula A = πr². Show working: A = π × 5² = 25π ≈ 78.54 cm²",
        "marks": 5
    }
]

Important guidelines:
- Only extract actual exam questions that students need to answer
- Skip instructions, examples, sample answers, or administrative text
- If marks are not explicitly stated, estimate based on question complexity (typically 5-20 marks)
- If question text is unclear, clean it up while preserving meaning
- Include sub-questions as separate entries
- If no clear questions are found, return an empty array []
- Return ONLY the JSON array, no additional text or markdown formatting"""

        user_prompt = f"Extract questions from this marking guide content:\n\n{content_text}"
        
        # Generate response using LLM
        response = llm_service.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1  # Low temperature for consistent extraction
        )
        
        # Parse JSON response
        try:
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]  # Remove ```
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```
            cleaned_response = cleaned_response.strip()
            
            questions_data = json.loads(cleaned_response)
            
            # Validate the structure
            if not isinstance(questions_data, list):
                logger.error("LLM response is not a list")
                return None
            
            # Validate each question
            validated_questions = []
            for i, question in enumerate(questions_data):
                if not isinstance(question, dict):
                    logger.warning(f"Question {i} is not a dictionary, skipping")
                    continue
                
                # Ensure required fields
                validated_question = {
                    'number': str(question.get('number', str(i + 1))),
                    'text': str(question.get('text', '')),
                    'criteria': str(question.get('criteria', '')),
                    'marks': int(question.get('marks', 0))
                }
                
                # Skip empty questions
                if not validated_question['text'].strip():
                    continue
                
                validated_questions.append(validated_question)
            
            logger.info(f"Successfully extracted {len(validated_questions)} questions")
            return validated_questions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"LLM response was: {response}")
            
            # Try to extract questions using fallback method
            return extract_questions_fallback(response)
            
    except Exception as e:
        logger.error(f"Error extracting questions with LLM: {e}")
        return None

def extract_questions_fallback(llm_response: str) -> list:
    """Fallback method to extract questions when JSON parsing fails."""
    try:
        import re
        
        # Try to find JSON-like content in the response
        json_match = re.search(r'\[.*\]', llm_response, re.DOTALL)
        if json_match:
            try:
                questions_data = json.loads(json_match.group())
                if isinstance(questions_data, list):
                    return questions_data
            except json.JSONDecodeError:
                pass
        
        # Manual parsing as last resort
        questions = []
        lines = llm_response.split('\n')
        current_question = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            question_match = re.match(r'^(\d+[a-z]?\.?)\s*(.+)', line, re.IGNORECASE)
            if question_match:
                if current_question.get('text'):
                    questions.append(current_question)
                
                # Start new question
                current_question = {
                    'number': question_match.group(1).rstrip('.'),
                    'text': question_match.group(2),
                    'criteria': '',
                    'marks': 5  # Default marks
                }
            
            marks_match = re.search(r'(\d+)\s*marks?', line, re.IGNORECASE)
            if marks_match and current_question:
                current_question['marks'] = int(marks_match.group(1))
        
        # Add last question
        if current_question.get('text'):
            questions.append(current_question)
        
        logger.info(f"Fallback extraction found {len(questions)} questions")
        return questions if questions else None
        
    except Exception as e:
        logger.error(f"Fallback question extraction failed: {e}")
        return None

@guide_processing_bp.route('/api/guide/<guide_id>/questions', methods=['GET'])
@login_required
def get_guide_questions(guide_id):
    """Get questions for a specific guide."""
    try:
        guide = MarkingGuide.query.filter_by(
            id=guide_id,
            user_id=current_user.id
        ).first()
        
        if not guide:
            return jsonify({'success': False, 'message': 'Guide not found'}), 404
        
        return jsonify({
            'success': True,
            'questions': guide.questions or [],
            'total_marks': guide.total_marks or 0
        })
        
    except Exception as e:
        logger.error(f"Error getting guide questions: {e}")
        return jsonify({'success': False, 'message': 'Error retrieving questions'}), 500

@guide_processing_bp.route('/api/guide/<guide_id>/questions', methods=['PUT'])
@login_required
def update_guide_questions(guide_id):
    """Update questions for a specific guide."""
    try:
        data = request.get_json()
        if not data or 'questions' not in data:
            return jsonify({'success': False, 'message': 'Questions data is required'}), 400
        
        guide = MarkingGuide.query.filter_by(
            id=guide_id,
            user_id=current_user.id
        ).first()
        
        if not guide:
            return jsonify({'success': False, 'message': 'Guide not found'}), 404
        
        questions = data['questions']
        total_marks = sum(q.get('marks', 0) for q in questions)
        
        guide.questions = questions
        guide.total_marks = total_marks
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Questions updated successfully',
            'total_marks': total_marks
        })
        
    except Exception as e:
        logger.error(f"Error updating guide questions: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error updating questions'}), 500