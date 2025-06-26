"""
Grading Service for grading student submissions.
This service grades student submissions by comparing their answers to the solutions in the marking guide.
"""

import json
import os
import re
from utils.logger import logger

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import logger


class GradingService:
    """
    Grading service that evaluates student submissions by comparing answers to solutions.
    The score is determined by how closely the submission answers match the marking guide answers.
    """

    def __init__(self, llm_service=None, mapping_service=None):
        """Initialize with optional LLM and mapping services."""
        self.llm_service = llm_service
        self.mapping_service = mapping_service

    def grade_submission(
        self,
        marking_guide_content: str,
        student_submission_content: str,
        mapped_questions: Optional[List[Dict]] = None,
        guide_type: Optional[str] = None,
    ) -> Tuple[Dict, Optional[str]]:
        """
        Grade a student submission against a marking guide.

        Args:
            marking_guide_content: Text content of the marking guide
            student_submission_content: Text content of the student submission
            mapped_questions: Optional list of pre-mapped questions and answers.
            guide_type: Optional type of the guide (e.g., "questions", "answers").

        Returns:
            Tuple[Dict, Optional[str]]: (Grading result, Error message if any)
        """
        if not isinstance(marking_guide_content, dict):
            logger.error(f"TypeError: marking_guide_content is not a dictionary. Type: {type(marking_guide_content)}")
            return {}, "Invalid marking guide content: Expected a dictionary."
        marking_guide_data = marking_guide_content

        # Determine guide type if not provided
        if guide_type is None and self.mapping_service:
            guide_type, _ = self.mapping_service.determine_guide_type(marking_guide_data.get("raw_content", ""))

        # Extract answers from student submission content using mapping service
        # This assumes student_submission_content is raw text, not JSON
        if self.mapping_service:
            parsed_student_submission = self.mapping_service.extract_questions_and_answers(student_submission_content)
            if not parsed_student_submission:
                logger.warning(f"No answers extracted from student submission content. Content: {student_submission_content[:200]}...")
                return {}, "Could not extract answers from student submission."
        else:
            # Fallback if mapping service is not available, instantiate one to extract answers
            logger.warning("Mapping service not initialized. Instantiating a temporary MappingService to extract answers.")
            from src.services.mapping_service import MappingService
            temp_mapping_service = MappingService(llm_service=self.llm_service) # Pass LLM service if available
            parsed_student_submission = temp_mapping_service.extract_questions_and_answers(student_submission_content)
            if not parsed_student_submission:
                logger.warning(f"No answers extracted from student submission content using temporary mapping service. Content: {student_submission_content[:200]}...")
                return {}, "Could not extract answers from student submission using fallback mapping service."

        # Extract raw_content from marking_guide_data if it's a dictionary
        if isinstance(marking_guide_data, dict):
            marking_guide_raw_content = marking_guide_data.get("raw_content", "")
        else:
            marking_guide_raw_content = marking_guide_data # Fallback if it's somehow not a dict

        return self.grade_answers(
            marking_guide_raw_content,
            parsed_student_submission,
            mapped_questions=mapped_questions,
            guide_type=guide_type,
        )

    def grade_answers(
        self,
        guide_data: str, # Now expects raw content string
        student_answers: List[Dict],
        mapped_questions: Optional[List[Dict]] = None,
        guide_type: Optional[str] = None,
    ) -> Tuple[Dict, Optional[str]]:
        """
        Grade a student submission against a marking guide.

        Args:
            marking_guide_content: Text content of the marking guide
            student_submission_content: Text content of the student submission

        Returns:
            Tuple[Dict, Optional[str]]: (Grading result, Error message if any)
        """
        try:
            if mapped_questions is not None:
                mappings = mapped_questions
                # If guide_type is not provided, try to infer from guide_data
                # This part needs to be adjusted as guide_data is now a string
                # For now, we'll assume guide_type is passed or defaults to 'unknown'
                if guide_type is None:
                    guide_type = "unknown"
                mapping_result = {"mappings": mappings, "metadata": {"guide_type": guide_type}}
            else:
                # Use mapping service to match questions and answers
                # Ensure marking_guide_content and student_submission_content are passed
                # These are not directly available in grade_answers, so we need to reconstruct them
                # from guide_data and student_answers if mapping_service is used here.
                # However, the current flow passes raw content to grade_submission, which then calls grade_answers.
                # So, we need to ensure the mapping service receives the correct input.
                # For now, assuming guide_data and student_answers are sufficient for mapping service if it's called directly.
                # This part might need adjustment based on how mapping_service.map_submission_to_guide expects its input.

                # marking_guide_content is already the raw content string
                marking_guide_content = guide_data
                student_submission_content = json.dumps(student_answers)

                if self.mapping_service:
                    mapping_result, mapping_error = (
                        self.mapping_service.map_submission_to_guide(
                            marking_guide_content, student_submission_content
                        )
                    )

                    if mapping_error:
                        return {
                            "status": "error",
                            "message": f"Mapping error: {mapping_error}",
                        }, mapping_error

                    mappings = mapping_result.get("mappings", [])
                else:
                    # Initialize mapping service if none was provided
                    from src.services.mapping_service import MappingService

                    temp_mapping_service = MappingService()
                    mapping_result, mapping_error = (
                        temp_mapping_service.map_submission_to_guide(
                            marking_guide_content, student_submission_content
                        )
                    )

                    if mapping_error:
                        return {
                            "status": "error",
                            "message": f"Mapping error: {mapping_error}",
                        }, mapping_error

                    mappings = mapping_result.get("mappings", [])

            # Grade each mapped question
            overall_score = 0
            max_possible_score = 0
            criteria_scores = []
            strengths = []
            weaknesses = []
            improvement_suggestions = []

            # Get guide type from mapping result
            guide_type = mapping_result.get("metadata", {}).get("guide_type", "unknown")
            logger.info(f"Grading submission with guide type: {guide_type}")

            for mapping in mappings:
                guide_text = mapping.get("guide_text", "")
                guide_answer = mapping.get("guide_answer", "")
                submission_text = mapping.get("submission_text", "")
                submission_answer = mapping.get("submission_answer", "")
                max_score = mapping.get("max_score")
                match_score = mapping.get("match_score", 0.5)
                match_reason = mapping.get("match_reason", "")

                # Use default max score if not specified
                if max_score is None:
                    max_score = 10
                    logger.warning(
                        f"No max score specified for question, using default: {guide_text[:50]}..."
                    )

                # For question-based guides, use submission_text as the answer if submission_answer is empty
                if (
                    guide_type == "questions"
                    and not submission_answer
                    and submission_text
                ):
                    submission_answer = submission_text

                # For answer-based guides, use guide_text as the answer if guide_answer is empty
                if guide_type == "answers" and not guide_answer and guide_text:
                    guide_answer = guide_text

                # Skip if no guide text/answer or submission text/answer
                if (not guide_text and not guide_answer) or (
                    not submission_text and not submission_answer
                ):
                    logger.warning(
                        f"Skipping question due to missing content: {guide_text[:50]}..."
                    )
                    continue

                # Use LLM for comparison if available
                if self.llm_service:
                    try:
                        # Use LLM to compare answers with improved system prompt
                        system_prompt = """
                        You are an expert educational grader with years of experience in assessing student work.
                        Your task is to evaluate a student's answer against a model answer from a marking guide.

                        Evaluate the student's answer based on the following criteria:
                        1. Content Accuracy (40%): Correctness of facts, concepts, or procedures
                        2. Completeness (30%): Inclusion of all required information or steps
                        3. Understanding (20%): Demonstrated comprehension of underlying principles
                        4. Clarity (10%): Clear and coherent expression of ideas

                        IMPORTANT GUIDELINES:
                        - Be fair and objective in your assessment
                        - Consider partial credit for partially correct answers
                        - Identify specific points where the student's answer matches or differs from the model answer
                        - Provide constructive feedback that helps the student understand what they did well and what they missed
                        - Your feedback should be specific and directly reference the student's response
                        - Look for semantic similarity, not just exact word matches
                        - Consider alternative correct approaches that might differ from the model answer
                        - Be lenient on minor formatting differences or slight wording variations
                        - Focus on how closely the student's answer matches the model answer in terms of content and understanding
                        - Evaluate the quality and correctness of the student's response, not just the presence of keywords

                        Output in JSON format:
                        {
                            "score": <numeric_score>,
                            "percentage": <percent_of_max_score>,
                            "feedback": "<detailed_feedback_with_specifics>",
                            "strengths": ["<specific_strength1>", "<specific_strength2>", ...],
                            "weaknesses": ["<specific_weakness1>", "<specific_weakness2>", ...],
                            "improvement_suggestions": ["<specific_suggestion1>", "<specific_suggestion2>", ...],
                            "key_points": {
                                "matched": ["<specific_point1>", "<specific_point2>", ...],
                                "missed": ["<specific_point1>", "<specific_point2>", ...],
                                "partially_matched": ["<specific_point1>", "<specific_point2>", ...]
                            },
                            "grading_breakdown": {
                                "content_accuracy": {
                                    "score": <0-10>,
                                    "comments": "<specific_comments>"
                                },
                                "completeness": {
                                    "score": <0-10>,
                                    "comments": "<specific_comments>"
                                },
                                "understanding": {
                                    "score": <0-10>,
                                    "comments": "<specific_comments>"
                                },
                                "clarity": {
                                    "score": <0-10>,
                                    "comments": "<specific_comments>"
                                }
                            }
                        }
                        """

                        # Include match score and reason from mapping service in the prompt
                        match_info = ""
                        if match_score > 0:
                            match_info = f"""
                        The mapping service has already analyzed this answer and assigned a match score of {match_score:.2f} (on a scale of 0-1).
                        Reason for the match: {match_reason}

                        Please consider this match score in your evaluation, but make your own assessment based on the content.
                        """

                        user_prompt = f"""
                        Question: {guide_text}

                        Model Answer from Marking Guide:
                        {guide_answer}

                        Student's Answer:
                        {submission_answer}

                        Maximum Score: {max_score}

                        {match_info}

                        Please evaluate how closely the student's answer matches the model answer and assign a score out of {max_score}.
                        Focus on semantic similarity and conceptual understanding rather than exact wording.
                        Consider both the content accuracy and the demonstrated understanding.
                        Provide detailed feedback explaining your scoring.
                        """

                        logger.info(
                            f"Sending grading request to LLM for question: {guide_text[:50]}..."
                        )

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
                                temperature=0.1,  # Slightly more variability for nuanced judgments
                                response_format={"type": "json_object"},
                            )
                        else:
                            # For models that don't support JSON response format
                            modified_system_prompt = (
                                system_prompt
                                + """
                            IMPORTANT: Your response must be valid JSON. Format your entire response as a JSON object.
                            Do not include any text before or after the JSON object.
                            """
                            )
                            response = self.llm_service.client.chat.completions.create(
                                model=self.llm_service.model,
                                messages=[
                                    {
                                        "role": "system",
                                        "content": modified_system_prompt,
                                    },
                                    {"role": "user", "content": user_prompt},
                                ],
                                temperature=0.1,  # Slightly more variability for nuanced judgments
                            )

                        # Validate response structure first
                        if not hasattr(response, 'choices') or len(response.choices) == 0:
                            logger.error("No response choices received from LLM")
                            raise Exception("No response choices received from LLM")

                        result = response.choices[0].message.content

                        # Validate response content
                        if not result or not result.strip():
                            logger.error("Empty response received from LLM")
                            raise Exception("Empty response received from LLM")

                        logger.debug(f"Raw LLM response: {result[:200]}...")

                        # Enhanced JSON parsing with fallback
                        try:
                            # Try direct JSON parsing first
                            parsed = json.loads(result)
                        except json.JSONDecodeError as json_error:
                            logger.warning(f"Direct JSON parsing failed: {str(json_error)}")

                            # Try to extract JSON from the response
                            json_match = re.search(r'\{.*\}', result, re.DOTALL)
                            if json_match:
                                try:
                                    parsed = json.loads(json_match.group(0))
                                    logger.info("Successfully extracted JSON from response")
                                except json.JSONDecodeError:
                                    logger.warning("JSON extraction also failed, using manual extraction")
                                    # Manual extraction fallback
                                    score_match = re.search(r'(?:score|points?)[:\s]*(\d+(?:\.\d+)?)', result, re.IGNORECASE)
                                    score = float(score_match.group(1)) if score_match else 0
                                    parsed = {
                                        "score": score,
                                        "feedback": result.strip(),
                                        "extraction_method": "manual"
                                    }
                            else:
                                logger.warning("No JSON found in response, using manual extraction")
                                # Manual extraction fallback
                                score_match = re.search(r'(?:score|points?)[:\s]*(\d+(?:\.\d+)?)', result, re.IGNORECASE)
                                score = float(score_match.group(1)) if score_match else 0
                                parsed = {
                                    "score": score,
                                    "feedback": result.strip(),
                                    "extraction_method": "manual"
                                }

                        # Extract detailed grading information with safe defaults
                        score = float(parsed.get("score", 0))

                        # Ensure score doesn't exceed max_score
                        score = min(score, max_score)

                        feedback = parsed.get("feedback", "")
                        question_strengths = parsed.get("strengths", [])
                        question_weaknesses = parsed.get("weaknesses", [])
                        question_suggestions = parsed.get("improvement_suggestions", [])

                        # Get key points information
                        key_points = parsed.get("key_points", {})
                        matched_points = key_points.get("matched", [])
                        missed_points = key_points.get("missed", [])
                        partial_points = key_points.get("partially_matched", [])

                        # Get detailed breakdown
                        grading_breakdown = parsed.get("grading_breakdown", {})

                        # Add extraction method info if manual extraction was used
                        if parsed.get("extraction_method") == "manual":
                            feedback = f"[Manual extraction] {feedback}"

                        # Add to overall strengths and weaknesses
                        strengths.extend(question_strengths)
                        weaknesses.extend(question_weaknesses)
                        improvement_suggestions.extend(question_suggestions)

                        # Create detailed feedback incorporating the breakdown
                        detailed_feedback = {
                            "general": feedback,
                            "key_points": {
                                "matched": matched_points,
                                "missed": missed_points,
                                "partially_matched": partial_points,
                            },
                            "breakdown": grading_breakdown,
                        }

                        logger.info(f"LLM grading complete. Score: {score}/{max_score}")

                    except Exception as e:
                        logger.warning(
                            f"LLM grading failed, falling back to similarity: {str(e)}"
                        )
                        # Fall back to similarity scoring
                        similarity = self._enhanced_similarity_score(
                            guide_answer, submission_answer
                        )
                        score = round(similarity * max_score, 1)
                        feedback = (
                            f"Graded based on text similarity (LLM error: {str(e)})"
                        )
                        detailed_feedback = {"general": feedback}
                else:
                    # Use enhanced similarity scoring
                    similarity = self._enhanced_similarity_score(
                        guide_answer, submission_answer
                    )
                    score = round(similarity * max_score, 1)
                    feedback = "Graded based on text similarity"
                    detailed_feedback = {"general": feedback}

                # Add to overall score
                overall_score += score
                max_possible_score += max_score

                # Check if we have a grade_score from the mapping service
                if "grade_score" in mapping and mapping["grade_score"] > 0:
                    # Use the grade_score from the mapping service
                    score = mapping["grade_score"]

                    # Add match reason to feedback if available
                    if "match_reason" in mapping and mapping["match_reason"]:
                        feedback = (
                            f"{feedback}\n\nMatch details: {mapping['match_reason']}"
                        )

                # Add to criteria scores
                criteria_scores.append(
                    {
                        "question_id": mapping.get("guide_id", ""),
                        "description": guide_text,
                        "points_earned": score,
                        "points_possible": max_score,
                        "similarity": score / max_score if max_score > 0 else 0,
                        "answer_score": mapping.get(
                            "answer_score", score / max_score if max_score > 0 else 0
                        ),
                        "keyword_score": mapping.get("keyword_score", 0),
                        "match_score": mapping.get("match_score", 0),
                        "feedback": feedback,
                        "detailed_feedback": detailed_feedback,
                        "guide_answer": guide_answer,
                        "student_answer": submission_answer,
                        "match_reason": mapping.get("match_reason", ""),
                    }
                )

            # Calculate percentage score
            percent_score = (
                (overall_score / max_possible_score * 100)
                if max_possible_score > 0
                else 0
            )

            # Normalize the overall score to be out of 100
            normalized_score = (
                percent_score  # This is already the percentage out of 100
            )

            # Assign letter grade based on percentage
            letter_grade = self._get_letter_grade(percent_score)

            # Create result
            result = {
                "status": "success",
                "overall_score": round(
                    overall_score, 1
                ),  # Original score (sum of all points)
                "max_possible_score": max_possible_score,  # Original max possible score
                "normalized_score": round(
                    normalized_score, 1
                ),  # Score normalized to 100
                "percent_score": round(
                    percent_score, 1
                ),  # Same as normalized_score for backward compatibility
                "letter_grade": letter_grade,
                "criteria_scores": criteria_scores,
                "detailed_feedback": {
                    "strengths": list(set(strengths)),  # Remove duplicates
                    "weaknesses": list(set(weaknesses)),  # Remove duplicates
                    "improvement_suggestions": list(
                        set(improvement_suggestions)
                    ),  # Remove duplicates
                },
                "metadata": {
                    "total_questions": len(criteria_scores),
                    "graded_at": datetime.now().isoformat(),
                    "grading_method": "LLM" if self.llm_service else "Similarity",
                    "guide_type": guide_type,
                    "total_marks_available": max_possible_score,
                    "unmapped_guide_count": len(
                        mapping_result.get("unmapped_guide_items", [])
                    ),
                    "unmapped_submission_count": len(
                        mapping_result.get("unmapped_submission_items", [])
                    ),
                },
            }

            return result, None

        except Exception as e:
            error_message = f"Error in grading service: {str(e)}"
            logger.error(error_message)
            return {"status": "error", "message": error_message}, error_message

    def _enhanced_similarity_score(
        self, guide_answer: str, submission_answer: str
    ) -> float:
        """
        Calculate an enhanced similarity score between the guide answer and submission answer.
        This method uses multiple metrics to get a more accurate similarity.

        Returns:
            float: Similarity score between 0.0 and 1.0
        """
        if not guide_answer or not submission_answer:
            return 0.0

        # Remove punctuation and convert to lowercase for comparison
        guide_clean = re.sub(r"[^\w\s]", "", guide_answer.lower())
        submission_clean = re.sub(r"[^\w\s]", "", submission_answer.lower())

        # Split into words
        guide_words = guide_clean.split()
        submission_words = submission_clean.split()

        if not guide_words:
            return 0.0

        # Calculate word overlap (Jaccard similarity)
        guide_set = set(guide_words)
        submission_set = set(submission_words)

        intersection = len(guide_set.intersection(submission_set))
        union = len(guide_set.union(submission_set))

        jaccard_score = intersection / union if union > 0 else 0.0

        # Calculate word order similarity (simple approach)
        # Count sequences of words that appear in the same order
        sequence_matches = 0
        max_sequence_length = min(len(guide_words), len(submission_words))

        for i in range(1, 4):  # Check sequences of length 1, 2, and 3
            if i > max_sequence_length:
                break

            guide_sequences = set()
            for j in range(len(guide_words) - i + 1):
                guide_sequences.add(" ".join(guide_words[j : j + i]))

            submission_sequences = set()
            for j in range(len(submission_words) - i + 1):
                submission_sequences.add(" ".join(submission_words[j : j + i]))

            sequence_matches += len(
                guide_sequences.intersection(submission_sequences)
            ) / (i * 2)

        sequence_score = sequence_matches / max(len(guide_words), 1)

        # Calculate length ratio as a penalty for answers that are too short
        length_ratio = min(len(submission_words) / max(len(guide_words), 1), 1.0)

        # Keyword importance - check if important words are present
        # This is a simple approach; in a real-world scenario, you might extract keywords using NLP
        important_words = set()
        for word in guide_words:
            if len(word) > 5 or word.lower() not in {
                "and",
                "the",
                "is",
                "are",
                "that",
                "this",
                "with",
                "for",
                "from",
            }:
                important_words.add(word)

        important_word_match = len(important_words.intersection(submission_set)) / max(
            len(important_words), 1
        )

        # Combine the scores with appropriate weights
        combined_score = (
            (0.4 * jaccard_score)  # Word overlap
            + (0.3 * sequence_score)  # Word order
            + (0.2 * important_word_match)  # Important words
            + (0.1 * length_ratio)  # Length penalty
        )

        return min(max(combined_score, 0.0), 1.0)  # Ensure score is between 0 and 1

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

    def save_grading_result(
        self, grading_result: Dict, output_path: str, filename: str = None
    ) -> str:
        """
        Save grading results to a file.

        Args:
            grading_result: The grading result dictionary
            output_path: Directory to save the result
            filename: Optional filename (generated if not provided)

        Returns:
            str: Path to the saved file
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)

        # Generate a unique filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"grading_result_{timestamp}.json"

        # Ensure the filename has a .json extension
        if not filename.endswith(".json"):
            filename += ".json"

        # Full path to the output file
        output_file = Path(output_path) / filename

        # Save the result as JSON
        with open(output_file, "w") as f:
            json.dump(grading_result, f, indent=2)

        return str(output_file)

    def grade_multiple_submissions(
        self,
        marking_guide_content: str,
        submissions: List[Dict[str, str]],
        batch_size: int = 5
    ) -> List[Tuple[Dict, Optional[str]]]:
        """
        Grade multiple submissions with optimized batch processing.

        Args:
            marking_guide_content: The marking guide content
            submissions: List of submission dictionaries with 'content' key
            batch_size: Number of submissions to process in parallel

        Returns:
            List of (grading_result, error_message) tuples
        """
        results = []

        logger.info(f"Starting batch grading of {len(submissions)} submissions")

        # Process submissions in batches for better performance
        for i in range(0, len(submissions), batch_size):
            batch = submissions[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}/{(len(submissions) + batch_size - 1) // batch_size}")

            batch_results = []
            for submission in batch:
                try:
                    result, error = self.grade_submission(
                        marking_guide_content,
                        submission.get('content', '')
                    )
                    batch_results.append((result, error))
                except Exception as e:
                    logger.error(f"Error grading submission: {str(e)}")
                    batch_results.append((
                        {"status": "error", "message": str(e)},
                        str(e)
                    ))

            results.extend(batch_results)

            # Small delay between batches to avoid overwhelming the API
            if i + batch_size < len(submissions):
                import time
                time.sleep(0.5)

        logger.info(f"Completed batch grading of {len(submissions)} submissions")
        return results

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics from the LLM service."""
        if self.llm_service and hasattr(self.llm_service, 'get_cache_stats'):
            return {
                "llm_cache_stats": self.llm_service.get_cache_stats(),
                "grading_service": "active"
            }
        return {"grading_service": "active", "llm_cache_stats": "not_available"}
