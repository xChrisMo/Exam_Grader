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
from src.services.consolidated_llm_service import get_llm_service_for_current_user
ocr_service = ConsolidatedOCRService()

@guide_processing_bp.route("/api/test-guide-processing", methods=["GET"])
def test_guide_processing():
    """Test route to verify blueprint is working."""
    return jsonify({"success": True, "message": "Guide processing blueprint is working"})

@guide_processing_bp.route("/api/reprocess-guide", methods=["POST"])
@login_required
def reprocess_guide():
    """Reprocess a marking guide to re-extract questions using LLM, replacing existing questions."""
    try:
        data = request.get_json()
        if not data or "guide_id" not in data:
            return jsonify({"success": False, "message": "Guide ID is required"}), 400

        guide_id = data["guide_id"]
        logger.info(f"Reprocessing guide {guide_id} for user {current_user.id}")

        # Get the guide
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            logger.warning(f"Guide {guide_id} not found for user {current_user.id}")
            return jsonify({"success": False, "message": "Guide not found"}), 404

        # Get content text (reprocess from file if needed)
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

        # Use LLM to extract questions (this will replace existing questions)
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

        # Update the guide (replace existing questions)
        guide.questions = questions_data
        guide.total_marks = total_marks

        db.session.commit()

        logger.info(
            f"Successfully reprocessed guide {guide_id} - extracted {len(questions_data)} questions"
        )

        return jsonify(
            {
                "success": True,
                "message": f"Successfully reprocessed guide with {len(questions_data)} questions",
                "questions": questions_data,
                "total_marks": total_marks,
            }
        )

    except Exception as e:
        logger.error(f"Error reprocessing guide: {e}", exc_info=True)
        db.session.rollback()
        return (
            jsonify({"success": False, "message": f"Error reprocessing guide: {str(e)}"}),
            500,
        )

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
                # No fallback - OCR service is required
                logger.error("OCR service failed and no fallback is available")
                raise Exception("OCR service is required for PDF processing but failed")

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
        raise Exception("Unable to determine guide type - LLM service required")

def extract_questions_with_llm(content_text: str) -> list:
    """Extract questions from guide content using LLM."""
    try:
        # Get LLM service with current user's settings
        llm_service = get_llm_service_for_current_user()

        if not llm_service.is_available():
            logger.error("LLM service not available - cannot extract questions")
            raise Exception("LLM service is required for question extraction but is not available")

        # First, try to identify if this is a question-based or answer-based guide
        guide_type = _determine_guide_type_simple(content_text)

        system_prompt = """You are an expert at analyzing academic marking guides and extracting questions with their marks.

TASK: Extract questions and their marks from the provided marking guide text.

OUTPUT FORMAT: Return ONLY a valid JSON array with this exact structure:

[
  {
    "number": "1",
    "text": "Complete question text here",
    "marks": 10,
    "criteria": "Marking criteria or expected answer"
  },
  {
    "number": "1a", 
    "text": "Sub-question text here",
    "marks": 5,
    "criteria": "Sub-question marking criteria"
  }
]

EXTRACTION RULES:
1. Look for numbered questions (1, 2, 3, etc.) or sub-questions (1a, 1b, etc.)
2. Extract the complete question text as it appears
3. Find explicit mark values: "10 marks", "(15)", "[20 points]", "worth 25 marks"
4. If no marks are found for a question, set "marks": 0
5. Include marking criteria if available
6. Preserve original question numbering exactly
7. Do NOT combine or group questions - extract each separately
8. Do NOT create questions that don't exist in the text

IMPORTANT: Return ONLY the JSON array - no explanations, no markdown, no extra text."""

        user_prompt = f"""Extract questions and marks from this marking guide:

{content_text}

Return the JSON array of questions as specified in the system prompt."""

        # Generate response using LLM
        response = llm_service.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1
        )

        if not response or not response.strip():
            logger.error("Empty response from LLM service")
            raise Exception("LLM service returned empty response - cannot extract questions")

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

            # Find JSON boundaries (prefer array format)
            start_bracket = cleaned_response.find('[')
            end_bracket = cleaned_response.rfind(']')
            start_brace = cleaned_response.find('{')
            end_brace = cleaned_response.rfind('}')

            # Prefer array format, fall back to object format
            if start_bracket != -1 and end_bracket != -1 and start_bracket < end_bracket:
                # Array format (preferred)
                json_text = cleaned_response[start_bracket:end_bracket + 1]
            elif start_brace != -1 and end_brace != -1 and start_brace < end_brace:
                # Object format (legacy)
                json_text = cleaned_response[start_brace:end_brace + 1]
            else:
                logger.error("No valid JSON found in LLM response")
                raise Exception("LLM response does not contain valid JSON format")

            # Clean up common issues
            json_text = re.sub(r',\s*]', ']', json_text)  # Remove trailing commas
            json_text = re.sub(r'\s+', ' ', json_text)  # Normalize whitespace

            # Try to fix unterminated strings
            json_text = _fix_unterminated_strings(json_text)

            logger.info(f"Attempting to parse JSON array of length {len(json_text)}")
            response_data = json.loads(json_text)

            # Handle the new array format (preferred)
            if isinstance(response_data, list):
                # New array format (preferred)
                logger.info("LLM returned array format, processing questions")
                validated_questions = []
                for i, question in enumerate(response_data):
                    if not isinstance(question, dict):
                        logger.warning(f"Question {i} is not a dictionary, skipping")
                        continue

                    # Extract fields with validation
                    number = str(question.get("number", str(i + 1))).strip()
                    text = str(question.get("text", "")).strip()
                    marks = question.get("marks", 0)
                    criteria = str(question.get("criteria", "")).strip()

                    # Skip empty questions
                    if not text:
                        continue

                    # Validate marks
                    if not isinstance(marks, (int, float)) or marks < 0:
                        marks = 0

                    validated_question = {
                        "number": number,
                        "text": text,
                        "criteria": criteria or "No specific criteria provided",
                        "marks": int(marks),
                        "type": "individual"
                    }

                    validated_questions.append(validated_question)

            elif isinstance(response_data, dict) and "questions" in response_data:
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

                        # Don't default to 5 marks per subquestion - extract from guide or use 0
                        if total_marks == 0:
                            logger.warning(f"No marks found for grouped question {question_number}, guide may need better mark extraction")

                        validated_question = {
                            "number": str(question_number),
                            "text": "\n".join(combined_text_parts),
                            "criteria": "\n".join(criteria_parts) if criteria_parts else "Multi-part question",
                            "marks": total_marks,  # Use actual extracted marks, don't default
                            "type": "grouped",
                            "sub_parts": sub_parts
                        }
                    else:
                        # Individual question
                        if total_marks == 0:
                            logger.warning(f"No marks found for individual question {question_number}, guide may need better mark extraction")

                        validated_question = {
                            "number": str(question_number),
                            "text": str(question.get("text", "")),
                            "criteria": "\n".join(criteria_parts) if criteria_parts else "Individual question",
                            "marks": total_marks,  # Use actual extracted marks, don't default
                            "type": "individual"
                        }

                    # Skip empty questions
                    if not validated_question["text"].strip():
                        continue

                    validated_questions.append(validated_question)

            elif isinstance(response_data, list):
                # Legacy array format - convert to our internal format
                logger.info("LLM returned legacy array format, converting to internal format")
                validated_questions = []

                for i, question in enumerate(response_data):
                    if not isinstance(question, dict):
                        logger.warning(f"Question {i} is not a dictionary, skipping")
                        continue

                    # Convert legacy format to internal format
                    validated_question = {
                        "number": str(question.get("number", str(i + 1))),
                        "text": str(question.get("text", "")),
                        "criteria": str(question.get("criteria", "")),
                        "marks": int(question.get("marks", 0)) if question.get("marks") else 0,
                        "type": "individual"
                    }

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

            # Re-raise the exception - no fallback allowed
            raise

    except Exception as e:
        logger.error(f"Error extracting questions with LLM: {e}")
        logger.error("LLM extraction failed - no fallback allowed. Only LLM extraction should be used.")
        raise Exception(f"LLM extraction failed: {e}. Only LLM extraction is allowed for marking guides.")

# Basic question extraction function removed - only LLM extraction is allowed

def group_related_questions(questions: list) -> list:
    """Group related questions together based on question numbering patterns."""
    if not questions:
        return []

    # Dictionary to group questions by their base number
    question_groups = {}

    for question in questions:
        # Skip non-dictionary questions
        if not isinstance(question, dict):
            logger.warning(f"Skipping non-dictionary question in grouping: {type(question)}")
            continue

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

# Fallback functions removed - LLM is now required for all question extraction

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
            # No fallback - return error
            return jsonify({
                "success": False,
                "message": "LLM extraction failed and no fallback is available",
                "questions": [],
                "extraction_method": "None",
                "error": "LLM service is required but failed"
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
