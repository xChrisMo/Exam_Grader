"""
Mapping Service for mapping submissions to marking guide criteria.
This service groups questions and answers from marking guides with corresponding
questions and answers in student submissions.
"""
import re
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

from utils.logger import logger
from src.services.progress_tracker import progress_tracker

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
            # Create a tracker for the operation
            tracker_id = progress_tracker.create_tracker(
                operation_type="llm",
                task_name="Determining Guide Type",
                total_steps=3
            )

            # Update progress - Step 1: Analyzing content
            progress_tracker.update_progress(
                tracker_id=tracker_id,
                current_step=1,
                status="analyzing",
                message="Analyzing marking guide content..."
            )

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

            # Update progress - Step 2: Sending request
            progress_tracker.update_progress(
                tracker_id=tracker_id,
                current_step=2,
                status="processing",
                message="Sending request to LLM service..."
            )

            # Check if the model supports JSON output format
            supports_json = "deepseek-reasoner" not in self.llm_service.model.lower()

            if supports_json:
                # Make the API call with JSON response format
                response = self.llm_service.client.chat.completions.create(
                    model=self.llm_service.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
            else:
                # For models that don't support JSON response format
                modified_system_prompt = system_prompt + """
                IMPORTANT: Your response must be valid JSON. Format your entire response as a JSON object.
                Do not include any text before or after the JSON object.
                """
                response = self.llm_service.client.chat.completions.create(
                    model=self.llm_service.model,
                    messages=[
                        {"role": "system", "content": modified_system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0
                )

            # Update progress - Step 3: Processing response
            progress_tracker.update_progress(
                tracker_id=tracker_id,
                current_step=3,
                status="analyzing",
                message="Processing LLM response..."
            )

            # Parse the response
            result = response.choices[0].message.content
            parsed = json.loads(result)

            guide_type = parsed.get("guide_type", "questions")
            confidence = parsed.get("confidence", 0.5)
            reasoning = parsed.get("reasoning", "No reasoning provided")

            # Update progress - Complete
            progress_tracker.update_progress(
                tracker_id=tracker_id,
                status="completed",
                message=f"Guide type determined: {guide_type}",
                completed=True,
                success=True,
                result={"guide_type": guide_type, "confidence": confidence, "reasoning": reasoning}
            )

            logger.info(f"Determined guide type: {guide_type} (confidence: {confidence})")
            logger.info(f"Reasoning: {reasoning}")

            return guide_type, confidence

        except Exception as e:
            logger.error(f"Error determining guide type: {str(e)}")
            # Default to questions on error
            return "questions", 0.5

    def extract_questions_and_answers(self, content: str, tracker_id: str = None) -> List[Dict[str, Any]]:
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
                # Update progress if tracker_id is provided
                if tracker_id:
                    progress_tracker.update_progress(
                        tracker_id=tracker_id,
                        status="processing",
                        message="Extracting questions and answers from content..."
                    )

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
                supports_json = "deepseek-reasoner" not in self.llm_service.model.lower()

                if supports_json:
                    response = self.llm_service.client.chat.completions.create(
                        model=self.llm_service.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.0,
                        response_format={"type": "json_object"}
                    )
                else:
                    # For models that don't support JSON response format
                    modified_system_prompt = system_prompt + """
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
                    response = self.llm_service.client.chat.completions.create(
                        model=self.llm_service.model,
                        messages=[
                            {"role": "system", "content": modified_system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.0
                    )

                result = response.choices[0].message.content

                # Update progress if tracker_id is provided
                if tracker_id:
                    progress_tracker.update_progress(
                        tracker_id=tracker_id,
                        status="processing",
                        message="Processing LLM response for question extraction..."
                    )

                # Try to clean up the response for models that don't properly format JSON
                try:
                    # Find JSON content between curly braces if there's text before/after
                    json_match = re.search(r'\{.*\}', result, re.DOTALL)
                    if json_match:
                        result = json_match.group(0)

                    parsed = json.loads(result)

                    # Update progress if tracker_id is provided
                    if tracker_id:
                        progress_tracker.update_progress(
                            tracker_id=tracker_id,
                            status="success",
                            message=f"Successfully extracted {len(parsed.get('items', []))} items from content"
                        )

                    return parsed.get("items", [])
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parsing error in extract_questions_and_answers: {str(e)}")

                    # Update progress if tracker_id is provided
                    if tracker_id:
                        progress_tracker.update_progress(
                            tracker_id=tracker_id,
                            status="warning",
                            message=f"JSON parsing error: {str(e)}. Falling back to regex extraction.",
                            error=str(e)
                        )

                    # Return an empty list to trigger the fallback extraction
                    return []

            except Exception as e:
                logger.warning(f"LLM extraction failed, falling back to regex: {str(e)}")

        # Fallback to regex-based extraction
        items = []
        content = re.sub(r'\n{3,}', '\n\n', content.strip())
        content = re.sub(r'([^\n])(\s*)(Question|Q)\s+(\d+)', r'\1\n\n\3 \4', content, flags=re.IGNORECASE)

        question_matches = list(re.finditer(r'(?:^|\n+)((?:Question|Q)[.\s]*\d+[.\s]*:?[.\s]*)(.*?)(?=(?:\n+(?:Question|Q)[.\s]*\d+[.\s]*:?)|$)',
                                           content, re.IGNORECASE | re.DOTALL))

        if not question_matches:
            items.append({
                "id": "item1",
                "text": content.strip(),
                "type": "unknown"
            })
            return items

        for i, match in enumerate(question_matches):
            current_id = i + 1
            # Extract question content from the match
            question_content = match.group(2).strip()

            answer_match = re.search(r'(?:^|\n+)((?:Answer|A|Solution|Sol)[.\s]*:?[.\s]*)(.*)',
                                    question_content, re.IGNORECASE | re.DOTALL)

            if answer_match:
                question_text = question_content[:answer_match.start()].strip()
                answer_text = answer_match.group(2).strip()
            else:
                question_text = question_content
                answer_text = ""

            # Try to extract max score with more patterns
            max_score = None
            score_patterns = [
                r'(?:max|maximum|total)[.\s]*(?:score|points|marks)[.\s]*:?\s*(\d+)',
                r'\((\d+)\s*(?:marks|points)\)',
                r'(\d+)\s*(?:marks|points)\s*(?:each|total|maximum)?',
                r'(?:worth|total|maximum)\s*(?:of\s*)?(\d+)\s*(?:marks|points)'
            ]

            for pattern in score_patterns:
                max_score_match = re.search(pattern, question_content, re.IGNORECASE)
                if max_score_match:
                    max_score = int(max_score_match.group(1))
                    break

                items.append({
                    "id": f"q{current_id}",
                    "text": question_text,
                    "answer": answer_text,
                "max_score": max_score  # Will be None if no marks found
                })

        return items

    def map_submission_to_guide(self, marking_guide_content: str, student_submission_content: str) -> Tuple[Dict, Optional[str]]:
        """
        Map a student submission to a marking guide using LLM for intelligent grouping.

        This method:
        1. Determines if the marking guide contains questions or answers
        2. Uses the LLM to group guide and submission content based on the guide type
        3. Falls back to text-based mapping if LLM is not available

        Args:
            marking_guide_content: Raw text content of the marking guide
            student_submission_content: Raw text content of the student submission

        Returns:
            Tuple[Dict, Optional[str]]: (Mapping result, Error message if any)
        """
        try:
            # Create a tracker for the mapping operation
            tracker_id = progress_tracker.create_tracker(
                operation_type="llm",
                task_name="Mapping Submission to Guide",
                total_steps=4
            )

            # Update progress - Step 1: Validating content
            progress_tracker.update_progress(
                tracker_id=tracker_id,
                current_step=1,
                status="validating",
                message="Validating document content..."
            )

            # Check if we have content to work with
            if not marking_guide_content or not marking_guide_content.strip():
                progress_tracker.update_progress(
                    tracker_id=tracker_id,
                    status="failed",
                    message="Marking guide content is empty",
                    completed=True,
                    success=False,
                    error="Empty marking guide"
                )
                return {
                    "status": "error",
                    "message": "Marking guide content is empty"
                }, "Empty marking guide"

            if not student_submission_content or not student_submission_content.strip():
                progress_tracker.update_progress(
                    tracker_id=tracker_id,
                    status="failed",
                    message="Student submission content is empty",
                    completed=True,
                    success=False,
                    error="Empty student submission"
                )
                return {
                    "status": "error",
                    "message": "Student submission content is empty"
                }, "Empty student submission"

            mappings = []
            guide_items = []
            submission_items = []

            if self.llm_service:
                try:
                    # Update progress - Step 2: Determining guide type
                    progress_tracker.update_progress(
                        tracker_id=tracker_id,
                        current_step=2,
                        status="analyzing",
                        message="Determining if marking guide contains questions or answers..."
                    )

                    # Determine if the marking guide contains questions or answers
                    guide_type, confidence = self.determine_guide_type(marking_guide_content)

                    # Update progress - Step 3: Preparing for mapping
                    progress_tracker.update_progress(
                        tracker_id=tracker_id,
                        current_step=3,
                        status="preparing",
                        message=f"Guide type determined: {guide_type} (confidence: {confidence:.2f}). Preparing for mapping..."
                    )

                    # Use LLM to map submission to guide based on guide type
                    if guide_type == "questions":
                        system_prompt = """
                        You are an expert at matching exam questions with student answers.
                        Your task is to analyze the raw text of a marking guide containing QUESTIONS and a student submission containing ANSWERS.
                        You need to identify and match each question in the guide with the corresponding answer in the submission.

                        Important guidelines:
                        1. First, identify the questions in the marking guide
                        2. Look for mark allocations in the marking guide (e.g., "5 marks", "[10]", "(15 points)", etc.)
                        3. Then, identify the answers in the student submission
                        4. Match each question with the answer that best addresses it
                        5. Consider semantic similarity and content relevance
                        6. Provide a high confidence score (0.8-1.0) only for very clear matches
                        7. For partial matches, provide a lower score (0.5-0.7) and explain why
                        8. If a question has no matching answer, do not include it in the mappings

                        Pay special attention to mark allocations:
                        - Look for numbers followed by "marks", "points", "%" or enclosed in brackets/parentheses
                        - Check for mark breakdowns in sub-questions (e.g., "a) 5 marks, b) 10 marks")
                        - If marks are mentioned in a section header, apply them to all questions in that section
                        - If no marks are explicitly stated for a question, leave max_score as null

                        Output in JSON format:
                        {
                            "mappings": [
                                {
                                    "guide_id": "q1",
                                    "guide_text": "What is the capital of France?",
                                    "guide_answer": "",
                                    "max_score": 5,  # Include the mark allocation found in the guide
                                    "submission_id": "a1",
                                    "submission_text": "The capital of France is Paris.",
                                    "match_score": 0.95,
                                    "match_reason": "This submission answer directly addresses the question in the guide"
                                }
                            ]
                        }
                        """
                    else:  # guide_type == "answers"
                        system_prompt = """
                        You are an expert at matching exam answers between a marking guide and a student submission.
                        Your task is to analyze the raw text of a marking guide containing MODEL ANSWERS and a student submission containing STUDENT ANSWERS.
                        You need to identify and match answers that address the same questions.

                        Important guidelines:
                        1. First, identify the model answers in the marking guide
                        2. Look for mark allocations in the marking guide (e.g., "5 marks", "[10]", "(15 points)", etc.)
                        3. Then, identify the student answers in the submission
                        4. Match answers that address the same question, even if they differ in content
                        5. Look for semantic similarity and shared key concepts
                        6. Provide a high confidence score (0.8-1.0) only for very clear matches
                        7. For partial matches, provide a lower score (0.5-0.7) and explain why
                        8. If a student answer has no matching guide answer, do not include it in the mappings

                        Pay special attention to mark allocations:
                        - Look for numbers followed by "marks", "points", "%" or enclosed in brackets/parentheses
                        - Check for mark breakdowns in sub-answers (e.g., "a) 5 marks, b) 10 marks")
                        - If marks are mentioned in a section header, apply them to all answers in that section
                        - If no marks are explicitly stated for an answer, leave max_score as null

                        Output in JSON format:
                        {
                            "mappings": [
                                {
                                    "guide_id": "a1",
                                    "guide_text": "The capital of France is Paris.",
                                    "max_score": 5,  # Include the mark allocation found in the guide
                                    "submission_id": "a1",
                                    "submission_text": "Paris is the capital of France.",
                                    "match_score": 0.95,
                                    "match_reason": "Both answers address the same question about the capital of France"
                                }
                            ]
                        }
                        """

                    # Update progress - Step 4: Mapping content
                    progress_tracker.update_progress(
                        tracker_id=tracker_id,
                        current_step=4,
                        status="mapping",
                        message="Using LLM to map submission to guide..."
                    )

                    # Pass the raw content to the LLM for mapping
                    user_prompt = f"""
                    Marking Guide Content:
                    {marking_guide_content[:5000]}  # Limit to first 5000 chars for efficiency

                    Student Submission Content:
                    {student_submission_content[:5000]}  # Limit to first 5000 chars for efficiency

                    Please analyze both documents and identify matching content based on the guidelines.
                    Focus on the raw text content and create mappings between related parts of the guide and submission.

                    Pay special attention to mark allocations in the marking guide:
                    - Look for numbers followed by "marks", "points", "%" or enclosed in brackets/parentheses
                    - Examples: "5 marks", "[10]", "(15 points)", "20%", etc.
                    - Include these mark allocations in the max_score field for each mapping
                    """

                    # Check if the model supports JSON output format
                    supports_json = "deepseek-reasoner" not in self.llm_service.model.lower()

                    if supports_json:
                        response = self.llm_service.client.chat.completions.create(
                            model=self.llm_service.model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.0,
                            response_format={"type": "json_object"}
                        )
                    else:
                        # For models that don't support JSON response format
                        modified_system_prompt = system_prompt + """
                        IMPORTANT: Your response must be valid JSON. Format your entire response as a JSON object.
                        Do not include any text before or after the JSON object.

                        Example of valid JSON format:
                        {
                            "mappings": [
                                {
                                    "guide_id": "q1",
                                    "guide_text": "What is the capital of France?",
                                    "guide_answer": "",
                                    "max_score": 5,
                                    "submission_id": "a1",
                                    "submission_text": "The capital of France is Paris.",
                                    "match_score": 0.95,
                                    "match_reason": "This submission answer directly addresses the question in the guide"
                                }
                            ]
                        }
                        """
                        response = self.llm_service.client.chat.completions.create(
                            model=self.llm_service.model,
                            messages=[
                                {"role": "system", "content": modified_system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.0
                        )

                    result = response.choices[0].message.content

                    # Update progress - Step 4.5: Processing LLM response
                    progress_tracker.update_progress(
                        tracker_id=tracker_id,
                        current_step=4.5,
                        status="processing",
                        message="Processing LLM response..."
                    )

                    # Try to clean up the response for models that don't properly format JSON
                    try:
                        # Find JSON content between curly braces if there's text before/after
                        json_match = re.search(r'\{.*\}', result, re.DOTALL)
                        if json_match:
                            result = json_match.group(0)

                        parsed = json.loads(result)
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON parsing error: {str(e)}")
                        # Update progress - JSON parsing error
                        progress_tracker.update_progress(
                            tracker_id=tracker_id,
                            status="warning",
                            message=f"JSON parsing error: {str(e)}. Using fallback mapping.",
                            error=str(e)
                        )

                        # Create a default mapping structure
                        parsed = {"mappings": []}

                        # Add a simple mapping with the raw content
                        parsed["mappings"].append({
                            "guide_id": "g1",
                            "guide_text": marking_guide_content[:500],
                            "guide_answer": "",
                            "max_score": None,
                            "submission_id": "s1",
                            "submission_text": student_submission_content[:500],
                            "submission_answer": "",
                            "match_score": 0.5,
                            "match_reason": "Fallback mapping due to JSON parsing error"
                        })

                    # Process LLM mappings
                    for mapping in parsed.get("mappings", []):
                        mappings.append({
                            "guide_id": mapping.get("guide_id", f"g{len(mappings)+1}"),
                            "guide_text": mapping.get("guide_text", ""),
                            "guide_answer": mapping.get("guide_answer", ""),
                            "max_score": mapping.get("max_score"),  # No default value
                            "submission_id": mapping.get("submission_id", f"s{len(mappings)+1}"),
                            "submission_text": mapping.get("submission_text", ""),
                            "submission_answer": mapping.get("submission_answer", ""),
                            "match_score": mapping.get("match_score", 0.5),
                            "match_reason": mapping.get("match_reason", ""),
                            "guide_type": guide_type
                        })

                except Exception as e:
                    logger.warning(f"LLM mapping failed, falling back to text-based extraction: {str(e)}")
                    # Update progress - Error in LLM mapping
                    progress_tracker.update_progress(
                        tracker_id=tracker_id,
                        status="warning",
                        message="LLM mapping failed, falling back to text-based extraction",
                        error=str(e)
                    )

                    # Update progress - Extracting items
                    progress_tracker.update_progress(
                        tracker_id=tracker_id,
                        current_step=3.5,
                        status="extracting",
                        message="Extracting questions and answers from guide..."
                    )

                    # Extract items and use text-based mapping as fallback
                    guide_items = self.extract_questions_and_answers(marking_guide_content, tracker_id)

                    # Update progress - Extracting submission items
                    progress_tracker.update_progress(
                        tracker_id=tracker_id,
                        current_step=3.7,
                        status="extracting",
                        message="Extracting questions and answers from submission..."
                    )

                    submission_items = self.extract_questions_and_answers(student_submission_content, tracker_id)

                    # Update progress - Text-based mapping
                    progress_tracker.update_progress(
                        tracker_id=tracker_id,
                        current_step=3.9,
                        status="mapping",
                        message="Performing text-based mapping..."
                    )

                    if guide_items and submission_items:
                        mappings = self._text_based_mapping(guide_items, submission_items)
                    else:
                        # Create a simple mapping with the entire content
                        mappings = [{
                            "guide_id": "g1",
                            "guide_text": marking_guide_content[:500],  # First 500 chars
                            "guide_answer": "",
                            "max_score": None,
                            "submission_id": "s1",
                            "submission_text": student_submission_content[:500],  # First 500 chars
                            "submission_answer": "",
                            "match_score": 0.5,
                            "match_reason": "Fallback mapping of raw content",
                            "guide_type": "unknown"
                        }]
            else:
                # Update progress - No LLM service
                progress_tracker.update_progress(
                    tracker_id=tracker_id,
                    current_step=3,
                    status="processing",
                    message="No LLM service available, using text-based extraction..."
                )

                # Update progress - Extracting items
                progress_tracker.update_progress(
                    tracker_id=tracker_id,
                    current_step=3.5,
                    status="extracting",
                    message="Extracting questions and answers from guide..."
                )

                # Extract items and use text-based mapping
                guide_items = self.extract_questions_and_answers(marking_guide_content, tracker_id)

                # Update progress - Extracting submission items
                progress_tracker.update_progress(
                    tracker_id=tracker_id,
                    current_step=3.7,
                    status="extracting",
                    message="Extracting questions and answers from submission..."
                )

                submission_items = self.extract_questions_and_answers(student_submission_content, tracker_id)

                # Update progress - Text-based mapping
                progress_tracker.update_progress(
                    tracker_id=tracker_id,
                    current_step=3.9,
                    status="mapping",
                    message="Performing text-based mapping..."
                )

                if guide_items and submission_items:
                    mappings = self._text_based_mapping(guide_items, submission_items)
                else:
                    # Create a simple mapping with the entire content
                    mappings = [{
                        "guide_id": "g1",
                        "guide_text": marking_guide_content[:500],  # First 500 chars
                        "guide_answer": "",
                        "max_score": None,
                        "submission_id": "s1",
                        "submission_text": student_submission_content[:500],  # First 500 chars
                        "submission_answer": "",
                        "match_score": 0.5,
                        "match_reason": "Fallback mapping of raw content",
                        "guide_type": "unknown"
                    }]

            # Get guide type if available (from first mapping)
            guide_type = mappings[0].get("guide_type", "unknown") if mappings else "unknown"

            # Identify unmapped guide items and submission items
            mapped_guide_ids = [mapping.get("guide_id") for mapping in mappings]
            mapped_submission_ids = [mapping.get("submission_id") for mapping in mappings]

            # Find unmapped guide items
            unmapped_guide_items = []
            if guide_items:
                for item in guide_items:
                    if item.get("id") not in mapped_guide_ids:
                        unmapped_guide_items.append(item)

            # Find unmapped submission items
            unmapped_submission_items = []
            if submission_items:
                for item in submission_items:
                    if item.get("id") not in mapped_submission_ids:
                        unmapped_submission_items.append(item)

            # Update progress - Identifying unmapped items
            if 'tracker_id' in locals() and tracker_id:
                progress_tracker.update_progress(
                    tracker_id=tracker_id,
                    current_step=3.95,
                    status="processing",
                    message=f"Identified {len(unmapped_guide_items)} unmapped guide items and {len(unmapped_submission_items)} unmapped submission items"
                )

            # Create result
            result = {
                "status": "success",
                "message": "Content mapped successfully",
                "mappings": mappings,
                "metadata": {
                    "mapping_count": len(mappings),
                    "guide_type": guide_type,
                    "mapping_method": "LLM" if self.llm_service else "Text-based",
                    "timestamp": datetime.now().isoformat(),
                    "guide_item_count": len(guide_items) if guide_items else 0,
                    "submission_item_count": len(submission_items) if submission_items else 0,
                    "unmapped_guide_count": len(unmapped_guide_items),
                    "unmapped_submission_count": len(unmapped_submission_items)
                },
                "unmapped_guide_items": unmapped_guide_items,
                "unmapped_submission_items": unmapped_submission_items
            }

            # Update progress - Complete
            if 'tracker_id' in locals() and tracker_id:
                progress_tracker.update_progress(
                    tracker_id=tracker_id,
                    status="completed",
                    message="Mapping completed successfully",
                    completed=True,
                    success=True,
                    result={
                        "mapping_count": len(mappings),
                        "guide_type": guide_type
                    }
                )

            return result, None

        except Exception as e:
            error_message = f"Error in mapping service: {str(e)}"

            # Update progress - Error
            if 'tracker_id' in locals() and tracker_id:
                progress_tracker.update_progress(
                    tracker_id=tracker_id,
                    status="failed",
                    message=f"Mapping failed: {str(e)}",
                    completed=True,
                    success=False,
                    error=str(e)
                )

            return {"status": "error", "message": error_message}, error_message

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
        words = re.findall(r'\b\w+\b', text.lower())

        # Remove common stop words
        stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what', 'when',
            'where', 'how', 'why', 'which', 'who', 'whom', 'this', 'that', 'these', 'those',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having',
            'do', 'does', 'did', 'doing', 'to', 'from', 'in', 'out', 'on', 'off', 'over', 'under',
            'again', 'further', 'then', 'once', 'here', 'there', 'all', 'any', 'both', 'each',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just', 'should', 'now'
        }

        # Filter out stop words and short words
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]

        # Count word frequencies
        word_counts = {}
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1

        # Extract phrases (2-3 word combinations)
        phrases = []
        words = text.lower().split()
        for i in range(len(words) - 1):
            if words[i] not in stop_words and words[i+1] not in stop_words:
                phrases.append(f"{words[i]} {words[i+1]}")

        # Get top keywords by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, _ in sorted_words[:10]]

        # Add important phrases
        keywords.extend(phrases[:5])

        # Add any numerical values as they're often important
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        keywords.extend(numbers)

        # Remove duplicates and return
        return list(set(keywords))

    def _text_based_mapping(self, guide_items: List[Dict], submission_items: List[Dict]) -> List[Dict]:
        """Fallback method for text-based question matching with improved accuracy."""
        mappings = []

        # Simple text preprocessing function without NLTK dependency
        def preprocess_text(text):
            if not text:
                return []
            # Convert to lowercase
            text = text.lower()
            # Remove special characters and digits
            text = re.sub(r'[^\w\s]', ' ', text)
            text = re.sub(r'\d+', ' ', text)
            # Split into words
            words = text.split()
            # Remove common stopwords
            common_stopwords = {'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you',
                              "you're", "you've", "you'll", "you'd", 'your', 'yours', 'yourself',
                              'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her',
                              'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them',
                              'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom',
                              'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was',
                              'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do',
                              'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or',
                              'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with',
                              'about', 'against', 'between', 'into', 'through', 'during', 'before',
                              'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out',
                              'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once'}
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
                magnitude1 += tf1 ** 2
                magnitude2 += tf2 ** 2

            # Prevent division by zero
            if magnitude1 == 0 or magnitude2 == 0:
                return 0

            return dot_product / ((magnitude1 ** 0.5) * (magnitude2 ** 0.5))

        # Preprocess all guide items and submission items
        guide_tokens = {}
        submission_tokens = {}

        for guide_item in guide_items:
            guide_text = guide_item.get('text', '')
            guide_tokens[guide_item.get('id')] = preprocess_text(guide_text)

        for submission_item in submission_items:
            submission_text = submission_item.get('text', '')
            submission_tokens[submission_item.get('id')] = preprocess_text(submission_text)

        # For each guide item, find the best match in submission items
        for guide_item in guide_items:
            guide_id = guide_item.get('id')
            guide_text_tokens = guide_tokens[guide_id]

            best_score = 0
            best_match = None

            for submission_item in submission_items:
                # Skip if already mapped
                if any(m.get('submission_id') == submission_item.get('id') for m in mappings):
                    continue

                submission_id = submission_item.get('id')
                submission_text_tokens = submission_tokens[submission_id]

                # Calculate similarity scores
                jaccard_score = jaccard_similarity(guide_text_tokens, submission_text_tokens)
                cosine_score = cosine_similarity_tokens(guide_text_tokens, submission_text_tokens)

                # Combine scores (weighted average favoring cosine similarity)
                combined_score = (0.3 * jaccard_score) + (0.7 * cosine_score)

                # Check exact ID match (e.g., "Question 1" matching with "1.")
                guide_id_match = re.search(r'(\d+)', guide_item.get('text', ''))
                submission_id_match = re.search(r'(\d+)', submission_item.get('text', ''))

                if guide_id_match and submission_id_match:
                    if guide_id_match.group(1) == submission_id_match.group(1):
                        # Boost score for ID match
                        combined_score = max(combined_score, 0.6)

                # Also match by guide answer and submission answer if available
                if guide_item.get('answer') and submission_item.get('answer'):
                    guide_answer_tokens = preprocess_text(guide_item.get('answer', ''))
                    submission_answer_tokens = preprocess_text(submission_item.get('answer', ''))

                    answer_jaccard = jaccard_similarity(guide_answer_tokens, submission_answer_tokens)
                    answer_cosine = cosine_similarity_tokens(guide_answer_tokens, submission_answer_tokens)

                    # Calculate a more detailed answer similarity score
                    answer_score = (0.3 * answer_jaccard) + (0.7 * answer_cosine)

                    # Calculate keyword match score
                    guide_keywords = self._extract_keywords(guide_item.get('answer', ''))
                    submission_keywords = self._extract_keywords(submission_item.get('answer', ''))

                    # Calculate keyword match percentage
                    keyword_matches = [kw for kw in guide_keywords if any(kw.lower() in sub_kw.lower() for sub_kw in submission_keywords)]
                    keyword_score = len(keyword_matches) / max(len(guide_keywords), 1) if guide_keywords else 0

                    # Generate reason for match based on keywords
                    match_reason = f"Matched {len(keyword_matches)} of {len(guide_keywords)} key concepts"
                    if keyword_matches:
                        match_reason += f": {', '.join(keyword_matches[:3])}"
                        if len(keyword_matches) > 3:
                            match_reason += f" and {len(keyword_matches) - 3} more"

                    # Store the answer score for later use in grading
                    submission_item['answer_score'] = answer_score
                    submission_item['keyword_score'] = keyword_score
                    submission_item['match_reason'] = match_reason

                    # Consider answer similarity in overall score with higher weight
                    combined_score = (0.5 * combined_score) + (0.3 * answer_score) + (0.2 * keyword_score)

                if combined_score > best_score:
                    best_score = combined_score
                    best_match = (submission_item, combined_score)

            if best_match and best_score > 0.2:  # Only map if similarity exceeds threshold
                submission_item, match_score = best_match

                # Get the match reason if available
                match_reason = submission_item.get('match_reason', "")
                if not match_reason:
                    match_reason = f"Similarity score: {match_score:.2f}"

                # Get the answer score if available
                answer_score = submission_item.get('answer_score', 0)
                keyword_score = submission_item.get('keyword_score', 0)

                # Calculate a grade based on similarity
                grade_score = 0
                if guide_item.get('max_score'):
                    # Use answer_score with higher weight if available
                    if answer_score > 0:
                        grade_score = (0.6 * answer_score + 0.4 * keyword_score) * float(guide_item.get('max_score'))
                    else:
                        grade_score = match_score * float(guide_item.get('max_score'))
                    grade_score = round(grade_score, 1)

                mappings.append({
                    "guide_id": guide_item.get('id'),
                    "guide_text": guide_item.get('text'),
                    "guide_answer": guide_item.get('answer', ''),
                    "max_score": guide_item.get('max_score'),  # No default value
                    "submission_id": submission_item.get('id'),
                    "submission_text": submission_item.get('text'),
                    "submission_answer": submission_item.get('answer', ''),
                    "match_score": match_score,
                    "answer_score": answer_score,
                    "keyword_score": keyword_score,
                    "grade_score": grade_score,
                    "match_reason": match_reason
                })

        return mappings
