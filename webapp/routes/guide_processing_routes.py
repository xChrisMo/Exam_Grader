"""
Guide Processing Routes

This module contains routes for processing marking guides with LLM
to extract questions and marking criteria.
"""

import json
import os

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from src.database.models import MarkingGuide, db
from src.services.consolidated_llm_service import ConsolidatedLLMService
from src.services.consolidated_ocr_service import ConsolidatedOCRService
from utils.logger import logger

guide_processing_bp = Blueprint("guide_processing", __name__)

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


def extract_questions_with_llm(content_text: str) -> list:
    """Extract questions from guide content using LLM."""
    try:
        if not llm_service.is_available():
            logger.error("LLM service not available for question extraction")
            return None

        system_prompt = """You are an expert at analyzing marking guides and exam papers to extract questions and marking criteria.

Your task is to analyze the provided marking guide content and intelligently determine when questions should be grouped together vs kept separate, regardless of their formatting.

FLEXIBLE PATTERN RECOGNITION:

You must be able to handle ANY format of questions, including but not limited to:

GROUPING PATTERNS (should be combined):
- Traditional: "1a) ... 1b) ... 1c) ..."
- Numbered: "1.1 ... 1.2 ... 1.3 ..."
- Roman: "1(i) ... 1(ii) ... 1(iii) ..."
- Lettered: "Question 1 Part A ... Part B ... Part C"
- Descriptive: "Question 1: First, ... Second, ... Third, ..."
- Bullet points: "Question 1: • ... • ... • ..."
- Sequential: "Question 1: Step 1 ... Step 2 ... Step 3 ..."
- Scenario-based: Multiple questions referencing the same case study/scenario
- Building questions: Where later parts depend on earlier answers
- Thematic clusters: Questions on the same topic with shared context

SEPARATION PATTERNS (should be individual):
- Different topics: Math question followed by history question
- Independent scenarios: Different case studies or contexts
- Standalone questions: Complete questions that don't reference others
- Different skill assessments: Essay vs calculation vs diagram
- Unrelated content: Questions that can be answered in isolation

INTELLIGENT ANALYSIS APPROACH:

1. CONTENT ANALYSIS:
   - Read the entire content to understand the overall structure
   - Identify recurring themes, scenarios, or contexts
   - Look for dependencies between questions (does one build on another?)
   - Recognize when questions share the same subject matter

2. RELATIONSHIP DETECTION:
   - Questions that reference the same diagram, table, or passage → GROUP
   - Questions that use phrases like "Based on your answer above" → GROUP
   - Questions with shared variables or data sets → GROUP
   - Questions that form a logical sequence or workflow → GROUP
   - Questions on completely different topics → SEPARATE

3. FORMATTING FLEXIBILITY:
   - Don't rely solely on numbering patterns (1a, 1b, etc.)
   - Look for semantic relationships and logical connections
   - Consider the educational intent behind the question structure
   - Preserve the instructor's pedagogical approach

4. CONTEXTUAL UNDERSTANDING:
   - If questions share a common scenario or case study → GROUP
   - If questions build upon each other logically → GROUP
   - If questions test the same concept from different angles → Consider grouping
   - If questions are completely independent → SEPARATE

ADAPTIVE EXAMPLES:

Example 1 - GROUPED (various formats):
Source: "Question 1: Consider the following business case... First, analyze the market position. Second, identify key competitors. Finally, recommend a strategy."
Output: [{
    "number": "1",
    "text": "Question 1: Consider the following business case...\nFirst, analyze the market position.\nSecond, identify key competitors.\nFinally, recommend a strategy.",
    "criteria": "Part 1: Market analysis with supporting data\nPart 2: Competitor identification with rationale\nPart 3: Strategic recommendation with justification",
    "marks": 25,
    "type": "grouped",
    "sub_parts": ["First", "Second", "Finally"]
}]

Example 2 - GROUPED (unconventional format):
Source: "Problem Set A: Given the equation y = 2x + 3... • Plot the graph • Find the y-intercept • Calculate the slope"
Output: [{
    "number": "A",
    "text": "Problem Set A: Given the equation y = 2x + 3...\n• Plot the graph\n• Find the y-intercept\n• Calculate the slope",
    "criteria": "Graph plotting with accurate scale and points\nCorrect identification of y-intercept\nAccurate slope calculation with working",
    "marks": 15,
    "type": "grouped",
    "sub_parts": ["plot", "intercept", "slope"]
}]

Example 3 - MIXED (some grouped, some separate):
Source: "Section A: Essay Questions\n1. Discuss climate change impacts (20 marks)\n2. Analyze renewable energy: (a) Solar benefits (5 marks) (b) Wind challenges (5 marks)\n\nSection B: Calculations\n3. Solve: 3x + 7 = 22 (8 marks)"
Output: [
    {
        "number": "1",
        "text": "Discuss climate change impacts",
        "criteria": "Comprehensive discussion covering environmental, economic, and social impacts",
        "marks": 20,
        "type": "individual"
    },
    {
        "number": "2",
        "text": "Analyze renewable energy:\na) Solar benefits\nb) Wind challenges",
        "criteria": "Part a: Clear benefits of solar energy with examples\nPart b: Realistic challenges of wind energy with solutions",
        "marks": 10,
        "type": "grouped",
        "sub_parts": ["a", "b"]
    },
    {
        "number": "3",
        "text": "Solve: 3x + 7 = 22",
        "criteria": "Show all working steps and provide correct final answer",
        "marks": 8,
        "type": "individual"
    }
]

CRITICAL GUIDELINES:
- Be extremely flexible with formatting - don't get stuck on specific patterns
- Focus on semantic meaning and logical relationships over formatting
- Use your understanding of educational assessment to make intelligent decisions
- When in doubt, consider how a student would naturally approach the questions
- Preserve the instructor's intended structure while making it clear and logical
- Group questions that belong together, separate those that don't
- Extract only actual questions students need to answer
- Skip instructions, examples, headers, or administrative text
- Return ONLY the JSON array, no additional text or markdown formatting

REMEMBER: Your goal is to understand the INTENT behind the question structure, not just follow rigid formatting rules. Be intelligent and adaptive!"""

        user_prompt = (
            f"Extract questions from this marking guide content:\n\n{content_text}"
        )

        # Generate response using LLM
        response = llm_service.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,  # Low temperature for consistent extraction
        )

        # Parse JSON response
        try:
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]  # Remove ```
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```
            cleaned_response = cleaned_response.strip()

            questions_data = json.loads(cleaned_response)

            # Validate the structure
            if not isinstance(questions_data, list):
                logger.error("LLM response is not a list")
                return None

            # Validate and process questions with enhanced structure
            validated_questions = []
            for i, question in enumerate(questions_data):
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

            # Return questions as-is, preserving original structure from LLM
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


def group_related_questions(questions: list) -> list:
    """Group related questions together and ensure proper sequential numbering."""
    if not questions:
        return []
    
    # Dictionary to group questions by their base number
    question_groups = {}
    
    for question in questions:
        number = question.get("number", "1")
        text = question.get("text", "")
        criteria = question.get("criteria", "")
        marks = question.get("marks", 0)
        
        # Extract base number (e.g., "1" from "1a", "1b", or "1")
        import re
        base_match = re.match(r"^(\d+)", str(number))
        base_number = base_match.group(1) if base_match else "1"
        
        # Check if this question has sub-parts (a, b, c, etc.)
        sub_part_match = re.search(r"^(\d+)([a-z])", str(number))
        
        if base_number not in question_groups:
            question_groups[base_number] = {
                "parts": [],
                "total_marks": 0,
                "combined_text": "",
                "combined_criteria": ""
            }
        
        # Add this question/part to the group
        question_groups[base_number]["parts"].append({
            "number": number,
            "text": text,
            "criteria": criteria,
            "marks": marks,
            "has_sub_part": bool(sub_part_match)
        })
        question_groups[base_number]["total_marks"] += marks
    
    # Process groups and create final question list
    final_questions = []
    sequential_number = 1
    
    for base_number in sorted(question_groups.keys(), key=int):
        group = question_groups[base_number]
        parts = group["parts"]
        
        if len(parts) == 1 and not parts[0]["has_sub_part"]:
            # Single question without sub-parts
            final_questions.append({
                "number": str(sequential_number),
                "text": parts[0]["text"],
                "criteria": parts[0]["criteria"],
                "marks": parts[0]["marks"]
            })
        else:
            # Multiple parts or sub-parts - combine them
            combined_text_parts = []
            combined_criteria_parts = []
            
            # Sort parts by their sub-part letter if they have one
            sorted_parts = sorted(parts, key=lambda x: (
                x["number"] if not re.search(r"[a-z]", str(x["number"])) else 
                str(x["number"])
            ))
            
            for i, part in enumerate(sorted_parts):
                part_text = part["text"]
                part_criteria = part["criteria"]
                
                # Format sub-parts with letters if not already present
                if len(sorted_parts) > 1 and not re.search(r"^[a-z]\)", part_text.strip()):
                    sub_letter = chr(ord('a') + i)
                    part_text = f"{sub_letter}) {part_text}"
                    if part_criteria:
                        part_criteria = f"Part {sub_letter}: {part_criteria}"
                
                combined_text_parts.append(part_text)
                if part_criteria:
                    combined_criteria_parts.append(part_criteria)
            
            # Create the combined question
            combined_text = f"Question {sequential_number}:\n" + "\n".join(combined_text_parts)
            combined_criteria = "\n".join(combined_criteria_parts) if combined_criteria_parts else ""
            
            final_questions.append({
                "number": str(sequential_number),
                "text": combined_text,
                "criteria": combined_criteria,
                "marks": group["total_marks"]
            })
        
        sequential_number += 1
    
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
                r"^([a-z])[\)\.\:]?\s*(.+)",  # a) text or a. text
            ]
            
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

        logger.info(f"Enhanced fallback extraction found {len(questions)} questions")
        return questions if questions else None

    except Exception as e:
        logger.error(f"Enhanced fallback question extraction failed: {e}")
        return None


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
