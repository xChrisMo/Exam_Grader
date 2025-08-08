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
from src.services.websocket_manager import websocket_manager
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
        Enhanced training session orchestration with comprehensive workflow management
        
        Args:
            session: Training session to process
        """
        try:
            start_time = time.time()
            
            # Initialize training orchestrator
            orchestrator = TrainingOrchestrator(session, self)
            
            # Execute training workflow
            orchestrator.execute_training_workflow()
            
        except Exception as e:
            logger.error(f"Training session {session.id} failed: {e}")
            session.status = "failed"
            session.error_message = str(e)
            session.current_step = "failed"
            db.session.commit()
    
    def _process_training_guide(self, guide: TrainingGuide, session: TrainingSession) -> None:
        """
        Process a single training guide using DirectLLMGuideProcessor
        
        Args:
            guide: Training guide to process
            session: Training session
        """
        try:
            guide.processing_status = "processing"
            db.session.commit()
            
            # Prepare file info for processing
            file_info = {
                'path': guide.file_path,
                'name': guide.filename,
                'size': guide.file_size,
                'size_mb': guide.file_size / (1024 * 1024),
                'type': guide.file_type,
            }
            
            # Processing options
            options = {
                'guide_type': guide.guide_type,
                'confidence_threshold': session.confidence_threshold,
                'max_questions': session.max_questions_to_answer
            }
            
            # Use DirectLLMGuideProcessor for comprehensive analysis
            processing_result = self.guide_processor.process_guide_directly(
                guide.file_path, 
                file_info, 
                options
            )
            
            if not processing_result.success:
                # Try fallback processing with file processor
                logger.warning(f"Direct LLM processing failed for {guide.filename}, trying fallback")
                processing_result = self._fallback_guide_processing(guide, file_info, options)
            
            if processing_result.success:
                # Extract and store guide data
                self._extract_guide_data(guide, processing_result, session)
                
                # Create question records from extracted criteria
                self._create_training_questions(guide, processing_result, session)
                
                guide.processing_status = "completed"
                logger.info(f"Successfully processed guide {guide.filename}")
            else:
                guide.processing_status = "failed"
                guide.processing_error = processing_result.error_message
                logger.error(f"Failed to process guide {guide.filename}: {processing_result.error_message}")
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to process training guide {guide.id}: {e}")
            guide.processing_status = "failed"
            guide.processing_error = str(e)
            db.session.commit()
            raise
    
    def _create_training_results(self, session: TrainingSession) -> None:
        """
        Create training results summary
        
        Args:
            session: Training session
        """
        try:
            # Calculate metrics
            total_questions = sum(guide.question_count for guide in session.training_guides)
            high_confidence_count = 0
            review_required_count = 0
            confidence_scores = []
            
            for guide in session.training_guides:
                for question in guide.training_questions:
                    if question.extraction_confidence is not None:
                        confidence_scores.append(question.extraction_confidence)
                        if question.extraction_confidence >= session.confidence_threshold:
                            high_confidence_count += 1
                        else:
                            review_required_count += 1
                    
                    if question.manual_review_required:
                        review_required_count += 1
            
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Create training result record
            training_result = TrainingResult(
                session_id=session.id,
                total_processing_time=session.training_duration_seconds or 0,
                questions_processed=total_questions,
                questions_with_high_confidence=high_confidence_count,
                questions_requiring_review=review_required_count,
                average_confidence_score=avg_confidence,
                predicted_accuracy=min(avg_confidence * 1.2, 1.0),  # Estimate based on confidence
                training_metadata={
                    'guides_processed': len(session.training_guides),
                    'guide_types': [guide.guide_type for guide in session.training_guides],
                    'processing_timestamp': datetime.now(timezone.utc).isoformat()
                },
                model_parameters={
                    'confidence_threshold': session.confidence_threshold,
                    'max_questions_to_answer': session.max_questions_to_answer
                }
            )
            
            db.session.add(training_result)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to create training results for session {session.id}: {e}")
            raise
    
    def _grade_with_trained_model(self, session: TrainingSession, submission_text: str) -> Dict[str, Any]:
        """
        Grade submission using trained model
        
        Args:
            session: Training session with trained model
            submission_text: Text content of submission
            
        Returns:
            Dictionary with grading results
        """
        try:
            # This is a simplified implementation
            # In a real implementation, this would use the trained model data
            
            # Get training questions for comparison
            all_questions = []
            for guide in session.training_guides:
                for question in guide.training_questions:
                    all_questions.append(question)
            
            if not all_questions:
                return {
                    'score': 0.0,
                    'confidence': 0.0,
                    'matched_questions': [],
                    'misalignments': ['No training questions available']
                }
            
            # Use LLM to grade against training questions
            grading_prompt = self._build_grading_prompt(all_questions, submission_text)
            
            try:
                llm_response = self.llm_service.process_request(
                    prompt=grading_prompt,
                    max_tokens=1000,
                    temperature=0.1
                )
                
                # Parse LLM response (simplified)
                response_text = llm_response.get('response', '')
                
                # Extract score and confidence (this would be more sophisticated in practice)
                score = self._extract_score_from_response(response_text)
                confidence = self._extract_confidence_from_response(response_text)
                
                return {
                    'score': score,
                    'confidence': confidence,
                    'matched_questions': [q.question_number for q in all_questions[:3]],  # Simplified
                    'misalignments': []
                }
                
            except Exception as e:
                logger.error(f"LLM grading failed: {e}")
                return {
                    'score': 0.0,
                    'confidence': 0.0,
                    'matched_questions': [],
                    'misalignments': [f'Grading failed: {str(e)}']
                }
                
        except Exception as e:
            logger.error(f"Failed to grade with trained model: {e}")
            return {
                'score': 0.0,
                'confidence': 0.0,
                'matched_questions': [],
                'misalignments': [f'Grading error: {str(e)}']
            }
    
    def _build_grading_prompt(self, questions: List[TrainingQuestion], submission_text: str) -> str:
        """
        Build grading prompt for LLM
        
        Args:
            questions: List of training questions
            submission_text: Submission text to grade
            
        Returns:
            Grading prompt string
        """
        prompt = "You are an expert grader. Grade the following submission based on the provided questions and expected answers.\n\n"
        
        prompt += "QUESTIONS AND EXPECTED ANSWERS:\n"
        for i, question in enumerate(questions[:5], 1):  # Limit to first 5 questions
            prompt += f"{i}. {question.question_text}\n"
            if question.expected_answer:
                prompt += f"Expected Answer: {question.expected_answer}\n"
            prompt += f"Points: {question.point_value}\n\n"
        
        prompt += f"STUDENT SUBMISSION:\n{submission_text}\n\n"
        
        prompt += "Please provide:\n"
        prompt += "1. A score out of the total possible points\n"
        prompt += "2. Your confidence level (0.0 to 1.0)\n"
        prompt += "3. Brief justification for the score\n"
        
        return prompt
    
    def _extract_score_from_response(self, response: str) -> float:
        """
        Extract score from LLM response
        
        Args:
            response: LLM response text
            
        Returns:
            Extracted score
        """
        # Simplified score extraction
        import re
        
        # Look for patterns like "Score: 8/10" or "8 out of 10"
        score_patterns = [
            r'score[:\s]+(\d+(?:\.\d+)?)[/\s]+(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)[/\s]+(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)%'
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, response.lower())
            if match:
                if len(match.groups()) == 2:
                    # Fraction format
                    numerator = float(match.group(1))
                    denominator = float(match.group(2))
                    return numerator / denominator if denominator > 0 else 0.0
                else:
                    # Percentage format
                    return float(match.group(1)) / 100.0
        
        return 0.5  # Default score if extraction fails
    
    def _extract_confidence_from_response(self, response: str) -> float:
        """
        Extract confidence from LLM response
        
        Args:
            response: LLM response text
            
        Returns:
            Extracted confidence
        """
        # Simplified confidence extraction
        import re
        
        confidence_patterns = [
            r'confidence[:\s]+(\d+(?:\.\d+)?)',
            r'confident[:\s]+(\d+(?:\.\d+)?)',
        ]
        
        for pattern in confidence_patterns:
            match = re.search(pattern, response.lower())
            if match:
                confidence = float(match.group(1))
                # Normalize to 0-1 range
                if confidence > 1.0:
                    confidence = confidence / 100.0
                return min(max(confidence, 0.0), 1.0)
        
        return 0.7  # Default confidence if extraction fails    

    def _fallback_guide_processing(self, guide: TrainingGuide, file_info: Dict[str, Any], options: Dict[str, Any]) -> 'ProcessingResult':
        """
        Fallback processing method when DirectLLMGuideProcessor fails
        
        Args:
            guide: Training guide to process
            file_info: File information
            options: Processing options
            
        Returns:
            ProcessingResult with fallback data
        """
        try:
            logger.info(f"Using fallback processing for guide {guide.filename}")
            
            # Use file processor to extract text
            process_result = self.file_processor.process_file(file_info)
            content_text = process_result.get('text', '')
            
            if not content_text:
                return ProcessingResult(
                    success=False,
                    processing_method="fallback",
                    error_message="No text content extracted"
                )
            
            # Simple text-based analysis
            fallback_data = self._analyze_text_content(content_text, guide.guide_type)
            
            # Create a simplified ProcessingResult
            from src.services.guide_processing_router import ProcessingResult
            
            return ProcessingResult(
                success=True,
                processing_method="fallback",
                data={
                    "extracted_criteria": fallback_data.get("criteria", []),
                    "guide_structure": {
                        "metadata": fallback_data.get("metadata", {}),
                        "processing_method": "fallback",
                        "total_criteria": len(fallback_data.get("criteria", []))
                    },
                    "confidence_score": 0.5  # Lower confidence for fallback
                }
            )
            
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return ProcessingResult(
                success=False,
                processing_method="fallback",
                error_message=f"Fallback processing failed: {str(e)}"
            )
    
    def _analyze_text_content(self, content_text: str, guide_type: str) -> Dict[str, Any]:
        """
        Simple text-based analysis for fallback processing
        
        Args:
            content_text: Extracted text content
            guide_type: Type of guide
            
        Returns:
            Dictionary with analysis results
        """
        import re
        
        # Simple pattern matching for questions and points
        question_patterns = [
            r'(?:question|q\.?)\s*(\d+)[:\.]?\s*(.+?)(?=(?:question|q\.?)\s*\d+|$)',
            r'(\d+)[:\.]?\s*(.+?)(?=\d+[:\.]|$)',
        ]
        
        point_patterns = [
            r'(\d+)\s*(?:points?|marks?|pts?)',
            r'\[(\d+)\]',
            r'\((\d+)\s*(?:points?|marks?|pts?)\)'
        ]
        
        criteria = []
        questions_found = []
        
        # Extract questions
        for pattern in question_patterns:
            matches = re.finditer(pattern, content_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if len(match.groups()) >= 2:
                    question_num = match.group(1)
                    question_text = match.group(2).strip()[:500]  # Limit length
                    
                    if question_text and len(question_text) > 10:  # Filter out very short matches
                        questions_found.append({
                            'number': question_num,
                            'text': question_text
                        })
        
        # Extract points
        total_points = 0
        for pattern in point_patterns:
            matches = re.findall(pattern, content_text, re.IGNORECASE)
            for match in matches:
                try:
                    points = int(match)
                    total_points += points
                except ValueError:
                    continue
        
        # Create criteria from found questions
        for i, question in enumerate(questions_found[:10]):  # Limit to 10 questions
            # Try to find points for this specific question
            question_points = self._extract_points_for_question(content_text, question['text'])
            
            criterion = {
                'id': f"fallback_q_{question['number']}",
                'question_text': question['text'],
                'expected_answer': '',  # Not available in fallback
                'point_value': question_points or (total_points // len(questions_found) if questions_found else 1),
                'rubric_details': {},
                'visual_elements': [],
                'context': f"Extracted via fallback processing from {guide_type} guide"
            }
            criteria.append(criterion)
        
        return {
            'criteria': criteria,
            'metadata': {
                'title': 'Fallback Analysis',
                'total_points': total_points,
                'question_count': len(questions_found),
                'processing_method': 'fallback'
            }
        }
    
    def _extract_points_for_question(self, content_text: str, question_text: str) -> Optional[int]:
        """
        Try to extract points for a specific question
        
        Args:
            content_text: Full content text
            question_text: Specific question text
            
        Returns:
            Points value or None
        """
        import re
        
        # Look for points near the question text
        question_start = content_text.find(question_text)
        if question_start == -1:
            return None
        
        # Search in a window around the question
        window_start = max(0, question_start - 100)
        window_end = min(len(content_text), question_start + len(question_text) + 100)
        window_text = content_text[window_start:window_end]
        
        point_patterns = [
            r'(\d+)\s*(?:points?|marks?|pts?)',
            r'\[(\d+)\]',
            r'\((\d+)\s*(?:points?|marks?|pts?)\)'
        ]
        
        for pattern in point_patterns:
            match = re.search(pattern, window_text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_guide_data(self, guide: TrainingGuide, processing_result: 'ProcessingResult', session: TrainingSession) -> None:
        """
        Extract and store guide data from processing result
        
        Args:
            guide: Training guide to update
            processing_result: Result from guide processing
            session: Training session
        """
        try:
            result_data = processing_result.data or {}
            guide_structure = result_data.get('guide_structure', {})
            metadata = guide_structure.get('metadata', {})
            
            # Update guide with extracted data
            guide.content_text = result_data.get('raw_text', '')
            guide.question_count = int(metadata.get('question_count', 0))
            guide.total_marks = float(metadata.get('total_points', 0))
            guide.format_confidence = float(guide_structure.get('confidence_indicators', {}).get('structure_clarity', 0.5))
            guide.confidence_score = float(result_data.get('confidence_score', 0.5))
            
            logger.info(f"Extracted guide data: {guide.question_count} questions, {guide.total_marks} total marks")
            
        except Exception as e:
            logger.error(f"Failed to extract guide data: {e}")
            # Set default values
            guide.question_count = 0
            guide.total_marks = 0.0
            guide.format_confidence = 0.0
            guide.confidence_score = 0.0
    
    def _create_training_questions(self, guide: TrainingGuide, processing_result: 'ProcessingResult', session: TrainingSession) -> None:
        """
        Create training question records from processing result
        
        Args:
            guide: Training guide
            processing_result: Result from guide processing
            session: Training session
        """
        try:
            result_data = processing_result.data or {}
            extracted_criteria = result_data.get('extracted_criteria', [])
            
            questions_created = 0
            
            for criterion_data in extracted_criteria:
                try:
                    # Handle both dict and object formats
                    if hasattr(criterion_data, '__dict__'):
                        criterion_dict = criterion_data.__dict__
                    else:
                        criterion_dict = criterion_data
                    
                    # Extract confidence score
                    confidence = float(criterion_dict.get('confidence', 0.5))
                    if 'extraction_confidence' in criterion_dict:
                        confidence = float(criterion_dict['extraction_confidence'])
                    
                    training_question = TrainingQuestion(
                        guide_id=guide.id,
                        question_number=str(criterion_dict.get('id', f'q_{questions_created + 1}')),
                        question_text=str(criterion_dict.get('question_text', '')),
                        expected_answer=str(criterion_dict.get('expected_answer', '')),
                        point_value=float(criterion_dict.get('point_value', 0)),
                        rubric_details=criterion_dict.get('rubric_details', {}),
                        visual_elements=criterion_dict.get('visual_elements', []),
                        context=str(criterion_dict.get('context', '')),
                        extraction_confidence=confidence,
                        manual_review_required=confidence < session.confidence_threshold
                    )
                    
                    db.session.add(training_question)
                    questions_created += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to create training question from criterion: {e}")
                    continue
            
            logger.info(f"Created {questions_created} training questions for guide {guide.filename}")
            
        except Exception as e:
            logger.error(f"Failed to create training questions: {e}")
    
    def _implement_advanced_guide_type_detection(self, guide: TrainingGuide) -> str:
        """
        Advanced guide type detection using content analysis
        
        Args:
            guide: Training guide to analyze
            
        Returns:
            Detected guide type
        """
        try:
            if not guide.content_text:
                return guide.guide_type  # Return existing type if no content
            
            content_lower = guide.content_text.lower()
            
            # Count indicators for different guide types
            question_indicators = len([
                word for word in ['question', 'problem', 'solve', 'calculate', 'explain', 'describe']
                if word in content_lower
            ])
            
            answer_indicators = len([
                word for word in ['answer', 'solution', 'correct', 'expected', 'model answer']
                if word in content_lower
            ])
            
            rubric_indicators = len([
                word for word in ['rubric', 'criteria', 'marking', 'points', 'assessment', 'quality']
                if word in content_lower
            ])
            
            # Determine guide type based on indicators
            if question_indicators > answer_indicators and rubric_indicators > 0:
                return "questions_only"
            elif answer_indicators > question_indicators:
                return "answers_only"
            else:
                return "questions_answers"
        
        except Exception as e:
            logger.warning(f"Error analyzing guide content: {e}")
            return "questions_answers"  # Default fallback
    
    def _assess_question_quality(self, question: TrainingQuestion, session: TrainingSession) -> Dict[str, Any]:
        """
        Assess the quality of an extracted question
        
        Args:
            question: Training question to assess
            session: Training session
            
        Returns:
            Dictionary with quality assessment data
        """
        try:
            # Implement quality assessment logic
            confidence_score = min(1.0, max(0.0, question.extraction_confidence or 0.5))
            
            return {
                'confidence': confidence_score,
                'quality_score': confidence_score,
                'needs_review': confidence_score < session.confidence_threshold
            }
            
        except Exception as e:
            logger.error(f"Error assessing question quality: {e}")
            return {
                'confidence': 0.5,
                'quality_score': 0.5,
                'needs_review': True
            }


# Global instance for easy access
training_service = TrainingService()
 mprovement"es Iquirady - Reot Reeturn "N         r   lse:
           e   esting"
  ditional T"Needs Ad return             >= 0.6:
   rate if success_       el
     ring"h Monitowiturn "Ready  ret               5:
_rate >= 0.dencegh_confiand hirate >= 0.8  success_     elif      n"
 ductioro P"Ready for return        
        7:e >= 0.ratonfidence_d high_c>= 0.9 anss_rate ucce   if s    
         l
        essful_succ / totaonfidence_c = highate_rh_confidence        hig    
       
     )issions", 1l_submessfusuccmary.get("l = sumssfual_succe        tot", 0)
    fidenceon"high_c, {}).get(on"_distributi"confidencet(geuracy.idence = acc   high_conf)
         , 0s_rate"succesmary.get(" sum_rate =  success      
              })
   {_analysis",cyccuraults.get("analysis_resracy = a accu
            {})"summary",ults.get(s_resysi = analryumma     s   y:
           tr""
 
        "t stringessmenadiness ass      Re:
          Returns
     
           ltssis resunalys_results: A   analysi        gs:
       Ar      
  ion use
  ctprodu ready for  if model isss  Asse"
       ""
       ]) -> str:nyr, At[stlts: Dics_resulysianass(self, inemodel_readf _assess_   de"
    
 nowneturn "Unk          r")
  e}ed: {lation failalcumance cerforarning(f"Plogger.w         as e:
    eptioncept Exc        ex 
            
   provement"n "Needs Im    retur       :
        else     air"
    turn "F      re           0.4:
ore >=scl_eral    elif ov    "
    oodn "G   retur           0.6:
  >= all_score f over     eli
       nt"Excelleurn "         ret      
 8:ore >= 0.overall_sc  if             
  
        * 0.2)nsistency y * 0.5 + coracmated_accu + esti_rate * 0.3uccessore = (s  overall_sc          re
ed scote weightlcula     # Ca     
             re", 0)
 ency_sco("consisty.getccuracy = aenc consist     , 0)
      uracy"timated_acc.get("escuracycy = acraccu estimated_a       )
    e", 0success_ratry.get("mma sue =atsuccess_r        
          })
      ", {y_analysisacaccurlts.get("alysis_resu anaccuracy =       {})
     mary", .get("sumtsis_resul = analys   summary               try:
  """
  ring
      ce rating strman       Perfo
     eturns:    R       
       s
  sultsis re Analys_results:ysi     anal
         Args:
            g
  mance ratinall perforculate over     Cal
         """str:
  ]) ->  Any Dict[str,s_results:ysie(self, analrformancpeverall_te_ocula  def _cal
    
  ommendations  return rec  
      ")
      s errors.o analysi due tndationsc recommeate specifi generble tond("Unaons.appecommendati         re  {e}")
 : ion failedgeneratation Recommendng(f"er.warnilogg   
         n as e:t Exceptio   excep          
       ")
e.tion usg for producoyinsider deplactory. Conisf appears satormancedel perfMos.append("commendation re             ns:
  ecommendationot r   if               
 ")
      ement.finret r prompraining oal tadditioned el may neMod. re:.2f})ean_sco ({mverage scoreend(f"Low aons.appecommendati    r            :
     0.6mean_score <    if         an"]
    stats["mescore_core =   mean_s       
       core_stats:ean" in s "ms, dict) andore_statce(scan   if isinst         )
istics", {}re_stat"scoesults.get( analysis_re_stats = scor     s
      mmendationrecoerformance  P      #           
  y.")
     aritquestion clality and ng guide qunig traiviewinsider red. Con detectesalignmentsr of mih numbeappend("Higtions.endacomm     re    5:
       ful * 0.l_success> totasalignments      if mi)
       nts", 0l_misalignmetat("tohing.geatc = mlignments misa  
         ndationscommegnment re # Misali            
       ")
    ality.g qurainintion and tstion extrac queewvi1%}). Reng_rate:.e ({matchimatching ration estw qu(f"Londappedations.mmeneco r              0.5:
 _rate < ngif matchi            0)
 g_rate",atching.get("mtchinate = mang_rchi        mattions
     recommendaatching       # M  
     
          zation.")pt optimi or promdataaining l trionaider additnsults. Conce resdenficotion of low-opor("High prons.appendmmendatieco       r:
         ul > 0.3uccessf / total_sidenceonf_c     if low
                  ", 1)
 sionbmissuccessful_su.get("srysummassful = l_succe        tota   ", 0)
 ce_confident.get("lowe_disdencnfience = co  low_confid        )
  on", {}tributi_disnfidencecoacy.get("st = accurnfidence_di co     ons
      endatimmnce reco # Confide                    

   lity.")nd OCR quaformats aewing file onsider revi. Cate:.1%})success_ress rate ({"Low succ.append(ftionsmendaecom   r           
  :s_rate < 0.8 if succes           0)
 e",ess_rat"succmary.get(sumate = ess_r   succ      ions
   mmendate reco Success rat         #      
      
   }) {ysis",ng_anal"matchits.get(ysis_resulhing = anal       matc, {})
     sis"aly"accuracy_ants.get(s_resuly = analysi     accurac)
       ummary", {}et("slts.gysis_resualmmary = an su            try:
          
 s = []
    iondatecommen  r
            """ions
  ommendat rect ofis       Lurns:
            Ret    
   lts
      alysis resu: Anysis_resultsanal    
               Args: 
 
       ts resulests based on tmmendationte reco Genera"
            "":
   str]> List[y]) -r, Anct[stults: Dis_resalysi, anelfs(sendationecommenerate_r_gef   d
  
     }           esults]
t_relf.tes sr int() for to_dic": [r.ts"test_resul          ,
      )}"d: {str(eration faileeport gene": f"R   "error      
       ion_id,ssself.se": sion_id"ses        
          return {       ")
    failed: {e}generationort ep"Test r.error(f logger         on as e:
  tixcep  except E    
              urn report
       ret     ")
on_id}elf.sessi session {seport for test rhensiverated compre"Genefo(fgger.in    lo  
              }
             }
           
        ults)alysis_ress(aninsightct_key_f._extraghts": sel "key_insi                 ults),
  analysis_resiness(del_read_mo_assess: self.diness"_reael "mod                  sults),
 _resis(analyerformanceerall_pte_ovculalf._calce": seormanerall_perf"ov               {
      mary":  "sum         ,
     ionsommendatecions": rdatcommen    "re          
  sults,lysis_re anas":   "analysi       a,
      ": test_datest_results       "t         },
             s)
   _guidetrainingsession. in self. for guideestions)ng_qutrainiide.sum(len(guns": ning_questiotrai  "total_            
      ),oformat(c).isone.utme.now(timezateti dd":t_executetes     "            ,
   ormat()isofted_at.creaelf.session.ted": sing_comple"train                 ,
   ssion.name": self.seion_name      "sess          : {
    a"st_metadat"te                ssion_id,
f.seelid": son_  "sessi      
        {  report =     port
      rehensive rereate comp       # C     
           results)
 alysis_s(anommendationenerate_rec = self._gendationscomm    res
        ndationrate recomme  # Gene      
             ())
   _dictsult.toa.append(reest_dat           t   ts:
  _resulin self.testt resulfor          
   = []t_data      tes       sults
l test reCompile al    # y:
                tr""
     "rt
   po relete test Comp         ns:
      Retur  
    
          m analysis froResultsults: reslysis_         anas:
   rg   A  
          report
  hensive testompre  Generate c"
      ""  :
      r, Any] -> Dict[stny])t[str, A Dicresults:f, analysis_elrt(srepoate_test_f _gener
    de
    }(e)}"failed: {strg analysis f"Matchinor": n {"err     retur      
 : {e}")ysis failednaln matching a(f"Questioer.errorgg lo      as e:
     xception    except E   
     }
              )
       nments)l_misalig(set(totaents": listlignmmon_misa"com           ),
     ntsignmetotal_misal": len(lignmentstotal_misa     "        quency,
   ion_fre": questuencyon_freq    "questi          e 0,
   els > 0_questionsf totalestions ial_quency) / totrequestion_fte": len(qu_ra"matching               ns,
 stiototal_quens": uestioavailable_q   "total_             cy),
_frequenn(question": le_matchede_questions"uniqu            
    _matched),(alltches": len "total_ma      
         rn {     retu
                   _guides)
ngniion.trai.sess in self for guideuestions)ng_qainitrde. sum(len(guitions =_questotal      ns
      tiole quesilab ava# Get total        
             + 1
    id, 0)get(q_cy.tion_frequend] = quesequency[q_ifr  question_                
              r(match)
id = st    q_              se:
        el       tch
   = ma    q_id           
      tr):h, sstance(matc  elif isin        )
      , 'unknown'_id'('questionget= match.       q_id              
tch, dict):matance(  if isins        hed:
      in all_matcmatch      for }
        {requency =question_f        
    spatternze matching Analy         #   
             ments)
salignlt.mitend(resuments.exgn_misali     total            ments:
   align.misesult   if r           ons)
  stihed_quet.matc(resulextendl_matched.al                    ions:
ched_questt.matif resul           ults:
     essful_res succresult in        for       
          s = []
isalignmenttotal_m    
        matched = []     all_ns
       ed questiochmatlect all ol      # C    
         
     lysis"}ng anamatchifor l results successfuo ": "Nn {"errorretur       
         lts:successful_re  if not su          
            leted"]
"comp== s statuessing_proc if r.lts.test_resur in selfor r f [l_results =sfu    succes           try:
""
     "     
   alysisching anry with matictiona   D         ns:
     Retur  
   d
      red answeanatched were m questions w well Analyze ho      """
         y]:
tr, An Dict[s ->hing(self)stion_matc_queyzedef _anal   
    r(e)}"}
 ailed: {st flysiscy anaracu: f"Ac"rrorn {"e     retur    ")
   iled: {e}analysis faAccuracy f".error(ogger  l
          on as e:pti except Exce       
           }
    
         ) / 1.0)results]successful_ for r in ore or 0e_scr.confidenc([devd_alculate_st._c - (self": 1.0cy_scoreonsisten        "c0,
        ults else ful_resf success il_results)en(successfuce_count / lnfiden_co highacy":accurimated_st"e                ranges,
on": score_ributie_dist"scor                      },
         ce_count
 _confidenowfidence": l"low_con                   count,
 nce_ium_confidence": mednfidem_coiu      "med         t,
     ounence_cfidgh_conce": hionfiden   "high_c          
       n": {istributiodence_d  "confi              urn {
      ret
             }
          5)
       0.s if s < in score1 for s  sum("poor":         ,
       7)5 <= s < 0.ores if 0.for s in sc: sum(1   "fair"          9),
    < 0..7 <= s cores if 0 for s in s: sum(1d"goo     "          
  >= 0.9),s if scores in s for ent": sum(1excell        "        anges = {
re_rco          sts]
  ul_resulcessfr in suc or 0 for coreredicted_s = [r.pscores           analysis
 istribution   # Score d        
        )
      < 0.4ore or 0) ence_scnfidlts if (r.coessful_resuor r in succ = sum(1 fence_count low_confid          
 .7)r 0) < 0ce_score ofiden.con4 <= (rf 0.ults iful_res success in(1 for rt = sumnce_counnfideum_co   medi      
   = 0.7)ore or 0) >ce_scenr.confidif (_results fuln successr r i = sum(1 fonce_countigh_confide  h      ion
    imatcuracy estbased acence- Confid  #     
                
 sis"}cy analycuras for acesultl rsfu "No succes"error":  return {        :
      resultsl_ot successfu if n           
            leted"]
= "compstatus =processing_f r._results iest r in self.ts = [r forssful_resultucce   s
         ry: t      "
    ""sis
     y analyaccurac with ary  Diction        turns:
  Re  
        ency
      and consistcy g accuraalyze gradin      An """
  y]:
       str, Anict[y(self) -> Durace_accanalyz _ef    
    d5
 0.variance **urn         ret
ues) - 1) / (len(valx in values)* 2 for an) *((x - meum = svariance        en(values)
) / les= sum(valu      mean  
  
        return 0.0   
        lues) < 2:len(vaf   i    """
        iation
  d devndar       Sta
      Returns:        
           lues
ic vaumer ns: List ofue  val
                Args:     
  
    valuesion ofiatev standard dCalculate          """
t:
      -> floa]) : List[floatueslf, valev(selate_std_d _calcu
    defe)}"}
    {str(failed: f"Analysis "error": urn {et          r: {e}")
  edalysis failesults an r"Testr(flogger.erro          as e:
   oneptixcexcept E   
                     }
       )
 ).isoformat(zone.utc(timetime.nowtemp": dais_timesta "analys            
   ysis,g_analhinmatc": sis_analyching"mat           sis,
     uracy_analylysis": accuracy_anacc "a            tats,
   cs": ocr_sstatisti     "ocr_           ts,
ence_stanfidics": cotistidence_sta      "conf     ts,
     ore_stasctistics": score_sta     "          
      },         0
   lsens > 0 esiol_submisotaif tsions l_submis/ totans ul_submissio successf":ccess_rate        "su          
  ,bmissionsed_su": failsubmissionsiled_       "fa           ssions,
  miessful_subccons": susiul_submis"successf                 ions,
   tal_submissions": tosubmissal_"tot                   
 mmary": {       "su    {
        return                  

    ching()mation_questalyze_._an= selfysis nal matching_a           ysis
ing analtchn ma  # Questio               
 y()
      accurace_lf._analyznalysis = seuracy_aacc       ysis
     curacy anal   # Ac      
           "}
    onsssibmiessful su: "No succ"error"ats = {ocr_st= ats _st= confidencere_stats sco                else:
  
                }   s)
       fidence_con(ocr max  "max":           s),
       r_confidencen": min(oc"mi            
        ,idences)confocr_en( ldences) /um(ocr_confi"mean": s            
        ts = {   ocr_sta                  
                 }
       nces)
   idev(confate_std_deculal": self._c  "std_dev                nces),
  ax(confide": mmax       "             ),
idences": min(conf "min                   s),
celen(confidens) / encenfid: sum(co   "mean"                
  {_stats =idence     conf          
            
       }          
    dev(scores)std__calculate_self.td_dev":        "s    
         max(scores),ax":         "m  
          s), min(score":     "min           s),
    len(scorees) / or(sc: sum    "mean"               s = {
 re_stat      sco          
               sults]
 reessful_ccn su for r ior 0idence .ocr_confences = [rfid ocr_con               
results]ul_cessfsucfor r in  0 re ornfidence_scococes = [r.fiden      con        esults]
  successful_r 0 for r in _score orr.predictedscores = [       
         ults:essful_ressuccf       i    
           ]
   ompleted"= "cng_status =.processi if r_resultsn self.test i= [r for rsults _re  successful        s)
   submissionessfuluccr sics (only foistcore stat # S               
     s
   bmissionssful_suucceissions - s= total_submsions bmisd_su faile           ted")
 "completus ==sing_staprocessults if r._ren self.test i sum(1 for rubmissions =successful_s       ts)
     _resul.tests = len(selfmissionl_sub        totastics
    stati # Basic      
                  alyze"}
esults to anest r t: "Noor"urn {"err    ret            :
ltsest_resut self.t   if no          try:
     
     """ults
     es rh analysisonary witti     Dic     ns:
  Retur     
   s
        tricmerehensive culate complts and calsulyze test re      Ana
  """:
        [str, Any]Dict> ts(self) -resulalyze_test_    def _an
 }
    
       ageror_messor': er      'err',
      rorhod': 'ering_metad 'gr          age],
 error_messignments': [misal           '[],
 : estions'tched_qu'ma         ,
   idence': 0.0     'conf


class ModelTester:
    """
    Comprehensive model testing system that validates trained models
    with test submissions and provides detailed accuracy analysis.
    """
    
    def __init__(self, session_id: str, training_service: 'TrainingService'):
        """
        Initialize the model tester
        
        Args:
            session_id: ID of the training session to test
            training_service: Reference to the training service
        """
        self.session_id = session_id
        self.training_service = training_service
        self.session = None
        self.test_start_time = time.time()
        
        logger.info(f"ModelTester initialized for session {session_id}")
    
    def execute_model_testing(self, test_submissions: List[FileUpload]) -> Dict[str, Any]:
        """
        Execute comprehensive model testing with detailed analysis
        
        Args:
            test_submissions: List of test submission files
            
        Returns:
            Dictionary with comprehensive test results
        """
        try:
            # Initialize testing
            self._initialize_testing()
            
            # Validate test submissions
            self._validate_test_submissions(test_submissions)
            
            # Process test submissions
            test_results = self._process_test_submissions(test_submissions)
            
            # Analyze results
            analysis = self._analyze_test_results(test_results)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(test_results, analysis)
            
            # Create comprehensive report
            return self._create_test_report(test_results, analysis, recommendations)
            
        except Exception as e:
            logger.error(f"Model testing failed for session {self.session_id}: {e}")
            raise
    
    def _initialize_testing(self) -> None:
        """
        Initialize the testing process
        """
        try:
            # Get training session
            self.session = db.session.query(TrainingSession).filter_by(id=self.session_id).first()
            if not self.session:
                raise ValueError(f"Training session {self.session_id} not found")
            
            if self.session.status != "completed":
                raise ValueError(f"Training session {self.session_id} is not completed")
            
            # Validate that training data exists
            if not self.session.training_guides:
                raise ValueError("No training guides found for testing")
            
            # Count available questions
            total_questions = sum(len(guide.training_questions) for guide in self.session.training_guides)
            if total_questions == 0:
                raise ValueError("No training questions available for testing")
            
            logger.info(f"Testing initialized with {total_questions} training questions")
            
        except Exception as e:
            logger.error(f"Testing initialization failed: {e}")
            raise
    
    def _validate_test_submissions(self, test_submissions: List[FileUpload]) -> None:
        """
        Validate test submissions before processing
        
        Args:
            test_submissions: List of test submission files
        """
        try:
            if not test_submissions:
                raise ValueError("No test submissions provided")
            
            if len(test_submissions) > 50:  # Reasonable limit
                raise ValueError(f"Too many test submissions ({len(test_submissions)}). Maximum is 50.")
            
            # Validate each submission
            for i, submission in enumerate(test_submissions):
                try:
                    self.training_service._validate_file(submission)
                except Exc   }
          testing"]ase retryd - plen faileratio geneeport"Rns": [datiommen"reco            
    s": {},analysi     "    
       ts": [],ailed_resul   "det          : 0},
   ions"al_submiss"totary": {      "summ         ",
 tr(e)}led: {son fairatiort gene": f"Reperror     "       ),
    at(.isoformone.utc)timeze.now(tetim: dastamp"est_time  "t             on_id,
 si: self.sesssion_id"   "se           
  return {            e}")
ed: {ion failatrt cre repoor(f"Testr.errlogge      :
      n as eioept Except        exc       

       }             }
             e
lse Nond_at ecreateession.f self.s() iisoformatt.n.created_af.sessio": selpletionining_comra"t                  r,
  _to_answex_questionsf.session.mat": sel_limiquestionsmax_"                    threshold,
nfidence_n.colf.sessio sed":holdence_thresconfi      "           
   uides),n.training_gself.sessio in guide) for questionsaining_truide.um(len(g: sons"estiaining_qu "tr            {
       el_info":  "mod     
          endations,: recommendations"omm"rec          is,
      alysalysis": an   "an            _results,
 s": test_resultled"detai       
         y,ry": summarma  "sum             at(),
 oformone.utc).isez(timime.nowp": datetimestam"test_t                ion_id,
elf.sess": sssion_id     "se      {
         return                  
       }
      
      imetart_t self.test_sime() -ime.ttime": tng_"processi          
           0,ns":actioxtr_e"successful              ,
      max": 0}": 0, "{"minge": "score_ran                    ": 0,
e_confidenceragve  "a                  0,
": percentageverage_  "a                 : 0,
 rage_score"       "ave       
      : 0,missions"sub   "total_            {
     ry =        summa     
    lse:           e       }
         t_time
 f.test_starel- s() time.time_time": ssing     "proce           
    .5),'] > 0onfidence'c'][ractiontr['ext_results if tr in test sum(1 for tractions":excessful_"suc           
         cores)},max(smax": res), "min(scon": mie": {"ore_rang"sc          
          es),(confidences) / lenncideonf(c": sum_confidencege "avera           
        entages), / len(percntages): sum(perce"_percentage"average           
         ),len(scores / s)(score": sumscore "average_         
          sults),(test_re": lenonsmissi "total_sub                 = {
      summary         
                 esults]
   r in test_rr tidence'] fo]['confgrading' = [tr['cesconfiden          ts]
      t_resuln tes for tr itage']ng']['percen[tr['gradis =   percentage             
 st_results]tefor tr in 'score'] '][ngr['gradi scores = [t           s:
    result   if test_
         tatisticsmary s sum# Calculate              try:
 
     "     ""port
    reensive testith comprehary wonti        Dic
    ns:ur     Ret
       
        nstio recommendaoft tions: Lisdaommenec         results
   ysis rlysis: Anal    anas
        ictionariesult df test re o Listlts:est_resu     t:
        Args 
          t
    est reporsive tehenreate compr        C"
       ""y]:
 r, An) -> Dict[st List[str]dations: recommen[str, Any],lysis: Dictny]], anat[str, Ast[Dicults: Lif, test_res(sel_test_report def _create    
   s error"]
 to analysindations dueate recommeto generable "Un   return [)
         }"ailed: {eration feneon gcommendatiReer.error(f"       logg
     ption as e:pt Exce      exce    
  
        mendationscomop 10 reimit to t]  # L:10mendations[eturn recom         r     
        )
  issions"t submnal tesadditiomance with ng perfor monitoritinued("Conpen.aponscommendati         re")
       tsest resul current tased onry bs satisfactoarpeaperformance Model pns.append("datiommen     reco           ions:
ommendat if not rec          
             ce")
orman perfent of modeler assessm betto get a tsubmissions with more ("Testappenddations.    recommen           < 5:
 ) ultsst_res(teen l if          tions
 recommendaeneral     # G  
                 
 on types")stiected queaffes for ining examplmproving tra by isalignmentsn miss commoddre("Apendns.apecommendatio        r
        ts:en_misalignmmmon  if co         )
  []',entsignmaln_misommoterns.get('catnts = psalignme common_mi        s', {})
   patternlysis.get('rns = ana       patte
     mendationsed recomattern-bas  # P
               ")
        examplese specificd mory and adsistencfor conriteria ng ciew gradippend("Revons.adatiommenec       r   
          er():lowin issue.ncy' f 'consiste eli             )
   clarity"irthed improve scores ane ow confidench lwituestions ng qew trainivi"Red(ations.appencommend        re            
er():ssue.low in ice'denif 'confi          el    g")
  nninr better scamages otion iher resolu higusingby lity R quamprove OCs.append("Imendationom       rec        ue:
     n issR' if 'OC        i
         issues:issue in for       [])
     ntified', ssues_idelysis.get('isues = ana          is  ations
 recommendsedue-ba # Iss                  
 
    roduction")n pore using iresults befl review of manuaonsider "Cnd(ations.appe  recommend           ")
   xamples better e data orre trainingneeds momodel ests the  suggfidenceverage conpend("Low aapons.recommendati                
dence < 0.6:_confi     if avg     
  idence', 0)e_conft('averag}).ge, {tistics''stalysis.get(ence = ana  avg_confid     ions
     endat recommence-based  # Confid
                   ata")
    dir trainingprove thetions and imquesconfidence Review low-ns.append("ioendat   recomm        
     )xamples"aining etrding more consider adance - rmperfoate shows modernd("Model dations.appecommen     re          fair':
 rmance == 'perfooverall_lif         e  ining")
  for tra used ing guidesity of markve the qual improeview andnd("Rs.appecommendation    re    ")
        ang daty trainiigher-qualit he diverse orwith morel  the mod retrainingd("Considerppendations.a    recommen        or':
    mance == 'poll_perfor   if overa   n')
      unknow, 'mance'erall_perforsis.get('ovnaly ace =manorrfll_pevera          oions
  ndatmmereco-based Performance      #                
ns = []
   tiomenda       recomy:
        tr"
        ""
      stringscommendationf re     List os:
         Return     
            sults
 s resinalyis: A    analys
        tionariest diculrest of test ults: List_res     tes
       s:rg A       
     alysis
   sults and anst reased on te bmmendationsrate reco       Gene """
       
 [str]:]) -> Listt[str, Anyalysis: Dic an, Any]],ct[str: List[Diults_reself, testtions(se_recommendageneratef _ 
    d
   []   return 
          {e}")ailed:ysis fnment analg(f"Misaligarnin logger.w      e:
     tion as t Excepcep        ex         
n
   5 most commo]  # Top lignments[:5misaurn common_        ret      
     ]
                count > 1
    if             
 nts.items()lignment_couount in misa clignment,or misa    f       "
     ount} times){ccurred t} (ocisalignmenf"{m             s = [
   gnmentn_misali commo    
       ssionbmione sure than ur in mos that occsalignment miurn   # Ret                  
  1
 + ent, 0) isalignmcounts.get(ment_ misalignmnment] =igunts[misallignment_co      misa          
nts:l_misalignmein alsalignment     for mi     = {}
    ntsnt_cou  misalignme         urrences
  Count occ        #      
    ]
       return [             ments:
  gnisalil_m  if not al                    
nts)
  salignmed(mints.extenisalignme  all_m             s', [])
 nmentmisaligt('rading'].gents = tr['galignme       mis
         s:t_result tesr tr in      fo     = []
  entsll_misalignm  a
               try:""
         "erns
  attalignment pis mst of common Li   
        s:rnRetu
                   ionaries
 sult dictf test reList oresults:       test_      Args:
     
       
    test results across gnments misaliommonnd c       Fi"""
     str]:
    st[]]) -> Lit[str, AnyList[Dicesults: test_r, nments(selfsalignd_common_mi def _fi
    
       }
        ics': {}tatist     's         ,
  atterns': {}'p         ,
       }']str(e)is failed: {f'Analystified': [s_idenue        'iss       ed',
 sis_failnalyormance': 'averall_perf       'o    
     rn {etu         re}")
   led: {s fai analysiesults"Test rger.error(f   log      n as e:
   xceptioxcept E     e            
    }
        istics
    stats':atistic     'st           terns,
erns': pattt      'pa
          ed,es_identifiied': issuidentif    'issues_       ,
     rformancel_pe: overalrformance' 'overall_pe             {
  n ur     ret
                     }
   )
       tsresulents(test_alignmn_misommoelf._find_cts': smenmon_misalignom   'c          e 0,
   fidences elss) if cononfidence / len(cnfidences))en(set(coency': le_consist'confidenc              0,
   s elsecentage perentages) if len(perc /tages))set(percen': len(nsistencyore_co        'sc      {
  rns = tte       paterns
     dentify pat      # I   
          r'
     poo= 'rmance rall_perfo         ovee:
                els 'fair'
   ormance =erfverall_p o            :
   age >= 40_percentf avg      eli
      = 'good'e erformancverall_p         o        >= 60:
ntageperce   elif avg_         ellent'
ce = 'excformaneroverall_p           
     e >= 80:vg_percentag   if a         ']
ercentages['average_ptatistic = sg_percentage     av
       performance overall Determine        #             
 
   ")consistencyate in- may indicing results radvariable g"Highly ed.append(ifiues_ident         iss       cores
 different s 3:  # Allrcentages) >(pelen and percentages)n() == lees)et(percentagf len(s      i  ues
    tency issing consisad# Gr                  
      s")
ubmissionfailures} sn {ocr_s isuequality isend(f"OCR .apps_identifiedue         iss       lures > 0:
if ocr_fai           ] < 0.5)
 ce''confidenaction'][xtr['ets if trest_resulfor tr in tes = sum(1 ocr_failur       
      issues     # OCR
                  es)})")
 dencnfien(cocount}/{ldence_ow_confisults ({lidence re-conflow of High number(f"ndified.appeentidssues_     i          30%
 an   # More th) * 0.3:nces len(confidecount >nce_ low_confide          if5)
  < 0.f c ces iconfidenc in for (1 t = sumdence_counficon  low_      es
    dence issu Low confi      #
                ied = []
  es_identif      issus
      issuedentify    # I           

                  }
    es else 0}ercentages) if pntagerceax': max(p0, 'mntages else  if percees)n(percentag{'min': mie': age_rang  'percent           
   se 0},res elcos) if s': max(score0, 'maxscores else scores) if min(min': ge': {'an    'score_r        lse 0,
    nfidences e if coes)denclen(confies) / nfidencce': sum(codenage_confi    'aver        se 0,
     elercentagesges) if penta) / len(percntagesm(perce supercentage': 'average_          
     se 0,ores el) if scn(scoresles) / sum(scoree_score': 'averag      
          ts),resul': len(test_ssionssubmital_    'to      = {
      statistics                
      ]
   est_resultsr in tor t fnce']']['confidegrading [tr['onfidences =           c_results]
  testfor tr ine'] ]['percentag'grading' [tr[ntages =    perce   ts]
     ul_resn testr tr i] foore'ax_scding']['ms = [tr['gra_score       max]
     est_resultsr in tfor t] re'cong']['s['gradies = [tr scor           tistics
overall sta# Calculate     
                          }
        {}
   s':tic  'statis          
        s': {},attern         'p         lyze'],
   anatolts  test resud': ['Noes_identifie     'issu          
      'no_data',formance':'overall_per                   {
  return          s:
      _result not test          ifry:
      t""
     "
       s resultswith analysi Dictionary          
      Returns:   
             es
t dictionari resulist of test_results: Lst      te     gs:
       Ar
       issues
   terns and ntify pato idet results ttes    Analyze ""
            "]:
str, Any]]) -> Dict[tr, Any List[Dict[sest_results:lf, tlts(see_test_resuef _analyz   d    
         }

    ': str(e)error        '    
    : {},tion'stribu_dinfidenceco '               ,
ibution': {}ore_distr      'sc
          ,': 0.0encefiderage_con       'av
         d': 0,corestions_s'que           ,
      0d':ns_attempte'questio            n {
         retur      }")
  failed: {eculationrics caluracy meterror(f"Accogger.         ls e:
   tion aExceppt   exce                

      }    anges
     conf_rution':_distribfidence      'con         s,
 ngera score_':ibution_distrore    'sc            ,
ncerage_confide aveidence':erage_conf         'av0,
       ed > 0 else ons_attempt questittempted ifuestions_aed / qions_scorte': questg_ra     'scorin     
      _scored,questionsd': tions_score 'ques          ,
     mptedtteions_aquestted': tions_attemp'ques            
     return {                   

    .0)'] += 1.7-1ges['High (0onf_ran      c              :
lse          e
      ] += 1)'0.7(0.3-um nges['Mediconf_ra                    .7:
conf < 0 elif         
       ] += 1 (0-0.3)'Low_ranges['  conf               
    0.3:nf <       if co   s:
      ncenfidein co conf   for         ': 0}
 .7-1.0)h (0Hig0.7)': 0, '3-(0.0, 'Medium 3)':  {'Low (0-0.nf_ranges =co     
       tributionidence dis    # Conf
                    1
'] += 100%6-ges['7  score_ran                       else:
                   75%'] += 1
ges['51- score_ran                      
 75:ge <= nta  elif perce                 += 1
 50%'] 26-anges['ore_r    sc                  :
  <= 50 percentage elif                ] += 1
    '1-25%'es[e_rang       scor           
      ntage <= 25:lif perce    e           
     ] += 10%'ges['re_ran         sco               :
= 0ntage =perce if            00
        score']) * 1'max_ore'] / qr[arded_scqr['awe = ( percentag               0:
    re'] > scomax_   if qr['        lts:
     esustion_rin que  for qr         %': 0}
  : 0, '76-10051-75%'%': 0, '50'26-1-25%': 0,  0, '%':nges = {'0ore_ra    sc   ution
     re distrib   # Sco
                  
   0.0ences else onfids) if cencefidones) / len(confidence = sum(cidenconf   average_c        
  not None]] isnfidence'qr['coif lts on_resuqr in questifor nce'] r['confideces = [q confiden                   
   > 0)
  core']_s['awardedqrs if _resultuestionr qr in q= sum(1 fons_scored stioque       ts)
     stion_resullen(que = _attemptedquestions          
  icsetr Calculate m  #          
            }
              }
  ution': {_distribceden  'confi             : {},
     ibution'score_distr           '      0.0,
    ce':ge_confiden  'avera       
           ed': 0,oruestions_sc        'q             0,
empted':tions_att     'ques       
        {  return            ults:
   _resstiont que  if no        
           )
   s', []n_resultget('questioed_analysis. = detail_resultsquestion         
   sis', {})led_analyaiet('deting_result.gysis = gradtailed_anal de      
       try:""
             "
 smetricracy ry with accuctiona      Di
      s:     Return    
        grading
    from model lt: Resultng_resu       gradi  s:
   
        Arg     lt
   ading resuhe grcs for tacy metriurculate acc      Cal """
  ]:
        Any-> Dict[str,Any])  Dict[str, _result:inggradself, trics(_accuracy_mef _calculate
    de}
             led"
   aising fponse parssue': "Res     'i     
      ",e: {str(e)}sponsarse reto p"Failed ': ffeedback   '            e': 0.0,
 denc      'confi       ,
   : 0.0e'    'scor     {
       return           ")
  }onse: {eresp grading o parseFailed tg(f"r.warnin     logge
       eption as e:xcept Exc        e  
      }
      
           issues'issue':          
      ': feedback,ackedb 'fe           ence,
     confidnfidence':  'co         core,
     core': s's             
   {eturn  r       
               e
 issues = Non            ']:
    sues', 'n/ae', 'no is() in ['nonlowerissues.and f issues  i     one
       Nch elses_matp() if issueup(1).strimatch.gros = issues_   issue
         OTALL)r(), re.Dowense.l respo.+?)$',\s]+(es[:(r'issu = re.searches_match     issu  
     sues Extract is     #     
     "
         ck providedfeedbaelse "No h eedback_matc if f(1).strip()roupk_match.g feedbac =back    feed        ALL)
r(), re.DOTe.loweespons r',s|$))\n(?:issue?)(?=k[:\s]+(.+acrch(r'feedbh = re.seaeedback_matc  f
          dbackact fee    # Extr       
            nce))
 1.0, confide(0.0, min( = maxce    confiden   
     imalto decge entarcpe # Convert nce / 100.0 e = confideidenc       conf    
      > 1.0:dencef confi           i
 5lse 0.tch ema) if conf_ch.group(1)_matfloat(confence = onfid      c())
      nse.lowerespo\d+)?)', r\d+(?:\.e[:\s]+(confidencarch(r'e.se= rconf_match         ce
     confiden  # Extract             
         s
 max pointp atalue)  # Capoint_vn.e, question(scorscore = mi             else 0.0
tch_ma if score.group(1))re_matchsco float(     score =      
 se.lower())respon, d+)?)'?:\.\:\s]+(\d+(e['scor.search(rch = rere_mat  sco         act score
 Extr   #         
     try:       
 
      import re""
      
        " dataadingsed grarith pary wtion       Dic     Returns:
    
                ng graded
ei question bningion: Traist que       text
     LLM responseesponse:         rs:
     Arg  
         
     data structurede intosponsading regrLLM rse     Pa"
            ""r, Any]:
 -> Dict[stQuestion)rainingn: Tr, questioesponse: st(self, rponse_resding_parse_gradef     
    ompt
urn pr      ret
          
none]"erns or s: [any conc += "Issue     prompt
   ation]\n"explandback: [ += "Feerompt   pn"
     1.0]\ce: [0.0- "Confidenrompt +=  p
      ]\n" [number+= "Score:   prompt      s:\n"
response a your = "Format  prompt +
      \n"s\n or concernes4. Any issu += " prompt
       score\n"he ing tk explainef feedbac"3. Brimpt += 
        pro"to 1.0)\n(0.0 vel leonfidence  += "2. Cmpt        pron"
points)\mum  maxie (0 toort += "1. Sc promp"
       e:\ne provid += "Pleasrompt     p
         \n\n"
  ext}n_t\n{submissioBMISSION:TUDENT SUt += f"S     promp"
   \n\nlue}int_va{question.poINTS: MUM PO"MAXImpt += f      pro     
  n"
   }\n\2)ils, indent=ubric_detation.r.dumps(quesRIC: {json"GRADING RUB= fompt +  pr         ils:
 rubric_detaestion.      if qu 
  "
       n\nanswer}\on.expected_ER: {questiED ANSW"EXPECT += fompt       prr:
     ted_answeecon.expf questi i   
            }\n\n"
on_textquestiestion.N: {quESTIOQU+= f"  prompt      
 \n\n"c question:pecififor this sion ent submisstudng s the followiGradempt = f"  pro"
      ""
        ringrompt stading p       Gr   s:
    Return
              
    ion textubmissnt st: Studebmission_tex     suon
       ing questiainn: Trio   quest     gs:
         Ar     
   stion
   ific quea specmpt for  grading pro ate   Crea"""
            tr:
  sext: str) ->ssion_tmion, subingQuestion: Trainself, questipt(ading_promtion_grues _create_q   def   
         }
 
    {str(e)}"error: ocessing f"Prsue':          'is   }",
    r(e)d: {stding faileck': f"Grabaeed   'f      0,
       ce': 0.'confiden       ,
         e': 0.0ded_scor  'awar         e,
     .point_valutionre': ques   'max_sco            ,
 "..." 0] +ext[:10estion_tqu question.tion_text':      'ques       ,
   on_numberstiquestion.queon_id': questi         ' {
            return       
}: {e}")tion_numberesuestion.quuestion {qled for qfaiading "Question gr(fger.error       loge:
     n as t Exceptiocep   ex           

              }nse
    spo llm_re00 elsense) > 2(llm_respo" if len.. ".[:200] +onsellm_resp': sponse'llm_re               e'),
 ('issugetanalysis.ding_graue':        'iss
         k'],sis['feedbacnalyg_aack': gradinedb      'fe
          e'],nc'confideng_analysis[gradi': ceonfiden   'c            core'],
 lysis['s grading_anarded_score':'awa         ,
       luet_vaon.poinestiquscore': 'max_             t,
   estion_texestion.quse qu> 100 elon_text) n.questin(questioif le"  + "...ext[:100]question_testion.on_text': qutiques   '    ,
         _numbertionques: question.ion_id'st 'que             n {
      retur  
           n)
       tioquesesponse, (llm_ring_response_parse_grad = self.alysisrading_an       gponse
     rading res # Parse g    
                     )
          
ruehe=Tse_cac          u      nt grading
or consisteperature f,  # Low temerature=0.1emp          t      ,
ptgrading_promompt=er_pr  us        .",
      edteria provide cri on thbaseding air grad fnde acuratide acrader. Provt g an experare"You ompt=_pr      system          sponse(
_re.generatem_service_service.llainingself.tr = nselm_respo   l
         derato g # Use LLM                    
  xt)
  sion_te submisestion,mpt(qung_proestion_gradieate_qu = self._crading_prompt        grtion
    c quesfir this speciprompt foate grading       # Cretry:
             ""
 
        "ding resultcific graestion-speh quary witiction      D    
     Returns:        
     inst
    de agaon to graestiraining ququestion: T      on
      ubmissintent of s Text coion_text:misssub       
           Args:    
  
    tionaining ques specific trn against asiomis Grade sub""
         "      tr, Any]:
ict[sstion) -> DningQueion: Traiestext: str, quon_tssimilf, subion(seinst_quest_agaf _grade  
    de }
       (e)}
      or': str': {'errd_analysis'detaile        ],
        d: {str(e)}' faile [f'Gradingts':alignmen        'mis     
   [],tions': hed_ques    'matc          0.0,
  ': confidence  '       .0,
       rcentage': 0pe     '       
    core': 0.0,'max_s         
       : 0.0,e' 'scor      {
             return ")
        }ename}: {e for {filailedng f gradif"Modelor( logger.err
           :ption as eept Exce    exc    
            
  }             }
           ame
  ': filenlename 'fi            
       ns),(all_questio: lened'_evaluattions'ques                 el',
   odained_mod': 'trading_meth'gr                ts,
    esul: question_rlts'resution_es     'qu          : {
     analysis'led_    'detai           s,
 nmentaligs': misisalignment'm               ns,
 ed_questios': matchionquesttched_ 'ma             dence,
  _confie': overall 'confidenc         
      centage,ntage': per     'perce        core,
   possible_score': max_   'max_s            l_score,
  tota   'score':               return {
           
           ('issue')]
s if qr.getn_resultquestio] for qr in ['issue'= [qrts menmisalign         ]
    > 0e']scorr['awarded_sults if qn_rer in questiod'] for qtion_i [qr['quesns =uestio_q   matched         nts
lignmes and misa questionhedmatc # Identify           
           0
  ces else 0.en confidnces) ifconfidences) / len(onfidesum(cce = all_confiden over
            not None]fidence'] is qr['conresults iftion_ in ques] for qr'confidence'qr[ces = [   confiden       ences
  nfidtion covidual quesd on indince basenfideulate co# Calc                    
    se 0
ore > 0 ele_scmax_possibl0) if ore * 10le_sc_possib_score / maxtale = (to percentag      s
     ricmete overall alculat      # C     
         lue
    on.point_vauestie_score += qibl  max_poss          core']
    ed_sult['awardrestion_e += quesscor   total_             on_result)
uestiappend(qlts.tion_resu        ques       n)
 iost, quext_te(submissionionqueste_against__gradelf.t = sn_resulquestio          ons:
      all_questiquestion in for               
    .0
      score = 0_possible_       max     = 0.0
 _scoretotal      
      s = []sult question_re    ion
       stuet each qade againsGr   #              
        to_answer]
x_questions_.session.maselfns[:_questioll = ationsl_ques      al        )
  ruerse=Teveence or 0, rction_confidxtraa q: q.e=lambdort(keyions.sall_quest           e)
     idencst confheg (higtraininin used were that ions e quest the sam Use    #          r:
  o_answe_tnsquestioon.max_elf.sessions) > suestill_qand len(ar ons_to_answeti.max_ques.sessionf self     i    ed
   cifi spemit ifquestion li # Apply            
         
       }          sis': {}
  d_analytaile      'de            lable'],
  s avaiquestionining o trants': ['Nmisalignme       '           ns': [],
  estioed_qu      'match           0,
   nce': 0.nfide    'co           
     ntage': 0.0,ce    'per               0.0,
 e': ax_scor        'm         0,
   ore': 0.sc '                   return {
              
  tions:uesall_q     if not       
   
          ons)ing_questiainguide.trons.extend( all_questi           es:
    aining_guidon.trsies.slf guide in se        for[]
    stions = ue    all_q        
stionsraining queall tGet    #           try:
      "
     ""   analysis
 s and esultrading rwith gctionary      Di
       s:     Return         
     on file
 missisubame of the  filename: N      ssion
     rom submit ftracted textext: Exbmission_       su
      Args:
         sis
      ed analyancith enhdel wned mong the trai usibmissionrade su     G
     """
      Any]:[str, tr) -> Dictfilename: s str, ission_text:ubmf, ssel_model(ion_withmiss_sub def _grade    
        }
      e)
 error': str(     '         nknown',
  : 'ue_type''fil                'failed',
d': tho       'me        ': 0.0,
 fidence       'con   
      : '',text'    '          turn {
       re
       {e}")ame}: ission.filen for {submn failedtioextracext rror(f"Ter.e logg         n as e:
  ept Exceptio exc
                     
             }     'document'
_type':        'file       g',
      ocessinent_prumd': 'doc     'metho             reliable
  g assumed rocessin p# Document': 1.0,  confidence        '            ),
('text', ''s_result.getoces 'text': pr          
         eturn {           r     le_info)
(fiilecess_for.pro_processervice.fileining_sraself.tult = s_res     proces         ocuments
  cessor for dle pro  # Use fi              :
      else  
          }      '
    age 'imile_type': 'f               ocr',
    ethod': '      'm           
   e', 0.0),denct.get('confiocr_resulnfidence': co   '                t', ''),
 et('texsult.gre': ocr_text           '        eturn {
            rpath)
     file_mission.age(sub_imfromtext_extract_cr_service.rvice.og_setraininsult = self.cr_re     o       s
    lege fifor ima  # Use OCR     
          gif'}:, '.bmp', '., '.tiff'', '.png'', '.jpegin {'.jpgle_ext     if fi 
                 
  x.lower()fiame).sufsion.filenPath(submis file_ext =           e
 le typn fid based otion methone extracrmi    # Dete 
                }
        pe,
       tyssion.file_mi'type': sub         
       le_size,sion.fimisze': sub         'si     ,
  .filenameissionbm'name': su         ,
       athssion.file_psubmi'path':            = {
      _infolefi         :
         try"
  "    "    nfidence
coext and acted ttr ex withonary    Dicti:
          Returns
         e
         ission filsubmst ission: Te   subm       gs:
    Ar        
    od
  ate methg approprission usintest submirom act text ftr  Ex         """
     :
t[str, Any]-> DicUpload) ion: File submissself,t(bmission_tex_extract_su
    def ise
        ra")
        {e}: sing failedrocesn pssioTest submir.error(f"ge log           tion as e:
cepexcept Ex
                   sults
 urn test_re        ret      
 )
         errors"errors)} rocessing_len(pith {ed wcompletrocessing "Pwarning(fogger.   l        ors:
     sing_err   if proces
                   it()
  mmsession.co       db.      
         inue
   cont             ")
      ame}: {e}filenssion.on {submisubmississ test led to proceai"Fr.error(f      logge          
    })                   (e)
 : str"error"                      ,
  filenamen.missio": subilename       "f           
      d({errors.appenessing_        proc             as e:
ont Excepti    excep                  
          ult)
    (ress.appendsultst_re   te                          

                 }          _time
    test_start - self. time.time()ng_time":ssi     "proce              cs,
     cy_metri": accuraacy    "accur             t,
       _resulrading": gading       "gr                sult,
 raction_re: exttion"  "extrac                      ename,
ission.filsubm": ename      "fil                 .id,
 est_sub_id": tmission    "sub                  t = {
  esul           r   lt
      resuve mprehensireate co   # C          
                         leted"
  comp_status = ".processing   test_sub               s']
  salignment['mi_result gradingnments =b.misalig     test_su          s']
     estionatched_quresult['mading_estions = grhed_quub.matc    test_s                e']
onfidencg_result['cradine_score = gonfidenc  test_sub.c          
        lt['score']ng_resuore = gradidicted_sc_sub.pre        test            nfidence']
_result['cotion= extracfidence onst_sub.ocr_cte                    t']
sult['texraction_retext = exttracted_ub.ex   test_s            ecord
     ion rsubmissst tedate   # Up                  
                ult)
    g_resadintrics(grccuracy_mee_aculat= self._calcs _metricyccura          a    ics
       metrte accuracyalcula C #                
                            )
            
   on.filename submissi                    , 
   ult['text']tion_res     extrac                 
  odel(_with_mbmissionade_su= self._grding_result ra        g            ned model
aiusing tr# Grade            
                           )
  sionxt(submisteubmission_._extract_sesult = selfxtraction_r   e         
        t contentct tex Extra #                         
              h()
ssion.flus db.se               sub)
    est_sion.add(tsesdb.              
                                )
              ng"
="processiing_status  process                     e_path,
 n.filbmissiole_path=su    fi               ,
     amen.filensiome=submis     filena               ,
    _idonssid=self.session_i    se                on(
    ubmissi = TestSubst_s     te         cord
      ssion re submistate teCre        #     
                         ")
   ilename}ission.f)}: {submsubmissionsst_len(te+1}/{sion {ist submissing te(f"Proceser.info    logg              y:
       tr           issions):
subme(test_ enumeratssion in submi      for i,
           ]
       g_errors = [cessin       pro
     = []st_results          te  try:
   ""
      
        "est dictionarisulrest of test           Lins:
    Retur
                  es
ilsion ftest submisf st oLis: t_submission   tes
              Args:
     ts
      esule grading rd generats anubmissioncess test s        Pro"""

        , Any]]:trt[Dict[sLisUpload]) -> : List[Fileonsissitest_submsions(self, est_submisocess_tdef _pr  
       raise
          {e}")
 failed: alidation ssion v"Test submier.error(fogg l      :
     eption as except Exc
        e  
          ")bmissions)} test suubmissions {len(test_stedo(f"Validagger.inf         lo
      
         id: {e}")vale}) is inilenamssion.fmi1} ({sub{i+ion bmiss(f"Test sualueError   raise V              
   eption as e: