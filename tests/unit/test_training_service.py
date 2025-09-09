"""
Unit tests for TrainingService

Tests the core training service functionality including session management,
file processing, and training orchestration.
"""

import os
from pathlib import Path
import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock

from tests.conftest import create_test_user
from src.services.training_service import TrainingService
from src.database.models import TrainingSession, TrainingGuide, TrainingQuestion

class TestTrainingService:
    """Test cases for TrainingService"""

    @pytest.fixture
    def training_service(self, app, db_session):
        """Create a TrainingService instance for testing"""
        return TrainingService()

    @pytest.fixture
    def test_user(self, db_session):
        """Create a test user"""
        return create_test_user()

    # Remove the local sample_files fixture since it's now in conftest.py

    def test_create_training_session_success(self, training_service, test_user, sample_files):
        """Test successful training session creation"""
        from src.services.training_service import TrainingConfig, FileUpload

        # Convert sample files to FileUpload objects
        guides = []
        for file_info in sample_files:
            guide = FileUpload(
                filename=file_info['filename'],
                file_path=file_info['file_path'],
                file_size=file_info['size'],
                file_type=file_info['extension']
            )
            guides.append(guide)

        config = TrainingConfig(
            name='Test Training Session',
            description='Test description',
            max_questions_to_answer=10,
            confidence_threshold=0.7,
            use_in_main_app=False
        )

        with patch.object(training_service, '_validate_file') as mock_validate:
            mock_validate.return_value = None  # _validate_file doesn't return anything, just raises on error

            session = training_service.create_training_session(test_user.id, guides, config)

            assert session is not None
            assert session.name == 'Test Training Session'
            assert session.user_id == test_user.id
            assert session.max_questions_to_answer == 10
            assert session.confidence_threshold == 0.7
            assert session.status == 'created'

    def test_create_training_session_invalid_config(self, training_service, test_user):
        """Test training session creation with invalid configuration"""
        from src.services.training_service import TrainingConfig

        # Test missing name
        with pytest.raises(ValueError):  # Empty name should be invalid
            config = TrainingConfig(name="")  # Empty name should be invalid
            training_service.create_training_session(test_user.id, [], config)

        # Test invalid confidence threshold
        with pytest.raises(ValueError):
            config = TrainingConfig(
                name='Test Session',
                confidence_threshold=1.5  # Invalid threshold > 1.0
            )
            training_service.create_training_session(test_user.id, [], config)

        # Test no files (empty guides list)
        with pytest.raises(ValueError):
            config = TrainingConfig(name='Test Session')
            training_service.create_training_session(test_user.id, [], config)

    def test_start_training_session_success(self, training_service, test_user, db_session):
        """Test successful training session start"""
        # Create a pending session
        session = TrainingSession(
            name='Test Session',
            user_id=test_user.id,
            status='pending',
            confidence_threshold=0.6
        )
        db_session.add(session)
        db_session.commit()

        # Change status to 'created' as that's what start_training expects
        session.status = 'created'
        db_session.commit()

        with patch.object(training_service, '_process_training_session') as mock_process:
            mock_process.return_value = None  # _process_training_session doesn't return anything

            result = training_service.start_training(session.id)

            assert result is True
            db_session.refresh(session)
            assert session.status == 'processing'

    def test_start_training_session_invalid_status(self, training_service, test_user, db_session):
        """Test starting training session with invalid status"""
        # Create a completed session
        session = TrainingSession(
            name='Test Session',
            user_id=test_user.id,
            status='completed',
            confidence_threshold=0.6
        )
        db_session.add(session)
        db_session.commit()

        with pytest.raises(ValueError, match="Cannot start training"):
            training_service.start_training_session(session.id)

    def test_pause_training_session(self, training_service, test_user, db_session):
        """Test pausing an in-progress training session"""
        session = TrainingSession(
            name='Test Session',
            user_id=test_user.id,
            status='in_progress',
            confidence_threshold=0.6
        )
        db_session.add(session)
        db_session.commit()

        result = training_service.pause_training_session(session.id)

        assert result is True
        db_session.refresh(session)
        assert session.status == 'paused'

    def test_resume_training_session(self, training_service, test_user, db_session):
        """Test resuming a paused training session"""
        session = TrainingSession(
            name='Test Session',
            user_id=test_user.id,
            status='paused',
            confidence_threshold=0.6
        )
        db_session.add(session)
        db_session.commit()

        with patch.object(training_service, '_resume_training_process') as mock_resume:
            mock_resume.return_value = True

            result = training_service.resume_training_session(session.id)

            assert result is True
            db_session.refresh(session)
            assert session.status == 'in_progress'

    def test_stop_training_session(self, training_service, test_user, db_session):
        """Test stopping an in-progress training session"""
        session = TrainingSession(
            name='Test Session',
            user_id=test_user.id,
            status='in_progress',
            confidence_threshold=0.6
        )
        db_session.add(session)
        db_session.commit()

        result = training_service.stop_training_session(session.id, save_partial=True)

        assert result is True
        db_session.refresh(session)
        assert session.status == 'stopped'

    def test_get_training_progress(self, training_service, test_user, db_session):
        """Test getting training progress for a session"""
        session = TrainingSession(
            name='Test Session',
            user_id=test_user.id,
            status='in_progress',
            confidence_threshold=0.6,
            progress_percentage=45.5
        )
        db_session.add(session)
        db_session.commit()

        progress = training_service.get_training_progress(session.id)

        assert progress is not None
        assert progress['session_id'] == session.id
        assert progress['percentage'] == 45.5
        assert progress['status'] == 'in_progress'

    def test_validate_files_success(self, training_service, sample_files):
        """Test successful file validation"""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 1024

                result = training_service._validate_files(sample_files)
                assert result is True

    def test_validate_files_missing_file(self, training_service, sample_files):
        """Test file validation with missing file"""
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                training_service._validate_files(sample_files)

    def test_validate_files_oversized(self, training_service, sample_files):
        """Test file validation with oversized file"""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 100 * 1024 * 1024  # 100MB

                with pytest.raises(ValueError, match="File too large"):
                    training_service._validate_files(sample_files)

    @patch('src.services.training_service.ConsolidatedOCRService')
    def test_process_training_files(self, mock_ocr, training_service, sample_files):
        """Test processing training files"""
        mock_ocr_instance = Mock()
        mock_ocr.return_value = mock_ocr_instance
        mock_ocr_instance.process_file.return_value = {
            'text': 'Sample extracted text',
            'confidence': 0.85
        }

        with patch.object(training_service, '_extract_questions') as mock_extract:
            mock_extract.return_value = [
                {'text': 'What is 2+2?', 'answer': '4', 'confidence': 0.9}
            ]

            result = training_service._process_training_files(sample_files)

            assert result is True
            mock_ocr_instance.process_file.assert_called()
            mock_extract.assert_called()

    def test_extract_questions_from_text(self, training_service):
        """Test question extraction from text"""
        sample_text = """
        Question 1: What is the capital of France?
        Answer: Paris

        Question 2: What is 2 + 2?
        Answer: 4
        """

        with patch.object(training_service, '_llm_extract_questions') as mock_llm:
            mock_llm.return_value = [
                {
                    'text': 'What is the capital of France?',
                    'answer': 'Paris',
                    'confidence': 0.9,
                    'question_type': 'factual'
                },
                {
                    'text': 'What is 2 + 2?',
                    'answer': '4',
                    'confidence': 0.95,
                    'question_type': 'calculation'
                }
            ]

            questions = training_service._extract_questions(sample_text)

            assert len(questions) == 2
            assert questions[0]['text'] == 'What is the capital of France?'
            assert questions[1]['answer'] == '4'

    def test_calculate_confidence_score(self, training_service):
        """Test confidence score calculation"""
        questions = [
            {'confidence': 0.9},
            {'confidence': 0.8},
            {'confidence': 0.7},
            {'confidence': 0.6}
        ]

        avg_confidence = training_service._calculate_confidence_score(questions)

        assert avg_confidence == 0.75

    def test_get_training_results(self, training_service, test_user, db_session):
        """Test getting training results for a completed session"""
        session = TrainingSession(
            name='Test Session',
            user_id=test_user.id,
            status='completed',
            confidence_threshold=0.6,
            progress_percentage=100.0
        )
        db_session.add(session)
        db_session.commit()

        # Add some training questions
        questions = [
            TrainingQuestion(
                session_id=session.id,
                text='Sample question 1',
                answer='Sample answer 1',
                confidence=0.85
            ),
            TrainingQuestion(
                session_id=session.id,
                text='Sample question 2',
                answer='Sample answer 2',
                confidence=0.75
            )
        ]
        db_session.add_all(questions)
        db_session.commit()

        results = training_service.get_training_results(session.id)

        assert results is not None
        assert results['session_id'] == session.id
        assert results['status'] == 'completed'
        assert results['total_questions'] == 2
        assert 'avg_confidence' in results
        assert 'questions' in results

    def test_delete_training_session(self, training_service, test_user, db_session):
        """Test deleting a training session"""
        session = TrainingSession(
            name='Test Session',
            user_id=test_user.id,
            status='completed',
            confidence_threshold=0.6
        )
        db_session.add(session)
        db_session.commit()
        session_id = session.id

        result = training_service.delete_training_session(session_id)

        assert result is True

        # Verify session is deleted
        deleted_session = db_session.query(TrainingSession).filter_by(id=session_id).first()
        assert deleted_session is None

    def test_list_user_sessions(self, training_service, test_user, db_session):
        """Test listing training sessions for a user"""
        # Create multiple sessions
        sessions = [
            TrainingSession(
                name='Session 1',
                user_id=test_user.id,
                status='completed',
                confidence_threshold=0.6
            ),
            TrainingSession(
                name='Session 2',
                user_id=test_user.id,
                status='in_progress',
                confidence_threshold=0.7
            ),
            TrainingSession(
                name='Session 3',
                user_id=test_user.id,
                status='pending',
                confidence_threshold=0.8
            )
        ]
        db_session.add_all(sessions)
        db_session.commit()

        user_sessions = training_service.list_user_sessions(test_user.id)

        assert len(user_sessions) == 3
        assert all(session['user_id'] == test_user.id for session in user_sessions)

    def test_get_session_by_id(self, training_service, test_user, db_session):
        """Test getting a specific training session by ID"""
        session = TrainingSession(
            name='Test Session',
            user_id=test_user.id,
            status='completed',
            confidence_threshold=0.6
        )
        db_session.add(session)
        db_session.commit()

        retrieved_session = training_service.get_session_by_id(session.id)

        assert retrieved_session is not None
        assert retrieved_session.id == session.id
        assert retrieved_session.name == 'Test Session'
        assert retrieved_session.user_id == test_user.id

    def test_update_session_config(self, training_service, test_user, db_session):
        """Test updating training session configuration"""
        session = TrainingSession(
            name='Test Session',
            user_id=test_user.id,
            status='pending',
            confidence_threshold=0.6
        )
        db_session.add(session)
        db_session.commit()

        updates = {
            'name': 'Updated Session Name',
            'confidence_threshold': 0.8,
            'max_questions_to_answer': 20
        }

        result = training_service.update_session_config(session.id, updates)

        assert result is True
        db_session.refresh(session)
        assert session.name == 'Updated Session Name'
        assert session.confidence_threshold == 0.8
        assert session.max_questions_to_answer == 20

    def test_update_session_config_invalid_status(self, training_service, test_user, db_session):
        """Test updating configuration for non-pending session"""
        session = TrainingSession(
            name='Test Session',
            user_id=test_user.id,
            status='in_progress',
            confidence_threshold=0.6
        )
        db_session.add(session)
        db_session.commit()

        updates = {'name': 'Updated Name'}

        with pytest.raises(ValueError, match="Cannot update configuration"):
            training_service.update_session_config(session.id, updates)