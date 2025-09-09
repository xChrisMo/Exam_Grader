"""
Confidence Monitoring and Quality Assurance System

Provides comprehensive confidence monitoring, quality assurance checks,
and manual review workflows for training questions and answers.
"""

from datetime import datetime, timedelta
import statistics
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass

from src.database.models import TrainingQuestion, TrainingSession, TrainingGuide
from src.database.models import db
from utils.logger import logger

class ConfidenceLevel(Enum):
    """Confidence level classifications"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"

class ReviewStatus(Enum):
    """Review status for quality assurance"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"

class QualityFlag(Enum):
    """Quality flags for questions"""
    LOW_CONFIDENCE = "low_confidence"
    INCONSISTENT_ANSWER = "inconsistent_answer"
    UNCLEAR_QUESTION = "unclear_question"
    POTENTIAL_ERROR = "potential_error"
    DUPLICATE_CONTENT = "duplicate_content"
    FORMATTING_ISSUE = "formatting_issue"
    LANGUAGE_ISSUE = "language_issue"

@dataclass
class ConfidenceMetrics:
    """Confidence metrics for a set of questions"""
    total_questions: int
    avg_confidence: float
    median_confidence: float
    std_deviation: float
    high_confidence_count: int
    medium_confidence_count: int
    low_confidence_count: int
    critical_confidence_count: int
    confidence_distribution: Dict[str, int]

@dataclass
class QualityAssessment:
    """Quality assessment results"""
    question_id: int
    confidence_level: ConfidenceLevel
    quality_score: float
    flags: List[QualityFlag]
    review_required: bool
    priority: int
    assessment_notes: str

class ConfidenceMonitor:
    """
    Confidence monitoring and quality assurance system
    """

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.8
    MEDIUM_CONFIDENCE_THRESHOLD = 0.6
    LOW_CONFIDENCE_THRESHOLD = 0.4

    # Quality score weights
    CONFIDENCE_WEIGHT = 0.4
    CONSISTENCY_WEIGHT = 0.3
    CLARITY_WEIGHT = 0.2
    COMPLETENESS_WEIGHT = 0.1

    def __init__(self):
        """Initialize confidence monitor"""
        self.review_queue = []
        self.quality_metrics = {}

    def analyze_session_confidence(self, session_id: str) -> ConfidenceMetrics:
        """
        Analyze confidence metrics for a training session

        Args:
            session_id: Training session ID

        Returns:
            ConfidenceMetrics object with detailed analysis
        """
        try:
            # Get all questions for the session through guides
            guides = db.session.query(TrainingGuide).filter_by(session_id=session_id).all()
            questions = []
            for guide in guides:
                guide_questions = db.session.query(TrainingQuestion).filter_by(guide_id=guide.id).all()
                questions.extend(guide_questions)

            if not questions:
                return ConfidenceMetrics(
                    total_questions=0,
                    avg_confidence=0.0,
                    median_confidence=0.0,
                    std_deviation=0.0,
                    high_confidence_count=0,
                    medium_confidence_count=0,
                    low_confidence_count=0,
                    critical_confidence_count=0,
                    confidence_distribution={}
                )

            # Extract confidence scores
            confidence_scores = [q.extraction_confidence for q in questions if q.extraction_confidence is not None]

            if not confidence_scores:
                logger.warning(f"No confidence scores found for session {session_id}")
                return ConfidenceMetrics(
                    total_questions=len(questions),
                    avg_confidence=0.0,
                    median_confidence=0.0,
                    std_deviation=0.0,
                    high_confidence_count=0,
                    medium_confidence_count=0,
                    low_confidence_count=0,
                    critical_confidence_count=0,
                    confidence_distribution={}
                )

            # Calculate basic statistics
            avg_confidence = statistics.mean(confidence_scores)
            median_confidence = statistics.median(confidence_scores)
            std_deviation = statistics.stdev(confidence_scores) if len(confidence_scores) > 1 else 0.0

            # Classify confidence levels
            high_count = sum(1 for score in confidence_scores if score >= self.HIGH_CONFIDENCE_THRESHOLD)
            medium_count = sum(1 for score in confidence_scores
                             if self.MEDIUM_CONFIDENCE_THRESHOLD <= score < self.HIGH_CONFIDENCE_THRESHOLD)
            low_count = sum(1 for score in confidence_scores
                          if self.LOW_CONFIDENCE_THRESHOLD <= score < self.MEDIUM_CONFIDENCE_THRESHOLD)
            critical_count = sum(1 for score in confidence_scores if score < self.LOW_CONFIDENCE_THRESHOLD)

            # Create distribution histogram
            distribution = {}
            for i in range(0, 11):
                range_start = i / 10.0
                range_end = (i + 1) / 10.0
                count = sum(1 for score in confidence_scores
                          if range_start <= score < range_end)
                distribution[f"{range_start:.1f}-{range_end:.1f}"] = count

            metrics = ConfidenceMetrics(
                total_questions=len(questions),
                avg_confidence=avg_confidence,
                median_confidence=median_confidence,
                std_deviation=std_deviation,
                high_confidence_count=high_count,
                medium_confidence_count=medium_count,
                low_confidence_count=low_count,
                critical_confidence_count=critical_count,
                confidence_distribution=distribution
            )

            logger.info(f"Confidence analysis completed for session {session_id}: "
                       f"avg={avg_confidence:.3f}, high={high_count}, low={low_count}, critical={critical_count}")

            return metrics

        except Exception as e:
            logger.error(f"Error analyzing session confidence {session_id}: {e}")
            raise

    def assess_question_quality(self, question: TrainingQuestion) -> QualityAssessment:
        """
        Assess the quality of a training question

        Args:
            question: TrainingQuestion object

        Returns:
            QualityAssessment object
        """
        try:
            flags = []
            quality_score = 0.0

            # Confidence assessment
            confidence_score = question.extraction_confidence or 0.0
            confidence_level = self._classify_confidence(confidence_score)

            # Quality scoring components
            confidence_component = confidence_score * self.CONFIDENCE_WEIGHT

            # Consistency check
            consistency_score = self._check_consistency(question)
            consistency_component = consistency_score * self.CONSISTENCY_WEIGHT

            # Clarity check
            clarity_score = self._check_clarity(question)
            clarity_component = clarity_score * self.CLARITY_WEIGHT

            # Completeness check
            completeness_score = self._check_completeness(question)
            completeness_component = completeness_score * self.COMPLETENESS_WEIGHT

            # Calculate overall quality score
            quality_score = (confidence_component + consistency_component +
                           clarity_component + completeness_component)

            # Determine flags based on assessment
            if confidence_score < self.LOW_CONFIDENCE_THRESHOLD:
                flags.append(QualityFlag.LOW_CONFIDENCE)

            if consistency_score < 0.5:
                flags.append(QualityFlag.INCONSISTENT_ANSWER)

            if clarity_score < 0.5:
                flags.append(QualityFlag.UNCLEAR_QUESTION)

            if completeness_score < 0.5:
                flags.append(QualityFlag.POTENTIAL_ERROR)

            # Check for formatting issues
            if self._has_formatting_issues(question):
                flags.append(QualityFlag.FORMATTING_ISSUE)

            # Determine if manual review is required
            review_required = (confidence_level in [ConfidenceLevel.LOW, ConfidenceLevel.CRITICAL] or
                             len(flags) > 2 or
                             quality_score < 0.6)

            # Calculate priority (1-5, where 5 is highest priority)
            priority = self._calculate_priority(confidence_level, flags, quality_score)

            # Generate assessment notes
            notes = self._generate_assessment_notes(question, flags, quality_score)

            assessment = QualityAssessment(
                question_id=question.id,
                confidence_level=confidence_level,
                quality_score=quality_score,
                flags=flags,
                review_required=review_required,
                priority=priority,
                assessment_notes=notes
            )

            # Update question with review requirement
            if review_required and not question.manual_review_required:
                question.manual_review_required = True
                db.session.commit()

            return assessment

        except Exception as e:
            logger.error(f"Error assessing question quality {question.id}: {e}")
            raise

    def flag_low_confidence_items(self, session_id: str, threshold: float = 0.6) -> List[Dict]:
        """
        Flag items with confidence below threshold

        Args:
            session_id: Training session ID
            threshold: Confidence threshold for flagging

        Returns:
            List of flagged items with details
        """
        try:
            flagged_items = []

            # Get all questions for the session
            guides = db.session.query(TrainingGuide).filter_by(session_id=session_id).all()

            for guide in guides:
                questions = db.session.query(TrainingQuestion).filter_by(guide_id=guide.id).all()

                for question in questions:
                    if (question.extraction_confidence is not None and
                        question.extraction_confidence < threshold):

                        # Assess quality for detailed information
                        assessment = self.assess_question_quality(question)

                        flagged_item = {
                            'question_id': question.id,
                            'guide_id': guide.id,
                            'question_number': question.question_number,
                            'confidence_score': question.extraction_confidence,
                            'quality_assessment': assessment,
                            'suggested_actions': self._get_improvement_suggestions(assessment)
                        }

                        flagged_items.append(flagged_item)

            # Sort by priority (highest first)
            flagged_items.sort(key=lambda x: x['quality_assessment'].priority, reverse=True)

            logger.info(f"Flagged {len(flagged_items)} low-confidence items for session {session_id}")

            return flagged_items

        except Exception as e:
            logger.error(f"Error flagging low confidence items for session {session_id}: {e}")
            return []

    def track_confidence_trends(self, user_id: int, days: int = 30) -> Dict[str, Union[List, float]]:
        """
        Track confidence trends over time for a user

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            Dict containing trend analysis
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Get sessions within the time period
            sessions = db.session.query(TrainingSession).filter(
                TrainingSession.user_id == user_id,
                TrainingSession.created_at >= cutoff_date
            ).order_by(TrainingSession.created_at).all()

            trend_data = {
                'dates': [],
                'avg_confidence': [],
                'session_count': [],
                'improvement_trend': 0.0,
                'recommendations': []
            }

            for session in sessions:
                metrics = self.analyze_session_confidence(session.id)

                trend_data['dates'].append(session.created_at.strftime('%Y-%m-%d'))
                trend_data['avg_confidence'].append(metrics.avg_confidence)
                trend_data['session_count'].append(metrics.total_questions)

            # Calculate improvement trend
            if len(trend_data['avg_confidence']) >= 2:
                recent_avg = statistics.mean(trend_data['avg_confidence'][-3:])
                early_avg = statistics.mean(trend_data['avg_confidence'][:3])
                trend_data['improvement_trend'] = recent_avg - early_avg

            # Generate recommendations based on trends
            trend_data['recommendations'] = self._generate_trend_recommendations(trend_data)

            return trend_data

        except Exception as e:
            logger.error(f"Error tracking confidence trends for user {user_id}: {e}")
            return {'error': str(e)}

    def get_improvement_suggestions(self, assessment: QualityAssessment) -> List[str]:
        """
        Get specific improvement suggestions based on quality assessment

        Args:
            assessment: QualityAssessment object

        Returns:
            List of improvement suggestions
        """
        return self._get_improvement_suggestions(assessment)

    def update_confidence_after_review(self, question_id: int, new_confidence: float,
                                     reviewer_notes: str) -> bool:
        """
        Update confidence score after manual review

        Args:
            question_id: Question ID
            new_confidence: Updated confidence score
            reviewer_notes: Notes from reviewer

        Returns:
            Success status
        """
        try:
            question = db.session.query(TrainingQuestion).get(question_id)
            if not question:
                logger.error(f"Question {question_id} not found")
                return False

            # Store original confidence for audit
            original_confidence = question.extraction_confidence

            # Update confidence and review status
            question.extraction_confidence = new_confidence
            question.manual_review_required = False

            # Add review metadata to context
            if question.context:
                context = eval(question.context) if isinstance(question.context, str) else question.context
            else:
                context = {}

            context['manual_review'] = {
                'original_confidence': original_confidence,
                'updated_confidence': new_confidence,
                'reviewer_notes': reviewer_notes,
                'review_date': datetime.now().isoformat()
            }

            question.context = str(context)

            db.session.commit()

            logger.info(f"Updated confidence for question {question_id}: {original_confidence} -> {new_confidence}")

            return True

        except Exception as e:
            logger.error(f"Error updating confidence for question {question_id}: {e}")
            db.session.rollback()
            return False

    def _classify_confidence(self, confidence_score: float) -> ConfidenceLevel:
        """Classify confidence score into levels"""
        if confidence_score >= self.HIGH_CONFIDENCE_THRESHOLD:
            return ConfidenceLevel.HIGH
        elif confidence_score >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            return ConfidenceLevel.MEDIUM
        elif confidence_score >= self.LOW_CONFIDENCE_THRESHOLD:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.CRITICAL

    def _check_consistency(self, question: TrainingQuestion) -> float:
        """Check consistency of question and answer"""
        try:
            # Basic consistency checks
            score = 1.0

            # Check if question text and expected answer are related
            if question.question_text and question.expected_answer:
                question_words = set(question.question_text.lower().split())
                answer_words = set(question.expected_answer.lower().split())

                # Calculate word overlap (simple consistency metric)
                overlap = len(question_words.intersection(answer_words))
                total_unique = len(question_words.union(answer_words))

                if total_unique > 0:
                    overlap_ratio = overlap / total_unique
                    score = min(1.0, overlap_ratio * 2)  # Scale appropriately

            return score

        except Exception:
            return 0.5  # Default neutral score

    def _check_clarity(self, question: TrainingQuestion) -> float:
        """Check clarity of question text"""
        try:
            score = 1.0

            if not question.question_text:
                return 0.0

            text = question.question_text.strip()

            # Basic clarity metrics
            if len(text) < 10:
                score -= 0.3  # Too short

            if len(text) > 500:
                score -= 0.2  # Potentially too long

            # Check for question marks or clear question structure
            if '?' not in text and not any(word in text.lower() for word in ['what', 'how', 'why', 'when', 'where', 'which']):
                score -= 0.3  # Doesn't appear to be a clear question

            return max(0.0, score)

        except Exception:
            return 0.5

    def _check_completeness(self, question: TrainingQuestion) -> float:
        """Check completeness of question data"""
        try:
            score = 1.0

            # Check required fields
            if not question.question_text:
                score -= 0.4

            if not question.expected_answer:
                score -= 0.3

            if question.point_value <= 0:
                score -= 0.2

            if not question.question_number:
                score -= 0.1

            return max(0.0, score)

        except Exception:
            return 0.5

    def _has_formatting_issues(self, question: TrainingQuestion) -> bool:
        """Check for formatting issues"""
        try:
            if not question.question_text:
                return True

            text = question.question_text

            # Check for common formatting issues
            issues = [
                len(text.strip()) != len(text),  # Leading/trailing whitespace
                '  ' in text,  # Multiple consecutive spaces
                text != text.replace('\t', ' '),  # Tab characters
                any(ord(char) > 127 for char in text[:100])  # Non-ASCII characters in first 100 chars
            ]

            return any(issues)

        except Exception:
            return False

    def _calculate_priority(self, confidence_level: ConfidenceLevel, flags: List[QualityFlag],
                          quality_score: float) -> int:
        """Calculate review priority (1-5)"""
        priority = 1

        # Base priority on confidence level
        if confidence_level == ConfidenceLevel.CRITICAL:
            priority = 5
        elif confidence_level == ConfidenceLevel.LOW:
            priority = 4
        elif confidence_level == ConfidenceLevel.MEDIUM:
            priority = 2

        # Adjust based on number of flags
        priority += min(2, len(flags))

        # Adjust based on quality score
        if quality_score < 0.3:
            priority += 1

        return min(5, priority)

    def _generate_assessment_notes(self, question: TrainingQuestion, flags: List[QualityFlag],
                                 quality_score: float) -> str:
        """Generate assessment notes"""
        notes = []

        notes.append(f"Quality Score: {quality_score:.2f}")

        if question.extraction_confidence:
            notes.append(f"Confidence: {question.extraction_confidence:.2f}")

        if flags:
            flag_names = [flag.value.replace('_', ' ').title() for flag in flags]
            notes.append(f"Issues: {', '.join(flag_names)}")

        return "; ".join(notes)

    def _get_improvement_suggestions(self, assessment: QualityAssessment) -> List[str]:
        """Get improvement suggestions based on assessment"""
        suggestions = []

        for flag in assessment.flags:
            if flag == QualityFlag.LOW_CONFIDENCE:
                suggestions.append("Review question extraction and consider manual verification")
            elif flag == QualityFlag.INCONSISTENT_ANSWER:
                suggestions.append("Check alignment between question and expected answer")
            elif flag == QualityFlag.UNCLEAR_QUESTION:
                suggestions.append("Clarify question wording and structure")
            elif flag == QualityFlag.POTENTIAL_ERROR:
                suggestions.append("Verify question completeness and accuracy")
            elif flag == QualityFlag.FORMATTING_ISSUE:
                suggestions.append("Fix formatting and whitespace issues")

        if assessment.quality_score < 0.5:
            suggestions.append("Consider reprocessing this question with different parameters")

        return suggestions

    def _generate_trend_recommendations(self, trend_data: Dict) -> List[str]:
        """Generate recommendations based on confidence trends"""
        recommendations = []

        if not trend_data['avg_confidence']:
            return ["No data available for trend analysis"]

        avg_confidence = statistics.mean(trend_data['avg_confidence'])

        if avg_confidence < 0.5:
            recommendations.append("Overall confidence is low - consider reviewing training data quality")

        if trend_data['improvement_trend'] < -0.1:
            recommendations.append("Confidence is declining - review recent changes to training process")
        elif trend_data['improvement_trend'] > 0.1:
            recommendations.append("Confidence is improving - current approach is working well")

        if len(trend_data['avg_confidence']) > 5:
            recent_variance = statistics.stdev(trend_data['avg_confidence'][-5:])
            if recent_variance > 0.2:
                recommendations.append("High variance in recent sessions - ensure consistent training data")

        return recommendations

# Global instance
confidence_monitor = ConfidenceMonitor()