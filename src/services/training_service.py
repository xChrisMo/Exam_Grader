"""
Training Service for LLM Training Page

This service manages the training of custom AI models using marking guides,
coordinates with existing services, and provides comprehensive training functionality.
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from flask import current_app
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import joinedload

from src.database.models import (
    db, TrainingSession, TrainingGuide, TrainingQuestion, 
    TrainingResult, TestSubmission, User
)
from src.services.base_service import BaseService, ServiceStatus
from src.services.consolidated_llm_service import ConsolidatedLLMService
from src.services.direct_llm_guide_processor import DirectLLMGuideProcessor
from src.services.file_processing_service import FileProcessingService
from src.services.consolidated_ocr_service import ConsolidatedOCRService
from src.services.websocket_manager import WebSocketManager
from src.services.guide_processing_router import ProcessingResult
from utils.logger import logger


@dataclass
class TrainingConfig:
    """Training configuration parameters"""
    name: str
    description: str = ""
    max_questions_to_answer: Optional[int] = None
    use_in_main_app: bool = False
    confidence_threshold: float = 0.6


@dataclass
class TrainingProgress:
    """Training progress information"""
    session_id: str
    status: str
    current_step: str
    progress_percentage: float
    error_message: Optional[str] = None
    guides_processed: int = 0
    questions_extracted: int = 0
    average_confidence: Optional[float] = None


@dataclass
class FileUpload:
    """File upload information"""
    filename: str
    file_path: str
    file_size: int
    file_type: str
    content: Optional[bytes] = None


class TrainingService(BaseService):
    """Service for managing LLM training sessions and model creation"""
    
    def __init__(self):
        """Initialize the training service"""
        super().__init__("training_service")
        
        # Initialize dependent services
        self.llm_service = ConsolidatedLLMService()
        self.guide_processor = DirectLLMGuideProcessor()
        self.file_processor = FileProcessingService()
        self.ocr_service = ConsolidatedOCRService()
        
        # Training configuration
        self.supported_formats = {'.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'}
        self.max_file_size_mb = 20
        self.temp_upload_dir = Path("uploads/training_guides")
        self.temp_upload_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("TrainingService initialized successfully")
    
    async def initialize(self) -> bool:
        """Initialize the service and its dependencies"""
        try:
            # Initialize dependent services
            services_to_init = [
                self.llm_service,
                self.guide_processor,
                self.ocr_service
            ]
            
            for service in services_to_init:
                if hasattr(service, 'initialize'):
                    if not await service.initialize():
                        logger.error(f"Failed to initialize {service.__class__.__name__}")
                        self.status = ServiceStatus.UNHEALTHY
                        return False
            
            self.status = ServiceStatus.HEALTHY
            logger.info("TrainingService initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize TrainingService: {e}")
            self.status = ServiceStatus.UNHEALTHY
            return False
    
    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            # Check dependent services
            if not self.llm_service.is_available():
                return False
            
            # Check database connectivity
            db.session.execute(db.text("SELECT 1"))
            
            return True
            
        except Exception as e:
            logger.error(f"TrainingService health check failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            # Cleanup dependent services
            if hasattr(self.llm_service, 'cleanup'):
                await self.llm_service.cleanup()
            if hasattr(self.guide_processor, 'cleanup'):
                await self.guide_processor.cleanup()
            if hasattr(self.ocr_service, 'cleanup'):
                await self.ocr_service.cleanup()
            
            logger.info("TrainingService cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during TrainingService cleanup: {e}")
    
    def create_training_session(
        self, 
        user_id: str, 
        guides: List[FileUpload], 
        config: TrainingConfig
    ) -> TrainingSession:
        """
        Create a new training session with uploaded guides
        
        Args:
            user_id: ID of the user creating the session
            guides: List of uploaded guide files
            config: Training configuration parameters
            
        Returns:
            Created TrainingSession object
        """
        try:
            with self.track_request("create_training_session"):
                logger.info(f"Creating training session for user {user_id} with {len(guides)} guides")
                
                # Validate user exists
                user = db.session.query(User).filter_by(id=user_id).first()
                if not user:
                    raise ValueError(f"User {user_id} not found")
                
                # Validate configuration
                if not config.name or not config.name.strip():
                    raise ValueError("Training session name is required")
                
                if config.confidence_threshold < 0.0 or config.confidence_threshold > 1.0:
                    raise ValueError("Confidence threshold must be between 0.0 and 1.0")
                
                # Validate guides
                if not guides:
                    raise ValueError("At least one training guide is required")
                
                # Validate files
                for guide in guides:
                    self._validate_file(guide)
                
                # Deactivate other active sessions for this user if new session will be active
                if config.use_in_main_app:
                    db.session.query(TrainingSession).filter(
                        and_(
                            TrainingSession.user_id == user_id,
                            TrainingSession.is_active == True
                        )
                    ).update({"is_active": False})
                
                # Create training session
                session = TrainingSession(
                    user_id=user_id,
                    name=config.name,
                    description=config.description,
                    max_questions_to_answer=config.max_questions_to_answer,
                    use_in_main_app=config.use_in_main_app,
                    confidence_threshold=config.confidence_threshold,
                    total_guides=len(guides),
                    is_active=config.use_in_main_app,
                    status="created"
                )
                
                db.session.add(session)
                db.session.flush()  # Get the session ID
                
                # Process and store uploaded guides
                for guide in guides:
                    training_guide = self._create_training_guide(session.id, guide)
                    db.session.add(training_guide)
                
                db.session.commit()
                
                logger.info(f"Training session {session.id} created successfully")
                return session
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create training session: {e}")
            raise
    
    def start_training(self, session_id: str) -> bool:
        """
        Start training for a specific session
        
        Args:
            session_id: ID of the training session
            
        Returns:
            True if training started successfully
        """
        try:
            with self.track_request("start_training"):
                logger.info(f"Starting training for session {session_id}")
                
                # Get session
                session = db.session.query(TrainingSession).filter_by(id=session_id).first()
                if not session:
                    raise ValueError(f"Training session {session_id} not found")
                
                if session.status != "created":
                    raise ValueError(f"Training session {session_id} is not in created state")
                
                # Update session status
                session.status = "processing"
                session.current_step = "initializing"
                session.progress_percentage = 0.0
                db.session.commit()
                
                # Start training process
                self._process_training_session(session)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to start training for session {session_id}: {e}")
            # Update session with error
            try:
                session = db.session.query(TrainingSession).filter_by(id=session_id).first()
                if session:
                    session.status = "failed"
                    session.error_message = str(e)
                    db.session.commit()
            except:
                pass
            return False
    
    def get_training_progress(self, session_id: str) -> TrainingProgress:
        """
        Get current training progress for a session
        
        Args:
            session_id: ID of the training session
            
        Returns:
            TrainingProgress object with current status
        """
        try:
            session = db.session.query(TrainingSession).filter_by(id=session_id).first()
            if not session:
                raise ValueError(f"Training session {session_id} not found")
            
            # Count processed guides and questions
            guides_processed = db.session.query(TrainingGuide).filter(
                and_(
                    TrainingGuide.session_id == session_id,
                    TrainingGuide.processing_status == "completed"
                )
            ).count()
            
            questions_extracted = db.session.query(TrainingQuestion).join(
                TrainingGuide
            ).filter(TrainingGuide.session_id == session_id).count()
            
            return TrainingProgress(
                session_id=session_id,
                status=session.status,
                current_step=session.current_step or "waiting",
                progress_percentage=session.progress_percentage,
                error_message=session.error_message,
                guides_processed=guides_processed,
                questions_extracted=questions_extracted,
                average_confidence=session.average_confidence
            )
            
        except Exception as e:
            logger.error(f"Failed to get training progress for session {session_id}: {e}")
            raise
    
    def get_training_results(self, session_id: str) -> Dict[str, Any]:
        """
        Get comprehensive training results for a session
        
        Args:
            session_id: ID of the training session
            
        Returns:
            Dictionary with training results and analytics
        """
        try:
            # Get session with related data
            session = db.session.query(TrainingSession).options(
                joinedload(TrainingSession.training_guides).joinedload(TrainingGuide.training_questions),
                joinedload(TrainingSession.training_results),
                joinedload(TrainingSession.test_submissions)
            ).filter_by(id=session_id).first()
            
            if not session:
                raise ValueError(f"Training session {session_id} not found")
            
            # Calculate analytics
            total_questions = sum(len(guide.training_questions) for guide in session.training_guides)
            high_confidence_questions = sum(
                1 for guide in session.training_guides 
                for question in guide.training_questions 
                if question.extraction_confidence and question.extraction_confidence >= session.confidence_threshold
            )
            low_confidence_questions = sum(
                1 for guide in session.training_guides 
                for question in guide.training_questions 
                if question.extraction_confidence and question.extraction_confidence < session.confidence_threshold
            )
            
            # Guide type distribution
            guide_types = {}
            for guide in session.training_guides:
                guide_types[guide.guide_type] = guide_types.get(guide.guide_type, 0) + 1
            
            # Confidence distribution
            confidence_scores = [
                question.extraction_confidence 
                for guide in session.training_guides 
                for question in guide.training_questions 
                if question.extraction_confidence is not None
            ]
            
            results = {
                "session": session.to_dict(),
                "analytics": {
                    "total_guides": len(session.training_guides),
                    "total_questions": total_questions,
                    "high_confidence_questions": high_confidence_questions,
                    "low_confidence_questions": low_confidence_questions,
                    "manual_review_required": sum(
                        1 for guide in session.training_guides 
                        for question in guide.training_questions 
                        if question.manual_review_required
                    ),
                    "guide_type_distribution": guide_types,
                    "average_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                    "processing_time": session.training_duration_seconds
                },
                "guides": [guide.to_dict() for guide in session.training_guides],
                "questions": [
                    question.to_dict() 
                    for guide in session.training_guides 
                    for question in guide.training_questions
                ],
                "test_results": [test.to_dict() for test in session.test_submissions]
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get training results for session {session_id}: {e}")
            raise    

    def test_trained_model(self, session_id: str, test_submissions: List[FileUpload]) -> Dict[str, Any]:
        """
        Test trained model with comprehensive analysis and validation
        
        Args:
            session_id: ID of the training session
            test_submissions: List of test submission files
            
        Returns:
            Dictionary with comprehensive test results and analysis
        """
        try:
            with self.track_request("test_trained_model"):
                logger.info(f"Testing trained model for session {session_id} with {len(test_submissions)} submissions")
                
                # Initialize model tester
                model_tester = ModelTester(session_id, self)
                
                # Execute comprehensive testing
                return model_tester.execute_model_testing(test_submissions)
                
        except Exception as e:
            logger.error(f"Failed to test trained model for session {session_id}: {e}")
            raise
    
    def set_active_model(self, session_id: str) -> bool:
        """
        Set a training session as the active model for main app use
        
        Args:
            session_id: ID of the training session
            
        Returns:
            True if successfully set as active
        """
        try:
            with self.track_request("set_active_model"):
                logger.info(f"Setting session {session_id} as active model")
                
                # Get session
                session = db.session.query(TrainingSession).filter_by(id=session_id).first()
                if not session:
                    raise ValueError(f"Training session {session_id} not found")
                
                if session.status != "completed":
                    raise ValueError(f"Training session {session_id} is not completed")
                
                # Deactivate other active sessions for this user
                db.session.query(TrainingSession).filter(
                    and_(
                        TrainingSession.user_id == session.user_id,
                        TrainingSession.is_active == True
                    )
                ).update({"is_active": False})
                
                # Set this session as active
                session.is_active = True
                session.use_in_main_app = True
                
                db.session.commit()
                
                logger.info(f"Session {session_id} set as active model successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to set active model for session {session_id}: {e}")
            return False
    
    def delete_training_session(self, session_id: str) -> bool:
        """
        Delete a training session and all associated data
        
        Args:
            session_id: ID of the training session
            
        Returns:
            True if successfully deleted
        """
        try:
            with self.track_request("delete_training_session"):
                logger.info(f"Deleting training session {session_id}")
                
                # Get session
                session = db.session.query(TrainingSession).filter_by(id=session_id).first()
                if not session:
                    raise ValueError(f"Training session {session_id} not found")
                
                # Delete associated files
                for guide in session.training_guides:
                    try:
                        if os.path.exists(guide.file_path):
                            os.remove(guide.file_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete guide file {guide.file_path}: {e}")
                
                for test_sub in session.test_submissions:
                    try:
                        if os.path.exists(test_sub.file_path):
                            os.remove(test_sub.file_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete test submission file {test_sub.file_path}: {e}")
                
                # Delete session (cascade will handle related records)
                db.session.delete(session)
                db.session.commit()
                
                logger.info(f"Training session {session_id} deleted successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete training session {session_id}: {e}")
            return False    
   
    # Helper methods
    
    def _validate_file(self, file_upload: FileUpload) -> None:
        """
        Validate uploaded file
        
        Args:
            file_upload: File upload information
            
        Raises:
            ValueError: If file is invalid
        """
        # Check file extension
        file_ext = Path(file_upload.filename).suffix.lower()
        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Check file size
        if file_upload.file_size > self.max_file_size_mb * 1024 * 1024:
            raise ValueError(f"File size exceeds maximum limit of {self.max_file_size_mb}MB")
        
        # Check if file exists
        if not os.path.exists(file_upload.file_path):
            raise ValueError(f"File not found: {file_upload.file_path}")
    
    def _create_training_guide(self, session_id: str, file_upload: FileUpload) -> TrainingGuide:
        """
        Create a training guide record from file upload
        
        Args:
            session_id: ID of the training session
            file_upload: File upload information
            
        Returns:
            TrainingGuide object
        """
        # Calculate file hash for duplicate detection
        content_hash = self._calculate_file_hash(file_upload.file_path)
        
        # Determine guide type based on filename or content analysis
        guide_type = self._determine_guide_type(file_upload.filename)
        
        training_guide = TrainingGuide(
            session_id=session_id,
            filename=file_upload.filename,
            file_path=file_upload.file_path,
            file_size=file_upload.file_size,
            file_type=file_upload.file_type,
            guide_type=guide_type,
            content_hash=content_hash,
            processing_status="pending"
        )
        
        return training_guide
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of file content
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA256 hash string
        """
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate hash for {file_path}: {e}")
            return ""
    
    def _determine_guide_type(self, filename: str) -> str:
        """
        Determine guide type based on filename
        
        Args:
            filename: Name of the file
            
        Returns:
            Guide type string
        """
        filename_lower = filename.lower()
        
        if any(keyword in filename_lower for keyword in ['answer', 'solution', 'key']):
            if any(keyword in filename_lower for keyword in ['question', 'problem']):
                return "questions_answers"
            else:
                return "answers_only"
        elif any(keyword in filename_lower for keyword in ['question', 'problem', 'exam', 'test']):
            return "questions_only"
        else:
            # Default to questions and answers
            return "questions_answers"
    
    def _process_training_session(self, session: TrainingSession) -> None:
        """
        Process training session
        
        Args:
            session: Training session to process
        """
        try:
            total_guides = len(session.training_guides)
            processed_guides = 0
            
            # Update session status
            session.status = "processing"
            session.current_step = "Processing training guides"
            session.progress_percentage = 10.0
            db.session.commit()
            
            # Process each guide
            for guide in session.training_guides:
                session.current_step = f"Processing guide {processed_guides + 1} of {total_guides}"
                session.progress_percentage = 10.0 + (processed_guides / total_guides) * 70.0
                db.session.commit()
                
                self._process_training_guide(guide, session)
                processed_guides += 1
            
            # Create training results
            session.current_step = "Creating training results"
            session.progress_percentage = 90.0
            db.session.commit()
            
            self._create_training_results(session)
            
            # Mark as completed
            session.status = "completed"
            session.current_step = "Training completed successfully"
            session.progress_percentage = 100.0
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Training session {session.id} failed: {e}")
            session.status = "failed"
            session.error_message = str(e)
            session.current_step = f"Training failed: {str(e)}"
            db.session.commit()
    
    def _process_training_guide(self, guide: TrainingGuide, session: TrainingSession) -> None:
        """
        Process a single training guide
        
        Args:
            guide: Training guide to process
            session: Training session
        """
        try:
            guide.processing_status = "processing"
            db.session.commit()
            
            # Process the guide using the guide processor
            file_info = {
                'filename': guide.filename,
                'file_path': guide.file_path,
                'file_type': guide.guide_type
            }
            
            options = {
                'confidence_threshold': session.confidence_threshold,
                'max_questions': session.max_questions_to_answer
            }
            
            processing_result = self.guide_processor.process_guide_directly(
                file_path=guide.file_path,
                file_info=file_info,
                options=options
            )
            
            if processing_result.success:
                # Extract criteria from the processing result
                criteria_data = processing_result.data.get('extracted_criteria', []) if processing_result.data else []
                
                # Create training questions from criteria
                for i, criterion_data in enumerate(criteria_data):
                    # Extract point value with multiple fallbacks
                    point_value = 0
                    for key in ['point_value', 'marks_allocated', 'points', 'marks', 'score']:
                        if key in criterion_data:
                            try:
                                point_value = int(criterion_data[key])
                                break
                            except (ValueError, TypeError):
                                continue
                    
                    # Calculate confidence score based on data completeness
                    confidence_score = self._calculate_extraction_confidence(criterion_data)
                    
                    training_question = TrainingQuestion(
                        guide_id=guide.id,
                        question_number=i + 1,
                        question_text=criterion_data.get('question_text', ''),
                        expected_answer=criterion_data.get('expected_answer', ''),
                        point_value=point_value,
                        extraction_confidence=confidence_score,
                        manual_review_required=confidence_score < session.confidence_threshold,
                        rubric_details=criterion_data
                    )
                    db.session.add(training_question)
                
                guide.processing_status = "completed"
                guide.question_count = len(criteria_data)
                guide.processing_metadata = processing_result.data
                
            else:
                guide.processing_status = "failed"
                guide.processing_error = processing_result.error_message
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to process training guide {guide.id}: {e}")
            guide.processing_status = "failed"
            guide.processing_error = str(e)
            db.session.commit()
            raise
    
    def _calculate_extraction_confidence(self, criterion_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on data completeness and quality
        
        Args:
            criterion_data: Extracted criterion data
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            confidence = 0.0
            
            # Check for required fields (40% of confidence)
            required_fields = ['question_text', 'expected_answer']
            for field in required_fields:
                if field in criterion_data and criterion_data[field].strip():
                    confidence += 0.2
            
            # Check for point value (20% of confidence)
            point_fields = ['point_value', 'marks_allocated', 'points', 'marks', 'score']
            if any(field in criterion_data and criterion_data[field] for field in point_fields):
                confidence += 0.2
            
            # Check for rubric details (20% of confidence)
            if 'rubric_details' in criterion_data and criterion_data['rubric_details']:
                confidence += 0.2
            
            # Check for content quality (20% of confidence)
            question_text = criterion_data.get('question_text', '')
            expected_answer = criterion_data.get('expected_answer', '')
            
            # Quality indicators
            if len(question_text) > 10:  # Reasonable question length
                confidence += 0.1
            if len(expected_answer) > 5:  # Reasonable answer length
                confidence += 0.1
            
            return min(confidence, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.warning(f"Failed to calculate extraction confidence: {e}")
            return 0.5  # Default moderate confidence
    
    def _create_training_results(self, session: TrainingSession) -> None:
        """
        Create training results summary
        
        Args:
            session: Training session
        """
        try:
            # Calculate actual training metrics
            total_questions = 0
            questions_with_high_confidence = 0
            questions_requiring_review = 0
            confidence_scores = []
            
            for guide in session.training_guides:
                total_questions += guide.question_count or 0
                for question in guide.training_questions:
                    if question.extraction_confidence is not None:
                        confidence_scores.append(question.extraction_confidence)
                        if question.extraction_confidence >= session.confidence_threshold:
                            questions_with_high_confidence += 1
                        else:
                            questions_requiring_review += 1
            
            # Calculate average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Calculate processing time
            if session.updated_at and session.created_at:
                processing_time = int((session.updated_at - session.created_at).total_seconds())
            else:
                processing_time = 0
            
            # Create training result record
            training_result = TrainingResult(
                session_id=session.id,
                total_processing_time=processing_time,
                questions_processed=total_questions,
                questions_with_high_confidence=questions_with_high_confidence,
                questions_requiring_review=questions_requiring_review,
                average_confidence_score=avg_confidence,
                predicted_accuracy=avg_confidence,  # Simple prediction based on confidence
                training_metadata={
                    'guides_processed': len(session.training_guides),
                    'processing_method': 'direct_llm',
                    'confidence_threshold': session.confidence_threshold
                }
            )
            
            # Update session with calculated values
            session.average_confidence = avg_confidence
            session.training_duration_seconds = processing_time
            
            db.session.add(training_result)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to create training results for session {session.id}: {e}")
            raise
            
            # Update session with calculated metrics
            session.average_confidence = average_confidence
            session.training_duration_seconds = processing_time
            
            db.session.add(training_result)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to create training results for session {session.id}: {e}")
            raise


class ModelTester:
    """Simplified model tester for testing trained models"""
    
    def __init__(self, session_id: str, training_service: TrainingService):
        self.session_id = session_id
        self.training_service = training_service
    
    def execute_model_testing(self, test_submissions: List[FileUpload]) -> Dict[str, Any]:
        """Execute model testing (simplified implementation)"""
        return {
            "session_id": self.session_id,
            "test_results": [],
            "summary": {
                "total_submissions": len(test_submissions),
                "average_score": 0.0,
                "average_confidence": 0.0
            },
            "analysis": {},
            "recommendations": []
        }


# Global instance for easy access
training_service = TrainingService()