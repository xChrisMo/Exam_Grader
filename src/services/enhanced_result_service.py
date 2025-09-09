"""
Enhanced Result Service

This service provides comprehensive formatting and enhancement of grading results
for detailed display in the UI. It processes raw grading data and adds additional
analytics, formatting, and metadata for improved user experience.
"""

import json
from datetime import datetime
import statistics
from typing import Any, Dict, List, Optional

from utils.logger import logger

class EnhancedResultService:
    """Service for enhancing and formatting grading results for detailed display."""

    def __init__(self):
        self.confidence_thresholds = {"high": 0.85, "medium": 0.65, "low": 0.4}

    def enhance_result(
        self,
        result: Dict[str, Any],
        submission: Optional[Dict] = None,
        guide: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Enhance a grading result with additional analytics and formatting.

        Args:
            result: Raw grading result data
            submission: Submission data
            guide: Marking guide data

        Returns:
            Enhanced result with additional fields and analytics
        """
        try:
            enhanced = result.copy()

            # Parse detailed_feedback if it's a JSON string
            detailed_grades = self._parse_detailed_feedback(
                result.get("detailed_feedback")
            )

            # Enhance detailed grades with analytics
            if detailed_grades:
                enhanced["detailed_grades_enhanced"] = self._enhance_detailed_grades(
                    detailed_grades
                )
                enhanced["grade_analytics"] = self._calculate_grade_analytics(
                    detailed_grades
                )

            # Add confidence analysis
            confidence = result.get("confidence")
            enhanced["confidence_analysis"] = self._analyze_confidence(confidence)

            # Add performance insights
            enhanced["performance_insights"] = self._generate_performance_insights(
                detailed_grades, result.get("percentage", 0)
            )

            # Add question-level analytics
            if detailed_grades:
                enhanced["question_analytics"] = self._calculate_question_analytics(
                    detailed_grades
                )

            # Format processing metadata
            if result.get("processing_metadata"):
                enhanced["processing_metadata_formatted"] = (
                    self._format_processing_metadata(result["processing_metadata"])
                )

            # Calculate additional statistics
            enhanced["result_statistics"] = self._calculate_result_statistics(
                result, detailed_grades
            )

            # Add grading quality indicators
            enhanced["quality_indicators"] = self._assess_grading_quality(
                detailed_grades, result
            )

            logger.info(
                f"Enhanced result {result.get('id', 'unknown')} with additional analytics"
            )
            return enhanced

        except Exception as e:
            logger.error(f"Failed to enhance result: {str(e)}")
            return result

    def _parse_detailed_feedback(self, detailed_feedback: Any) -> List[Dict[str, Any]]:
        """Parse detailed feedback from various formats."""
        if not detailed_feedback:
            return []

        try:
            if isinstance(detailed_feedback, str):
                # Try to parse as JSON
                parsed = json.loads(detailed_feedback)
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, dict) and "detailed_grades" in parsed:
                    return parsed["detailed_grades"]
                elif isinstance(parsed, dict) and "grades" in parsed:
                    return parsed["grades"]
                else:
                    return []
            elif isinstance(detailed_feedback, list):
                return detailed_feedback
            elif isinstance(detailed_feedback, dict):
                if "detailed_grades" in detailed_feedback:
                    return detailed_feedback["detailed_grades"]
                elif "grades" in detailed_feedback:
                    return detailed_feedback["grades"]
                else:
                    return []
            else:
                return []
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"Failed to parse detailed feedback: {str(e)}")
            return []

    def _enhance_detailed_grades(
        self, detailed_grades: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enhance individual grade entries with additional information."""
        enhanced_grades = []

        for i, grade in enumerate(detailed_grades):
            enhanced_grade = grade.copy()

            # Ensure required fields with safe type conversion
            enhanced_grade["question_number"] = i + 1
            enhanced_grade["question_id"] = grade.get("question_id", f"Q{i + 1}")

            # Safe conversion of score and max_score
            try:
                score = grade.get("score", 0)
                enhanced_grade["score"] = float(score) if score is not None else 0.0
            except (TypeError, ValueError):
                enhanced_grade["score"] = 0.0

            try:
                max_score = grade.get("max_score")
                if max_score is None:
                    logger.warning("No max_score found in enhanced result processing, guide may not be properly processed")
                    max_score = 0.0  # Use 0 to indicate missing score
                enhanced_grade["max_score"] = float(max_score)
            except (TypeError, ValueError):
                enhanced_grade["max_score"] = 0.0  # Use 0 to indicate missing score

            enhanced_grade["feedback"] = grade.get("feedback", "No feedback provided")

            # Calculate percentage for this question
            if enhanced_grade["max_score"] > 0:
                enhanced_grade["percentage"] = round(
                    (enhanced_grade["score"] / enhanced_grade["max_score"]) * 100, 1
                )
            else:
                enhanced_grade["percentage"] = 0

            # Assign performance level
            enhanced_grade["performance_level"] = self._get_performance_level(
                enhanced_grade["percentage"]
            )

            # Add score color coding
            enhanced_grade["score_color"] = self._get_score_color(
                enhanced_grade["percentage"]
            )

            # Analyze feedback sentiment
            enhanced_grade["feedback_sentiment"] = self._analyze_feedback_sentiment(
                enhanced_grade["feedback"]
            )

            # Add question and student answer if available
            enhanced_grade["question_text"] = grade.get(
                "question_text", grade.get("question", "Question text not available")
            )
            enhanced_grade["student_answer"] = grade.get(
                "student_answer", grade.get("answer_text", "Answer not available")
            )

            # Truncate long text for display
            enhanced_grade["question_text_short"] = self._truncate_text(
                enhanced_grade["question_text"], 100
            )
            enhanced_grade["student_answer_short"] = self._truncate_text(
                enhanced_grade["student_answer"], 150
            )
            enhanced_grade["feedback_short"] = self._truncate_text(
                enhanced_grade["feedback"], 100
            )

            enhanced_grades.append(enhanced_grade)

        return enhanced_grades

    def _calculate_grade_analytics(
        self, detailed_grades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate analytics across all grades."""
        if not detailed_grades:
            return {}

        # Safe conversion of scores and max_scores
        scores = []
        max_scores = []

        for grade in detailed_grades:
            try:
                score = grade.get("score", 0)
                scores.append(float(score) if score is not None else 0.0)
            except (TypeError, ValueError):
                scores.append(0.0)

            try:
                max_score = grade.get("max_score")
                if max_score is None:
                    logger.warning("No max_score found in grade analytics, guide may not be properly processed")
                    max_score = 0.0
                max_scores.append(float(max_score))
            except (TypeError, ValueError):
                max_scores.append(0.0)  # Use 0 to indicate missing score

        percentages = [
            (score / max_score * 100) if max_score > 0 else 0
            for score, max_score in zip(scores, max_scores)
        ]

        analytics = {
            "total_questions": len(detailed_grades),
            "total_score": round(sum(scores), 2),
            "total_max_score": round(sum(max_scores), 2),
            "average_score": round(statistics.mean(scores), 2) if scores else 0,
            "average_percentage": (
                round(statistics.mean(percentages), 1) if percentages else 0
            ),
            "median_percentage": (
                round(statistics.median(percentages), 1) if percentages else 0
            ),
            "highest_score": max(scores) if scores else 0,
            "lowest_score": min(scores) if scores else 0,
            "score_range": (
                round(max(scores) - min(scores), 2) if len(scores) > 1 else 0
            ),
        }

        # Performance distribution
        performance_levels = [self._get_performance_level(p) for p in percentages]
        analytics["performance_distribution"] = {
            "excellent": performance_levels.count("excellent"),
            "good": performance_levels.count("good"),
            "fair": performance_levels.count("fair"),
            "poor": performance_levels.count("poor"),
        }

        # Standard deviation if we have enough data points
        if len(percentages) > 1:
            analytics["score_std_dev"] = round(statistics.stdev(percentages), 2)
        else:
            analytics["score_std_dev"] = 0

        return analytics

    def _analyze_confidence(self, confidence: float) -> Dict[str, Any]:
        """Analyze confidence score and provide interpretation."""
        # Handle None or invalid confidence values
        if confidence is None:
            confidence = 0.0

        # Ensure confidence is a float and within valid range
        try:
            confidence = float(confidence) if confidence is not None else 0.0
            confidence = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
        except (TypeError, ValueError):
            confidence = 0.0

        if confidence >= self.confidence_thresholds["high"]:
            level = "high"
            interpretation = "High confidence - results are very reliable"
            color = "green"
        elif confidence >= self.confidence_thresholds["medium"]:
            level = "medium"
            interpretation = "Medium confidence - results are generally reliable"
            color = "yellow"
        elif confidence >= self.confidence_thresholds["low"]:
            level = "low"
            interpretation = "Low confidence - results may need review"
            color = "orange"
        else:
            level = "very_low"
            interpretation = (
                "Very low confidence - results should be reviewed carefully"
            )
            color = "red"

        return {
            "score": round(confidence * 100, 1),
            "level": level,
            "interpretation": interpretation,
            "color": color,
            "recommendation": self._get_confidence_recommendation(level),
        }

    def _generate_performance_insights(
        self, detailed_grades: List[Dict[str, Any]], overall_percentage: float
    ) -> List[str]:
        """Generate insights about the student's performance."""
        insights = []

        if not detailed_grades:
            return insights

        # Handle None or invalid percentage values
        try:
            overall_percentage = float(overall_percentage) if overall_percentage is not None else 0.0
            overall_percentage = max(0.0, min(100.0, overall_percentage))  # Clamp between 0 and 100
        except (TypeError, ValueError):
            overall_percentage = 0.0

        # Overall performance insight
        if overall_percentage >= 90:
            insights.append(
                "Excellent overall performance with strong understanding across topics"
            )
        elif overall_percentage >= 80:
            insights.append(
                "Good overall performance with solid grasp of most concepts"
            )
        elif overall_percentage >= 70:
            insights.append(
                "Fair performance with room for improvement in several areas"
            )
        elif overall_percentage >= 60:
            insights.append("Below average performance - additional study recommended")
        else:
            insights.append("Poor performance - significant improvement needed")

        # Analyze consistency
        percentages = []
        for grade in detailed_grades:
            try:
                score = grade.get("score", 0)
                max_score = grade.get("max_score", 10)
                score = float(score) if score is not None else 0.0
                max_score = float(max_score) if max_score is not None else 10.0
                percentage = (score / max_score * 100) if max_score > 0 else 0
                # Ensure percentage is a valid number
                if percentage is not None and not (isinstance(percentage, float) and (percentage != percentage)):  # Check for NaN
                    percentages.append(float(percentage))
                else:
                    percentages.append(0.0)
            except (TypeError, ValueError):
                percentages.append(0.0)

        # Filter out any None values that might have slipped through
        percentages = [p for p in percentages if p is not None and isinstance(p, (int, float))]

        if len(percentages) > 1:
            try:
                std_dev = statistics.stdev(percentages)
                if std_dev < 10:
                    insights.append("Consistent performance across all questions")
                elif std_dev > 25:
                    insights.append(
                        "Highly variable performance - some topics well understood, others need work"
                    )
                else:
                    insights.append(
                        "Moderate variation in performance across different topics"
                    )
            except (TypeError, ValueError, statistics.StatisticsError):
                # If we can't calculate std dev, skip consistency analysis
                pass

        # Identify strengths and weaknesses
        if percentages and len(percentages) > 0:
            try:
                max_score_idx = percentages.index(max(percentages))
                min_score_idx = percentages.index(min(percentages))

                if max_score_idx < len(detailed_grades):
                    best_question = detailed_grades[max_score_idx].get(
                        "question_id", f"Q{max_score_idx + 1}"
                    )
                    insights.append(f"Strongest performance on {best_question}")

                if (
                    min_score_idx < len(detailed_grades)
                    and len(percentages) > 1
                    and max(percentages) - min(percentages) > 20
                ):
                    worst_question = detailed_grades[min_score_idx].get(
                        "question_id", f"Q{min_score_idx + 1}"
                    )
                    insights.append(f"Needs improvement on {worst_question}")
            except (ValueError, TypeError):
                # If we can't find max/min, skip this analysis
                pass

        return insights

    def _calculate_question_analytics(
        self, detailed_grades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate analytics for individual questions."""
        if not detailed_grades:
            return {}

        question_data = []
        for grade in detailed_grades:
            try:
                score = grade.get("score", 0)
                max_score = grade.get("max_score", 10)
                score = float(score) if score is not None else 0.0
                max_score = float(max_score) if max_score is not None else 10.0
                percentage = (score / max_score * 100) if max_score > 0 else 0
            except (TypeError, ValueError):
                score = 0.0
                max_score = 10.0
                percentage = 0.0

            question_data.append(
                {
                    "question_id": grade.get("question_id", "Unknown"),
                    "score": score,
                    "max_score": max_score,
                    "percentage": round(percentage, 1),
                    "difficulty_assessment": self._assess_question_difficulty(
                        percentage
                    ),
                    "feedback_length": len(grade.get("feedback", "")),
                    "has_detailed_feedback": len(grade.get("feedback", "")) > 50,
                }
            )

        return {
            "questions": question_data,
            "most_difficult": (
                min(question_data, key=lambda x: x["percentage"])
                if question_data
                else None
            ),
            "easiest": (
                max(question_data, key=lambda x: x["percentage"])
                if question_data
                else None
            ),
            "average_feedback_length": (
                round(statistics.mean([q["feedback_length"] for q in question_data]), 1)
                if question_data
                else 0
            ),
        }

    def _format_processing_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format processing metadata for display."""
        formatted = {}

        # Processing time
        if "processing_time" in metadata:
            time_sec = float(metadata["processing_time"])
            if time_sec < 1:
                formatted["processing_time_display"] = f"{time_sec * 1000:.0f}ms"
            elif time_sec < 60:
                formatted["processing_time_display"] = f"{time_sec:.1f}s"
            else:
                formatted["processing_time_display"] = f"{time_sec / 60:.1f}m"

        # Model information
        if "model_used" in metadata:
            formatted["model_display"] = metadata["model_used"]

        # Confidence
        if "confidence_score" in metadata:
            conf = float(metadata["confidence_score"])
            formatted["confidence_display"] = f"{conf * 100:.1f}%"

        # Version
        if "version" in metadata:
            formatted["version_display"] = metadata["version"]

        # Additional processing info
        formatted["processed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return formatted

    def _calculate_result_statistics(
        self, result: Dict[str, Any], detailed_grades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate comprehensive result statistics."""
        stats = {
            "total_score": result.get("score", 0),
            "max_possible_score": result.get("max_score", 0),
            "percentage": result.get("percentage", 0),
            "letter_grade": self._calculate_letter_grade(result.get("percentage", 0)),
            "grade_points": self._calculate_grade_points(result.get("percentage", 0)),
        }

        if detailed_grades:
            # Question-level statistics
            total_questions = len(detailed_grades)
            questions_passed = 0
            for g in detailed_grades:
                try:
                    score = g.get("score", 0)
                    max_score = g.get("max_score", 10)
                    score = float(score) if score is not None else 0.0
                    max_score = float(max_score) if max_score is not None else 10.0
                    if max_score > 0 and (score / max_score) >= 0.6:
                        questions_passed += 1
                except (TypeError, ValueError):
                    continue

            stats.update(
                {
                    "total_questions": total_questions,
                    "questions_passed": questions_passed,
                    "pass_rate": (
                        round((questions_passed / total_questions) * 100, 1)
                        if total_questions > 0
                        else 0
                    ),
                    "questions_failed": total_questions - questions_passed,
                }
            )

        return stats

    def _assess_grading_quality(
        self, detailed_grades: List[Dict[str, Any]], result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess the quality of the grading process."""
        quality = {
            "has_detailed_feedback": bool(detailed_grades),
            "feedback_completeness": 0,
            "scoring_consistency": "unknown",
            "overall_quality": "unknown",
        }

        if detailed_grades:
            # Check feedback completeness
            feedback_scores = []
            for grade in detailed_grades:
                feedback = grade.get("feedback", "")
                if len(feedback) > 100:
                    feedback_scores.append(3)  # Detailed
                elif len(feedback) > 30:
                    feedback_scores.append(2)  # Moderate
                elif len(feedback) > 0:
                    feedback_scores.append(1)  # Brief
                else:
                    feedback_scores.append(0)  # None

            quality["feedback_completeness"] = (
                round(statistics.mean(feedback_scores) * 25, 1)
                if feedback_scores
                else 0
            )

            # Assess scoring consistency (simplified)
            percentages = []
            for g in detailed_grades:
                try:
                    score = g.get("score", 0)
                    max_score = g.get("max_score", 10)
                    score = float(score) if score is not None else 0.0
                    max_score = float(max_score) if max_score is not None else 10.0
                    percentage = (score / max_score * 100) if max_score > 0 else 0
                    percentages.append(percentage)
                except (TypeError, ValueError):
                    percentages.append(0.0)

            if len(percentages) > 1:
                consistency_cv = (
                    statistics.stdev(percentages) / statistics.mean(percentages)
                    if statistics.mean(percentages) > 0
                    else 1
                )
                if consistency_cv < 0.3:
                    quality["scoring_consistency"] = "high"
                elif consistency_cv < 0.6:
                    quality["scoring_consistency"] = "medium"
                else:
                    quality["scoring_consistency"] = "low"

        # Overall quality assessment
        confidence = result.get("confidence", 0)
        # Ensure confidence is a valid number
        try:
            confidence = float(confidence) if confidence is not None else 0.0
        except (TypeError, ValueError):
            confidence = 0.0

        if (
            quality["has_detailed_feedback"]
            and quality["feedback_completeness"] > 50
            and confidence > 0.8
        ):
            quality["overall_quality"] = "high"
        elif quality["has_detailed_feedback"] and confidence > 0.6:
            quality["overall_quality"] = "medium"
        else:
            quality["overall_quality"] = "low"

        return quality

    # Helper methods
    def _get_performance_level(self, percentage: float) -> str:
        """Get performance level based on percentage."""
        if percentage >= 90:
            return "excellent"
        elif percentage >= 80:
            return "good"
        elif percentage >= 60:
            return "fair"
        else:
            return "poor"

    def _get_score_color(self, percentage: float) -> str:
        """Get color coding for score display."""
        if percentage >= 90:
            return "text-green-600"
        elif percentage >= 80:
            return "text-blue-600"
        elif percentage >= 60:
            return "text-yellow-600"
        else:
            return "text-red-600"

    def _analyze_feedback_sentiment(self, feedback: str) -> str:
        """Simple sentiment analysis of feedback."""
        if not feedback:
            return "neutral"

        feedback_lower = feedback.lower()
        positive_words = [
            "good",
            "excellent",
            "correct",
            "well",
            "strong",
            "clear",
            "accurate",
        ]
        negative_words = [
            "poor",
            "incorrect",
            "missing",
            "weak",
            "unclear",
            "incomplete",
            "wrong",
        ]

        positive_count = sum(1 for word in positive_words if word in feedback_lower)
        negative_count = sum(1 for word in negative_words if word in feedback_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to specified length."""
        if not text or len(text) <= max_length:
            return text
        return text[:max_length] + "..."

    def _get_confidence_recommendation(self, level: str) -> str:
        """Get recommendation based on confidence level."""
        recommendations = {
            "high": "Results are reliable and can be used as-is",
            "medium": "Results are generally good but may benefit from spot checking",
            "low": "Consider reviewing the results manually",
            "very_low": "Manual review strongly recommended before using these results",
        }
        return recommendations.get(level, "No recommendation available")

    def _assess_question_difficulty(self, percentage: float) -> str:
        """Assess question difficulty based on student performance."""
        if percentage >= 90:
            return "easy"
        elif percentage >= 70:
            return "moderate"
        elif percentage >= 50:
            return "difficult"
        else:
            return "very_difficult"

    def _calculate_letter_grade(self, percentage: float) -> str:
        """Calculate letter grade from percentage."""
        if percentage >= 97:
            return "A+"
        elif percentage >= 93:
            return "A"
        elif percentage >= 90:
            return "A-"
        elif percentage >= 87:
            return "B+"
        elif percentage >= 83:
            return "B"
        elif percentage >= 80:
            return "B-"
        elif percentage >= 77:
            return "C+"
        elif percentage >= 73:
            return "C"
        elif percentage >= 70:
            return "C-"
        elif percentage >= 67:
            return "D+"
        elif percentage >= 63:
            return "D"
        elif percentage >= 60:
            return "D-"
        else:
            return "F"

    def _calculate_grade_points(self, percentage: float) -> float:
        """Calculate grade points (4.0 scale) from percentage."""
        if percentage >= 97:
            return 4.0
        elif percentage >= 93:
            return 4.0
        elif percentage >= 90:
            return 3.7
        elif percentage >= 87:
            return 3.3
        elif percentage >= 83:
            return 3.0
        elif percentage >= 80:
            return 2.7
        elif percentage >= 77:
            return 2.3
        elif percentage >= 73:
            return 2.0
        elif percentage >= 70:
            return 1.7
        elif percentage >= 67:
            return 1.3
        elif percentage >= 63:
            return 1.0
        elif percentage >= 60:
            return 0.7
        else:
            return 0.0

# Global instance
enhanced_result_service = EnhancedResultService()
