"""
Enhanced Mapping Service for improved LLM-based grading workflows.
This service provides better prompt formatting, OCR artifact handling, and JSON validation.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import logger


class EnhancedMappingService:
    """Enhanced mapping service with improved LLM integration and error handling."""

    def __init__(self, llm_service=None):
        """Initialize with LLM service."""
        self.llm_service = llm_service

    def preprocess_content(self, content: str) -> str:
        """
        Preprocess content using LLM to improve understanding and handle OCR artifacts.
        
        Args:
            content: Raw content to preprocess
            
        Returns:
            str: Preprocessed content
        """
        if not content:
            return ""
            
        # For short content, return as-is to avoid unnecessary LLM calls
        if len(content.strip()) < 100:
            return content.strip()
            
        # Use LLM to clean and normalize content
        try:
            if self.llm_service:
                system_prompt = """
                You are a text preprocessing assistant. Your task is to clean and normalize text content while preserving all meaningful information.
                
                Tasks:
                1. Fix common OCR artifacts and character recognition errors
                2. Normalize excessive whitespace and line breaks
                3. Fix punctuation and quote formatting
                4. Preserve all original content meaning and structure
                5. Do not add, remove, or interpret content - only clean formatting
                
                Return only the cleaned text without any explanations or comments.
                """
                
                user_prompt = f"Clean and normalize this text content:\n\n{content}"
                
                params = {
                    "model": self.llm_service.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.0,
                }
                
                response = self.llm_service.client.chat.completions.create(**params)
                cleaned_content = response.choices[0].message.content.strip()
                
                logger.info("Content preprocessing completed using LLM")
                return cleaned_content
        except Exception as e:
            logger.warning(f"LLM preprocessing failed: {str(e)}, using basic cleanup")
            
        # Fallback to basic cleanup if LLM fails
        return content.strip()

    def clean_and_parse_llm_response(self, result: str) -> Dict:
        """
        Clean and parse LLM response using LLM-only approach for JSON extraction.
        
        Args:
            result: Raw LLM response
            
        Returns:
            Dict: Parsed JSON response
        """
        try:
            # Log the raw response for debugging
            logger.info(f"Raw LLM response: {result[:200]}...")

            # Second attempt: use LLM to clean and extract valid JSON
            if self.llm_service:
                try:
                    system_prompt = """
                    You are a JSON extraction and cleaning assistant. Your task is to extract valid JSON from text that may contain formatting issues, comments, or extra content.
                    
                    Rules:
                    1. Extract only the JSON object from the provided text
                    2. Remove any comments, explanations, or non-JSON content
                    3. Fix common JSON formatting issues (trailing commas, quote issues, etc.)
                    4. Ensure the output is valid, parseable JSON
                    5. Preserve all data content - only fix formatting
                    6. Return ONLY the cleaned JSON object, no explanations
                    
                    The expected JSON structure should contain:
                    - "mappings" array with question-answer mappings
                    - "overall_grade" object with scoring information
                    """
                    
                    user_prompt = f"Extract and clean the JSON from this text:\n\n{result}"
                    
                    params = {
                        "model": self.llm_service.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.0,
                    }
                    
                    response = self.llm_service.client.chat.completions.create(**params)
                    cleaned_result = response.choices[0].message.content.strip()
                    
                    logger.info(f"LLM-cleaned JSON: {cleaned_result[:200]}...")
                    
                    # Try parsing the cleaned result
                    parsed = json.loads(cleaned_result)
                    logger.info("JSON parsing successful after LLM cleaning")
                    return parsed
                    
                except Exception as llm_error:
                    logger.error(f"LLM JSON cleaning failed: {str(llm_error)}")

            # Third attempt: use LLM to reconstruct the JSON from scratch
            if self.llm_service:
                try:
                    system_prompt = """
                    You are a data extraction assistant. The provided text contains information about question-answer mappings and grading, but the JSON format is corrupted.
                    
                    Your task is to extract the meaningful data and reconstruct it as valid JSON with this structure:
                    {
                        "mappings": [
                            {
                                "guide_id": "string",
                                "guide_text": "string", 
                                "guide_answer": "string",
                                "max_score": number,
                                "submission_id": "string",
                                "submission_text": "string",
                                "match_score": number,
                                "match_reason": "string",
                                "grade_score": number,
                                "grade_percentage": number,
                                "grade_feedback": "string",
                                "strengths": ["string"],
                                "weaknesses": ["string"]
                            }
                        ],
                        "overall_grade": {
                            "total_score": number,
                            "max_possible_score": number,
                            "percentage": number,
                            "letter_grade": "string"
                        }
                    }
                    
                    Extract all available information and provide reasonable defaults for missing fields.
                    Return ONLY the JSON object, no explanations.
                    """
                    
                    user_prompt = f"Reconstruct valid JSON from this corrupted data:\n\n{result}"
                    
                    params = {
                        "model": self.llm_service.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.0,
                    }
                    
                    response = self.llm_service.client.chat.completions.create(**params)
                    reconstructed_result = response.choices[0].message.content.strip()
                    
                    logger.info(f"LLM-reconstructed JSON: {reconstructed_result[:200]}...")
                    
                    # Try parsing the reconstructed result
                    parsed = json.loads(reconstructed_result)
                    logger.info("JSON parsing successful after LLM reconstruction")
                    return parsed
                    
                except Exception as reconstruction_error:
                    logger.error(f"LLM JSON reconstruction failed: {str(reconstruction_error)}")

            # Final fallback: create minimal valid structure
            logger.warning("All JSON parsing attempts failed, creating minimal valid structure")
            
            return {
                "mappings": [],
                "overall_grade": {
                    "total_score": 0,
                    "max_possible_score": 0,
                    "percentage": 0,
                    "letter_grade": "F"
                }
            }
            
        except Exception as e:
            logger.error(f"Critical error in JSON parsing: {str(e)}")
            raise Exception(f"Unable to parse LLM response: {str(e)}")

    def get_enhanced_system_prompt(self, guide_type: str, num_questions: int) -> str:
        """
        Get enhanced system prompt for better LLM understanding.
        
        Args:
            guide_type: Type of guide (questions or answers)
            num_questions: Number of questions to answer
            
        Returns:
            str: Enhanced system prompt
        """
        if guide_type == "questions":
            return f"""
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
            return f"""
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

    def get_enhanced_user_prompt(self, marking_guide_content: str, student_submission_content: str, num_questions: int) -> str:
        """
        Get enhanced user prompt for better LLM understanding.
        
        Args:
            marking_guide_content: Preprocessed marking guide content
            student_submission_content: Preprocessed student submission content
            num_questions: Number of questions to answer
            
        Returns:
            str: Enhanced user prompt
        """
        return f"""
        MARKING GUIDE CONTENT:
        {marking_guide_content}

        STUDENT SUBMISSION CONTENT:
        {student_submission_content}

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

    def map_submission_to_guide_enhanced(
        self,
        marking_guide_content: str,
        student_submission_content: str,
        num_questions: int = 1,
    ) -> Tuple[Dict, Optional[str]]:
        """
        Enhanced mapping with improved prompt formatting and error handling.
        
        Args:
            marking_guide_content: Raw text content of the marking guide
            student_submission_content: Raw text content of the student submission
            num_questions: Number of questions the student should answer
            
        Returns:
            Tuple[Dict, Optional[str]]: (Mapping and grading result, Error message if any)
        """
        try:
            logger.info("Starting enhanced mapping submission to guide...")

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
            marking_guide_content = self.preprocess_content(marking_guide_content)
            student_submission_content = self.preprocess_content(student_submission_content)

            if not self.llm_service:
                raise Exception("LLM service is required for enhanced mapping")

            # Determine guide type (simplified for now)
            guide_type = "questions"  # Default assumption

            # Get enhanced prompts
            system_prompt = self.get_enhanced_system_prompt(guide_type, num_questions)
            user_prompt = self.get_enhanced_user_prompt(marking_guide_content, student_submission_content, num_questions)

            # Call LLM with enhanced prompts
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

            response = self.llm_service.client.chat.completions.create(**params)
            result = response.choices[0].message.content

            # Clean and parse the response
            parsed = self.clean_and_parse_llm_response(result)

            # Process the results
            mappings = []
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
                    "max_score": max_score,
                    "submission_id": mapping.get("submission_id", f"s{len(mappings)+1}"),
                    "submission_text": mapping.get("submission_text", ""),
                    "submission_answer": mapping.get("submission_answer", ""),
                    "match_score": mapping.get("match_score", 0.5),
                    "match_reason": mapping.get("match_reason", ""),
                    "guide_type": guide_type,
                    "grade_score": grade_score,
                    "grade_percentage": grade_percentage,
                    "grade_feedback": grade_feedback,
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                }

                # Add parent_question field if it exists
                if mapping.get("parent_question"):
                    mapping_obj["parent_question"] = mapping.get("parent_question")

                mappings.append(mapping_obj)

            # Calculate overall grade
            overall_grade = parsed.get("overall_grade", {})
            if not overall_grade:
                percentage = (
                    (total_score / max_possible_score * 100)
                    if max_possible_score > 0
                    else 0
                )

                # Determine letter grade
                letter_grade = self._get_letter_grade(percentage)

                overall_grade = {
                    "total_score": round(total_score, 1),
                    "max_possible_score": max_possible_score,
                    "percentage": round(percentage, 1),
                    "letter_grade": letter_grade,
                }

            # Create result
            result = {
                "status": "success",
                "message": "Content mapped successfully with enhanced processing",
                "mappings": mappings,
                "metadata": {
                    "num_questions": num_questions,
                    "mapping_count": len(mappings),
                    "guide_type": guide_type,
                    "mapping_method": "Enhanced LLM",
                    "timestamp": datetime.now().isoformat(),
                },
                "raw_guide_content": marking_guide_content,
                "raw_submission_content": student_submission_content,
                "overall_grade": overall_grade,
            }

            logger.info(
                f"Enhanced mapping completed successfully. Score: {overall_grade.get('percentage', 0)}%"
            )

            return result, None

        except Exception as e:
            error_message = f"Error in enhanced mapping service: {str(e)}"
            logger.error(f"Enhanced mapping failed: {str(e)}")

            return {
                "status": "error",
                "message": error_message,
                "raw_guide_content": marking_guide_content,
                "raw_submission_content": student_submission_content,
            }, error_message

    def _get_letter_grade(self, percent_score: float) -> str:
        """Get letter grade from percentage score."""
        if percent_score >= 90:
            return "A+"
        elif percent_score >= 85:
            return "A"
        elif percent_score >= 80:
            return "A-"
        elif percent_score >= 75:
            return "B+"
        elif percent_score >= 70:
            return "B"
        elif percent_score >= 65:
            return "B-"
        elif percent_score >= 60:
            return "C+"
        elif percent_score >= 55:
            return "C"
        elif percent_score >= 50:
            return "C-"
        elif percent_score >= 45:
            return "D+"
        elif percent_score >= 40:
            return "D"
        else:
            return "F"