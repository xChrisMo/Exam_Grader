"""
Guide Processing Routes

This module contains routes for processing marking guides with LLM
to extract questions and marking criteria.
"""

import json
import os
import re
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from src.database.models import MarkingGuide, db
from src.services.consolidated_llm_service import ConsolidatedLLMService
from src.services.consolidated_ocr_service import ConsolidatedOCRService
from utils.logger import logger

guide_processing_bp = Blueprint("guide_processing", __name__)


def count_grouped_questions(questions):
    """Count questions treating grouped questions as one."""
    if not questions:
        return 0
    
    count = 0
    for question in questions:
        # Check if this is a grouped question
        if isinstance(question, dict) and question.get('type') == 'grouped':
            count += 1  # Count grouped question as one
        else:
            count += 1  # Count regular question as one
    
    return count


# Register the template filter when the blueprint is registered
@guide_processing_bp.record_once
def register_template_filters(state):
    """Register custom template filters when blueprint is registered."""
    state.app.jinja_env.filters['count_grouped_questions'] = count_grouped_questions


# Initialize services
llm_service = ConsolidatedLLMService()
ocr_service = ConsolidatedOCRService()


@guide_processing_bp.route("/api/process-guide", methods=["POST"])
@login_required
def process_guide():
    """Process a marking guide to extract questions using LLM."""
    try:
        data = request.get_json()
        if not data or "guide_id" not in data:
            return jsonify({"success": False, "message": "Guide ID is required"}), 400

        guide_id = data["guide_id"]
        logger.info(f"Processing guide {guide_id} for user {current_user.id}")

        # Get the guide
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            logger.warning(f"Guide {guide_id} not found for user {current_user.id}")
            return jsonify({"success": False, "message": "Guide not found"}), 404

        if guide.questions and len(guide.questions) > 0:
            return jsonify(
                {
                    "success": True,
                    "message": "Guide already processed",
                    "questions": guide.questions,
                    "total_marks": guide.total_marks,
                }
            )

        if not guide.content_text:
            content_text = extract_text_from_file(guide.file_path, guide.file_type)
            if not content_text:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Could not extract text from guide file",
                        }
                    ),
                    400,
                )

            guide.content_text = content_text
        else:
            content_text = guide.content_text

        # Use LLM to extract questions
        questions_data = extract_questions_with_llm(content_text)

        if not questions_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Could not extract questions from guide content",
                    }
                ),
                400,
            )

        # Calculate total marks
        total_marks = sum(q.get("marks", 0) for q in questions_data)

        # Update the guide
        guide.questions = questions_data
        guide.total_marks = total_marks

        db.session.commit()

        logger.info(
            f"Successfully processed guide {guide_id} - extracted {len(questions_data)} questions"
        )

        return jsonify(
            {
                "success": True,
                "message": f"Successfully extracted {len(questions_data)} questions",
                "questions": questions_data,
                "total_marks": total_marks,
            }
        )

    except Exception as e:
        logger.error(f"Error processing guide: {e}", exc_info=True)
        db.session.rollback()
        return (
            jsonify({"success": False, "message": f"Error processing guide: {str(e)}"}),
            500,
        )


def extract_text_from_file(file_path: str, file_type: str) -> str:
    """Extract text content from a file."""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        # Handle different file types
        if file_type.lower() in ["pdf"]:
            if ocr_service.is_available():
                result = ocr_service.extract_text(file_path)
                return result.get("text", "") if result else ""
            else:
                # Fallback: try to read PDF with PyPDF2
                try:
                    import PyPDF2

                    with open(file_path, "rb") as file:
                        reader = PyPDF2.PdfReader(file)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                        return text
                except ImportError:
                    logger.warning("PyPDF2 not available for PDF text extraction")
                    return None

        elif file_type.lower() in ["txt"]:
            # Read text file directly
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()

        elif file_type.lower() in ["docx", "doc"]:
            try:
                from docx import Document

                doc = Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                logger.warning("python-docx not available for Word document extraction")
                return None

        elif file_type.lower() in ["jpg", "jpeg", "png", "bmp", "tiff", "gif"]:
            if ocr_service.is_available():
                result = ocr_service.extract_text_from_image(file_path)
                return result if result else ""
            else:
                logger.warning("OCR service not available for image text extraction")
                return None

        else:
            logger.warning(f"Unsupported file type: {file_type}")
            return None

    except Exception as e:
        logger.error(f"Error extracting text from file {file_path}: {e}")
        return None


def _fix_unterminated_strings(json_text: str) -> str:
    """Fix unterminated strings in JSON text."""
    try:
        # Find unterminated strings by tracking quotes
        result = []
        i = 0
        in_string = False
        escape_next = False
        
        while i < len(json_text):
            char = json_text[i]
            
            if escape_next:
                result.append(char)
                escape_next = False
                i += 1
                continue
                
            if char == '\\':
                result.append(char)
                escape_next = True
                i += 1
                continue
                
            if char == '"':
                result.append(char)
                in_string = not in_string
                i += 1
                continue
                
            result.append(char)
            i += 1
        
        # If we end while in a string, close it
        if in_string:
            result.append('"')
            
        return ''.join(result)
        
    except Exception as e:
        logger.warning(f"Error fixing unterminated strings: {e}")
        return json_text


def _determine_guide_type_simple(content_text: str) -> str:
    """Simple guide type determination based on content analysis."""
    try:
        content_lower = content_text.lower()
        
        # Count question indicators
        question_indicators = [
            'question', 'q.', 'q:', 'problem', 'task', 'exercise',
            'what', 'how', 'why', 'when', 'where', 'which', 'who',
            'explain', 'describe', 'analyze', 'discuss', 'compare',
            'calculate', 'solve', 'find', 'determine', 'evaluate'
        ]
        
        # Count answer indicators
        answer_indicators = [
            'answer', 'solution', 'response', 'model answer',
            'expected', 'should include', 'must contain',
            'award marks', 'give credit', 'full marks',
            'marking scheme', 'rubric', 'criteria'
        ]
        
        question_count = sum(1 for indicator in question_indicators if indicator in content_lower)
        answer_count = sum(1 for indicator in answer_indicators if indicator in content_lower)
        
        # Also check for structural patterns
        question_patterns = len(re.findall(r'\b(?:question|q\.?)\s*\d+', content_lower))
        answer_patterns = len(re.findall(r'\b(?:answer|solution)\s*\d*', content_lower))
        
        total_question_score = question_count + question_patterns * 2
        total_answer_score = answer_count + answer_patterns * 2
        
        if total_question_score > total_answer_score:
            return "questions"
        else:
            return "answers"
            
    except Exception as e:
        logger.warning(f"Error determining guide type: {e}")
        return "questions"  # Default fallback


def extract_questions_with_llm(content_text: str) -> list:
    """Extract questions from guide content using LLM."""
    try:
        if not llm_service.is_available():
            logger.error("LLM service not available for question extraction")
            return None

        # First, try to identify if this is a question-based or answer-based guide
        guide_type = _determine_guide_type_simple(content_text)
        
        system_prompt = """You are an expert at extracting questions and marking criteria from academic guides.

CRITICAL INSTRUCTIONS:
1. Return ONLY a valid JSON array - no explanations, no markdown, no extra text
2. Start your response with [ and end with ]
3. Use double quotes for all strings
4. Ensure proper JSON syntax

REQUIRED JSON FORMAT:
[
  {
    "number": "1",
    "text": "Complete question or topic text",
    "criteria": "Marking criteria or expected answer content",
    "marks": 5
  }
]

EXTRACTION RULES:
- Look for numbered questions, topics, or assessment criteria
- Extract ANY text that represents something to be graded or assessed
- If you see marks/points mentioned, use those numbers
- If no marks specified, estimate 1-10 points based on complexity
- Include sub-questions as separate entries (1a, 1b, etc.)
- If the content has headings or sections, treat each as a potential question
- Even if formatting is messy, extract the core content
- If you find ANYTHING that could be assessed, include it

FALLBACK STRATEGY:
- If no clear questions exist, break content into logical assessment units
- Create reasonable question text from headings, topics, or key concepts
- Always return at least one item if there's any substantial content
- Never return an empty array unless the content is truly empty"""

        user_prompt = f"""Extract from this marking guide content:

{content_text}

Return ONLY the JSON array - no other text."""

        # Generate response using LLM
        response = llm_service.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1
        )

        if not response or not response.strip():
            logger.warning("Empty response from LLM service")
            return _create_basic_questions_from_content(content_text)

        # Simplified JSON parsing with robust error handling
        try:
            cleaned_response = response.strip()
            
            # Remove markdown code blocks
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            
            # Find JSON array boundaries
            start_bracket = cleaned_response.find('[')
            end_bracket = cleaned_response.rfind(']')
            
            if start_bracket == -1 or end_bracket == -1 or start_bracket >= end_bracket:
                logger.warning("No valid JSON array found in response, using fallback")
                return extract_questions_fallback(response)
            
            # Extract JSON array
            json_text = cleaned_response[start_bracket:end_bracket + 1]
            
            # Clean up common issues
            json_text = re.sub(r',\s*]', ']', json_text)  # Remove trailing commas
            json_text = re.sub(r'\s+', ' ', json_text)  # Normalize whitespace
            
            # Try to fix unterminated strings
            json_text = _fix_unterminated_strings(json_text)
            
            logger.info(f"Attempting to parse JSON array of length {len(json_text)}")
            response_data = json.loads(json_text)

            # Handle the new structured format from your prompt
            if isinstance(response_data, dict) and "questions" in response_data:
                # New structured format: {"questions": [...], "marking_guide": [...]}
                questions_list = response_data.get("questions", [])
                marking_guide = response_data.get("marking_guide", [])
                
                # Convert to our internal format
                validated_questions = []
                for i, question in enumerate(questions_list):
                    if not isinstance(question, dict):
                        logger.warning(f"Question {i} is not a dictionary, skipping")
                        continue

                    # Extract marks from marking guide if available
                    question_number = question.get("number", str(i + 1))
                    total_marks = 0
                    criteria_parts = []
                    
                    # Find matching marking guide entries
                    for guide_entry in marking_guide:
                        if guide_entry.get("question_number") == question_number:
                            for point in guide_entry.get("points", []):
                                if point.get("score") and point.get("score") != "null":
                                    try:
                                        total_marks += int(point["score"])
                                    except (ValueError, TypeError):
                                        pass
                                if point.get("description"):
                                    criteria_parts.append(point["description"])
                    
                    # Handle sub-questions
                    subquestions = question.get("subquestions", [])
                    if subquestions:
                        # This is a grouped question with sub-parts
                        sub_parts = []
                        combined_text_parts = [question.get("text", "")]
                        
                        for subq in subquestions:
                            sub_number = subq.get("number", "")
                            sub_text = subq.get("text", "")
                            sub_parts.append(sub_number)
                            combined_text_parts.append(f"{sub_number}) {sub_text}")
                            
                            # Find marks for sub-questions
                            for guide_entry in marking_guide:
                                if guide_entry.get("question_number") == sub_number:
                                    for point in guide_entry.get("points", []):
                                        if point.get("score") and point.get("score") != "null":
                                            try:
                                                total_marks += int(point["score"])
                                            except (ValueError, TypeError):
                                                pass
                                        if point.get("description"):
                                            criteria_parts.append(f"{sub_number}: {point['description']}")
                        
                        validated_question = {
                            "number": str(question_number),
                            "text": "\n".join(combined_text_parts),
                            "criteria": "\n".join(criteria_parts) if criteria_parts else "Multi-part question",
                            "marks": total_marks if total_marks > 0 else len(subquestions) * 5,
                            "type": "grouped",
                            "sub_parts": sub_parts
                        }
                    else:
                        # Individual question
                        validated_question = {
                            "number": str(question_number),
                            "text": str(question.get("text", "")),
                            "criteria": "\n".join(criteria_parts) if criteria_parts else "Individual question",
                            "marks": total_marks if total_marks > 0 else 5,
                            "type": "individual"
                        }
                    
                    # Skip empty questions
                    if not validated_question["text"].strip():
                        continue

                    validated_questions.append(validated_question)
                    
            elif isinstance(response_data, list):
                # Fallback: old list format
                validated_questions = []
                for i, question in enumerate(response_data):
                    if not isinstance(question, dict):
                        logger.warning(f"Question {i} is not a dictionary, skipping")
                        continue

                    # Ensure required fields with enhanced validation
                    validated_question = {
                        "number": str(question.get("number", str(i + 1))),
                        "text": str(question.get("text", "")),
                        "criteria": str(question.get("criteria", "")),
                        "marks": int(question.get("marks", 0)),
                    }

                    # Add optional enhanced fields if present
                    if "type" in question:
                        validated_question["type"] = str(question["type"])
                    
                    if "sub_parts" in question and isinstance(question["sub_parts"], list):
                        validated_question["sub_parts"] = question["sub_parts"]

                    # Skip empty questions
                    if not validated_question["text"].strip():
                        continue

                    validated_questions.append(validated_question)
            else:
                logger.error("LLM response is not in expected format")
                return None

            # Group related questions before returning
            grouped_questions = group_related_questions(validated_questions)
            logger.info(f"Successfully extracted {len(grouped_questions)} questions (after grouping)")
            return grouped_questions

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"LLM response was: {response}")

            # Try to extract questions using fallback method
            return extract_questions_fallback(response)

    except Exception as e:
        logger.error(f"Error extracting questions with LLM: {e}")
        return None


def group_related_questions(questions: list) -> list:
    """Group related questions together based on question numbering patterns."""
    if not questions:
        return []
    
    import re
    
    # Dictionary to group questions by their base number
    question_groups = {}
    
    for question in questions:
        number = str(question.get("number", "1")).strip()
        text = question.get("text", "")
        criteria = question.get("criteria", "")
        marks = question.get("marks", 0)
        
        # Extract base number using more comprehensive patterns
        # Handle patterns like: "1", "1a", "1b", "Question 1", "Q1", etc.
        base_number = "1"  # Default
        is_sub_part = False
        sub_part_letter = ""
        
        # Pattern 1: "1a", "1b", "2a", etc.
        match = re.match(r"^(\d+)([a-z])$", number.lower())
        if match:
            base_number = match.group(1)
            sub_part_letter = match.group(2)
            is_sub_part = True
        else:
            # Pattern 2: Just a number "1", "2", etc.
            match = re.match(r"^(\d+)$", number)
            if match:
                base_number = match.group(1)
                is_sub_part = False
            else:
                # Pattern 3: "Question 1", "Q1", etc.
                match = re.search(r"(\d+)", number)
                if match:
                    base_number = match.group(1)
                    is_sub_part = False
        
        # Initialize group if it doesn't exist
        if base_number not in question_groups:
            question_groups[base_number] = {
                "main_question": None,
                "sub_parts": [],
                "total_marks": 0,
                "has_sub_parts": False
            }
        
        # Add question to appropriate group
        question_data = {
            "original_number": number,
            "text": text,
            "criteria": criteria,
            "marks": marks,
            "sub_part_letter": sub_part_letter
        }
        
        if is_sub_part:
            question_groups[base_number]["sub_parts"].append(question_data)
            question_groups[base_number]["has_sub_parts"] = True
        else:
            # This could be the main question or a standalone question
            if question_groups[base_number]["main_question"] is None:
                question_groups[base_number]["main_question"] = question_data
            else:
                # If we already have a main question, treat this as a sub-part
                question_groups[base_number]["sub_parts"].append(question_data)
                question_groups[base_number]["has_sub_parts"] = True
        
        question_groups[base_number]["total_marks"] += marks
    
    # Process groups and create final question list
    final_questions = []
    sequential_number = 1
    
    for base_number in sorted(question_groups.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        group = question_groups[base_number]
        
        if not group["has_sub_parts"] and group["main_question"]:
            # Single standalone question
            main_q = group["main_question"]
            final_questions.append({
                "number": str(sequential_number),
                "text": main_q["text"],
                "criteria": main_q["criteria"],
                "marks": main_q["marks"],
                "type": "individual"
            })
        else:
            # Grouped question with sub-parts
            main_q = group["main_question"]
            sub_parts = sorted(group["sub_parts"], key=lambda x: x.get("sub_part_letter", x.get("original_number", "")))
            
            # Build combined text
            combined_text_parts = []
            combined_criteria_parts = []
            sub_part_numbers = []
            
            # Add main question text if available
            if main_q and main_q["text"].strip():
                combined_text_parts.append(main_q["text"])
                if main_q["criteria"].strip():
                    combined_criteria_parts.append(f"Main: {main_q['criteria']}")
            
            # Add sub-parts
            for i, sub_part in enumerate(sub_parts):
                # Determine sub-part letter
                if sub_part["sub_part_letter"]:
                    letter = sub_part["sub_part_letter"]
                else:
                    letter = chr(ord('a') + i)
                
                sub_part_numbers.append(f"{sequential_number}{letter}")
                
                # Format sub-part text
                sub_text = sub_part["text"].strip()
                if not sub_text.startswith(f"{letter})"):
                    sub_text = f"{letter}) {sub_text}"
                
                combined_text_parts.append(sub_text)
                
                # Format sub-part criteria
                if sub_part["criteria"].strip():
                    combined_criteria_parts.append(f"Part {letter}: {sub_part['criteria']}")
            
            # Create the grouped question
            final_question = {
                "number": str(sequential_number),
                "text": "\n".join(combined_text_parts),
                "criteria": "\n".join(combined_criteria_parts) if combined_criteria_parts else "Multi-part question",
                "marks": group["total_marks"],
                "type": "grouped",
                "sub_parts": sub_part_numbers
            }
            
            final_questions.append(final_question)
        
        sequential_number += 1
    
    logger.info(f"Grouped {len(questions)} individual questions into {len(final_questions)} final questions")
    return final_questions


def extract_questions_fallback(llm_response: str) -> list:
    """Enhanced fallback method to extract questions when JSON parsing fails."""
    try:
        import re

        # Try to find JSON-like content in the response
        json_match = re.search(r"\[.*\]", llm_response, re.DOTALL)
        if json_match:
            try:
                questions_data = json.loads(json_match.group())
                if isinstance(questions_data, list):
                    return questions_data
            except json.JSONDecodeError:
                pass

        # Enhanced manual parsing with intelligent grouping
        questions = []
        lines = llm_response.split("\n")
        current_question = {}
        current_group = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for question patterns with better regex
            question_patterns = [
                r"^(?:Question\s+)?(\d+)(?:[:\.]?\s*(.+))?",  # Question 1: text or 1. text
                r"^(\d+[a-z])[\)\.\:]?\s*(.+)",  # 1a) text or 1a. text
                r"^([a-z])[\)\.\:]?\s*(.+)",  # a) text or a. text (only if preceded by a number)
            ]
            
            # Skip lines that are clearly not questions
            skip_patterns = [
                r"^total\s*[:=]",  # Total: 24 marks
                r"^marks?\s*[:=]",  # Marks: 100
                r"^page\s+\d+",  # Page 1
                r"^section\s+[a-z]$",  # Section A (standalone)
                r"^\d+\s*$",  # Just a number
                r"^[a-z]\s*$",  # Just a letter
            ]
            
            # Check if this line should be skipped
            should_skip = any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns)
            if should_skip:
                continue
            
            question_match = None
            for pattern in question_patterns:
                question_match = re.match(pattern, line, re.IGNORECASE)
                if question_match:
                    break
            
            if question_match:
                number = question_match.group(1)
                text = question_match.group(2) if question_match.group(2) else ""
                
                # Determine if this is a sub-part or new question
                base_number_match = re.match(r"^(\d+)", number)
                base_number = base_number_match.group(1) if base_number_match else "1"
                
                # Check if this is a sub-part of an existing question
                is_sub_part = re.search(r"^(\d+)([a-z])", number) is not None
                
                if is_sub_part:
                    # This is a sub-part, group with main question
                    if base_number not in current_group:
                        current_group[base_number] = {
                            "number": base_number,
                            "parts": [],
                            "total_marks": 0,
                            "type": "grouped"
                        }
                    
                    current_group[base_number]["parts"].append({
                        "sub_number": number,
                        "text": text,
                        "marks": 5  # Default, will be updated if found
                    })
                else:
                    # This is a new main question
                    if current_question.get("text"):
                        questions.append(current_question)
                    
                    current_question = {
                        "number": number,
                        "text": text,
                        "criteria": "",
                        "marks": 5,  # Default marks
                        "type": "individual"
                    }

            # Look for marks information
            marks_match = re.search(r"(\d+)\s*marks?", line, re.IGNORECASE)
            if marks_match:
                marks_value = int(marks_match.group(1))
                if current_question:
                    current_question["marks"] = marks_value
                # Also update grouped questions
                for group in current_group.values():
                    if group["parts"]:
                        group["parts"][-1]["marks"] = marks_value
                        group["total_marks"] += marks_value

        # Add last individual question
        if current_question.get("text"):
            questions.append(current_question)
        
        # Process grouped questions
        for base_number, group in current_group.items():
            if group["parts"]:
                combined_text_parts = []
                for i, part in enumerate(group["parts"]):
                    part_text = part["text"]
                    if not re.match(r"^[a-z]\)", part_text.strip()):
                        sub_letter = chr(ord('a') + i)
                        part_text = f"{sub_letter}) {part_text}"
                    combined_text_parts.append(part_text)
                
                questions.append({
                    "number": base_number,
                    "text": f"Question {base_number}:\n" + "\n".join(combined_text_parts),
                    "criteria": f"Multi-part question with {len(group['parts'])} components",
                    "marks": group["total_marks"] if group["total_marks"] > 0 else len(group["parts"]) * 5,
                    "type": "grouped",
                    "sub_parts": [part["sub_number"] for part in group["parts"]]
                })

        # If no questions found with pattern matching, try content-based extraction
        if not questions:
            questions = _extract_questions_from_content(llm_response)

        # Group related questions before returning
        if questions:
            grouped_questions = group_related_questions(questions)
            logger.info(f"Enhanced fallback extraction found {len(grouped_questions)} questions (after grouping)")
            return grouped_questions
        else:
            return []

    except Exception as e:
        logger.error(f"Enhanced fallback question extraction failed: {e}")
        return []


def _extract_questions_from_content(content: str) -> list:
    """Extract questions from content using content analysis when pattern matching fails."""
    try:
        import re
        
        # Split content into potential question blocks
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        if not lines:
            return []
        
        questions = []
        current_question = None
        question_counter = 1
        
        # Look for any text that could be a question or marking criteria
        for i, line in enumerate(lines):
            # Skip very short lines (likely not questions)
            if len(line) < 10:
                continue
                
            # Check if this line contains question-like content
            is_question_like = any([
                '?' in line,
                any(word in line.lower() for word in ['explain', 'describe', 'what', 'how', 'why', 'calculate', 'find', 'determine']),
                re.search(r'\b\d+\s*marks?\b', line.lower()),
                re.search(r'question\s*\d+', line.lower()),
                re.search(r'^\d+[\.\)]\s*', line),
                re.search(r'^[a-z][\.\)]\s*', line)
            ])
            
            # Check if this could be marking criteria
            is_criteria_like = any([
                any(word in line.lower() for word in ['award', 'marks', 'credit', 'accept', 'must include', 'should contain']),
                'points' in line.lower() and any(char.isdigit() for char in line),
                re.search(r'\b\d+\s*points?\b', line.lower())
            ])
            
            if is_question_like or (len(line) > 20 and not is_criteria_like):
                # This looks like a question
                if current_question:
                    questions.append(current_question)
                
                # Extract marks if present
                marks_match = re.search(r'(\d+)\s*(?:marks?|points?)', line.lower())
                marks = int(marks_match.group(1)) if marks_match else 5
                
                current_question = {
                    "number": str(question_counter),
                    "text": line,
                    "criteria": "",
                    "marks": marks
                }
                question_counter += 1
                
            elif current_question and (is_criteria_like or len(line) > 15):
                # This looks like criteria for the current question
                if current_question["criteria"]:
                    current_question["criteria"] += " " + line
                else:
                    current_question["criteria"] = line
                    
                # Update marks if found in criteria
                marks_match = re.search(r'(\d+)\s*(?:marks?|points?)', line.lower())
                if marks_match:
                    current_question["marks"] = int(marks_match.group(1))
        
        # Add the last question
        if current_question:
            questions.append(current_question)
        
        # If still no questions, create a generic one from the content
        if not questions and content.strip():
            # Take the first substantial piece of content as a question
            substantial_lines = [line for line in lines if len(line) > 20]
            if substantial_lines:
                questions.append({
                    "number": "1",
                    "text": substantial_lines[0],
                    "criteria": "General marking criteria based on content",
                    "marks": 10
                })
        
        return questions
        
    except Exception as e:
        logger.error(f"Content-based extraction failed: {e}")
        return []


def _create_basic_questions_from_content(content_text: str) -> list:
    """Create basic questions from content when all other methods fail."""
    try:
        if not content_text or not content_text.strip():
            return []
        
        # Clean the content
        lines = [line.strip() for line in content_text.split('\n') if line.strip()]
        
        if not lines:
            return []
        
        # Try to find substantial content blocks
        substantial_lines = [line for line in lines if len(line) > 20]
        
        if not substantial_lines:
            # Use any available lines
            substantial_lines = lines[:5]  # Take first 5 lines
        
        questions = []
        
        # Create questions from substantial content
        for i, line in enumerate(substantial_lines):  # No limit on questions
            # Try to extract marks if present
            marks_match = re.search(r'(\d+)\s*(?:marks?|points?)', line.lower())
            marks = int(marks_match.group(1)) if marks_match else 5
            
            # Clean the line for question text
            question_text = re.sub(r'\d+\s*(?:marks?|points?)', '', line, flags=re.IGNORECASE).strip()
            if not question_text:
                question_text = line
            
            # Create a basic question
            question = {
                "number": str(i + 1),
                "text": question_text,
                "criteria": "General assessment criteria based on content",
                "marks": marks
            }
            
            questions.append(question)
        
        # If we still have no questions, create one from the entire content
        if not questions:
            questions.append({
                "number": "1",
                "text": content_text,
                "criteria": "General assessment of content understanding",
                "marks": 10
            })
        
        # Group related questions before returning
        if questions:
            grouped_questions = group_related_questions(questions)
            logger.info(f"Created {len(grouped_questions)} basic questions from content (after grouping)")
            return grouped_questions
        else:
            return questions
        
    except Exception as e:
        logger.error(f"Failed to create basic questions from content: {e}")
        # Return a minimal fallback question
        return [{
            "number": "1",
            "text": "Assessment question based on provided content",
            "criteria": "General assessment criteria",
            "marks": 10
        }]


@guide_processing_bp.route("/api/test-question-extraction", methods=["POST"])
@login_required
def test_question_extraction():
    """Test endpoint for question extraction with sample content."""
    try:
        data = request.get_json()
        test_content = data.get("content", "")
        
        if not test_content:
            return jsonify({"success": False, "message": "No content provided"}), 400
        
        # Test the extraction
        questions = extract_questions_with_llm(test_content)
        
        if questions:
            return jsonify({
                "success": True,
                "message": f"Successfully extracted {len(questions)} questions",
                "questions": questions,
                "extraction_method": "LLM"
            })
        else:
            # Try fallback
            fallback_questions = extract_questions_fallback(test_content)
            return jsonify({
                "success": bool(fallback_questions),
                "message": f"Fallback extraction found {len(fallback_questions) if fallback_questions else 0} questions",
                "questions": fallback_questions or [],
                "extraction_method": "Fallback"
            })
            
    except Exception as e:
        logger.error(f"Error in test question extraction: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@guide_processing_bp.route("/api/guide/<guide_id>/questions", methods=["GET"])
@login_required
def get_guide_questions(guide_id):
    """Get questions for a specific guide."""
    try:
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            return jsonify({"success": False, "message": "Guide not found"}), 404

        return jsonify(
            {
                "success": True,
                "questions": guide.questions or [],
                "total_marks": guide.total_marks or 0,
            }
        )

    except Exception as e:
        logger.error(f"Error getting guide questions: {e}")
        return jsonify({"success": False, "message": "Error retrieving questions"}), 500


@guide_processing_bp.route("/api/guide/<guide_id>/questions", methods=["PUT"])
@login_required
def update_guide_questions(guide_id):
    """Update questions for a specific guide."""
    try:
        data = request.get_json()
        if not data or "questions" not in data:
            return (
                jsonify({"success": False, "message": "Questions data is required"}),
                400,
            )

        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            return jsonify({"success": False, "message": "Guide not found"}), 404

        questions = data["questions"]
        total_marks = sum(q.get("marks", 0) for q in questions)

        guide.questions = questions
        guide.total_marks = total_marks

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Questions updated successfully",
                "total_marks": total_marks,
            }
        )

    except Exception as e:
        logger.error(f"Error updating guide questions: {e}")
        db.session.rollback()
        return jsonify({"success": False, "message": "Error updating questions"}), 500
