"""
Grading Service for grading student submissions.
This service grades student submissions by comparing their answers to the solutions in the marking guide.
"""
import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

class GradingService:
    """
    Grading service that evaluates student submissions by comparing answers to solutions.
    The score is determined by how closely the submission answers match the marking guide answers.
    """
    
    def __init__(self, llm_service=None, mapping_service=None):
        """Initialize with optional LLM and mapping services."""
        self.llm_service = llm_service
        self.mapping_service = mapping_service
        
    def _similarity_score(self, guide_answer: str, submission_answer: str) -> float:
        """
        Calculate a similarity score between the guide answer and submission answer.
        
        This is a simplified version used when LLM is not available.
        
        Returns:
            float: Similarity score between 0.0 and 1.0
        """
        if not guide_answer or not submission_answer:
            return 0.0
            
        # Remove punctuation and convert to lowercase for comparison
        guide_clean = re.sub(r'[^\w\s]', '', guide_answer.lower())
        submission_clean = re.sub(r'[^\w\s]', '', submission_answer.lower())
        
        # Split into words
        guide_words = set(guide_clean.split())
        submission_words = set(submission_clean.split())
        
        if not guide_words:
            return 0.0
            
        # Calculate Jaccard similarity
        intersection = len(guide_words.intersection(submission_words))
        union = len(guide_words.union(submission_words))
        
        if union == 0:
            return 0.0
            
        basic_similarity = intersection / union
        
        # Bonus for exact matches on key phrases (3+ words in sequence)
        guide_phrases = [w for w in guide_clean.split() if len(w) > 3]
        submission_phrases = [w for w in submission_clean.split() if len(w) > 3]
        
        phrase_matches = sum(1 for word in guide_phrases if word in submission_phrases)
        phrase_bonus = 0.2 * (phrase_matches / len(guide_phrases)) if guide_phrases else 0
        
        # Apply bonuses and penalties
        final_similarity = min(1.0, basic_similarity + phrase_bonus)
        
        return final_similarity
        
    def grade_submission(self, marking_guide_content: str, student_submission_content: str) -> Tuple[Dict, Optional[str]]:
        """
        Grade a student submission against a marking guide.
        
        Args:
            marking_guide_content: Text content of the marking guide
            student_submission_content: Text content of the student submission
            
        Returns:
            Tuple[Dict, Optional[str]]: (Grading result, Error message if any)
        """
        try:
            # Use mapping service to match questions and answers
            if self.mapping_service:
                mapping_result, mapping_error = self.mapping_service.map_submission_to_guide(
                    marking_guide_content, 
                    student_submission_content
                )
                
                if mapping_error:
                    return {"status": "error", "message": f"Mapping error: {mapping_error}"}, mapping_error
                
                mappings = mapping_result.get("mappings", [])
            else:
                # Create a placeholder mapping service if none was provided
                from src.services.mapping_service import MappingService
                temp_mapping_service = MappingService()
                mapping_result, mapping_error = temp_mapping_service.map_submission_to_guide(
                    marking_guide_content, 
                    student_submission_content
                )
                
                if mapping_error:
                    return {"status": "error", "message": f"Mapping error: {mapping_error}"}, mapping_error
                
                mappings = mapping_result.get("mappings", [])
            
            # Grade each mapped question
            overall_score = 0
            max_possible_score = 0
            criteria_scores = []
            detailed_feedback = []
            
            for mapping in mappings:
                guide_text = mapping.get("guide_text", "")
                guide_answer = mapping.get("guide_answer", "")
                submission_text = mapping.get("submission_text", "")
                submission_answer = mapping.get("submission_answer", "")
                max_score = mapping.get("max_score", 10)
                
                # Use LLM for comparison if available
                if self.llm_service and hasattr(self.llm_service, 'compare_answers'):
                    try:
                        # Use LLM to compare answers
                        score, feedback = self.llm_service.compare_answers(
                            question=guide_text,
                            guide_answer=guide_answer,
                            submission_answer=submission_answer,
                            max_score=max_score
                        )
                        similarity = score / max_score if max_score > 0 else 0
                    except Exception as e:
                        # Fall back to basic similarity if LLM fails
                        similarity = self._similarity_score(guide_answer, submission_answer)
                        score = round(similarity * max_score, 1)
                        feedback = f"Graded based on text similarity (LLM error: {str(e)})"
                else:
                    # Use basic similarity function
                    similarity = self._similarity_score(guide_answer, submission_answer)
                    score = round(similarity * max_score, 1)
                    feedback = "Graded based on text similarity"
                
                # Add to overall score
                overall_score += score
                max_possible_score += max_score
                
                # Add to detailed feedback
                detailed_feedback.append({
                    "question": guide_text.split("\n")[0] if guide_text else f"Question {len(detailed_feedback)+1}",
                    "score": score,
                    "max_score": max_score,
                    "feedback": feedback
                })
                
                # Add to criteria scores
                criteria_scores.append({
                    "description": guide_text.split("\n")[0] if guide_text else f"Question {len(criteria_scores)+1}",
                    "points_earned": score,
                    "points_possible": max_score,
                    "similarity": similarity,
                    "guide_id": mapping.get("guide_id"),
                    "submission_id": mapping.get("submission_id"),
                    "feedback": feedback
                })
            
            # Calculate percentage score
            percent_score = (overall_score / max_possible_score * 100) if max_possible_score > 0 else 0
            percent_score = round(percent_score, 1)
            
            # Generate summary feedback
            strengths = []
            weaknesses = []
            
            for score in criteria_scores:
                if score["similarity"] >= 0.8:
                    strengths.append(f"Strong understanding demonstrated in {score['description']}")
                elif score["similarity"] <= 0.3:
                    weaknesses.append(f"Significant improvement needed in {score['description']}")
            
            # Add general feedback
            if percent_score >= 80:
                strengths.append("Overall excellent understanding of the material")
            elif percent_score <= 50:
                weaknesses.append("Overall understanding of key concepts needs improvement")
            
            # Create result with both naming formats for compatibility
            submission_id = f"sub_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            result = {
                "overall_score": overall_score,
                "max_possible_score": max_possible_score,
                "percent_score": percent_score,
                "detailed_feedback": {
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "improvement_suggestions": [
                        "Review areas where scores were low",
                        "Focus on improving accuracy and completeness in your answers"
                    ],
                    "question_feedback": detailed_feedback
                },
                "criterion_scores": criteria_scores,  # For newer templates
                "criteria_scores": criteria_scores,   # For older templates
                "assessment_confidence": "high" if self.llm_service else "medium",
                "grading_notes": f"Graded based on answer similarity. Overall score: {overall_score}/{max_possible_score} ({percent_score}%)",
                "metadata": {
                    "submission_id": submission_id,
                    "timestamp": datetime.now().isoformat(),
                    "grader": "LLM Answer Comparison" if self.llm_service else "Text Similarity Comparison",
                    "question_count": len(criteria_scores),
                    "used_llm": self.llm_service is not None
                }
            }
            
            return result, None
            
        except Exception as e:
            error_message = f"Error in grading service: {str(e)}"
            return {"status": "error", "message": error_message}, error_message
        
    def save_grading_result(self, grading_result: Dict, output_path: str, filename: str = None) -> str:
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
        if not filename.endswith('.json'):
            filename += '.json'
            
        # Full path to the output file
        output_file = Path(output_path) / filename
        
        # Save the result as JSON
        with open(output_file, 'w') as f:
            json.dump(grading_result, f, indent=2)
            
        return str(output_file)
