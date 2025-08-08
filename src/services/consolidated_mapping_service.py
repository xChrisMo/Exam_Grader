"""Consolidated Mapping Service merging MappingService, OptimizedMappingService, and EnhancedMappingService.

This module provides a unified mapping service that combines the functionality of all
mapping services with integration to the base service architecture.
"""

import json
import time
from typing import Any, Dict, Optional, Tuple

from src.services.base_service import BaseService, ServiceStatus
from utils.logger import logger


class ConsolidatedMappingService(BaseService):
    """Consolidated mapping service with enhanced functionality and base service integration."""

    def __init__(
        self,
        llm_service=None,
        batch_size: int = 10,
        cache_size: int = 500,
        cache_ttl: int = 1800,  # 30 minutes
    ):
        """Initialize the consolidated mapping service.

        Args:
            llm_service: LLM service instance for intelligent mapping
            batch_size: Number of Q&A pairs to process at once
            cache_size: Maximum number of cached mapping results
            cache_ttl: Cache time-to-live in seconds
        """
        super().__init__("consolidated_mapping_service")

        self.llm_service = llm_service
        self.batch_size = batch_size
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl

        self._mapping_cache = {}
        self._cache_timestamps = {}

        self._guide_type_cache = {}

        # Set initial status
        self.status = ServiceStatus.HEALTHY if llm_service else ServiceStatus.DEGRADED

    async def initialize(self) -> bool:
        """Initialize the mapping service."""
        try:
            with self.track_request("initialize"):
                if self.llm_service:
                    # Test LLM service availability
                    if (
                        hasattr(self.llm_service, "is_available")
                        and self.llm_service.is_available()
                    ):
                        self.status = ServiceStatus.HEALTHY
                        logger.info("Mapping service initialized with LLM support")
                    else:
                        self.status = ServiceStatus.DEGRADED
                        logger.warning(
                            "Mapping service initialized with degraded LLM support"
                        )
                else:
                    self.status = ServiceStatus.DEGRADED
                    logger.warning("Mapping service initialized without LLM support")

                return True

        except Exception as e:
            self.status = ServiceStatus.UNHEALTHY
            logger.error(f"Failed to initialize mapping service: {str(e)}")
            return False

    async def health_check(self) -> bool:
        """Perform health check."""
        try:
            if self.llm_service and hasattr(self.llm_service, "is_available"):
                return self.llm_service.is_available()
            return self.status != ServiceStatus.UNHEALTHY

        except Exception as e:
            logger.error(f"Mapping service health check failed: {str(e)}")
            return False

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clear caches
            self._mapping_cache.clear()
            self._cache_timestamps.clear()
            self._guide_type_cache.clear()

            logger.info("Mapping service cleanup completed")

        except Exception as e:
            logger.error(f"Error during mapping service cleanup: {str(e)}")

    def _get_cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        return str(hash(str(args)))

    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if valid."""
        if cache_key in self._mapping_cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self.cache_ttl:
                self.metrics.add_custom_metric("cache_hits", 1)
                return self._mapping_cache[cache_key]
            else:
                # Remove expired entry
                del self._mapping_cache[cache_key]
                del self._cache_timestamps[cache_key]

        self.metrics.add_custom_metric("cache_misses", 1)
        return None

    def _cache_result(self, cache_key: str, result: Any) -> None:
        """Cache result with size limit."""
        if len(self._mapping_cache) >= self.cache_size:
            oldest_key = min(
                self._cache_timestamps.keys(), key=lambda k: self._cache_timestamps[k]
            )
            del self._mapping_cache[oldest_key]
            del self._cache_timestamps[oldest_key]

        self._mapping_cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()

    def preprocess_content(self, content: str) -> str:
        """Preprocess content to improve understanding and handle OCR artifacts."""
        if not content:
            return ""

        # For short content, return as-is to avoid unnecessary LLM calls
        if len(content.strip()) < 100:
            return content.strip()

        try:
            with self.track_request("preprocess_content"):
                if self.llm_service and hasattr(
                    self.llm_service, "preprocess_ocr_text"
                ):
                    return self.llm_service.preprocess_ocr_text(content)
                elif self.llm_service and hasattr(
                    self.llm_service, "generate_response"
                ):
                    # Use general LLM preprocessing
                    system_prompt = """
You are a text preprocessing assistant. Clean and normalize text content while preserving all meaningful information.

Tasks:
1. Fix common OCR artifacts and character recognition errors
2. Normalize excessive whitespace and line breaks
3. Fix punctuation and quote formatting
4. Preserve all original content meaning and structure
5. Do not add, remove, or interpret content - only clean formatting

Return only the cleaned text without any explanations or comments.
"""

                    user_prompt = f"Clean and normalize this text content:\n\n{content}"

                    cleaned_content = self.llm_service.generate_response(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=0.0,
                    )

                    logger.info("Content preprocessing completed using LLM")
                    return (
                        cleaned_content.strip() if cleaned_content else content.strip()
                    )
                else:
                    # Fallback to basic cleanup
                    return content.strip()

        except Exception as e:
            logger.warning(
                f"Content preprocessing failed: {str(e)}, using basic cleanup"
            )
            return content.strip()

    def _clean_and_deduplicate_content(self, content: str) -> str:
        """Clean and deduplicate content to reduce input size."""
        if not content:
            return ""

        try:
            with self.track_request("clean_content"):
                if self.llm_service and hasattr(self.llm_service, "generate_response"):
                    # Use LLM to clean and deduplicate content
                    system_prompt = """
You are a text cleaning expert. Clean and optimize the provided text by:
1. Removing excessive whitespace and normalizing formatting
2. Removing duplicate lines and redundant content
3. Removing OCR artifacts like page numbers, scan references, etc.
4. Preserving all meaningful content and structure
5. Return only the cleaned text without any explanations
"""

                    user_prompt = f"Clean and deduplicate this text:\n\n{content}"

                    response = self.llm_service.generate_response(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=0.1,
                    )

                    return response.strip() if response else content
                else:
                    # Basic fallback cleaning
                    lines = content.split("\n")
                    seen_lines = set()
                    unique_lines = []

                    for line in lines:
                        line_clean = line.strip().lower()
                        if line_clean and line_clean not in seen_lines:
                            seen_lines.add(line_clean)
                            unique_lines.append(line.strip())

                    return "\n".join(unique_lines)

        except Exception as e:
            logger.warning(f"Content cleaning failed: {e}, using basic cleanup")
            # Basic fallback
            lines = content.split("\n")
            return "\n".join(line.strip() for line in lines if line.strip())

    def determine_guide_type(self, marking_guide_content: str) -> Tuple[str, float]:
        """Determine if the marking guide contains questions or answers."""
        if not marking_guide_content:
            return "questions", 0.5

        # Check cache first
        cache_key = self._get_cache_key("guide_type", marking_guide_content[:1000])
        cached_result = self._guide_type_cache.get(cache_key)
        if cached_result:
            return cached_result

        try:
            with self.track_request("determine_guide_type"):
                if not self.llm_service:
                    result = ("questions", 0.5)
                    self._guide_type_cache[cache_key] = result
                    return result

                logger.info("Determining guide type from marking guide content...")

                # Use LLM to determine guide type
                system_prompt = """
You are an expert in analyzing academic documents. Determine whether a marking guide primarily contains questions or answers.

Definitions:
- Questions: Primarily lists exam questions, may include brief guidelines or marks allocation
- Answers: Primarily provides detailed model answers, may include assessment rubrics

Output JSON format:
{
    "guide_type": "questions" or "answers",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation"
}
"""

                user_prompt = f"Analyze this marking guide:\n\n{marking_guide_content}"

                if hasattr(self.llm_service, "generate_response"):
                    response_text = self.llm_service.generate_response(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=0.0,
                    )
                else:
                    params = {
                        "model": self.llm_service.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.0,
                    }

                    response = self.llm_service.client.chat.completions.create(**params)
                    response_text = response.choices[0].message.content

                # Parse response
                parsed = self._parse_json_response(response_text)

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

                result = (guide_type, confidence)
                self._guide_type_cache[cache_key] = result

                logger.info(
                    f"Guide type determined: {guide_type} (confidence: {confidence})"
                )
                logger.info(f"Reasoning: {reasoning}")

                return result

        except Exception as e:
            logger.error(f"Error determining guide type: {str(e)}")
            result = ("questions", 0.5)
            self._guide_type_cache[cache_key] = result
            return result

    def _intelligent_truncate(self, content: str, max_chars: int) -> str:
        """Truncate content at natural boundaries (sentences, questions) to preserve meaning."""
        if len(content) <= max_chars:
            return content

        # Try to truncate at natural boundaries
        truncated = content[:max_chars]

        sentence_boundaries = [
            truncated.rfind("."),
            truncated.rfind("?"),
            truncated.rfind("!"),
            truncated.rfind("\n\n"),  # Paragraph breaks
        ]

        # Find the best boundary (latest position that keeps at least 80% of content)
        min_keep = int(max_chars * 0.8)
        best_boundary = -1

        for boundary in sentence_boundaries:
            if boundary > min_keep:
                best_boundary = max(best_boundary, boundary)

        if best_boundary > 0:
            # Truncate at natural boundary
            result = content[: best_boundary + 1]
            logger.info(
                f"Intelligently truncated content from {len(content)} to {len(result)} chars at natural boundary"
            )
            return result
        else:
            # No good boundary found, truncate with indicator
            result = (
                content[:max_chars]
                + "... [CONTENT TRUNCATED - FULL TEXT NEEDED FOR COMPLETE ANALYSIS]"
            )
            logger.warning(
                f"Hard truncated content from {len(content)} to {max_chars} chars - may affect accuracy"
            )
            return result

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response with multiple strategies for improved reliability."""
        if not response_text or not response_text.strip():
            logger.warning("Empty response text provided for JSON parsing")
            return {}

        # Strategy 1: Direct parsing
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON block with markdown formatting
        import re

        try:
            json_block_match = re.search(
                r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL | re.IGNORECASE
            )
            if json_block_match:
                return json.loads(json_block_match.group(1))
        except json.JSONDecodeError:
            pass

        # Strategy 3: Find first complete JSON object
        try:
            json_object = self._find_complete_json(response_text)
            if json_object:
                return json.loads(json_object)
        except json.JSONDecodeError:
            pass

        # Strategy 4: Extract JSON with broader pattern
        try:
            json_match = re.search(
                r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response_text, re.DOTALL
            )
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        # Strategy 5: Try to fix common JSON issues
        try:
            fixed_json = self._fix_common_json_issues(response_text)
            if fixed_json:
                return json.loads(fixed_json)
        except json.JSONDecodeError:
            pass

        logger.error(
            f"All JSON parsing strategies failed for response: {response_text[:200]}..."
        )
        return {}

    def _find_complete_json(self, text: str) -> Optional[str]:
        """Find the first complete JSON object in text."""

        start_pos = text.find("{")
        if start_pos == -1:
            return None

        # Count braces to find matching closing brace
        brace_count = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start_pos:], start_pos):
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return text[start_pos : i + 1]

        return None

    def _fix_common_json_issues(self, text: str) -> Optional[str]:
        """Attempt to fix common JSON formatting issues."""
        import re

        # Extract potential JSON content
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            return None

        json_text = json_match.group()

        # Fix common issues
        fixes = [
            # Fix single quotes to double quotes
            (r"'([^']*)':", r'"\1":'),
            # Fix unquoted keys
            (r"(\w+):", r'"\1":'),
            # Fix trailing commas
            (r",\s*}", "}"),
            (r",\s*]", "]"),
            # Fix missing quotes around string values
            (r':\s*([^",\[\]{}]+)(?=\s*[,}])', r': "\1"'),
        ]

        for pattern, replacement in fixes:
            json_text = re.sub(pattern, replacement, json_text)

        return json_text

    def map_submission_to_guide(
        self,
        marking_guide_content: str,
        student_submission_content: str,
        num_questions: int = 1,
    ) -> Tuple[Dict, Optional[str]]:
        """Map a student submission to a marking guide using intelligent LLM-based mapping."""
        try:
            with self.track_request("map_submission"):
                # Check cache
                cache_key = self._get_cache_key(
                    marking_guide_content[:1000],
                    student_submission_content[:1000],
                    num_questions,
                )
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result

                # Preprocess content
                guide_content = self.preprocess_content(marking_guide_content)
                submission_content = self.preprocess_content(student_submission_content)

                # Determine guide type
                guide_type, confidence = self.determine_guide_type(guide_content)

                logger.info(f"Processing mapping with guide type: {guide_type}")

                # Perform mapping based on guide type
                if guide_type == "questions":
                    result = self._map_questions_to_answers(
                        guide_content, submission_content
                    )
                else:
                    result = self._map_answers_to_answers(
                        guide_content, submission_content
                    )

                # Cache result
                self._cache_result(cache_key, (result, None))

                return result, None

        except Exception as e:
            error_msg = f"Mapping failed: {str(e)}"
            logger.error(error_msg)
            return {"mappings": [], "error": error_msg}, error_msg

    def _map_questions_to_answers(
        self, guide_content: str, submission_content: str
    ) -> Dict[str, Any]:
        """Map questions from guide to answers in submission."""
        try:
            if not self.llm_service:
                return {"mappings": [], "error": "LLM service not available"}

            # Clean inputs
            guide_clean = self._clean_and_deduplicate_content(guide_content)
            submission_clean = self._clean_and_deduplicate_content(submission_content)

            system_prompt = """
You are an expert at mapping student answers to exam questions. Your task is to:
1. Extract questions from the marking guide
2. Extract answers from the student submission
3. Map each answer to its corresponding question
4. Return structured JSON output

Rules:
- Be precise and concise
- Only map clear matches
- Use question numbers/identifiers when available
- Skip unclear or incomplete content
"""

            user_prompt = f"""MARKING GUIDE (Questions):
{self._intelligent_truncate(guide_clean, 1500)}

STUDENT SUBMISSION (Answers):
{self._intelligent_truncate(submission_clean, 2000)}

Return JSON format:
{{
  "mappings": [
    {{
      "question_id": "Q1",
      "question_text": "What is...",
      "answer_text": "Student's answer...",
      "confidence": 0.95
    }}
  ]
}}"""

            response_text = self.llm_service.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0,  # Changed from 0.1 to 0.0 for full determinism
            )

            return self._parse_json_response(response_text)

        except Exception as e:
            logger.error(f"Question-to-answer mapping failed: {str(e)}")
            return {"mappings": [], "error": str(e)}

    def _map_answers_to_answers(
        self, guide_content: str, submission_content: str
    ) -> Dict[str, Any]:
        """Map answers from guide to answers in submission."""
        try:
            if not self.llm_service:
                return {"mappings": [], "error": "LLM service not available"}

            # Clean inputs
            guide_clean = self._clean_and_deduplicate_content(guide_content)
            submission_clean = self._clean_and_deduplicate_content(submission_content)

            system_prompt = """
You are an expert at comparing student answers to model answers. Your task is to:
1. Extract model answers from the marking guide
2. Extract student answers from the submission
3. Map each student answer to the most relevant model answer
4. Return structured JSON output

Rules:
- Match based on content similarity and topic relevance
- Consider partial matches and related concepts
- Provide confidence scores for each mapping
"""

            user_prompt = f"""MARKING GUIDE (Model Answers):
{guide_clean[:1500]}

STUDENT SUBMISSION (Student Answers):
{submission_clean[:2000]}

Return JSON format:
{{
  "mappings": [
    {{
      "model_answer_id": "A1",
      "model_answer_text": "Model answer...",
      "student_answer_text": "Student's answer...",
      "confidence": 0.85
    }}
  ]
}}"""

            response_text = self.llm_service.generate_response(
                system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.1
            )

            return self._parse_json_response(response_text)

        except Exception as e:
            logger.error(f"Answer-to-answer mapping failed: {str(e)}")
            return {"mappings": [], "error": str(e)}

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "mapping_cache_size": len(self._mapping_cache),
            "guide_type_cache_size": len(self._guide_type_cache),
            "max_cache_size": self.cache_size,
            "cache_ttl": self.cache_ttl,
            "cache_hits": self.metrics.custom_metrics.get("cache_hits", 0),
            "cache_misses": self.metrics.custom_metrics.get("cache_misses", 0),
        }

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._mapping_cache.clear()
        self._cache_timestamps.clear()
        self._guide_type_cache.clear()
        logger.info("Mapping service caches cleared")


# Backward compatibility aliases
MappingService = ConsolidatedMappingService
OptimizedMappingService = ConsolidatedMappingService
EnhancedMappingService = ConsolidatedMappingService
