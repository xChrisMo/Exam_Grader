"""Consolidated Grading Service merging GradingService and OptimizedGradingService.

This module provides a unified grading service that combines the functionality of all
grading services with integration to the base service architecture.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.services.base_service import BaseService, ServiceStatus
from utils.logger import logger


class ConsolidatedGradingService(BaseService):
    """Consolidated grading service with enhanced functionality and base service integration."""

    def __init__(
        self,
        llm_service=None,
        mapping_service=None,
        max_batch_size: int = 8,
        chunk_size: int = 3000,
        cache_size: int = 1000,
        cache_ttl: int = 3600,  # 1 hour
    ):
        """Initialize the consolidated grading service.

        Args:
            llm_service: LLM service instance for intelligent grading
            mapping_service: Mapping service for question-answer mapping
            max_batch_size: Maximum number of Q&A pairs to process at once
            chunk_size: Maximum characters per LLM call
            cache_size: Maximum number of cached grading results
            cache_ttl: Cache time-to-live in seconds
        """
        super().__init__("consolidated_grading_service")

        self.llm_service = llm_service
        self.mapping_service = mapping_service
        self.max_batch_size = max_batch_size
        self.chunk_size = chunk_size
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl

        self._grading_cache = {}
        self._cache_timestamps = {}

        # Set initial status
        self.status = ServiceStatus.HEALTHY if llm_service else ServiceStatus.DEGRADED

    async def initialize(self) -> bool:
        """Initialize the grading service."""
        try:
            with self.track_request("initialize"):
                if self.llm_service:
                    # Test LLM service availability
                    if (
                        hasattr(self.llm_service, "is_available")
                        and self.llm_service.is_available()
                    ):
                        self.status = ServiceStatus.HEALTHY
                        logger.info("Grading service initialized with LLM support")
                    else:
                        self.status = ServiceStatus.DEGRADED
                        logger.warning(
                            "Grading service initialized with degraded LLM support"
                        )
                else:
                    self.status = ServiceStatus.DEGRADED
                    logger.warning("Grading service initialized without LLM support")

                return True

        except Exception as e:
            self.status = ServiceStatus.UNHEALTHY
            logger.error(f"Failed to initialize grading service: {str(e)}")
            return False

    async def health_check(self) -> bool:
        """Perform health check."""
        try:
            if self.llm_service and hasattr(self.llm_service, "is_available"):
                return self.llm_service.is_available()
            return self.status != ServiceStatus.UNHEALTHY

        except Exception as e:
            logger.error(f"Grading service health check failed: {str(e)}")
            return False

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clear caches
            self._grading_cache.clear()
            self._cache_timestamps.clear()

            logger.info("Grading service cleanup completed")

        except Exception as e:
            logger.error(f"Error during grading service cleanup: {str(e)}")

    def _get_cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        return str(hash(str(args)))

    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if valid."""
        if cache_key in self._grading_cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self.cache_ttl:
                self.metrics.add_custom_metric("cache_hits", 1)
                return self._grading_cache[cache_key]
            else:
                # Remove expired entry
                del self._grading_cache[cache_key]
                del self._cache_timestamps[cache_key]

        self.metrics.add_custom_metric("cache_misses", 1)
        return None

    def _cache_result(self, cache_key: str, result: Any) -> None:
        """Cache result with size limit."""
        if len(self._grading_cache) >= self.cache_size:
            oldest_key = min(
                self._cache_timestamps.keys(), key=lambda k: self._cache_timestamps[k]
            )
            del self._grading_cache[oldest_key]
            del self._cache_timestamps[oldest_key]

        self._grading_cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()

    def grade_submission(
        self,
        marking_guide_content: str,
        student_submission_content: str,
        mapped_questions: Optional[List[Dict]] = None,
        guide_type: Optional[str] = None,
    ) -> Tuple[Dict, Optional[str]]:
        """Grade a student submission against a marking guide.

        Args:
            marking_guide_content: Text content of the marking guide
            student_submission_content: Text content of the student submission
            mapped_questions: Optional list of pre-mapped questions and answers
            guide_type: Optional type of the guide (e.g., "questions", "answers")

        Returns:
            Tuple[Dict, Optional[str]]: (Grading result, Error message if any)
        """
        try:
            with self.track_request("grade_submission"):
                # Check cache first
                cache_key = self._get_cache_key(
                    marking_guide_content[:1000],
                    student_submission_content[:1000],
                    str(mapped_questions)[:500] if mapped_questions else "",
                    guide_type or "",
                )
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result

                if isinstance(marking_guide_content, dict):
                    marking_guide_data = marking_guide_content
                    marking_guide_text = marking_guide_data.get("content", "")
                else:
                    marking_guide_text = str(marking_guide_content)
                    marking_guide_data = {"content": marking_guide_text}

                if not mapped_questions:
                    mapped_questions = self._get_mapped_questions(
                        marking_guide_text, student_submission_content
                    )

                if not mapped_questions:
                    error_msg = "No questions could be mapped from the submission"
                    result = ({"error": error_msg}, error_msg)
                    self._cache_result(cache_key, result)
                    return result

                grading_result = self.grade_submission_batch(
                    mapped_questions, marking_guide_text
                )

                result = (grading_result, None)
                self._cache_result(cache_key, result)
                return result

        except Exception as e:
            error_msg = f"Grading failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}, error_msg

    def grade_submission_batch(
        self, mapped_qa_pairs: List[Dict], marking_guide: str = ""
    ) -> Dict[str, Any]:
        """Grade multiple Q&A pairs efficiently in batches."""
        if not mapped_qa_pairs:
            return {
                "total_score": 0,
                "percentage": 0,
                "letter_grade": "F",
                "detailed_grades": [],
                "summary": {"total_questions": 0, "average_score": 0},
            }

        try:
            with self.track_request("grade_batch"):
                all_grades = []

                for i in range(0, len(mapped_qa_pairs), self.max_batch_size):
                    batch = mapped_qa_pairs[i : i + self.max_batch_size]
                    batch_grades = self._grade_batch_llm(batch, marking_guide)

                    if batch_grades:
                        all_grades.extend(batch_grades)
                    else:
                        # Fallback to individual grading
                        for qa_pair in batch:
                            grade = self._grade_single_qa_pair(qa_pair, marking_guide)
                            all_grades.append(grade)

                # Calculate overall results
                return self._calculate_final_results(all_grades)

        except Exception as e:
            logger.error(f"Batch grading failed: {str(e)}")
            # Fallback to individual grading
            return self._fallback_individual_grading(mapped_qa_pairs, marking_guide)

    def _get_mapped_questions(self, marking_guide: str, submission: str) -> List[Dict]:
        """Get mapped questions using mapping service or fallback."""
        try:
            if self.mapping_service:
                mapping_result, _ = self.mapping_service.map_submission_to_guide(
                    marking_guide, submission
                )
                return mapping_result.get("mappings", [])
            else:
                # Fallback: create temporary mapping service
                from src.services.consolidated_mapping_service import (
                    ConsolidatedMappingService,
                )

                temp_mapping_service = ConsolidatedMappingService(
                    llm_service=self.llm_service
                )
                mapping_result, _ = temp_mapping_service.map_submission_to_guide(
                    marking_guide, submission
                )
                return mapping_result.get("mappings", [])

        except Exception as e:
            logger.error(f"Mapping failed: {str(e)}")
            return []

    def _grade_batch_llm(
        self, qa_pairs: List[Dict], marking_guide: str
    ) -> Optional[List[Dict]]:
        """Grade a batch of Q&A pairs using LLM with timeout handling."""
        if not self.llm_service or not qa_pairs:
            return None

        try:
            system_prompt, user_prompt = self._create_deterministic_grading_prompt(
                qa_pairs, marking_guide
            )

            # Add timeout handling for LLM requests
            import signal
            import time
            
            def timeout_handler(signum, frame):
                raise TimeoutError("LLM grading request timed out")
            
            # Set timeout for LLM request (5 minutes)
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(300)  # 5 minutes timeout
            
            try:
                logger.info(f"Starting LLM grading for {len(qa_pairs)} questions...")
                start_time = time.time()
                
                response = self.llm_service.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.0,  # Fully deterministic for consistency
                    use_cache=True    # Enable caching for identical inputs
                )
                
                elapsed_time = time.time() - start_time
                logger.info(f"LLM grading completed in {elapsed_time:.2f} seconds")
                
                return self._parse_grading_response(response, qa_pairs)
                
            finally:
                # Reset alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        except TimeoutError as e:
            logger.error(f"LLM grading timed out after 5 minutes: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"LLM batch grading failed: {str(e)}")
            return None

    def _create_deterministic_grading_prompt(
        self, qa_pairs: List[Dict], marking_guide: str
    ) -> Tuple[str, str]:
        """Create optimized, deterministic prompt for grading multiple Q&A pairs."""
        system_prompt = """You are an expert exam grader. Grade student answers efficiently and consistently.

GRADING RULES:
1. Score each answer from 0 to the maximum score specified for that question
2. Provide concise feedback (max 50 words per answer)
3. Be consistent and fair across all answers
4. Focus on key concepts and accuracy
5. Return structured JSON output only

SCORING GUIDELINES:
- Award full marks for complete, accurate answers
- Deduct points proportionally for errors, omissions, or incomplete responses
- Consider partial credit for partially correct answers
- Use the full range from 0 to max_score for each question

Output JSON format:
{
  "grades": [
    {
      "question_id": "Q1",
      "score": 8.5,
      "max_score": 10,
      "feedback": "Good understanding but missing key detail about..."
    }
  ]
}"""

        # Prepare marking guide excerpt
        guide_excerpt = (
            marking_guide[:800]
            if marking_guide
            else "No specific marking guide provided."
        )

        user_prompt = f"""MARKING GUIDE:
{guide_excerpt}

GRADE THESE ANSWERS:
"""

        for i, qa in enumerate(qa_pairs, 1):
            question = qa.get("question_text", qa.get("question", f"Question {i}"))
            answer = qa.get(
                "answer_text", qa.get("student_answer", qa.get("answer", ""))
            )
            question_id = qa.get("question_id", f"Q{i}")
            max_score = qa.get("max_score")  # Extract from guide, no default
            if max_score is None:
                logger.warning(f"No max_score found for question {i}, guide may not be properly processed")
                max_score = 0.0  # Use 0 to indicate missing score

            user_prompt += f"""
{i}. ID: {question_id} (Max Score: {max_score} points)
Question: {question}
Student Answer: {answer}
"""

        return system_prompt, user_prompt

    def _parse_grading_response(
        self, response: str, qa_pairs: List[Dict]
    ) -> Optional[List[Dict]]:
        """Parse and validate LLM grading response."""
        try:
            # First attempt direct JSON parsing
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                if self.llm_service:
                    json_cleaning_prompt = f"""
Extract and clean the JSON from this response. Return only valid JSON:

{response[:1000]}

Return format: {{"grades": [...]}}
"""

                    cleaned_response = self.llm_service.generate_response(
                        system_prompt="You are a JSON extraction expert. Return only valid JSON.",
                        user_prompt=json_cleaning_prompt,
                        temperature=0.0,
                    )
                    result = json.loads(cleaned_response)
                else:
                    # Fallback: try to extract JSON using regex
                    import re

                    json_match = re.search(r"\{.*\}", response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                    else:
                        raise json.JSONDecodeError("No JSON found", response, 0)

            # Validate and clean grades
            grades = result.get("grades", [])
            validated_grades = []

            for i, grade in enumerate(grades):
                if i < len(qa_pairs):
                    validated_grade = self._validate_and_clean_grade(grade, qa_pairs[i])
                    validated_grades.append(validated_grade)

            # Fill missing grades with defaults
            while len(validated_grades) < len(qa_pairs):
                missing_qa = qa_pairs[len(validated_grades)]
                default_grade = {
                    "question_id": missing_qa.get(
                        "question_id", f"Q{len(validated_grades) + 1}"
                    ),
                    "score": 0,
                    "feedback": "No grade provided by LLM",
                }
                validated_grades.append(default_grade)

            return validated_grades

        except Exception as e:
            logger.error(f"Failed to parse grading response: {str(e)}")
            return None

    def _validate_and_clean_grade(self, grade: Dict, qa_pair: Dict) -> Dict:
        """Validate and clean individual grade."""
        # Get max score from qa_pair or grade - NO DEFAULT
        max_score = qa_pair.get("max_score") or grade.get("max_score")
        if max_score is None:
            logger.warning("No max_score found in grade validation, guide may not be properly processed")
            max_score = 0.0  # Use 0 to indicate missing score

        # Ensure required fields
        validated = {
            "question_id": grade.get(
                "question_id", qa_pair.get("question_id", "Unknown")
            ),
            "score": self._validate_score(grade.get("score", 0), max_score),
            "max_score": float(max_score),
            "feedback": self._clean_feedback(
                grade.get("feedback", "No feedback provided")
            ),
            "question_text": qa_pair.get("question_text", qa_pair.get("question", "")),
            "student_answer": qa_pair.get(
                "answer_text", qa_pair.get("student_answer", qa_pair.get("answer", ""))
            ),
        }

        return validated

    def _validate_score(self, score: Any, max_score: float = 100.0) -> float:
        """Validate and normalize score to 0-max_score range."""
        try:
            score = float(score)
            return max(0.0, min(max_score, round(score, 2)))
        except (ValueError, TypeError):
            return 0.0

    def _clean_feedback(self, feedback: str) -> str:
        """Clean and truncate feedback."""
        if not feedback or not isinstance(feedback, str):
            return "No feedback provided"

        # Truncate to reasonable length
        feedback = feedback.strip()[:200]
        return feedback if feedback else "No feedback provided"

    def _grade_single_qa_pair(self, qa_pair: Dict, marking_guide: str) -> Dict:
        """Grade a single Q&A pair as fallback."""
        max_score = qa_pair.get("max_score")
        if max_score is None:
            logger.warning("No max_score found for single Q&A grading, guide may not be properly processed")
            max_score = 0.0  # Use 0 to indicate missing score

        try:
            if self.llm_service:
                system_prompt = f"""Grade this single answer on a scale of 0-{max_score}. Provide brief feedback.

Return JSON format:
{{
  "score": 8.5,
  "max_score": {max_score},
  "feedback": "Good answer but missing..."
}}"""

                question = qa_pair.get("question_text", qa_pair.get("question", ""))
                answer = qa_pair.get(
                    "answer_text",
                    qa_pair.get("student_answer", qa_pair.get("answer", "")),
                )

                user_prompt = f"""Question: {question} (Max Score: {max_score} points)
Student Answer: {answer}
Marking Guide: {marking_guide[:500]}"""

                response = self.llm_service.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.0,  # Changed from 0.1 to 0.0 for full determinism
                )

                try:
                    result = json.loads(response)
                    return self._validate_and_clean_grade(result, qa_pair)
                except json.JSONDecodeError:
                    pass

            # LLM failed to score - return 0 with clear message
            return {
                "question_id": qa_pair.get("question_id", "Unknown"),
                "score": 0.0,
                "max_score": max_score,
                "feedback": "LLM failed to score submission",
                "question_text": qa_pair.get(
                    "question_text", qa_pair.get("question", "")
                ),
                "student_answer": qa_pair.get(
                    "answer_text",
                    qa_pair.get("student_answer", qa_pair.get("answer", "")),
                ),
            }

        except Exception as e:
            logger.error(f"Single Q&A grading failed: {str(e)}")
            return {
                "question_id": qa_pair.get("question_id", "Unknown"),
                "score": 0.0,
                "max_score": max_score,
                "feedback": f"Grading error: {str(e)}",
                "question_text": qa_pair.get(
                    "question_text", qa_pair.get("question", "")
                ),
                "student_answer": qa_pair.get(
                    "answer_text",
                    qa_pair.get("student_answer", qa_pair.get("answer", "")),
                ),
            }

    def _calculate_final_results(self, grades: List[Dict]) -> Dict[str, Any]:
        """Calculate final grading results from individual grades."""
        if not grades:
            return {
                "total_score": 0,
                "percentage": 0,
                "letter_grade": "F",
                "detailed_grades": [],
                "summary": {"total_questions": 0, "average_score": 0},
            }

        total_score = sum(grade.get("score", 0) for grade in grades)
        max_possible = 0.0
        for grade in grades:
            grade_max_score = grade.get("max_score")
            if grade_max_score is None:
                logger.warning("Grade missing max_score in final results calculation")
                grade_max_score = 0.0  # Use 0 instead of defaulting to 10
            max_possible += float(grade_max_score)
        
        percentage = (total_score / max_possible * 100) if max_possible > 0 else 0

        return {
            "total_score": round(total_score, 2),
            "max_possible_score": round(max_possible, 2),
            "percentage": round(percentage, 2),
            "letter_grade": self._calculate_letter_grade(percentage),
            "detailed_grades": grades,
            "summary": {
                "total_questions": len(grades),
                "average_score": round(total_score / len(grades), 2) if grades else 0,
                "graded_at": datetime.now().isoformat(),
            },
        }

    def _calculate_letter_grade(self, percentage: float) -> str:
        """Calculate letter grade from percentage."""
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"

    def _fallback_individual_grading(
        self, qa_pairs: List[Dict], marking_guide: str
    ) -> Dict[str, Any]:
        """Fallback to individual grading when batch processing fails."""
        logger.warning("Using fallback individual grading")

        grades = []
        for qa_pair in qa_pairs:
            grade = self._grade_single_qa_pair(qa_pair, marking_guide)
            grades.append(grade)

        return self._calculate_final_results(grades)

    def grade_submission_optimized(
        self, submission_content: str, marking_guide: str, mapped_data: Dict = None
    ) -> Dict[str, Any]:
        """Optimized single submission grading with optional pre-mapped data."""
        try:
            with self.track_request("grade_optimized"):
                if mapped_data and "mappings" in mapped_data:
                    qa_pairs = mapped_data["mappings"]
                else:
                    qa_pairs = self._get_mapped_questions(
                        marking_guide, submission_content
                    )

                if not qa_pairs:
                    logger.warning("No Q&A pairs available for grading")
                    return {
                        "total_score": 0,
                        "percentage": 0,
                        "letter_grade": "F",
                        "detailed_grades": [],
                        "summary": {
                            "total_questions": 0,
                            "average_score": 0,
                            "error": "No mappings found",
                        },
                    }

                return self.grade_submission_batch(qa_pairs, marking_guide)

        except Exception as e:
            logger.error(f"Optimized grading failed: {str(e)}")
            return {
                "total_score": 0,
                "percentage": 0,
                "letter_grade": "F",
                "detailed_grades": [],
                "summary": {"total_questions": 0, "average_score": 0, "error": str(e)},
            }

    def get_grading_stats(self) -> Dict[str, Any]:
        """Get grading performance statistics."""
        return {
            "max_batch_size": self.max_batch_size,
            "chunk_size": self.chunk_size,
            "cache_size": len(self._grading_cache),
            "max_cache_size": self.cache_size,
            "cache_ttl": self.cache_ttl,
            "cache_hits": self.metrics.custom_metrics.get("cache_hits", 0),
            "cache_misses": self.metrics.custom_metrics.get("cache_misses", 0),
            "llm_available": self.llm_service is not None,
            "mapping_available": self.mapping_service is not None,
            "total_requests": self.metrics.total_requests,
            "avg_response_time": self.metrics.avg_response_time,
        }

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._grading_cache.clear()
        self._cache_timestamps.clear()
        logger.info("Grading service caches cleared")


# Backward compatibility aliases
GradingService = ConsolidatedGradingService
OptimizedGradingService = ConsolidatedGradingService
