"""
Mapping Service for mapping submissions to marking guide criteria.
This service groups questions and answers from marking guides with corresponding
questions and answers in student submissions.
"""

import json
import re
import re
import re
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import logger


class MappingService:
    """Mapping service that groups questions and answers between marking guides and submissions."""

    def __init__(self, llm_service=None):
        """Initialize with or without LLM service."""
        self.llm_service = llm_service

    def determine_guide_type(self, marking_guide_content: str) -> Tuple[str, float]:
        """
        Determine if the marking guide contains questions or answers.

        Args:
            marking_guide_content: Content of the marking guide

        Returns:
            Tuple[str, float]: (Guide type, Confidence score)
                Guide type can be "questions" or "answers"
                Confidence score is a float between 0 and 1
        """
        if not self.llm_service or not marking_guide_content:
            # Default to questions if no LLM service or empty content
            return "questions", 0.5

        try:
            # Log the operation
            logger.info("Determining guide type from marking guide content...")

            # Use LLM to determine guide type
            system_prompt = """
            You are an expert in analyzing academic and exam-related documents across all disciplines. Your task is to determine whether a given marking guide primarily contains questions or answers, regardless of the academic department or subject matter.

            Definitions:
            Marking guide with questions:

            Primarily lists exam or assignment questions.

            May include brief answer guidelines, marks allocation, or marking criteria.

            Does not contain detailed model answers.

            Intended for students or to accompany an exam for instructors.

            Marking guide with answers:

            Primarily provides detailed model answers to specific questions.

            May include assessment rubrics or marking criteria.

            Structured for use by instructors or graders for evaluating student responses.

            Instructions:
            Analyze the structure, content, and wording of the document.

            Consider that different departments may phrase questions and answers differently (e.g., mathematical proofs, essays, multiple-choice responses).

            Use contextual clues to assess whether the document is primarily asking questions or providing answers..

            Output in JSON format:
            {
                "guide_type": "questions" or "answers",
                "confidence": 0.0 to 1.0,
                "reasoning": "Brief explanation of your determination"
            }
            """

            user_prompt = f"""
            Please analyze this marking guide and determine if it primarily contains questions or answers.

            Marking guide content:
            {marking_guide_content[:10000]}  # Limit to first 10000 chars for efficiency
            """

            # Log the request
            logger.info("Sending request to LLM service...")

            # Check if the model supports JSON output format
            # DeepSeek models support JSON output, so we explicitly set supports_json to True if it's a deepseek model.
            supports_json = "deepseek-reasoner" in self.llm_service.model.lower()

            # Make the API call with JSON response format
            params = {
                "model": self.llm_service.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            }

            # Add seed parameter if in deterministic mode
            if (
                hasattr(self.llm_service, "deterministic")
                and self.llm_service.deterministic
                and hasattr(self.llm_service, "seed")
                and self.llm_service.seed is not None
            ):
                params["seed"] = self.llm_service.seed

            response = self.llm_service.client.chat.completions.create(**params)

            # Log the response processing
            logger.info("Processing LLM response...")

            # Validate response structure
            if not hasattr(response, "choices") or len(response.choices) == 0:
                logger.error("No response choices received from LLM")
                return "questions", 0.5

            # Get the response content
            result = response.choices[0].message.content

            # Validate response content
            if not result or not result.strip():
                logger.error("Empty response received from LLM")
                return "questions", 0.5

            logger.debug(f"Raw LLM response: {result[:200]}...")

            # Parse the response with error handling
            try:
                # Clean up the response for models that don't properly format JSON
                # Attempt to find the start and end of the JSON object
                json_start = result.find('{')
                json_end = result.rfind('}')

                if json_start != -1 and json_end != -1 and json_end > json_start:
                    result = result[json_start : json_end + 1]
                    logger.info(f"Extracted JSON string: {result[:500]}...")
                else:
                    logger.warning("No JSON object found in LLM response.")
                    logger.error(f"Raw LLM response that failed JSON extraction: {result}")
                    # Instead of immediately raising an error, try to fix the response using LLM
                    if hasattr(self.llm_service, "_get_structured_response"):
                        logger.info("Attempting to fix malformed JSON using LLM...")
                        try:
                            # Use LLM to fix and structure the response
                            sanitized_response = self.llm_service._get_structured_response(result)
                            result = sanitized_response
                            logger.info(f"LLM-fixed JSON: {result[:500]}...")
                        except Exception as fix_error:
                            logger.error(f"Failed to fix JSON with LLM: {str(fix_error)}")
                            # Continue with the original result and let the JSON parser handle it

                parsed = json.loads(result)

                guide_type = parsed.get("guide_type", "questions")
                confidence = parsed.get("confidence", 0.5)
                reasoning = parsed.get("reasoning", "No reasoning provided")

                # Validate guide_type
                if guide_type not in ["questions", "answers"]:
                    logger.warning(
                        f"Invalid guide_type '{guide_type}', defaulting to 'questions'"
                    )
                    guide_type = "questions"

                # Validate confidence
                if (
                    not isinstance(confidence, (int, float))
                    or confidence < 0
                    or confidence > 1
                ):
                    logger.warning(
                        f"Invalid confidence '{confidence}', defaulting to 0.5"
                    )
                    confidence = 0.5

                # Log completion
                logger.info(
                    f"Guide type determined: {guide_type} (confidence: {confidence})"
                )
                logger.info(f"Reasoning: {reasoning}")

                return guide_type, confidence

            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {str(e)}")
                logger.error(f"Raw LLM response that failed to parse: {result}")
                return "questions", 0.5

        except Exception as e:
            logger.error(f"Error determining guide type: {str(e)}")
            # Default to questions on error
            return "questions", 0.5

    def extract_questions_and_answers(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract questions and answers from content using LLM if available.
        Otherwise falls back to regex-based extraction.

        Args:
            content: Text content to extract from
            tracker_id: Optional progress tracker ID to update progress
        """
        if not content or not content.strip():
            return []

        if self.llm_service:
            try:
                # Log the extraction process
                logger.info("Extracting questions and answers from content...")

                # Use LLM to extract questions and answers
                system_prompt = """
                You are an expert at analyzing exam documents. Your task is to identify questions and their corresponding answers.
                For each question-answer pair, provide:
                1. A unique ID
                2. The question text
                3. The answer text
                4. The maximum possible score (if mentioned)

                Important guidelines:
                - Questions may be numbered in different ways (e.g., "QUESTION ONE", "Question 1", "1.")
                - Quesion may be under one main quesion
                - Answers may be structured in different ways (e.g., bullet points, paragraphs, numbered lists)
                - Look for key phrases that indicate the start of questions (e.g., "QUESTION", "Q", "Question")
                - Look for key phrases that indicate answers (e.g., "Answer:", "Solution:", or content after the question)
                - For the marking guide, extract the full question text including any sub-questions
                - For submissions, match answers to their corresponding questions even if the numbering differs
                - Carefully scan for marks/points in the following formats:
                  * "X marks" or "X points"
                  * "(X marks)" or "(X points)"
                  * "Total: X marks" or "Total: X points"
                  * "Maximum: X marks" or "Maximum: X points"
                  * "X% of total marks"
                  * Any other format indicating marks/points
                - For sub-questions, look for mark allocations like:
                  * "Part (a): X marks"
                  * "Section 1: X marks"
                  * "(X marks each)"
                - DO NOT assume any default marks if not explicitly stated

                Output in JSON format:
                {
                    "items": [
                        {
                            "id": "q1",
                            "text": "question text",
                            "answer": "answer text",
                            "max_score": null,  # Only include if explicitly stated
                            "score_breakdown": {
                                "total": null,  # Only include if explicitly stated
                                "sub_questions": [
                                    {
                                        "text": "sub-question text",
                                        "answer": "sub-question answer",
                                        "marks": null  # Only include if explicitly stated
                                    }
                                ]
                            }
                        }
                    ]
                }
                """

                user_prompt = f"""
                Please analyze this exam document and extract all questions and answers.
                Pay special attention to:
                1. Question numbering and format
                2. Mark allocations for each question and sub-question
                3. Answer structure and format
                4. Any special instructions about marks or scoring

                Document content:
                {content}
                """

                # Check if the model supports JSON output format
                supports_json = "deepseek-reasoner" in self.llm_service.model.lower()

                params = {
                    "model": self.llm_service.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.0,
                }

                if supports_json:
                    params["response_format"] = {"type": "json_object"}

                # Add seed parameter if in deterministic mode
                if (
                    hasattr(self.llm_service, "deterministic")
                    and self.llm_service.deterministic
                    and hasattr(self.llm_service, "seed")
                    and self.llm_service.seed is not None
                ):
                    params["seed"] = self.llm_service.seed

                response = self.llm_service.client.chat.completions.create(**params)

                result = response.choices[0].message.content

                # Log the LLM response processing
                logger.info("Processing LLM response for question extraction...")

                # Try to clean up the response for models that don't properly format JSON
                try:
                    # Find JSON content between curly braces if there's text before/after
                    json_match = re.search(r"\{.*\}", result, re.DOTALL)
                    if json_match:
                        result = json_match.group(0)
                    else:
                        logger.warning("No JSON object found in LLM response.")
                        logger.error(
                            f"Raw LLM response that failed JSON extraction: {result}"
                        )
                        # Instead of immediately falling back to regex, try to fix the response using LLM
                        if self.llm_service and hasattr(self.llm_service, "_get_structured_response"):
                            logger.info("Attempting to fix malformed JSON using LLM...")
                            try:
                                # Use LLM to fix and structure the response
                                sanitized_response = self.llm_service._get_structured_response(result)
                                result = sanitized_response
                                logger.info(f"LLM-fixed JSON: {result[:500]}...")
                            except Exception as fix_error:
                                logger.error(f"Failed to fix JSON with LLM: {str(fix_error)}")
                                # Return an empty list to trigger the fallback extraction
                                return []
                        else:
                            # Return an empty list to trigger the fallback extraction
                            return []

                    parsed = json.loads(result)

                    # Log successful extraction
                    logger.info(
                        f"Successfully extracted {len(parsed.get('items', []))} items from content"
                    )

                    return parsed.get("items", [])
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"JSON parsing error in extract_questions_and_answers: {str(e)}"
                    )

                    # Log JSON parsing error
                    logger.warning(
                        f"JSON parsing error: {str(e)}. Falling back to regex extraction."
                    )

                    # Return an empty list to trigger the fallback extraction
                    return []

            except Exception as e:
                logger.warning(
                    f"LLM extraction failed, falling back to regex: {str(e)}"
                )

        # Fallback to regex-based extraction
        items = []
        content = re.sub(r"\n{3,}", "\n\n", content.strip())
        content = re.sub(
            r"([^\n])(\s*)(Question|Q)\s+(\d+)",
            r"\1\n\n\3 \4",
            content,
            flags=re.IGNORECASE,
        )

        question_matches = list(
            re.finditer(
                r"(?:^|\n+)((?:Question|Q)[.\s]*\d+[.\s]*:?[.\s]*)(.*?)(?=(?:\n+(?:Question|Q)[.\s]*\d+[.\s]*:?)|$)",
                content,
                re.IGNORECASE | re.DOTALL,
            )
        )

        if not question_matches:
            items.append({"id": "item1", "text": content.strip(), "type": "unknown"})
            return items

        for i, match in enumerate(question_matches):
            current_id = i + 1
            # Extract question content from the match
            question_content = match.group(2).strip()

            answer_match = re.search(
                r"(?:^|\n+)((?:Answer|A|Solution|Sol)[.\s]*:?[.\s]*)(.*)",
                question_content,
                re.IGNORECASE | re.DOTALL,
            )

            if answer_match:
                question_text = question_content[: answer_match.start()].strip()
                answer_text = answer_match.group(2).strip()
            else:
                question_text = question_content
                answer_text = ""

            # Try to extract max score with more patterns
            max_score = None
            score_patterns = [
                r"(?:max|maximum|total)[.\s]*(?:score|points|marks)[.\s]*:?\s*(\d+)",
                r"\((\d+)\s*(?:marks|points)\)",
                r"(\d+)\s*(?:marks|points)\s*(?:each|total|maximum)?",
                r"(?:worth|total|maximum)\s*(?:of\s*)?(\d+)\s*(?:marks|points)",
            ]

            for pattern in score_patterns:
                max_score_match = re.search(pattern, question_content, re.IGNORECASE)
                if max_score_match:
                    max_score = int(max_score_match.group(1))
                    break

                items.append(
                    {
                        "id": f"q{current_id}",
                        "text": question_text,
                        "answer": answer_text,
                        "max_score": max_score,  # Will be None if no marks found
                    }
                )

        return items

    def extract_questions_and_total_marks(self, content: str) -> Dict:
        """
        Extract questions and calculate total marks from marking guide content using LLM.
        This is specifically designed for marking guide upload and storage.

        Args:
            content: Raw text content of the marking guide

        Returns:
            Dict containing:
            - questions: List of extracted questions with marks
            - total_marks: Total marks calculated from all questions
            - extraction_method: Method used for extraction ('llm' or 'regex')
        """
        if not content or not content.strip():
            return {"questions": [], "total_marks": 0, "extraction_method": "none"}

        if self.llm_service:
            try:
                logger.info(
                    "Using LLM to extract questions and total marks from marking guide..."
                )

                # --- UPDATED SYSTEM PROMPT ---
                system_prompt = """
                You are an expert educational assessment analyst with deep knowledge across all academic disciplines. Your task is to extract ALL distinct questions and sub-questions from marking guides, regardless of format, discipline, or question type. You must:

                1. Identify every instruction, prompt, or task that requires a student response, including:
                   - Classification tasks (enumerate each item as a sub-question if multiple items are to be classified)
                   - Multi-part questions (extract each part as a sub-question)
                   - Case study analysis (extract each analysis prompt as a question)
                   - Programming assignments (extract each coding or debugging task as a question)
                   - Data analysis, calculations, essays, experiments, etc.

                2. For classification/categorization tasks:
                   - If the instruction is to classify multiple items (e.g., 10 texts), treat each item as a separate sub-question, each with its own number and marks.
                   - Example: "Classify each of the following 10 texts..." → 10 sub-questions, one per text.

                3. For multi-part or compound questions:
                   - Extract each part as a sub-question, preserving the parent-child relationship if possible.

                4. For all questions, extract:
                   - The exact question text as it appears
                   - Marks allocated
                   - Discipline (e.g., Computer Science, Mathematics, etc.)
                   - Question type (e.g., Classification, Programming, Analysis, Calculation, Essay, etc.)
                   - Reasoning for why this is a question
                   - If a sub-question, include a parent_question_number field

                5. Output a flat list of all questions and sub-questions, each with a unique number (e.g., 1, 2, 3a, 3b, 4, ...).

                6. Calculate the total marks as the sum of all extracted questions and sub-questions.

                OUTPUT FORMAT:
                Respond with ONLY valid JSON. Do not include any other text, explanations, or markdown formatting outside the JSON object. Your entire response must be a single, valid JSON object.
                {
                    "questions": [
                        {
                            "number": "1a",
                            "parent_question_number": "1",  // optional, for sub-questions
                            "text": "Complete exact question text as it appears",
                            "marks": 10,
                            "discipline": "Computer Science",
                            "question_type": "Classification",
                            "reasoning": "This is a classification sub-question for item 1."
                        }
                    ],
                    "total_marks": 100,
                    "analysis": {
                        "document_type": "Traditional Exam/Assignment/Case Study",
                        "primary_discipline": "Computer Science",
                        "question_format": "Mixed/Traditional/Case-based",
                        "extraction_confidence": "High/Medium/Low"
                    }
                }
                """

                user_prompt = f"""
                Analyze the following marking guide and extract ALL distinct questions and sub-questions that require student responses, following these rules:

                - For classification tasks with multiple items, enumerate each item as a separate sub-question.
                - For multi-part or compound questions, extract each part as a sub-question.
                - For case studies, extract each analysis prompt as a question.
                - For programming/data analysis/calculation/essay/experiment tasks, extract each as a question.
                - For each question or sub-question, provide: number, parent_question_number (if applicable), text, marks, discipline, question_type, and reasoning.
                - Output a flat list of all questions and sub-questions, each with a unique number.
                - Calculate total marks as the sum of all extracted questions and sub-questions.

                DOCUMENT TO ANALYZE:
                {content}

                Respond with ONLY valid JSON including your reasoning and analysis.
                """

                # Use the LLM service to extract questions
                # Check if the model supports JSON output format
                # DeepSeek models support json_object response format
                supports_json = True

                params = {
                    "model": self.llm_service.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.0,
        
                }

                if supports_json:
                    params["response_format"] = {"type": "json_object"}

                # Add seed parameter if in deterministic mode
                if (
                    hasattr(self.llm_service, "deterministic")
                    and self.llm_service.deterministic
                    and hasattr(self.llm_service, "seed")
                    and self.llm_service.seed is not None
                ):
                    params["seed"] = self.llm_service.seed

                response = self.llm_service.client.chat.completions.create(**params)
                result = response.choices[0].message.content

                logger.info("Processing LLM response for question extraction...")
                logger.info(f"Raw LLM response: {result}")
                logger.info(
                    f"Content sent to LLM (first 1000 chars): {content[:1000]}..."
                )
                logger.info(
                    f"Content sent to LLM (last 500 chars): ...{content[-500:]}"
                )

                try:
                    # Clean up the response for models that don't properly format JSON
                    # Attempt to find the start and end of the JSON object
                    json_start = result.find('{')
                    json_end = result.rfind('}')

                    if json_start != -1 and json_end != -1 and json_end > json_start:
                        result = result[json_start : json_end + 1]
                        logger.info(f"Extracted JSON string: {result[:500]}...")
                    else:
                        logger.warning("No JSON object found in LLM response.")
                        logger.error(
                            f"Raw LLM response that failed JSON extraction: {result}"
                        )
                        # Instead of immediately raising an error, try to fix the response using LLM
                        if self.llm_service and hasattr(self.llm_service, "_get_structured_response"):
                            logger.info("Attempting to fix malformed JSON using LLM...")
                            try:
                                # Use LLM to fix and structure the response
                                sanitized_response = self.llm_service._get_structured_response(result)
                                result = sanitized_response
                                logger.info(f"LLM-fixed JSON: {result[:500]}...")
                            except Exception as fix_error:
                                logger.error(f"Failed to fix JSON with LLM: {str(fix_error)}")
                                raise ValueError("No JSON object found in LLM response.")
                        else:
                            raise ValueError("No JSON object found in LLM response.")

                    parsed = json.loads(result)

                    # Validate the response structure
                    if "questions" in parsed and "total_marks" in parsed:
                        questions = parsed["questions"]
                        total_marks = parsed["total_marks"]

                        # Convert to the format expected by the application
                        formatted_questions = []
                        for i, q in enumerate(questions):
                            formatted_q = {
                                "number": q.get("number", str(i + 1)),
                                "text": q.get("text", ""),
                                "marks": q.get("marks", 0),
                                "reasoning": q.get("reasoning", ""),
                                "discipline": q.get("discipline", ""),
                                "question_type": q.get("question_type", ""),
                                "type": "question",
                            }
                            formatted_questions.append(formatted_q)

                        logger.info(
                            f"LLM successfully extracted {len(formatted_questions)} questions with {total_marks} total marks"
                        )

                        # Log detailed analysis if available
                        analysis = parsed.get("analysis", {})
                        if analysis:
                            logger.info(f"Document analysis:")
                            logger.info(
                                f"  - Document type: {analysis.get('document_type', 'Unknown')}"
                            )
                            logger.info(
                                f"  - Primary discipline: {analysis.get('primary_discipline', 'Unknown')}"
                            )
                            logger.info(
                                f"  - Question format: {analysis.get('question_format', 'Unknown')}"
                            )
                            logger.info(
                                f"  - Extraction confidence: {analysis.get('extraction_confidence', 'Unknown')}"
                            )

                        # Log detailed information for each question
                        for i, q in enumerate(formatted_questions, 1):
                            logger.info(f"Question {i}:")
                            logger.info(
                                f"  - Text: {q.get('text', 'No text')[:100]}..."
                            )
                            logger.info(f"  - Marks: {q.get('marks', 0)}")
                            logger.info(
                                f"  - Discipline: {q.get('discipline', 'Unknown')}"
                            )
                            logger.info(
                                f"  - Type: {q.get('question_type', 'Unknown')}"
                            )
                            if q.get("reasoning"):
                                logger.info(f"  - Reasoning: {q['reasoning']}")

                        result = {
                            "questions": formatted_questions,
                            "total_marks": total_marks,
                            "extraction_method": "llm",
                        }

                        # Include analysis in result if available
                        if analysis:
                            result["analysis"] = analysis

                        return result
                    else:
                        logger.error("LLM response missing required fields")
                    return {
                        "questions": [],
                        "total_marks": 0,
                        "extraction_method": "llm_failed",
                    }

                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error: {str(e)}")
                    logger.error(f"Raw LLM response that caused JSON error: {result}")
                    return {
                        "questions": [],
                        "total_marks": 0,
                        "extraction_method": "json_error",
                    }

            except Exception as e:
                logger.error(f"LLM extraction failed: {str(e)}")
                return {
                    "questions": [],
                    "total_marks": 0,
                    "extraction_method": "llm_error",
                }

        # No fallback - LLM only
        logger.error("No LLM service available")
        return {"questions": [], "total_marks": 0, "extraction_method": "no_llm"}

    def _extract_questions_regex_enhanced(self, content: str) -> Dict:
        """
        Enhanced regex-based question extraction with better mark detection.
        """
        questions = []
        total_marks = 0

        # Enhanced question patterns to match various formats
        question_patterns = [
            # QUESTION 1: ... (25 marks)
            r"(?:^|\n)\s*(?:QUESTION|Question|Q)\s*(\d+)[:\s]*([^(]*?)\s*\((\d+)\s*marks?\)",
            # Question 1: ... [10 marks]
            r"(?:^|\n)\s*(?:QUESTION|Question|Q)\s*(\d+)[:\s]*([^[]*?)\s*\[(\d+)\s*marks?\]",
            # a) Define object-oriented programming... (10 marks)
            r"(?:^|\n)\s*([a-z])\)\s*([^(]*?)\s*\((\d+)\s*marks?\)",
            # Question 1: ... 10 marks
            r"(?:^|\n)\s*(?:QUESTION|Question|Q)\s*(\d+)[:\s]*([^0-9]*?)(\d+)\s*marks?",
        ]

        for pattern in question_patterns:
            matches = re.findall(
                pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL
            )
            if matches:
                logger.info(f"Found {len(matches)} questions using regex pattern")
                for match in matches:
                    if len(match) == 3:
                        q_num, q_text, marks_str = match
                        try:
                            marks = int(marks_str)
                            question_data = {
                                "number": len(questions) + 1,
                                "text": f"Question {q_num}: {q_text.strip()}",
                                "marks": marks,
                                "criteria": "",
                                "type": "question",
                            }
                            questions.append(question_data)
                            total_marks += marks
                        except ValueError:
                            continue
                break  # Use first successful pattern

        # If no questions found with marks, try general patterns
        if not questions:
            logger.info(
                "No questions with marks found, trying general question patterns..."
            )
            general_patterns = [
                r"(?:^|\n)\s*(?:QUESTION|Question|Q)\s*(\d+)[:\s]*([^\n]+)",
                r"(?:^|\n)\s*([a-z])\)\s*([^\n]+)",
            ]

            for pattern in general_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                if matches:
                    logger.info(
                        f"Found {len(matches)} questions without explicit marks"
                    )
                    for match in matches:
                        q_num, q_text = match
                        # Assign default marks based on question complexity
                        if len(q_text) > 100:
                            marks = 25  # Complex question
                        elif len(q_text) > 50:
                            marks = 15  # Medium question
                        else:
                            marks = 10  # Simple question

                        question_data = {
                            "number": len(questions) + 1,
                            "text": f"Question {q_num}: {q_text.strip()}",
                            "marks": marks,
                            "criteria": "",
                            "type": "question",
                        }
                        questions.append(question_data)
                        total_marks += marks
                    break

        # Try to extract total marks from the document
        if not total_marks and questions:
            total_marks_match = re.search(
                r"total[:\s]*(\d+)\s*marks?", content, re.IGNORECASE
            )
            if total_marks_match:
                total_marks = int(total_marks_match.group(1))
                logger.info(f"Found total marks in document: {total_marks}")

        logger.info(
            f"Regex extraction complete: {len(questions)} questions, {total_marks} total marks"
        )

        return {
            "questions": questions,
            "total_marks": total_marks,
            "extraction_method": "regex",
        }

    def map_submission_to_guide(
        self,
        marking_guide_content: str,
        student_submission_content: str,
        num_questions: int = 1,
    ) -> Tuple[Dict, Optional[str]]:
        """
        Map a student submission to a marking guide using LLM for intelligent grouping and grading.

        This method:
        1. Determines if the marking guide contains questions or answers
        2. Uses the LLM to group guide and submission content based on the guide type
        3. Grades each mapped answer in a single LLM call
        4. Identifies the best N answers based on the num_questions parameter
        5. Calculates overall grade and provides detailed feedback

        Args:
            marking_guide_content: Raw text content of the marking guide
            student_submission_content: Raw text content of the student submission
            num_questions: Number of questions the student should answer (default: 1)

        Returns:
            Tuple[Dict, Optional[str]]: (Mapping and grading result, Error message if any)
        """
        try:
            # Log the operation
            logger.info("Starting mapping submission to guide...")

            # Check if we have content to work with
            if not marking_guide_content or not marking_guide_content.strip():
                logger.error("Marking guide content is empty")
                return {
                    "status": "error",
                    "message": "Marking guide content is empty",
                }, "Empty marking guide"

            if not student_submission_content or not student_submission_content.strip():
                logger.error("Student submission content is empty")
                return {
                    "status": "error",
                    "message": "Student submission content is empty",
                }, "Empty student submission"

            # Clean and preprocess content for better LLM understanding
            marking_guide_content = self._preprocess_content(marking_guide_content)
            student_submission_content = self._preprocess_content(student_submission_content)

            # Initialize empty mappings list
            mappings = []

            if self.llm_service:
                try:
                    # Log the guide type determination
                    logger.info(
                        "Determining if marking guide contains questions or answers..."
                    )

                    # Determine if the marking guide contains questions or answers
                    guide_type, confidence = self.determine_guide_type(
                        marking_guide_content
                    )

                    # Log the guide type determination result
                    logger.info(
                        f"Guide type determined: {guide_type} (confidence: {confidence:.2f}). Preparing for mapping..."
                    )

                    # Use LLM to map submission to guide based on guide type and perform grading
                    if guide_type == "questions":
                        system_prompt = f"""
                        You are an expert educational assessment AI with deep expertise in analyzing exam documents and grading student responses.

                        TASK: Analyze a marking guide containing QUESTIONS and a student submission containing ANSWERS to:
                        1. Identify and match the best {num_questions} questions in the guide with corresponding answers in the submission
                        2. Grade each matched answer comprehensively
                        3. Provide detailed feedback and scoring breakdown

                        CRITICAL GUIDELINES:

                        CONTENT ANALYSIS:
                        - Work directly with the RAW TEXT provided - do not attempt to extract or restructure
                        - Handle noisy OCR outputs gracefully by focusing on semantic meaning
                        - Ignore minor formatting issues, typos, or OCR artifacts
                        - Look for conceptual understanding rather than exact word matches
                        - Consider alternative correct approaches that may differ from the model answer

                        QUESTION IDENTIFICATION:
                        - Questions may be numbered (1, 2, 3) or lettered (a, b, c) or use other formats
                        - Multi-part questions should be treated as separate items for mapping
                        - Look for question indicators: "Question", "Q", "Problem", "Task", "Explain", "Calculate", etc.
                        - Pay attention to mark allocations: "(5 marks)", "[10 points]", "Total: 25 marks"

                        ANSWER MAPPING:
                        - Match answers based on semantic similarity and content relevance
                        - Consider the context and subject matter of both guide and submission
                        - Provide confidence scores: 0.8-1.0 for clear matches, 0.5-0.7 for partial matches
                        - If no clear match exists, do not force a mapping

                        GRADING STANDARDS:
                        - Grade based on content accuracy, completeness, and understanding
                        - Award partial credit for partially correct answers
                        - Consider alternative valid approaches
                        - Provide specific, constructive feedback
                        - Identify both strengths and areas for improvement

                        OUTPUT FORMAT:
                        Respond with ONLY valid JSON. No comments, explanations, or markdown outside the JSON object.

                        {{
                            "mappings": [
                                {{
                                    "guide_id": "g1",
                                    "guide_text": "exact question text from guide",
                                    "guide_answer": "model answer if available",
                                    "max_score": 10,
                                    "parent_question": "g1a",
                                    "submission_id": "s1",
                                    "submission_text": "student's answer text",
                                    "match_score": 0.85,
                                    "match_reason": "Clear semantic match on topic X",
                                    "grade_score": 8.5,
                                    "grade_percentage": 85.0,
                                    "grade_feedback": "Excellent understanding of concept X. Good explanation of Y. Could improve on Z.",
                                    "strengths": ["Clear explanation", "Correct methodology"],
                                    "weaknesses": ["Missing detail on Z", "Could be more specific"]
                                }}
                            ],
                            "overall_grade": {{
                                "total_score": 25.5,
                                "max_possible_score": 30.0,
                                "percentage": 85.0,
                                "letter_grade": "B+"
                            }}
                        }}
                        """
                    else:  # guide_type == "answers"
                        system_prompt = f"""
                        You are an expert educational assessment AI with deep expertise in analyzing exam documents and grading student responses.

                        TASK: Analyze a marking guide containing MODEL ANSWERS and a student submission containing STUDENT ANSWERS to:
                        1. Identify and match the best {num_questions} student answers with corresponding model answers
                        2. Grade each matched answer comprehensively
                        3. Provide detailed feedback and scoring breakdown

                        CRITICAL GUIDELINES:

                        CONTENT ANALYSIS:
                        - Work directly with the RAW TEXT provided - do not attempt to extract or restructure
                        - Handle noisy OCR outputs gracefully by focusing on semantic meaning
                        - Ignore minor formatting issues, typos, or OCR artifacts
                        - Look for conceptual understanding rather than exact word matches
                        - Consider alternative correct approaches that may differ from the model answer

                        ANSWER IDENTIFICATION:
                        - Model answers may be structured in various formats (bullet points, paragraphs, etc.)
                        - Student answers may be handwritten and contain OCR artifacts
                        - Look for answer indicators: "Answer:", "Solution:", "Response:", or content after questions
                        - Pay attention to mark allocations: "(5 marks)", "[10 points]", "Total: 25 marks"

                        ANSWER MAPPING:
                        - Match answers that address the same question or topic
                        - Consider semantic similarity and shared key concepts
                        - Provide confidence scores: 0.8-1.0 for clear matches, 0.5-0.7 for partial matches
                        - If no clear match exists, do not force a mapping

                        GRADING STANDARDS:
                        - Grade based on content accuracy, completeness, and understanding
                        - Award partial credit for partially correct answers
                        - Consider alternative valid approaches
                        - Provide specific, constructive feedback
                        - Identify both strengths and areas for improvement

                        OUTPUT FORMAT:
                        Respond with ONLY valid JSON. No comments, explanations, or markdown outside the JSON object.

                        {{
                            "mappings": [
                                {{
                                    "guide_id": "g1",
                                    "guide_text": "question or section from guide",
                                    "guide_answer": "model answer text",
                                    "max_score": 10,
                                    "parent_question": "g1a",
                                    "submission_id": "s1",
                                    "submission_text": "student's answer text",
                                    "match_score": 0.85,
                                    "match_reason": "Clear semantic match on topic X",
                                    "grade_score": 8.5,
                                    "grade_percentage": 85.0,
                                    "grade_feedback": "Excellent understanding of concept X. Good explanation of Y. Could improve on Z.",
                                    "strengths": ["Clear explanation", "Correct methodology"],
                                    "weaknesses": ["Missing detail on Z", "Could be more specific"]
                                }}
                            ],
                            "overall_grade": {{
                                "total_score": 25.5,
                                "max_possible_score": 30.0,
                                "percentage": 85.0,
                                "letter_grade": "B+"
                            }}
                        }}
                        """

                    # Log the mapping process
                    logger.info(
                        f"Using LLM to map submission to guide (finding best {num_questions} answers)..."
                    )

                    # Pass the raw content to the LLM for mapping and grading
                    user_prompt = f"""
                    MARKING GUIDE CONTENT:
                    {marking_guide_content[:8000]}

                    STUDENT SUBMISSION CONTENT:
                    {student_submission_content[:8000]}

                    REQUIREMENTS:
                    - Number of questions to answer: {num_questions}
                    - Work directly with the raw text content provided above
                    - Do not attempt to extract or restructure the content
                    - Handle any OCR artifacts or formatting issues gracefully
                    - Focus on semantic understanding and content relevance
                    - Provide comprehensive grading with detailed feedback

                    IMPORTANT NOTES:
                    1. The student is required to answer exactly {num_questions} questions from the marking guide
                    2. Find the best {num_questions} answers in the student submission and map them to corresponding guide content
                    3. If there are more potential answers, select only the best {num_questions} based on quality and completeness
                    4. Pay special attention to mark allocations and question structure
                    5. Grade each answer comprehensively with specific feedback
                    6. Calculate overall grade based on total scores and maximum possible scores

                    CRITICAL INSTRUCTIONS:
                    1. Respond with ONLY valid JSON - no comments, explanations, or markdown outside the JSON object
                    2. Do not use # or // in your response
                    3. Use ONLY the actual content from the documents provided
                    4. Ensure all JSON fields are properly formatted and complete
                    5. Handle any OCR artifacts or formatting issues in the content gracefully
                    """

                    # Use a simpler prompt for the deepseek-reasoner model
                    params = {
                        "model": self.llm_service.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.0,
                    }

                    # Add seed parameter if in deterministic mode
                    if (
                        hasattr(self.llm_service, "deterministic")
                        and self.llm_service.deterministic
                        and hasattr(self.llm_service, "seed")
                        and self.llm_service.seed is not None
                    ):
                        params["seed"] = self.llm_service.seed
                        logger.info(
                            f"Using deterministic mode with seed: {self.llm_service.seed} for mapping"
                        )

                    response = self.llm_service.client.chat.completions.create(**params)

                    result = response.choices[0].message.content

                    # Log the LLM response processing
                    logger.info("Processing LLM response...")

                    # Enhanced JSON cleaning and validation
                    parsed = self._clean_and_parse_llm_response(result)

                    # Process LLM mappings and grading
                    overall_grade = parsed.get("overall_grade", {})
                    total_score = 0
                    max_possible_score = 0

                    for mapping in parsed.get("mappings", []):
                        # Extract grading information
                        grade_score = mapping.get("grade_score", 0)
                        grade_percentage = mapping.get("grade_percentage", 0)
                        grade_feedback = mapping.get("grade_feedback", "")
                        strengths = mapping.get("strengths", [])
                        weaknesses = mapping.get("weaknesses", [])

                        # Add to total scores
                        max_score = mapping.get("max_score")
                        if max_score is not None:
                            try:
                                max_score_float = float(max_score)
                                max_possible_score += max_score_float
                                if grade_score:
                                    total_score += float(grade_score)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid max_score value: {max_score}")

                        # Create mapping with grading information
                        mapping_obj = {
                            "guide_id": mapping.get("guide_id", f"g{len(mappings)+1}"),
                            "guide_text": mapping.get("guide_text", ""),
                            "guide_answer": mapping.get("guide_answer", ""),
                            "max_score": max_score,  # No default value
                            "submission_id": mapping.get(
                                "submission_id", f"s{len(mappings)+1}"
                            ),
                            "submission_text": mapping.get("submission_text", ""),
                            "submission_answer": mapping.get("submission_answer", ""),
                            "match_score": mapping.get("match_score", 0.5),
                            "match_reason": mapping.get("match_reason", ""),
                            "guide_type": guide_type,
                            # Grading information
                            "grade_score": grade_score,
                            "grade_percentage": grade_percentage,
                            "grade_feedback": grade_feedback,
                            "strengths": strengths,
                            "weaknesses": weaknesses,
                        }

                        # Add parent_question field if it exists
                        if mapping.get("parent_question"):
                            mapping_obj["parent_question"] = mapping.get(
                                "parent_question"
                            )

                        mappings.append(mapping_obj)

                    # If overall grade wasn't provided by the LLM, calculate it
                    if not overall_grade:
                        # Calculate percentage
                        percentage = (
                            (total_score / max_possible_score * 100)
                            if max_possible_score > 0
                            else 0
                        )

                        # Normalize the score to be out of 100
                        normalized_score = (
                            percentage  # This is already the percentage out of 100
                        )

                        # Determine letter grade
                        letter_grade = self._get_letter_grade(percentage)

                        overall_grade = {
                            "total_score": round(total_score, 1),
                            "max_possible_score": max_possible_score,
                            "normalized_score": round(normalized_score, 1),
                            "percentage": round(percentage, 1),
                            "letter_grade": letter_grade,
                        }

                except Exception as e:
                    logger.error(f"LLM mapping failed: {str(e)}")
                    # Log the LLM mapping error
                    logger.error(f"LLM mapping failed: {str(e)}")

                    # Create a basic result with raw content
                    result = {
                        "status": "error",
                        "message": f"LLM mapping failed: {str(e)}",
                        "mappings": [],
                        "metadata": {
                            "mapping_count": 0,
                            "guide_type": "unknown",
                            "mapping_method": "Failed LLM",
                            "timestamp": datetime.now().isoformat(),
                            "num_questions": num_questions,
                        },
                        "raw_guide_content": marking_guide_content,
                        "raw_submission_content": student_submission_content,
                        "overall_grade": {
                            "total_score": 0,
                            "max_possible_score": 0,
                            "percentage": 0,
                            "letter_grade": "F",
                        },
                    }

                    return result, f"LLM mapping failed: {str(e)}"
            else:
                # Log the no LLM service error
                logger.error(
                    "No LLM service available. LLM service is required for mapping."
                )

                # Raise an error since LLM service is required
                raise Exception(
                    "LLM service is required for mapping. No fallback available."
                )

            # Get guide type if available (from first mapping)
            guide_type = (
                mappings[0].get("guide_type", "unknown") if mappings else "unknown"
            )

            # Log finalizing mapping
            logger.info("Finalizing mapping results")

            # Initialize overall_grade if it doesn't exist
            if "overall_grade" not in locals():
                # Calculate total score and max possible score
                total_score = 0
                max_possible_score = 0

                # Calculate the total points from all mappings
                for mapping in mappings:
                    if mapping.get("grade_score") is not None:
                        total_score += mapping.get("grade_score", 0)
                    if mapping.get("max_score") is not None:
                        max_possible_score += mapping.get("max_score", 0)

                # Ensure max_possible_score is not zero to avoid division by zero
                if max_possible_score == 0:
                    max_possible_score = 100  # Default to 100 if no max score is found

                # Calculate percentage
                percentage = (
                    (total_score / max_possible_score * 100)
                    if max_possible_score > 0
                    else 0
                )

                # Normalize the score to be out of 100
                normalized_score = (
                    percentage  # This is already the percentage out of 100
                )

                # Determine letter grade
                letter_grade = self._get_letter_grade(percentage)

                overall_grade = {
                    "total_score": round(total_score, 1),
                    "max_possible_score": max_possible_score,
                    "normalized_score": round(normalized_score, 1),
                    "percentage": round(percentage, 1),
                    "letter_grade": letter_grade,
                }

            # Create result
            result = {
                "status": "success",
                "message": "Content mapped successfully",
                "mappings": mappings,
                "metadata": {
                    "num_questions": num_questions,
                    "mapping_count": len(mappings),
                    "guide_type": guide_type,
                    "mapping_method": "LLM" if self.llm_service else "Text-based",
                    "timestamp": datetime.now().isoformat(),
                },
                "raw_guide_content": marking_guide_content,
                "raw_submission_content": student_submission_content,
                "overall_grade": overall_grade,
            }

            # Log completion
            logger.info(
                f"Mapping and grading completed successfully. Score: {overall_grade.get('percentage', 0)}%"
            )

            return result, None

        except Exception as e:
            error_message = f"Error in mapping service: {str(e)}"

            # Log error
            logger.error(f"Mapping failed: {str(e)}")

            # Return error with raw content included
            return {
                "status": "error",
                "message": error_message,
                "raw_guide_content": marking_guide_content,
                "raw_submission_content": student_submission_content,
            }, error_message

    def _preprocess_content(self, content: str) -> str:
        """
        Preprocess content to improve LLM understanding and handle OCR artifacts.
        
        Args:
            content: Raw content to preprocess
            
        Returns:
            str: Preprocessed content
        """
        if not content:
            return ""
            
        # Remove excessive whitespace and normalize line breaks
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = re.sub(r' +', ' ', content)
        
        # Fix common OCR artifacts
        content = re.sub(r'[|]', 'I', content)  # Fix common OCR confusion
        content = re.sub(r'[0]', 'O', content)  # Fix common OCR confusion
        content = re.sub(r'[1]', 'l', content)  # Fix common OCR confusion
        
        # Remove excessive punctuation that might confuse the LLM
        content = re.sub(r'[!]{2,}', '!', content)
        content = re.sub(r'[?]{2,}', '?', content)
        content = re.sub(r'[.]{3,}', '...', content)
        
        # Normalize quotes and apostrophes
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace(''', "'").replace(''', "'")
        
        return content.strip()

    def _clean_and_parse_llm_response(self, result: str) -> Dict:
        """
        Clean and parse LLM response with enhanced error handling.
        
        Args:
            result: Raw LLM response
            
        Returns:
            Dict: Parsed JSON response
        """
        try:
            # Log the raw response for debugging
            logger.info(f"Raw LLM response: {result[:200]}...")

            # Find JSON content between curly braces if there's text before/after
            json_match = re.search(r"\{.*\}", result, re.DOTALL)
            if json_match:
                result = json_match.group(0)
                logger.info(f"Extracted JSON: {result[:200]}...")

            # More aggressive cleaning for deepseek-reasoner model
            # First, try to extract just the JSON part if there's surrounding text
            json_pattern = r"(\{[\s\S]*\})"
            json_matches = re.findall(json_pattern, result)
            if json_matches:
                result = json_matches[0]
                logger.info(f"Extracted JSON object: {result[:100]}...")

            # Remove any comments in the JSON (deepseek-reasoner sometimes adds these)
            result = re.sub(r"//.*?$", "", result, flags=re.MULTILINE)
            result = re.sub(r"/\*.*?\*/", "", result, flags=re.DOTALL)
            result = re.sub(r"#.*?$", "", result, flags=re.MULTILINE)

            # Remove comments that appear after values (common in deepseek output)
            result = re.sub(r'(["}\]])(\s*#[^\n]*)', r"\1", result)
            result = re.sub(r"(\d+)(\s*#[^\n]*)(,|\n|})", r"\1\3", result)

            # Fix common JSON formatting issues
            # Replace single quotes with double quotes
            result = re.sub(r"'([^']*)':", r'"\1":', result)
            result = re.sub(r": *\'([^\']*)\'", r': "\1"', result)

            # Fix trailing commas in arrays and objects
            result = re.sub(r",\s*]", "]", result)
            result = re.sub(r",\s*}", "}", result)

            # Handle specific format issues with deepseek-reasoner
            # Replace any remaining instances of "key": value # comment
            result = re.sub(
                r'("[^"]+"):\s*([^,\n\]}{#]*)(\s*#[^\n]*)(,|\n|}|\])',
                r"\1: \2\4",
                result,
            )

            # Final pass to remove any remaining comments
            result = re.sub(r"#[^\n]*\n", "\n", result)

            # Log the cleaned JSON
            logger.info(f"Cleaned JSON: {result[:200]}...")

            try:
                parsed = json.loads(result)
                logger.info("JSON parsing successful")
                return parsed
            except json.JSONDecodeError as json_error:
                logger.warning(f"Initial JSON parsing failed: {str(json_error)}")
                logger.warning("Attempting to use _get_structured_response to fix malformed JSON")
                
                # Try to use the LLM to fix the malformed JSON
                try:
                    result = self.llm_service._get_structured_response(result)
                    logger.info(f"LLM-fixed JSON: {result[:200]}...")
                    parsed = json.loads(result)
                    logger.info("JSON parsing successful after LLM fix")
                    return parsed
                except Exception as llm_fix_error:
                    logger.error(f"LLM JSON fix failed: {str(llm_fix_error)}")
                    # Re-raise the original JSON error to continue with the existing fallback logic
                    raise json_error
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            logger.error(f"Problematic JSON: {result}")

            # Try a more aggressive approach to extract valid JSON
            try:
                logger.info("Attempting manual JSON extraction...")

                # Try to manually construct a valid JSON object
                mappings = []

                # Extract mappings using regex patterns
                mapping_pattern = r'"guide_id"\s*:\s*"([^"]+)".*?"guide_text"\s*:\s*"([^"]+)".*?"max_score"\s*:\s*(\d+).*?"submission_id"\s*:\s*"([^"]+)".*?"submission_text"\s*:\s*"([^"]+)".*?"match_score"\s*:\s*([\d\.]+)'
                mapping_matches = re.findall(
                    mapping_pattern, result, re.DOTALL
                )

                if mapping_matches:
                    logger.info(
                        f"Found {len(mapping_matches)} mappings using regex"
                    )

                    for i, match in enumerate(mapping_matches):
                        (
                            guide_id,
                            guide_text,
                            max_score,
                            submission_id,
                            submission_text,
                            match_score,
                        ) = match

                        # Create a basic mapping
                        mappings.append(
                            {
                                "guide_id": guide_id,
                                "guide_text": guide_text,
                                "guide_answer": "",
                                "max_score": float(max_score),
                                "submission_id": submission_id,
                                "submission_text": submission_text,
                                "match_score": float(match_score),
                                "match_reason": f"Mapping extracted from LLM response",
                                "grade_score": float(max_score)
                                * 0.8,  # Assume 80% score as default
                                "grade_percentage": 80,
                                "grade_feedback": "Score estimated due to parsing issues",
                                "strengths": [],
                                "weaknesses": [],
                            }
                        )

                    # Create a basic result structure
                    parsed = {
                        "mappings": mappings,
                        "overall_grade": {
                            "total_score": sum(
                                m["grade_score"] for m in mappings
                            ),
                            "max_possible_score": sum(
                                m["max_score"] for m in mappings
                            ),
                            "percentage": 80,  # Assume 80% as default
                            "letter_grade": "B",
                        },
                    }

                    logger.info(
                        "Successfully created mappings from regex extraction"
                    )
                    return parsed
                else:
                    # If regex extraction fails, create a minimal valid structure
                    logger.warning(
                        "Regex extraction failed, using minimal valid structure"
                    )

                    # Log the JSON parsing error with fallback
                    logger.warning(
                        f"JSON parsing error: {str(e)}. Using fallback mapping."
                    )

                    # Log the extraction failure
                    logger.error(
                        f"JSON parsing error: {str(e)}. Unable to extract mappings."
                    )

                    # Raise the exception to stop processing
                    raise Exception(
                        f"JSON parsing error: {str(e)}. Unable to extract mappings from LLM response."
                    )
            except Exception as fallback_error:
                logger.error(
                    f"Fallback extraction also failed: {str(fallback_error)}"
                )

                # Log the fallback extraction failure
                logger.error(f"JSON parsing error: {str(e)}")

                # Raise the exception to stop processing
                raise Exception(f"JSON parsing error: {str(e)}")

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract important keywords from text.

        Args:
            text: Text to extract keywords from

        Returns:
            List[str]: List of keywords
        """
        if not text:
            return []

        # Split text into words
        words = re.findall(r"\b\w+\b", text.lower())

        # Remove common stop words
        stop_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "if",
            "because",
            "as",
            "what",
            "when",
            "where",
            "how",
            "why",
            "which",
            "who",
            "whom",
            "this",
            "that",
            "these",
            "those",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "having",
            "do",
            "does",
            "did",
            "doing",
            "to",
            "from",
            "in",
            "out",
            "on",
            "off",
            "over",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "all",
            "any",
            "both",
            "each",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "can",
            "will",
            "just",
            "should",
            "now",
        }

        # Filter out stop words and short words
        filtered_words = [
            word for word in words if word not in stop_words and len(word) > 3
        ]

        # Count word frequencies
        word_counts = {}
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1

        # Extract phrases (2-3 word combinations)
        phrases = []
        words = text.lower().split()
        for i in range(len(words) - 1):
            if words[i] not in stop_words and words[i + 1] not in stop_words:
                phrases.append(f"{words[i]} {words[i+1]}")

        # Get top keywords by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, _ in sorted_words[:10]]

        # Add important phrases
        keywords.extend(phrases[:5])

        # Add any numerical values as they're often important
        numbers = re.findall(r"\b\d+(?:\.\d+)?\b", text)
        keywords.extend(numbers)

        # Remove duplicates and return
        return list(set(keywords))

    def _text_based_mapping(
        self, guide_items: List[Dict], submission_items: List[Dict]
    ) -> List[Dict]:
        """Fallback method for text-based question matching with improved accuracy."""
        mappings = []

        # Simple text preprocessing function without NLTK dependency
        def preprocess_text(text):
            if not text:
                return []
            # Convert to lowercase
            text = text.lower()
            # Remove special characters and digits
            text = re.sub(r"[^\w\s]", " ", text)
            text = re.sub(r"\d+", " ", text)
            # Split into words
            words = text.split()
            # Remove common stopwords
            common_stopwords = {
                "i",
                "me",
                "my",
                "myself",
                "we",
                "our",
                "ours",
                "ourselves",
                "you",
                "you're",
                "you've",
                "you'll",
                "you'd",
                "your",
                "yours",
                "yourself",
                "yourselves",
                "he",
                "him",
                "his",
                "himself",
                "she",
                "she's",
                "her",
                "hers",
                "herself",
                "it",
                "it's",
                "its",
                "itself",
                "they",
                "them",
                "their",
                "theirs",
                "themselves",
                "what",
                "which",
                "who",
                "whom",
                "this",
                "that",
                "that'll",
                "these",
                "those",
                "am",
                "is",
                "are",
                "was",
                "were",
                "be",
                "been",
                "being",
                "have",
                "has",
                "had",
                "having",
                "do",
                "does",
                "did",
                "doing",
                "a",
                "an",
                "the",
                "and",
                "but",
                "if",
                "or",
                "because",
                "as",
                "until",
                "while",
                "of",
                "at",
                "by",
                "for",
                "with",
                "about",
                "against",
                "between",
                "into",
                "through",
                "during",
                "before",
                "after",
                "above",
                "below",
                "to",
                "from",
                "up",
                "down",
                "in",
                "out",
                "on",
                "off",
                "over",
                "under",
                "again",
                "further",
                "then",
                "once",
            }
            return [w for w in words if w not in common_stopwords and len(w) > 1]

        # Function to calculate Jaccard similarity
        def jaccard_similarity(set1, set2):
            if not set1 or not set2:
                return 0
            intersection = len(set(set1).intersection(set(set2)))
            union = len(set(set1).union(set(set2)))
            return intersection / union if union > 0 else 0

        # Function to calculate cosine similarity using TF-IDF approach
        def cosine_similarity_tokens(tokens1, tokens2):
            if not tokens1 or not tokens2:
                return 0

            # Count term frequencies
            counts1 = {}
            counts2 = {}

            for token in tokens1:
                counts1[token] = counts1.get(token, 0) + 1

            for token in tokens2:
                counts2[token] = counts2.get(token, 0) + 1

            # Find all unique terms
            unique_terms = set(counts1.keys()).union(set(counts2.keys()))

            # Calculate dot product and magnitudes
            dot_product = 0
            magnitude1 = 0
            magnitude2 = 0

            for term in unique_terms:
                tf1 = counts1.get(term, 0)
                tf2 = counts2.get(term, 0)
                dot_product += tf1 * tf2
                magnitude1 += tf1**2
                magnitude2 += tf2**2

            # Prevent division by zero
            if magnitude1 == 0 or magnitude2 == 0:
                return 0

            return dot_product / ((magnitude1**0.5) * (magnitude2**0.5))

        # Preprocess all guide items and submission items
        guide_tokens = {}
        submission_tokens = {}

        for guide_item in guide_items:
            guide_text = guide_item.get("text", "")
            guide_tokens[guide_item.get("id")] = preprocess_text(guide_text)

        for submission_item in submission_items:
            submission_text = submission_item.get("text", "")
            submission_tokens[submission_item.get("id")] = preprocess_text(
                submission_text
            )

        # For each guide item, find the best match in submission items
        for guide_item in guide_items:
            guide_id = guide_item.get("id")
            guide_text_tokens = guide_tokens[guide_id]

            best_score = 0
            best_match = None

            for submission_item in submission_items:
                # Skip if already mapped
                if any(
                    m.get("submission_id") == submission_item.get("id")
                    for m in mappings
                ):
                    continue

                submission_id = submission_item.get("id")
                submission_text_tokens = submission_tokens[submission_id]

                # Calculate similarity scores
                jaccard_score = jaccard_similarity(
                    guide_text_tokens, submission_text_tokens
                )
                cosine_score = cosine_similarity_tokens(
                    guide_text_tokens, submission_text_tokens
                )

                # Combine scores (weighted average favoring cosine similarity)
                combined_score = (0.3 * jaccard_score) + (0.7 * cosine_score)

                # Check exact ID match (e.g., "Question 1" matching with "1.")
                guide_id_match = re.search(r"(\d+)", guide_item.get("text", ""))
                submission_id_match = re.search(
                    r"(\d+)", submission_item.get("text", "")
                )

                if guide_id_match and submission_id_match:
                    if guide_id_match.group(1) == submission_id_match.group(1):
                        # Boost score for ID match
                        combined_score = max(combined_score, 0.6)

                # Also match by guide answer and submission answer if available
                if guide_item.get("answer") and submission_item.get("answer"):
                    guide_answer_tokens = preprocess_text(guide_item.get("answer", ""))
                    submission_answer_tokens = preprocess_text(
                        submission_item.get("answer", "")
                    )

                    answer_jaccard = jaccard_similarity(
                        guide_answer_tokens, submission_answer_tokens
                    )
                    answer_cosine = cosine_similarity_tokens(
                        guide_answer_tokens, submission_answer_tokens
                    )

                    # Calculate a more detailed answer similarity score
                    answer_score = (0.3 * answer_jaccard) + (0.7 * answer_cosine)

                    # Calculate keyword match score
                    guide_keywords = self._extract_keywords(
                        guide_item.get("answer", "")
                    )
                    submission_keywords = self._extract_keywords(
                        submission_item.get("answer", "")
                    )

                    # Calculate keyword match percentage
                    keyword_matches = [
                        kw
                        for kw in guide_keywords
                        if any(
                            kw.lower() in sub_kw.lower()
                            for sub_kw in submission_keywords
                        )
                    ]
                    keyword_score = (
                        len(keyword_matches) / max(len(guide_keywords), 1)
                        if guide_keywords
                        else 0
                    )

                    # Generate reason for match based on keywords
                    match_reason = f"Matched {len(keyword_matches)} of {len(guide_keywords)} key concepts"
                    if keyword_matches:
                        match_reason += f": {', '.join(keyword_matches[:3])}"
                        if len(keyword_matches) > 3:
                            match_reason += f" and {len(keyword_matches) - 3} more"

                    # Store the answer score for later use in grading
                    submission_item["answer_score"] = answer_score
                    submission_item["keyword_score"] = keyword_score
                    submission_item["match_reason"] = match_reason

                    # Consider answer similarity in overall score with higher weight
                    combined_score = (
                        (0.5 * combined_score)
                        + (0.3 * answer_score)
                        + (0.2 * keyword_score)
                    )

                if combined_score > best_score:
                    best_score = combined_score
                    best_match = (submission_item, combined_score)

            if (
                best_match and best_score > 0.2
            ):  # Only map if similarity exceeds threshold
                submission_item, match_score = best_match

                # Get the match reason if available
                match_reason = submission_item.get("match_reason", "")
                if not match_reason:
                    match_reason = f"Similarity score: {match_score:.2f}"

                # Get the answer score if available
                answer_score = submission_item.get("answer_score", 0)
                keyword_score = submission_item.get("keyword_score", 0)

                # Calculate a grade based on similarity
                grade_score = 0
                if guide_item.get("max_score"):
                    # Use answer_score with higher weight if available
                    if answer_score > 0:
                        grade_score = (
                            0.6 * answer_score + 0.4 * keyword_score
                        ) * float(guide_item.get("max_score"))
                    else:
                        grade_score = match_score * float(guide_item.get("max_score"))
                    grade_score = round(grade_score, 1)

                mappings.append(
                    {
                        "guide_id": guide_item.get("id"),
                        "guide_text": guide_item.get("text"),
                        "guide_answer": guide_item.get("answer", ""),
                        "max_score": guide_item.get("max_score"),  # No default value
                        "submission_id": submission_item.get("id"),
                        "submission_text": submission_item.get("text"),
                        "submission_answer": submission_item.get("answer", ""),
                        "match_score": match_score,
                        "answer_score": answer_score,
                        "keyword_score": keyword_score,
                        "grade_score": grade_score,
                        "match_reason": match_reason,
                    }
                )

        return mappings

    def _get_letter_grade(self, percent_score: float) -> str:
        """
        Convert percentage score to letter grade.

        Args:
            percent_score: Percentage score (0-100)

        Returns:
            str: Letter grade (A+, A, A-, B+, etc.)
        """
        if percent_score >= 97:
            return "A+"
        elif percent_score >= 93:
            return "A"
        elif percent_score >= 90:
            return "A-"
        elif percent_score >= 87:
            return "B+"
        elif percent_score >= 83:
            return "B"
        elif percent_score >= 80:
            return "B-"
        elif percent_score >= 77:
            return "C+"
        elif percent_score >= 73:
            return "C"
        elif percent_score >= 70:
            return "C-"
        elif percent_score >= 67:
            return "D+"
        elif percent_score >= 63:
            return "D"
        elif percent_score >= 60:
            return "D-"
        else:
            return "F"
