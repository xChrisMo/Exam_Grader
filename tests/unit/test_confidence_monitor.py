"""
Unit tests for the confidence monitoring service
"""

from datetime import datetime, timedelta
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

from src.services.confidence_monitor import (
    ConfidenceMonitor, ConfidenceLevel, QualityFlag,
    ConfidenceMetrics, QualityAssessment
)
from src.database.models import TrainingQuestion, TrainingGuide, TrainingSession

class TestConfidenceMonitor:
    """Test confidence monitoring functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.monitor = ConfidenceMonitor()

    def test_classify_confidence_levels(self):
        """Test confidence level classification"""
        # Test high confidence
        assert self.monitor._classify_confidence(0.9) == ConfidenceLevel.HIGH
        assert self.monitor._classify_confidence(0.8) == ConfidenceLevel.HIGH

        # Test medium confidence
        assert self.monitor._classify_confidence(0.7) == ConfidenceLevel.MEDIUM
        assert self.monitor._classify_confidence(0.6) == ConfidenceLevel.MEDIUM

        # Test low confidence
        assert self.monitor._classify_confidence(0.5) == ConfidenceLevel.LOW
        assert self.monitor._classify_confidence(0.4) == ConfidenceLevel.LOW

        # Test critical confidence
        assert self.monitor._classify_confidence(0.3) == ConfidenceLevel.CRITICAL
        assert self.monitor._classify_confidence(0.1) == ConfidenceLevel.CRITICAL

    def test_check_consistency(self):
        """Test question-answer consistency checking"""
        # Create mock question with consistent Q&A
        question = Mock()
        question.question_text = "What is the capital of France?"
        question.expected_answer = "The capital of France is Paris"

        consistency_score = self.monitor._check_consistency(question)
        assert 0.0 <= consistency_score <= 1.0

        # Test with inconsistent Q&A
        question.question_text = "What is the capital of France?"
        question.expected_answer = "The largest ocean is Pacific"

        consistency_score = self.monitor._check_consistency(question)
        assert consistency_score < 0.5  # Should be low consistency

    def test_check_clarity(self):
        """Test question clarity checking"""
        # Create mock question with clear text
        question = Mock()
        question.question_text = "What is the capital of France?"

        clarity_score = self.monitor._check_clarity(question)
        assert clarity_score > 0.5

        # Test with unclear text
        question.question_text = "xyz abc def"

        clarity_score = self.monitor._check_clarity(question)
        assert clarity_score < 0.8  # Should be lower clarity

        # Test with empty text
        question.question_text = ""

        clarity_score = self.monitor._check_clarity(question)
        assert clarity_score == 0.0

    def test_check_completeness(self):
        """Test question completeness checking"""
        # Create complete question
        question = Mock()
        question.question_text = "What is the capital of France?"
        question.expected_answer = "Paris"
        question.point_value = 10.0
        question.question_number = "1"

        completeness_score = self.monitor._check_completeness(question)
        assert completeness_score == 1.0

        # Test incomplete question
        question.question_text = ""
        question.expected_answer = None
        question.point_value = 0
        question.question_number = ""

        completeness_score = self.monitor._check_completeness(question)
        assert completeness_score == 0.0

    def test_has_formatting_issues(self):
        """Test formatting issue detection"""
        # Create question with good formatting
        question = Mock()
        question.question_text = "What is the capital of France?"

        has_issues = self.monitor._has_formatting_issues(question)
        assert has_issues is False

        # Test with formatting issues
        question.question_text = "  What is the capital of France?  "  # Leading/trailing spaces

        has_issues = self.monitor._has_formatting_issues(question)
        assert has_issues is True

        # Test with multiple spaces
        question.question_text = "What  is  the  capital?"

        has_issues = self.monitor._has_formatting_issues(question)
        assert has_issues is True

    def test_calculate_priority(self):
        """Test priority calculation"""
        # High priority (critical confidence)
        priority = self.monitor._calculate_priority(
            ConfidenceLevel.CRITICAL,
            [QualityFlag.LOW_CONFIDENCE, QualityFlag.UNCLEAR_QUESTION],
            0.2
        )
        assert priority == 5  # Maximum priority

        # Medium priority
        priority = self.monitor._calculate_priority(
            ConfidenceLevel.MEDIUM,
            [QualityFlag.FORMATTING_ISSUE],
            0.6
        )
        assert 2 <= priority <= 4

        # Low priority
        priority = self.monitor._calculate_priority(
            ConfidenceLevel.HIGH,
            [],
            0.9
        )
        assert priority == 1

    def test_generate_assessment_notes(self):
        """Test assessment notes generation"""
        question = Mock()
        question.extraction_confidence = 0.7

        flags = [QualityFlag.LOW_CONFIDENCE, QualityFlag.FORMATTING_ISSUE]
        quality_score = 0.6

        notes = self.monitor._generate_assessment_notes(question, flags, quality_score)

        assert "Quality Score: 0.60" in notes
        assert "Confidence: 0.70" in notes
        assert "Low Confidence" in notes
        assert "Formatting Issue" in notes

    def test_get_improvement_suggestions(self):
        """Test improvement suggestions generation"""
        assessment = Mock()
        assessment.flags = [
            QualityFlag.LOW_CONFIDENCE,
            QualityFlag.INCONSISTENT_ANSWER,
            QualityFlag.UNCLEAR_QUESTION
        ]
        assessment.quality_score = 0.4

        suggestions = self.monitor._get_improvement_suggestions(assessment)

        assert len(suggestions) >= 3  # At least one suggestion per flag
        assert any("review" in s.lower() for s in suggestions)
        assert any("alignment" in s.lower() for s in suggestions)
        assert any("clarify" in s.lower() for s in suggestions)

    @patch('src.services.confidence_monitor.db.session')
    def test_analyze_session_confidence_empty(self, mock_db_session):
        """Test confidence analysis with no questions"""
        # Mock empty query result
        mock_db_session.query.return_value.filter_by.return_value.all.return_value = []

        metrics = self.monitor.analyze_session_confidence("test_session")

        assert metrics.total_questions == 0
        assert metrics.avg_confidence == 0.0
        assert metrics.high_confidence_count == 0

    @patch('src.services.confidence_monitor.db.session')
    def test_analyze_session_confidence_with_data(self, mock_db_session):
        """Test confidence analysis with sample data"""
        # Create mock guides and questions
        mock_guide = Mock()
        mock_guide.id = "guide_1"

        mock_questions = []
        confidence_scores = [0.9, 0.8, 0.7, 0.5, 0.3]

        for i, confidence in enumerate(confidence_scores):
            question = Mock()
            question.extraction_confidence = confidence
            mock_questions.append(question)

        # Mock database queries
        mock_db_session.query.return_value.filter_by.return_value.all.side_effect = [
            [mock_guide],  # First call returns guides
            mock_questions  # Second call returns questions
        ]

        metrics = self.monitor.analyze_session_confidence("test_session")

        assert metrics.total_questions == 5
        assert metrics.avg_confidence == 0.64  # Average of confidence scores
        assert metrics.high_confidence_count == 2  # 0.9, 0.8
        assert metrics.medium_confidence_count == 1  # 0.7
        assert metrics.low_confidence_count == 1  # 0.5
        assert metrics.critical_confidence_count == 1  # 0.3

    def test_assess_question_quality(self):
        """Test question quality assessment"""
        # Create Flask app context for database operations
        app = Flask(__name__)
        app.config['TESTING'] = True

        with app.app_context():
            # Create mock question
            question = Mock()
            question.id = 1
            question.extraction_confidence = 0.7
            question.question_text = "What is the capital of France?"
            question.expected_answer = "Paris"
            question.point_value = 10.0
            question.question_number = "1"
            question.manual_review_required = False

            assessment = self.monitor.assess_question_quality(question)

            assert isinstance(assessment, QualityAssessment)
            assert assessment.question_id == 1
            assert assessment.confidence_level == ConfidenceLevel.MEDIUM
            assert 0.0 <= assessment.quality_score <= 1.0
            assert isinstance(assessment.flags, list)
            assert isinstance(assessment.review_required, bool)
            assert 1 <= assessment.priority <= 5
            assert isinstance(assessment.assessment_notes, str)

    @patch('src.services.confidence_monitor.db.session')
    def test_flag_low_confidence_items(self, mock_db_session):
        """Test flagging of low confidence items"""
        # Create mock data
        mock_guide = Mock()
        mock_guide.id = "guide_1"

        # Create questions with varying confidence
        mock_questions = []
        for i, confidence in enumerate([0.9, 0.5, 0.3]):  # High, low, critical
            question = Mock()
            question.id = i
            question.extraction_confidence = confidence
            question.question_text = f"Question {i}"
            question.expected_answer = f"Answer {i}"
            question.point_value = 10.0
            question.question_number = str(i)
            question.manual_review_required = False
            mock_questions.append(question)

        mock_db_session.query.return_value.filter_by.return_value.all.side_effect = [
            [mock_guide],  # First call returns guides
            mock_questions  # Second call returns questions
        ]

        flagged_items = self.monitor.flag_low_confidence_items("test_session", threshold=0.6)

        # Should flag 2 items (confidence 0.5 and 0.3)
        assert len(flagged_items) == 2

        # Check that items are sorted by priority
        priorities = [item['quality_assessment'].priority for item in flagged_items]
        assert priorities == sorted(priorities, reverse=True)

    def test_update_confidence_after_review(self):
        """Test confidence update after manual review"""
        with patch('src.services.confidence_monitor.db.session') as mock_db_session:
            # Create mock question
            mock_question = Mock()
            mock_question.id = 1
            mock_question.extraction_confidence = 0.5
            mock_question.manual_review_required = True
            mock_question.context = None

            mock_db_session.query.return_value.get.return_value = mock_question

            # Test successful update
            success = self.monitor.update_confidence_after_review(
                question_id=1,
                new_confidence=0.8,
                reviewer_notes="Reviewed and improved"
            )

            assert success is True
            assert mock_question.extraction_confidence == 0.8
            assert mock_question.manual_review_required is False
            mock_db_session.commit.assert_called_once()

    def test_generate_trend_recommendations(self):
        """Test trend-based recommendations"""
        # Test with improving trend
        trend_data = {
            'avg_confidence': [0.5, 0.6, 0.7, 0.8],
            'improvement_trend': 0.2
        }

        recommendations = self.monitor._generate_trend_recommendations(trend_data)

        assert len(recommendations) > 0
        assert any("improving" in rec.lower() for rec in recommendations)

        # Test with declining trend
        trend_data['improvement_trend'] = -0.2

        recommendations = self.monitor._generate_trend_recommendations(trend_data)

        assert any("declining" in rec.lower() for rec in recommendations)

        # Test with low overall confidence
        trend_data['avg_confidence'] = [0.3, 0.4, 0.3, 0.4]

        recommendations = self.monitor._generate_trend_recommendations(trend_data)

        assert any("low" in rec.lower() for rec in recommendations)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])