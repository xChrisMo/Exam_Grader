"""
Score Validation Service

This service provides comprehensive validation and accuracy checking for LLM-generated scores
to ensure fair and consistent grading.
"""

import json
import re
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from utils.logger import logger

class ValidationLevel(Enum):
    """Validation strictness levels"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"

@dataclass
class ScoreValidationResult:
    """Result of score validation"""
    is_valid: bool
    confidence: float  # 0.0 to 1.0
    adjusted_score: Optional[int] = None
    warnings: List[str] = None
    errors: List[str] = None
    validation_details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []
        if self.validation_details is None:
            self.validation_details = {}

class ScoreValidationService:
    """Service for validating LLM-generated scores for accuracy and consistency"""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        self.validation_level = validation_level
        self.score_history = []  # For consistency checking
        
    def validate_score(
        self, 
        score: int, 
        question: str, 
        model_answer: str, 
        student_answer: str,
        criteria_scores: Dict[str, int] = None,
        feedback: str = None
    ) -> ScoreValidationResult:
        """
        Comprehensive score validation with multiple checks.
        
        Args:
            score: The overall score to validate
            question: The question being graded
            model_answer: The model/correct answer
            student_answer: The student's answer
            criteria_scores: Individual criteria scores
            feedback: LLM-generated feedback
            
        Returns:
            ScoreValidationResult with validation outcome
        """
        result = ScoreValidationResult(is_valid=True, confidence=1.0)
        
        # 1. Basic range validation
        if not self._validate_score_range(score, result):
            return result
        
        # 2. Criteria consistency check
        if criteria_scores:
            self._validate_criteria_consistency(score, criteria_scores, result)
        
        # 3. Answer quality vs score alignment
        self._validate_answer_quality_alignment(score, student_answer, model_answer, result)
        
        # 4. Feedback consistency check
        if feedback:
            self._validate_feedback_consistency(score, feedback, result)
        
        # 5. Statistical outlier detection
        self._check_statistical_outliers(score, result)
        
        # 6. Content-based reasonableness check
        self._validate_content_reasonableness(score, question, student_answer, model_answer, result)
        
        # Calculate final confidence
        result.confidence = self._calculate_confidence(result)
        
        # Log validation results
        self._log_validation_results(score, result)
        
        return result
    
    def _validate_score_range(self, score: int, result: ScoreValidationResult) -> bool:
        """Validate score is in valid range"""
        if not isinstance(score, int):
            result.is_valid = False
            result.errors.append(f"Score must be integer, got {type(score)}")
            return False
        
        if score < 0 or score > 100:
            result.is_valid = False
            result.errors.append(f"Score {score} outside valid range 0-100")
            result.adjusted_score = max(0, min(100, score))
            return False
        
        return True
    
    def _validate_criteria_consistency(self, overall_score: int, criteria_scores: Dict[str, int], result: ScoreValidationResult):
        """Check if overall score is consistent with criteria scores"""
        if not criteria_scores:
            return
        
        # Calculate average of criteria scores
        valid_criteria = {k: v for k, v in criteria_scores.items() if isinstance(v, int) and 0 <= v <= 100}
        
        if not valid_criteria:
            result.warnings.append("No valid criteria scores found")
            return
        
        avg_criteria = sum(valid_criteria.values()) / len(valid_criteria)
        difference = abs(overall_score - avg_criteria)
        
        # Allow some tolerance based on validation level
        tolerance = {
            ValidationLevel.BASIC: 20,
            ValidationLevel.STANDARD: 15,
            ValidationLevel.STRICT: 10
        }[self.validation_level]
        
        if difference > tolerance:
            result.warnings.append(
                f"Overall score {overall_score} differs significantly from criteria average {avg_criteria:.1f} (diff: {difference:.1f})"
            )
            result.confidence *= 0.8
        
        result.validation_details['criteria_average'] = avg_criteria
        result.validation_details['criteria_difference'] = difference
    
    def _validate_answer_quality_alignment(self, score: int, student_answer: str, model_answer: str, result: ScoreValidationResult):
        """Check if score aligns with apparent answer quality"""
        if not student_answer or not model_answer:
            return
        
        # Basic quality indicators
        quality_indicators = self._assess_answer_quality(student_answer, model_answer)
        expected_score_range = self._estimate_score_from_quality(quality_indicators)
        
        if score < expected_score_range[0] or score > expected_score_range[1]:
            result.warnings.append(
                f"Score {score} may not align with answer quality (expected range: {expected_score_range[0]}-{expected_score_range[1]})"
            )
            result.confidence *= 0.9
        
        result.validation_details['quality_indicators'] = quality_indicators
        result.validation_details['expected_score_range'] = expected_score_range
    
    def _assess_answer_quality(self, student_answer: str, model_answer: str) -> Dict[str, float]:
        """Assess basic quality indicators of the answer"""
        indicators = {}
        
        # Length comparison (normalized)
        student_len = len(student_answer.strip())
        model_len = len(model_answer.strip())
        indicators['length_ratio'] = min(student_len / max(model_len, 1), 2.0)  # Cap at 2x
        
        # Word overlap (simple similarity)
        student_words = set(student_answer.lower().split())
        model_words = set(model_answer.lower().split())
        if model_words:
            indicators['word_overlap'] = len(student_words & model_words) / len(model_words)
        else:
            indicators['word_overlap'] = 0.0
        
        # Basic completeness indicators
        indicators['has_content'] = 1.0 if student_len > 10 else 0.0
        indicators['not_empty'] = 1.0 if student_answer.strip() else 0.0
        
        negative_patterns = [
            r'\bi\s+don\'?t\s+know\b',
            r'\bno\s+idea\b',
            r'\bunsure\b',
            r'\bguess\b',
            r'\bmaybe\b',
            r'\bnot\s+sure\b'
        ]
        
        uncertainty_count = sum(1 for pattern in negative_patterns 
                              if re.search(pattern, student_answer.lower()))
        indicators['uncertainty_level'] = min(uncertainty_count / 3.0, 1.0)
        
        return indicators
    
    def _estimate_score_from_quality(self, quality_indicators: Dict[str, float]) -> Tuple[int, int]:
        """Estimate expected score range based on quality indicators"""
        base_score = 0
        
        # Length factor (0-25 points)
        length_score = min(quality_indicators.get('length_ratio', 0) * 25, 25)
        
        # Content overlap (0-40 points)
        overlap_score = quality_indicators.get('word_overlap', 0) * 40
        
        # Completeness (0-20 points)
        completeness_score = quality_indicators.get('has_content', 0) * 20
        
        # Confidence penalty (0-15 points deduction)
        uncertainty_penalty = quality_indicators.get('uncertainty_level', 0) * 15
        
        estimated_score = length_score + overlap_score + completeness_score - uncertainty_penalty
        estimated_score = max(0, min(100, estimated_score))
        
        # Return range with tolerance
        tolerance = 25  # ±25 points tolerance
        return (max(0, int(estimated_score - tolerance)), min(100, int(estimated_score + tolerance)))
    
    def _validate_feedback_consistency(self, score: int, feedback: str, result: ScoreValidationResult):
        """Check if feedback is consistent with the score"""
        if not feedback:
            return
        
        feedback_lower = feedback.lower()
        
        # Define score-feedback consistency patterns
        high_score_indicators = ['excellent', 'outstanding', 'perfect', 'great', 'very good', 'strong']
        medium_score_indicators = ['good', 'adequate', 'satisfactory', 'reasonable', 'fair']
        low_score_indicators = ['poor', 'weak', 'inadequate', 'incorrect', 'missing', 'wrong', 'failed']
        
        # Count indicators
        high_count = sum(1 for indicator in high_score_indicators if indicator in feedback_lower)
        medium_count = sum(1 for indicator in medium_score_indicators if indicator in feedback_lower)
        low_count = sum(1 for indicator in low_score_indicators if indicator in feedback_lower)
        
        # Check consistency
        if score >= 80 and low_count > high_count:
            result.warnings.append("High score but feedback contains negative language")
            result.confidence *= 0.85
        elif score <= 40 and high_count > low_count:
            result.warnings.append("Low score but feedback contains positive language")
            result.confidence *= 0.85
        
        result.validation_details['feedback_indicators'] = {
            'high_count': high_count,
            'medium_count': medium_count,
            'low_count': low_count
        }
    
    def _check_statistical_outliers(self, score: int, result: ScoreValidationResult):
        """Check if score is a statistical outlier compared to recent scores"""
        if len(self.score_history) < 5:
            self.score_history.append(score)
            return
        
        # Calculate statistics
        mean_score = statistics.mean(self.score_history)
        stdev_score = statistics.stdev(self.score_history) if len(self.score_history) > 1 else 0
        
        if stdev_score > 0:
            z_score = abs(score - mean_score) / stdev_score
            
            if z_score > 2:
                result.warnings.append(
                    f"Score {score} is statistical outlier (z-score: {z_score:.2f}, mean: {mean_score:.1f})"
                )
                result.confidence *= 0.9
        
        # Update history (keep last 20 scores)
        self.score_history.append(score)
        if len(self.score_history) > 20:
            self.score_history.pop(0)
        
        result.validation_details['statistical_info'] = {
            'mean_score': mean_score,
            'stdev_score': stdev_score,
            'z_score': abs(score - mean_score) / stdev_score if stdev_score > 0 else 0
        }
    
    def _validate_content_reasonableness(self, score: int, question: str, student_answer: str, model_answer: str, result: ScoreValidationResult):
        """Validate score reasonableness based on content analysis"""
        if not all([question, student_answer, model_answer]):
            return
        
        student_lower = student_answer.lower().strip()
        
        # Empty or very short answers shouldn't get high scores
        if len(student_lower) < 5 and score > 20:
            result.warnings.append(f"Very short answer ({len(student_lower)} chars) received high score {score}")
            result.confidence *= 0.7
        
        # Answers that are just "I don't know" shouldn't get high scores
        dont_know_patterns = [
            r'^i\s+don\'?t\s+know\.?$',
            r'^no\s+idea\.?$',
            r'^not\s+sure\.?$',
            r'^\?+$'
        ]
        
        if any(re.match(pattern, student_lower) for pattern in dont_know_patterns) and score > 10:
            result.warnings.append(f"'Don't know' type answer received score {score}")
            result.confidence *= 0.6
        
        # Very long answers that are mostly correct should get reasonable scores
        if len(student_lower) > len(model_answer) * 1.5 and score < 30:
            result.warnings.append(f"Long detailed answer ({len(student_lower)} chars) received low score {score}")
            result.confidence *= 0.8
    
    def _calculate_confidence(self, result: ScoreValidationResult) -> float:
        """Calculate final confidence score based on validation results"""
        base_confidence = result.confidence
        
        # Reduce confidence based on number of warnings and errors
        warning_penalty = len(result.warnings) * 0.05
        error_penalty = len(result.errors) * 0.2
        
        final_confidence = max(0.0, base_confidence - warning_penalty - error_penalty)
        
        return round(final_confidence, 3)
    
    def _log_validation_results(self, score: int, result: ScoreValidationResult):
        """Log validation results for monitoring"""
        if not result.is_valid:
            logger.error(f"Score validation failed for score {score}: {result.errors}")
        elif result.warnings:
            logger.warning(f"Score validation warnings for score {score}: {result.warnings}")
        elif result.confidence < 0.8:
            logger.warning(f"Low confidence ({result.confidence}) for score {score}")
        else:
            logger.debug(f"Score {score} validated successfully (confidence: {result.confidence})")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation statistics"""
        return {
            'total_scores_validated': len(self.score_history),
            'recent_scores': self.score_history[-10:] if self.score_history else [],
            'average_recent_score': statistics.mean(self.score_history[-10:]) if self.score_history else 0,
            'validation_level': self.validation_level.value
        }

# Global instance
score_validator = ScoreValidationService(ValidationLevel.STANDARD)