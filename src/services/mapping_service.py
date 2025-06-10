"""
Mapping Service for mapping submissions to marking guide criteria.
This service groups questions and answers from marking guides with corresponding
questions and answers in student submissions.
"""

import json
import re
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
            You are an expert at analyzing exam documents. Your task is to determine if a marking guide
            contains questions or answers.

            A marking guide with questions typically:
            - Contains questions without detailed answers
            - May have brief answer guidelines or marking criteria
            - Is structured as a list of questions for students to answer

            A marking guide with answers typically:
            - Contains detailed model answers to questions
            - May include marking criteria alongside answers
            - Is structured as a reference for graders to evaluate student responses

            Analyze the document carefully and determine its primary type.

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
            {marking_guide_content[:2000]}  # Limit to first 2000 chars for efficiency
            """

            # Log the request
            logger.info("Sending request to LLM service...")

            # Check if the model supports JSON output format
            supports_json = "deepseek-reasoner" not in self.llm_service.model.lower()

            if supports_json:
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
            else:
                # For models that don't support JSON response format
                modified_system_prompt = (
                    system_prompt
                    + """
                IMPORTANT: Your response must be valid JSON. Format your entire response as a JSON object.
                Do not include any text before or after the JSON object.
                """
                )

                params = {
                    "model": self.llm_service.model,
                    "messages": [
                        {"role": "system", "content": modified_system_prompt},
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

                response = self.llm_service.client.chat.completions.create(**params)

            # Log the response processing
            logger.info("Processing LLM response...")

            # Parse the response
            result = response.choices[0].message.content
            parsed = json.loads(result)

            guide_type = parsed.get("guide_type", "questions")
            confidence = parsed.get("confidence", 0.5)
            reasoning = parsed.get("reasoning", "No reasoning provided")

            # Log completion
            logger.info(f"Guide type determined: {guide_type}")

            logger.info(
                f"Determined guide type: {guide_type} (confidence: {confidence})"
            )
            logger.info(f"Reasoning: {reasoning}")

            return guide_type, confidence

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
                supports_json = (
                    "deepseek-reasoner" not in self.llm_service.model.lower()
                )

                if supports_json:
                    response = self.llm_service.client.chat.completions.create(
                        model=self.llm_service.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.0,
                        response_format={"type": "json_object"},
                    )
                else:
                    # For models that don't support JSON response format
                    modified_system_prompt = (
                        system_prompt
                        + """
                    IMPORTANT: Your response must be valid JSON. Format your entire response as a JSON object.
                    Do not include any text before or after the JSON object.

                    Example of valid JSON format:
                    {
                        "items": [
                            {
                                "id": "q1",
                                "text": "question text",
                                "answer": "answer text",
                                "max_score": 5
                            }
                        ]
                    }
                    """
                    )

                    params = {
                        "model": self.llm_service.model,
                        "messages": [
                            {"role": "system", "content": modified_system_prompt},
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

                # Enhanced system prompt specifically for marking guide question extraction
                system_prompt = """
                You are an expert at analyzing marking guides for educational assessments. Your task is to extract ALL questions and their mark allocations from a marking guide document.

                CRITICAL REQUIREMENTS:
                1. Extract EVERY question from the document, including sub-questions
                2. Find the exact mark allocation for each question/sub-question
                3. Calculate the total marks for the entire assessment
                4. Preserve the original question numbering and structure

                Question Identification Guidelines:
                - Look for patterns like: "QUESTION 1", "Question 1:", "Q1", "1.", "1)", etc.
                - Include sub-questions like: "a)", "i)", "1.1", "Part A", etc.
                - Questions may span multiple paragraphs
                - Some questions may have multiple parts with individual mark allocations

                Mark Allocation Guidelines:
                - Look for marks in formats like:
                  * "(25 marks)", "[25 marks]", "25 marks", "25 points"
                  * "Total: 25 marks", "Maximum: 25 marks"
                  * "25% of total", "Worth 25 marks"
                  * Sub-question marks: "a) 10 marks", "Part i: 5 marks"
                - If a question has sub-parts, sum up all sub-part marks for the total
                - If no marks are explicitly stated, set marks to null
                - Pay attention to mark distributions across question parts

                Total Marks Calculation:
                - Sum all individual question marks to get total marks
                - Look for explicit total marks statements like "Total marks: 100"
                - Verify that individual marks sum to any stated total

                Output Format:
                Respond with ONLY a valid JSON object in this exact format:
                {
                    "questions": [
                        {
                            "id": "q1",
                            "number": "1",
                            "text": "Complete question text including all parts",
                            "marks": 25,
                            "sub_questions": [
                                {
                                    "id": "q1a",
                                    "number": "1a",
                                    "text": "Sub-question text",
                                    "marks": 10
                                }
                            ]
                        }
                    ],
                    "total_marks": 100,
                    "extraction_summary": {
                        "total_questions": 4,
                        "questions_with_marks": 4,
                        "questions_without_marks": 0,
                        "total_sub_questions": 8
                    }
                }
                """

                user_prompt = f"""
                Please analyze this marking guide document and extract ALL questions with their mark allocations.

                IMPORTANT INSTRUCTIONS:
                1. Extract every single question from the document
                2. Find the exact marks for each question (look carefully for mark allocations)
                3. Include sub-questions and their individual marks
                4. Calculate the total marks for the entire assessment
                5. Preserve original question numbering

                Marking Guide Content:
                {content}

                Remember: Respond with ONLY valid JSON. No comments, no explanations, just the JSON object.
                """

                # Use the LLM service to extract questions
                params = {
                    "model": self.llm_service.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 2048,
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
                result = response.choices[0].message.content

                logger.info("Processing LLM response for question extraction...")

                # Clean up the response
                try:
                    # Find JSON content between curly braces
                    json_match = re.search(r"\{.*\}", result, re.DOTALL)
                    if json_match:
                        result = json_match.group(0)

                    # Remove comments
                    result = re.sub(r"//.*?$", "", result, flags=re.MULTILINE)
                    result = re.sub(r"/\*.*?\*/", "", result, flags=re.DOTALL)
                    result = re.sub(r"#.*?$", "", result, flags=re.MULTILINE)

                    parsed = json.loads(result)

                    # Validate the response structure
                    if "questions" in parsed and "total_marks" in parsed:
                        questions = parsed["questions"]
                        total_marks = parsed["total_marks"]

                        # Convert to the format expected by the application
                        formatted_questions = []
                        for i, q in enumerate(questions):
                            formatted_q = {
                                "number": i + 1,
                                "text": q.get("text", ""),
                                "marks": q.get("marks", 0),
                                "criteria": "",  # Can be populated later
                                "type": "question",
                            }
                            formatted_questions.append(formatted_q)

                        logger.info(
                            f"LLM successfully extracted {len(formatted_questions)} questions with {total_marks} total marks"
                        )

                        return {
                            "questions": formatted_questions,
                            "total_marks": total_marks,
                            "extraction_method": "llm",
                        }
                    else:
                        logger.warning(
                            "LLM response missing required fields, falling back to regex"
                        )

                except json.JSONDecodeError as e:
                    logger.warning(
                        f"JSON parsing error in LLM response: {str(e)}, falling back to regex"
                    )

            except Exception as e:
                logger.warning(
                    f"LLM extraction failed: {str(e)}, falling back to regex"
                )

        # Fallback to enhanced regex extraction
        logger.info("Using enhanced regex extraction for questions and marks...")
        return self._extract_questions_regex_enhanced(content)

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
                        You are an expert at matching and grading exam questions with student answers.
                        Your task is to analyze the raw text of a marking guide containing QUESTIONS and a student submission containing ANSWERS.
                        You need to identify and match the best {num_questions} questions in the guide with the corresponding answers in the submission, and then grade each answer.

                        Important guidelines:
                        1. First, identify the questions in the marking guide
                        2. Look for mark allocations in the marking guide (e.g., "5 marks", "[10]", "(15 points)", etc.)
                        3. Then, identify the answers in the student submission
                        4. Match each question with the answer that best addresses it
                        5. Consider semantic similarity and content relevance
                        6. Provide a high confidence score (0.8-1.0) only for very clear matches
                        7. For partial matches, provide a lower score (0.5-0.7) and explain why
                        8. If a question has no matching answer, do not include it in the mappings
                        9. IMPORTANT: The student is required to answer exactly {num_questions} questions from the marking guide
                        10. Find the best {num_questions} answers in the student submission and map them to the corresponding questions
                        11. If there are more potential answers, select only the best {num_questions} based on quality and completeness

                        Grading guidelines:
                        1. For each matched question-answer pair, grade the answer based on how well it addresses the question
                        2. Assign a score as a percentage of the maximum marks available (e.g., 8/10 = 80%)
                        3. Consider content accuracy, completeness, and relevance when grading
                        4. Provide brief feedback explaining the grade
                        5. Identify key strengths and weaknesses in the answer
                        6. The total possible score should be the sum of the maximum marks for the {num_questions} questions that were mapped

                        Pay special attention to mark allocations:
                        - Look for numbers followed by "marks", "points", "%" or enclosed in brackets/parentheses
                        - Check for mark breakdowns in sub-questions (e.g., "a) 5 marks, b) 10 marks")
                        - If marks are mentioned in a section header, apply them to all questions in that section
                        - If no marks are explicitly stated for a question, leave max_score as null

                        Output in JSON format with no comments.
                        """
                    else:  # guide_type == "answers"
                        system_prompt = f"""
                        You are an expert at matching and grading exam answers between a marking guide and a student submission.
                        Your task is to analyze the raw text of a marking guide containing MODEL ANSWERS and a student submission containing STUDENT ANSWERS.
                        You need to identify and match the best {num_questions} answers in the student submission with the corresponding model answers in the guide, and then grade each student answer.

                        Important guidelines:
                        1. First, identify the model answers in the marking guide
                        2. Look for mark allocations in the marking guide (e.g., "5 marks", "[10]", "(15 points)", etc.)
                        3. Then, identify the student answers in the submission
                        4. Match answers that address the same question, even if they differ in content
                        5. Look for semantic similarity and shared key concepts
                        6. Provide a high confidence score (0.8-1.0) only for very clear matches
                        7. For partial matches, provide a lower score (0.5-0.7) and explain why
                        8. If a student answer has no matching guide answer, do not include it in the mappings
                        9. IMPORTANT: The student is required to answer exactly {num_questions} questions from the marking guide
                        10. Find the best {num_questions} answers in the student submission and map them to the corresponding model answers
                        11. If there are more potential answers, select only the best {num_questions} based on quality and completeness

                        Grading guidelines:
                        1. For each matched answer pair, grade the student answer based on how well it matches the model answer
                        2. Assign a score as a percentage of the maximum marks available (e.g., 8/10 = 80%)
                        3. Consider content accuracy, completeness, and relevance when grading
                        4. Provide brief feedback explaining the grade
                        5. Identify key strengths and weaknesses in the student answer compared to the model answer
                        6. The total possible score should be the sum of the maximum marks for the {num_questions} questions that were mapped

                        Pay special attention to mark allocations:
                        - Look for numbers followed by "marks", "points", "%" or enclosed in brackets/parentheses
                        - Check for mark breakdowns in sub-answers (e.g., "a) 5 marks, b) 10 marks")
                        - If marks are mentioned in a section header, apply them to all answers in that section
                        - If no marks are explicitly stated for an answer, leave max_score as null

                        Output in JSON format with no comments.
                        """

                    # Log the mapping process
                    logger.info(
                        f"Using LLM to map submission to guide (finding best {num_questions} answers)..."
                    )

                    # Pass the raw content to the LLM for mapping and grading
                    user_prompt = f"""
                    Marking Guide Content:
                    {marking_guide_content[:5000]}

                    Student Submission Content:
                    {student_submission_content[:5000]}

                    Number of questions to answer: {num_questions}

                    Please analyze both documents using ONLY the raw text content provided above.
                    Do not attempt to extract questions and answers - work directly with the raw text.
                    Create mappings between related parts of the guide and submission.

                    IMPORTANT: The student is required to answer exactly {num_questions} questions from the marking guide.
                    Find the best {num_questions} answers in the student submission and map them to the corresponding questions in the marking guide.
                    If there are more potential answers, select only the best {num_questions} based on quality and completeness.

                    Pay special attention to:

                    1. Question structure:
                    - Some questions may contain multiple sub-questions (e.g., Question 1 might have parts a, b, c)
                    - Each sub-question may have its own mark allocation
                    - Treat each question or sub-question as a separate item to be mapped and graded
                    - Pay attention to question numbering and hierarchies (e.g., 1, 1.1, 1.2, or 1a, 1b, 1c)
                    - A student might answer some or all parts of a multi-part question
                    - For multi-part questions, count the entire question (with all its parts) as ONE question toward the {num_questions} total

                    2. Mark allocations:
                    - Look for numbers followed by "marks", "points", "%" or enclosed in brackets/parentheses
                    - Include these mark allocations in the max_score field for each mapping
                    - For questions with sub-parts, each sub-part may have its own mark allocation
                    - The total marks for a question with sub-parts is the sum of marks for all sub-parts

                    After mapping, grade each student answer based on how well it matches the expected answer:
                    - Assign a score out of the maximum marks available
                    - Calculate a percentage score
                    - Provide brief feedback explaining the grade
                    - Identify strengths and weaknesses in the answer

                    Finally, calculate an overall grade by summing all scores and determining the percentage of total available marks.
                    The total possible score should be the sum of the maximum marks for the {num_questions} questions that were mapped.

                    CRITICAL INSTRUCTIONS:
                    1. DO NOT include any comments in the JSON response
                    2. DO NOT use # or // in your response
                    3. DO NOT copy any example data - use ONLY the actual content from the documents
                    4. DO NOT include the text "What is the capital of France" or "Paris" in your response unless it actually appears in the documents
                    5. Use ONLY the actual content from the marking guide and student submission
                    6. Be sure to identify and properly map multi-part questions and their sub-questions
                    """

                    # For deepseek-reasoner model, we need to use a different approach
                    # since it doesn't support JSON response format
                    logger.info(f"Using model: {self.llm_service.model}")

                    # Modify the system prompt to request a specific format
                    # Remove all the JSON examples with comments from the original system prompt
                    system_prompt = system_prompt.replace("Output in JSON format:", "")
                    system_prompt = re.sub(
                        r"\{[^}]*\}", "", system_prompt, flags=re.DOTALL
                    )

                    modified_system_prompt = """
                    You are an expert at matching and grading exam content.

                    Your task is to analyze the RAW TEXT of a marking guide and a student submission.
                    DO NOT try to extract questions and answers - work directly with the raw text provided.

                    IMPORTANT: Understand the structure of exam questions:
                    1. Some questions may contain multiple sub-questions (e.g., Question 1 might have parts a, b, c)
                    2. Each sub-question may have its own mark allocation (e.g., 1a: 5 marks, 1b: 10 marks)
                    3. Treat each question or sub-question as a separate item to be mapped and graded
                    4. Pay attention to question numbering and hierarchies (e.g., 1, 1.1, 1.2, or 1a, 1b, 1c)
                    5. A student might answer some or all parts of a multi-part question

                    Your response must be valid JSON without any comments.

                    Format your entire response as a JSON object with these exact fields:
                    - mappings: an array of mapping objects
                    - overall_grade: an object with grading information

                    Each mapping object must have these fields:
                    - guide_id: a string identifier for the guide item (use "g1", "g1a", "g1b", "g2", etc.)
                    - guide_text: the text from the guide (a section, question, or sub-question)
                    - guide_answer: the answer from the guide (if any)
                    - max_score: the maximum score for this item (a number)
                    - parent_question: (optional) if this is a sub-question, include the parent question ID
                    - submission_id: a string identifier for the submission item (use "s1", "s1a", "s1b", "s2", etc.)
                    - submission_text: the text from the submission (the student's answer)
                    - match_score: a number between 0 and 1 indicating match confidence
                    - match_reason: a string explaining the match
                    - grade_score: the score awarded (a number)
                    - grade_percentage: the percentage score (a number)
                    - grade_feedback: feedback on the answer (a string)
                    - strengths: an array of strings listing strengths
                    - weaknesses: an array of strings listing weaknesses

                    The overall_grade object must have these fields:
                    - total_score: the total score awarded (a number)
                    - max_possible_score: the maximum possible score (a number)
                    - percentage: the percentage score (a number)
                    - letter_grade: the letter grade (a string)

                    CRITICAL INSTRUCTIONS:
                    1. DO NOT include any comments in the JSON
                    2. DO NOT use # or // in your response
                    3. DO NOT copy any example data - use ONLY the actual content from the documents
                    4. DO NOT include the text "What is the capital of France" or "Paris" in your response unless it actually appears in the documents
                    5. Use ONLY the actual content from the marking guide and student submission
                    6. Be sure to identify and properly map multi-part questions and their sub-questions
                    """

                    # Use a simpler prompt for the deepseek-reasoner model
                    params = {
                        "model": self.llm_service.model,
                        "messages": [
                            {"role": "system", "content": modified_system_prompt},
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

                    # Try to clean up the response for models that don't properly format JSON
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

                        parsed = json.loads(result)
                        logger.info("JSON parsing successful")
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

                    # No need to create items for unmapped sections anymore
                    # We'll just use the raw content

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

            # We're no longer generating unmapped items
            # Just store the raw content for display

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
