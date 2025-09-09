"""
Unit tests for TrainingReportService

Tests the report generation functionality including markdown reports,
PDF generation, and chart creation.
"""

from pathlib import Path
import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock

from tests.conftest import create_test_user
from src.services.training_report_service import TrainingReportService
from src.database.models import TrainingSession, TrainingQuestion, TrainingResult

class TestTrainingReportService:
    """Test cases for TrainingReportService"""

    @pytest.fixture
    def report_service(self, app, db_session):
        """Create a TrainingReportService instance for testing"""
        return TrainingReportService()

    @pytest.fixture
    def test_user(self, db_session):
        """Create a test user"""
        return create_test_user(db_session)

    @pytest.fixture
    def sample_session(self, test_user, db_session):
        """Create a sample training session with data"""
        session = TrainingSession(
            name='Test Training Session',
            user_id=test_user.id,
            status='completed',
            confidence_threshold=0.7,
            progress_percentage=100.0,
            total_questions=10,
            avg_confidence=0.82
        )
        db_session.add(session)
        db_session.commit()

        # Add sample questions
        questions = [
            TrainingQuestion(
                session_id=session.id,
                text='What is 2+2?',
                answer='4',
                confidence=0.95,
                question_type='calculation'
            ),
            TrainingQuestion(
                session_id=session.id,
                text='What is the capital of France?',
                answer='Paris',
                confidence=0.88,
                question_type='factual'
            ),
            TrainingQuestion(
                session_id=session.id,
                text='Explain photosynthesis',
                answer='Process by which plants convert light to energy',
                confidence=0.65,
                question_type='essay'
            )
        ]
        db_session.add_all(questions)
        db_session.commit()

        return session

    def test_generate_markdown_report_success(self, report_service, sample_session):
        """Test successful markdown report generation"""
        report = report_service.generate_markdown_report(sample_session.id)

        assert report is not None
        assert isinstance(report, str)
        assert 'Test Training Session' in report
        assert 'Training Report' in report
        assert 'Statistics' in report
        assert 'Confidence Distribution' in report
        assert 'Question Analysis' in report

    def test_generate_markdown_report_invalid_session(self, report_service):
        """Test markdown report generation with invalid session ID"""
        with pytest.raises(ValueError, match="Session not found"):
            report_service.generate_markdown_report(999999)

    def test_generate_pdf_report_success(self, report_service, sample_session):
        """Test successful PDF report generation"""
        with patch('src.services.training_report_service.TrainingReportPDFGenerator') as mock_pdf_gen:
            mock_generator = Mock()
            mock_pdf_gen.return_value = mock_generator
            mock_generator.generate_pdf.return_value = b'fake pdf content'

            pdf_content = report_service.generate_pdf_report(sample_session.id)

            assert pdf_content is not None
            assert isinstance(pdf_content, bytes)
            assert pdf_content == b'fake pdf content'
            mock_generator.generate_pdf.assert_called_once()

    def test_generate_report_data(self, report_service, sample_session):
        """Test generating structured report data"""
        report_data = report_service.generate_report_data(sample_session.id)

        assert report_data is not None
        assert report_data['session_id'] == sample_session.id
        assert report_data['session_name'] == 'Test Training Session'
        assert report_data['status'] == 'completed'
        assert 'statistics' in report_data
        assert 'confidence_analysis' in report_data
        assert 'question_breakdown' in report_data
        assert 'performance_metrics' in report_data

    def test_calculate_statistics(self, report_service, sample_session, db_session):
        """Test statistics calculation"""
        stats = report_service._calculate_statistics(sample_session.id)

        assert stats is not None
        assert stats['total_questions'] == 3
        assert stats['avg_confidence'] > 0
        assert 'question_types' in stats
        assert 'confidence_distribution' in stats
        assert 'processing_metrics' in stats

    def test_analyze_confidence_distribution(self, report_service, sample_session):
        """Test confidence distribution analysis"""
        questions = [
            {'confidence': 0.95},  # High
            {'confidence': 0.88},  # High
            {'confidence': 0.65},  # Medium
            {'confidence': 0.45},  # Low
            {'confidence': 0.92}   # High
        ]

        distribution = report_service._analyze_confidence_distribution(questions)

        assert distribution is not None
        assert distribution['high'] == 3
        assert distribution['medium'] == 1
        assert distribution['low'] == 1
        assert distribution['total'] == 5

    def test_analyze_question_types(self, report_service):
        """Test question type analysis"""
        questions = [
            {'question_type': 'calculation'},
            {'question_type': 'factual'},
            {'question_type': 'factual'},
            {'question_type': 'essay'},
            {'question_type': 'calculation'}
        ]

        type_analysis = report_service._analyze_question_types(questions)

        assert type_analysis is not None
        assert type_analysis['calculation'] == 2
        assert type_analysis['factual'] == 2
        assert type_analysis['essay'] == 1
        assert type_analysis['total'] == 5

    def test_generate_performance_metrics(self, report_service, sample_session):
        """Test performance metrics generation"""
        metrics = report_service._generate_performance_metrics(sample_session.id)

        assert metrics is not None
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 'processing_time' in metrics

    def test_create_confidence_chart_data(self, report_service):
        """Test confidence chart data creation"""
        confidence_data = {
            'high': 15,
            'medium': 8,
            'low': 2
        }

        chart_data = report_service._create_confidence_chart_data(confidence_data)

        assert chart_data is not None
        assert chart_data['type'] == 'pie'
        assert len(chart_data['labels']) == 3
        assert len(chart_data['values']) == 3
        assert chart_data['values'] == [15, 8, 2]

    def test_create_question_type_chart_data(self, report_service):
        """Test question type chart data creation"""
        type_data = {
            'multiple_choice': 10,
            'short_answer': 8,
            'essay': 5,
            'calculation': 7
        }

        chart_data = report_service._create_question_type_chart_data(type_data)

        assert chart_data is not None
        assert chart_data['type'] == 'doughnut'
        assert len(chart_data['labels']) == 4
        assert len(chart_data['values']) == 4
        assert sum(chart_data['values']) == 30

    def test_format_duration(self, report_service):
        """Test duration formatting"""
        test_cases = [
            (0, '0s'),
            (30, '30s'),
            (90, '1m 30s'),
            (3661, '1h 1m 1s'),
            (7200, '2h 0m 0s')
        ]

        for seconds, expected in test_cases:
            result = report_service._format_duration(seconds)
            assert result == expected

    def test_format_file_size(self, report_service):
        """Test file size formatting"""
        test_cases = [
            (0, '0 B'),
            (1024, '1.0 KB'),
            (1048576, '1.0 MB'),
            (1073741824, '1.0 GB'),
            (1536, '1.5 KB')
        ]

        for bytes_size, expected in test_cases:
            result = report_service._format_file_size(bytes_size)
            assert result == expected

    def test_get_low_confidence_questions(self, report_service, sample_session, db_session):
        """Test retrieving low confidence questions"""
        # Add a low confidence question
        low_conf_question = TrainingQuestion(
            session_id=sample_session.id,
            text='Complex question with low confidence',
            answer='Uncertain answer',
            confidence=0.45,
            question_type='essay'
        )
        db_session.add(low_conf_question)
        db_session.commit()

        low_questions = report_service._get_low_confidence_questions(
            sample_session.id,
            threshold=0.6
        )

        assert len(low_questions) >= 1
        assert all(q['confidence'] < 0.6 for q in low_questions)

    def test_generate_recommendations(self, report_service, sample_session):
        """Test recommendation generation"""
        report_data = {
            'confidence_analysis': {
                'distribution': {'high': 10, 'medium': 5, 'low': 3},
                'avg_confidence': 0.75
            },
            'statistics': {
                'question_types': {
                    'essay': 8,
                    'calculation': 5,
                    'factual': 5
                }
            },
            'performance_metrics': {
                'accuracy': 0.82,
                'processing_time': 120
            }
        }

        recommendations = report_service._generate_recommendations(report_data)

        assert recommendations is not None
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert all(isinstance(rec, str) for rec in recommendations)

    def test_export_report_json(self, report_service, sample_session):
        """Test exporting report as JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = report_service.export_report(
                sample_session.id,
                format='json',
                output_path=temp_path
            )

            assert result is True
            assert Path(temp_path).exists()

            # Verify JSON content
            import json
            with open(temp_path, 'r') as f:
                data = json.load(f)

            assert 'session_id' in data
            assert 'session_name' in data
            assert 'statistics' in data
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_export_report_csv(self, report_service, sample_session):
        """Test exporting report as CSV"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = report_service.export_report(
                sample_session.id,
                format='csv',
                output_path=temp_path
            )

            assert result is True
            assert Path(temp_path).exists()

            # Verify CSV content
            with open(temp_path, 'r') as f:
                content = f.read()

            assert 'question_id' in content
            assert 'confidence' in content
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_generate_chart_image(self, report_service):
        """Test chart image generation"""
        chart_data = {
            'type': 'pie',
            'labels': ['High', 'Medium', 'Low'],
            'values': [15, 8, 2],
            'colors': ['#10b981', '#f59e0b', '#ef4444']
        }

        with patch('matplotlib.pyplot.savefig') as mock_savefig:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                result = report_service._generate_chart_image(chart_data, temp_path)

                assert result is True
                mock_savefig.assert_called_once()
            finally:
                Path(temp_path).unlink(missing_ok=True)

    def test_validate_session_access(self, report_service, sample_session, test_user):
        """Test session access validation"""
        # Valid access
        result = report_service._validate_session_access(sample_session.id, test_user.id)
        assert result is True

        # Invalid access (different user)
        with pytest.raises(PermissionError):
            report_service._validate_session_access(sample_session.id, 999999)

    def test_get_report_metadata(self, report_service, sample_session):
        """Test report metadata generation"""
        metadata = report_service._get_report_metadata(sample_session.id)

        assert metadata is not None
        assert 'generated_at' in metadata
        assert 'session_id' in metadata
        assert 'report_version' in metadata
        assert 'generator' in metadata
        assert metadata['session_id'] == sample_session.id