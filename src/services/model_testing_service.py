"""
Model Testing Service

This service handles testing trained LLM models with student submissions,
providing comprehensive analysis and comparison capabilities.
"""

import os
import uuid
import time
import json
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from flask import current_app
from src.database.models import db, LLMModelTest, LLMTestSubmission, LLMTrainingJob
from src.services.file_processing_service import FileProcessingService
from utils.logger import logger

class ModelTestingService:
    """Service for testing trained LLM models with student submissions"""
    
    def __init__(self):
        self.file_processor = FileProcessingService()
        self._running_tests: Dict[str, threading.Thread] = {}
        self._cancelled_tests: set = set()
    
    def create_test_session(self, user_id: str, training_job_id: str, config: Dict[str, Any]) -> str:
        """Create a new model testing session"""
        try:
            # Verify training job exists and belongs to user
            training_job = LLMTrainingJob.query.filter_by(
                id=training_job_id,
                user_id=user_id
            ).first()
            
            if not training_job:
                raise ValueError("Training job not found or access denied")
            
            if training_job.status != 'completed':
                raise ValueError("Training job must be completed before testing")
            
            # Create test session
            test_session = LLMModelTest(
                user_id=user_id,
                training_job_id=training_job_id,
                name=config.get('name', f'Test for {training_job.name}'),
                description=config.get('description', ''),
                status='pending',
                config=config,
                grading_criteria=config.get('grading_criteria', {}),
                confidence_threshold=config.get('confidence_threshold', 0.8),
                comparison_mode=config.get('comparison_mode', 'strict'),
                feedback_level=config.get('feedback_level', 'detailed')
            )
            
            db.session.add(test_session)
            db.session.commit()
            
            logger.info(f"Created test session {test_session.id} for training job {training_job_id}")
            return test_session.id
            
        except Exception as e:
            logger.error(f"Error creating test session: {e}")
            db.session.rollback()
            raise
    
    def upload_test_submissions(self, test_id: str, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Upload and process test submission files"""
        try:
            # Verify test session exists
            test_session = db.session.get(LLMModelTest, test_id)
            if not test_session:
                raise ValueError("Test session not found")
            
            uploaded_submissions = []
            
            for file_info in files:
                try:
                    # Generate unique filename
                    original_name = file_info['original_name']
                    file_extension = Path(original_name).suffix.lower()
                    stored_name = f"{uuid.uuid4()}{file_extension}"
                    
                    # Create upload directory
                    upload_dir = os.path.join(current_app.root_path, 'uploads', 'test_submissions')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    file_path = os.path.join(upload_dir, stored_name)
                    
                    # Save file
                    if 'content' in file_info:
                        with open(file_path, 'wb') as f:
                            f.write(file_info['content'])
                    elif 'file_path' in file_info:
                        import shutil
                        shutil.copy2(file_info['file_path'], file_path)
                    
                    # Get file size
                    file_size = os.path.getsize(file_path)
                    
                    # Process file content
                    processing_result = self.file_processor.process_file_with_fallback(
                        file_path, file_info
                    )
                    
                    # Create submission record
                    submission = LLMTestSubmission(
                        test_id=test_id,
                        original_name=original_name,
                        stored_name=stored_name,
                        file_path=file_path,
                        file_size=file_size,
                        file_type=file_extension[1:] if file_extension else 'unknown',
                        text_content=processing_result.get('text_content', ''),
                        word_count=processing_result.get('word_count', 0),
                        processing_status='completed' if processing_result['success'] else 'failed',
                        processing_error='; '.join(processing_result.get('validation_errors', [])),
                        processing_duration_ms=processing_result.get('processing_duration_ms', 0),
                        expected_grade=file_info.get('expected_grade'),
                        expected_feedback=file_info.get('expected_feedback', '')
                    )
                    
                    db.session.add(submission)
                    uploaded_submissions.append(submission)
                    
                except Exception as e:
                    logger.error(f"Error processing submission {file_info.get('original_name', 'unknown')}: {e}")
                    # Create failed submission record
                    submission = LLMTestSubmission(
                        test_id=test_id,
                        original_name=file_info.get('original_name', 'unknown'),
                        stored_name='',
                        file_path='',
                        file_size=0,
                        file_type='unknown',
                        processing_status='failed',
                        processing_error=str(e)
                    )
                    db.session.add(submission)
                    uploaded_submissions.append(submission)
            
            # Update test session
            test_session.total_submissions = len(uploaded_submissions)
            test_session.status = 'ready'
            
            db.session.commit()
            
            logger.info(f"Uploaded {len(uploaded_submissions)} submissions for test {test_id}")
            return [sub.to_dict() for sub in uploaded_submissions]
            
        except Exception as e:
            logger.error(f"Error uploading test submissions: {e}")
            db.session.rollback()
            raise
    
    def run_model_test(self, test_id: str) -> Dict[str, Any]:
        """Run model test asynchronously"""
        try:
            # Verify test session
            test_session = db.session.get(LLMModelTest, test_id)
            if not test_session:
                raise ValueError("Test session not found")
            
            if test_session.status not in ['ready', 'failed']:
                raise ValueError(f"Test cannot be started in current state: {test_session.status}")
            
            if test_id in self._running_tests:
                logger.warning(f"Test {test_id} is already running")
                return {'status': 'already_running'}
            
            # Start test in background thread
            thread = threading.Thread(
                target=self._execute_test,
                args=(test_id,),
                daemon=True
            )
            thread.start()
            self._running_tests[test_id] = thread
            
            # Update test status
            test_session.status = 'running'
            test_session.started_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Started model test {test_id}")
            return {'status': 'started', 'test_id': test_id}
            
        except Exception as e:
            logger.error(f"Error starting model test: {e}")
            raise
    
    def _execute_test(self, test_id: str) -> None:
        """Execute model test in background thread"""
        start_time = time.time()
        
        try:
            with current_app.app_context():
                test_session = db.session.get(LLMModelTest, test_id)
                if not test_session:
                    logger.error(f"Test session {test_id} not found during execution")
                    return
                
                # Get test submissions
                submissions = LLMTestSubmission.query.filter_by(
                    test_id=test_id,
                    processing_status='completed'
                ).all()
                
                if not submissions:
                    self._update_test_status(test_id, 'failed', 'No valid submissions found')
                    return
                
                logger.info(f"Processing {len(submissions)} submissions for test {test_id}")
                
                # Process each submission
                processed_count = 0
                total_confidence = 0.0
                results_summary = {
                    'total_submissions': len(submissions),
                    'processed_submissions': 0,
                    'accurate_grades': 0,
                    'average_confidence': 0.0,
                    'average_accuracy': 0.0,
                    'grade_differences': [],
                    'processing_errors': []
                }
                
                for submission in submissions:
                    if test_id in self._cancelled_tests:
                        logger.info(f"Test {test_id} was cancelled")
                        return
                    
                    try:
                        # Process submission with model (placeholder implementation)
                        result = self._process_submission_with_model(submission, test_session)
                        
                        # Update submission with results
                        submission.model_grade = result.get('grade')
                        submission.model_feedback = result.get('feedback', '')
                        submission.confidence_score = result.get('confidence', 0.0)
                        submission.detailed_results = result.get('detailed_results', {})
                        
                        # Calculate comparison metrics
                        if submission.expected_grade is not None:
                            grade_diff = abs(submission.model_grade - submission.expected_grade)
                            submission.grade_difference = grade_diff
                            submission.grade_accuracy = grade_diff <= test_session.confidence_threshold
                            
                            if submission.grade_accuracy:
                                results_summary['accurate_grades'] += 1
                            
                            results_summary['grade_differences'].append(grade_diff)
                        
                        processed_count += 1
                        total_confidence += submission.confidence_score
                        
                        # Update progress
                        progress = (processed_count / len(submissions)) * 100
                        self._update_test_progress(test_id, progress, processed_count)
                        
                    except Exception as e:
                        logger.error(f"Error processing submission {submission.id}: {e}")
                        submission.processing_status = 'failed'
                        submission.processing_error = str(e)
                        results_summary['processing_errors'].append({
                            'submission_id': submission.id,
                            'error': str(e)
                        })
                
                # Calculate final metrics
                results_summary['processed_submissions'] = processed_count
                if processed_count > 0:
                    results_summary['average_confidence'] = total_confidence / processed_count
                    results_summary['average_accuracy'] = results_summary['accurate_grades'] / processed_count
                
                # Update test session with final results
                test_session.processed_submissions = processed_count
                test_session.accuracy_score = results_summary['average_accuracy']
                test_session.average_confidence = results_summary['average_confidence']
                test_session.results = results_summary
                test_session.status = 'completed'
                test_session.completed_at = datetime.utcnow()
                test_session.processing_duration_ms = int((time.time() - start_time) * 1000)
                
                db.session.commit()
                
                logger.info(f"Completed test {test_id} - processed {processed_count} submissions")
                
        except Exception as e:
            logger.error(f"Error executing test {test_id}: {e}")
            self._update_test_status(test_id, 'failed', str(e))
        
        finally:
            # Clean up
            if test_id in self._running_tests:
                del self._running_tests[test_id]
            self._cancelled_tests.discard(test_id)
    
    def _process_submission_with_model(self, submission: LLMTestSubmission, test_session: LLMModelTest) -> Dict[str, Any]:
        """Process a submission with the trained model (placeholder implementation)"""
        import random
        
        # Simulate processing time
        time.sleep(random.uniform(0.5, 2.0))
        
        if submission.expected_grade is not None:
            # Add some variance to simulate model behavior
            variance = random.uniform(-0.1, 0.1)
            model_grade = max(0, min(1, submission.expected_grade + variance))
        else:
            model_grade = random.uniform(0.6, 0.9)
        
        confidence = random.uniform(0.7, 0.95)
        
        feedback = f"Model feedback for {submission.original_name}. " \
                  f"Grade: {model_grade:.2f}, Confidence: {confidence:.2f}"
        
        return {
            'grade': model_grade,
            'feedback': feedback,
            'confidence': confidence,
            'detailed_results': {
                'processing_time_ms': random.randint(500, 2000),
                'model_version': test_session.training_job.model_id,
                'criteria_scores': {
                    'content_quality': random.uniform(0.6, 0.9),
                    'structure': random.uniform(0.7, 0.9),
                    'accuracy': random.uniform(0.6, 0.8)
                }
            }
        }
    
    def _update_test_status(self, test_id: str, status: str, error_message: Optional[str] = None) -> None:
        """Update test session status"""
        try:
            with current_app.app_context():
                test_session = db.session.get(LLMModelTest, test_id)
                if test_session:
                    test_session.status = status
                    if error_message:
                        test_session.error_message = error_message
                    if status in ['completed', 'failed', 'cancelled']:
                        test_session.completed_at = datetime.utcnow()
                    
                    db.session.commit()
        except Exception as e:
            logger.error(f"Error updating test status for {test_id}: {e}")
    
    def _update_test_progress(self, test_id: str, progress: float, processed_count: int) -> None:
        """Update test progress"""
        try:
            with current_app.app_context():
                test_session = db.session.get(LLMModelTest, test_id)
                if test_session:
                    test_session.progress = progress
                    test_session.processed_submissions = processed_count
                    db.session.commit()
        except Exception as e:
            logger.error(f"Error updating test progress for {test_id}: {e}")
    
    def get_test_results(self, test_id: str, user_id: str) -> Dict[str, Any]:
        """Get test results for a completed test"""
        try:
            test_session = LLMModelTest.query.filter_by(
                id=test_id,
                user_id=user_id
            ).first()
            
            if not test_session:
                raise ValueError("Test session not found or access denied")
            
            # Get submissions with results
            submissions = LLMTestSubmission.query.filter_by(test_id=test_id).all()
            
            return {
                'test_info': test_session.to_dict(),
                'submissions': [sub.to_dict() for sub in submissions],
                'summary': test_session.results or {},
                'performance_metrics': test_session.performance_metrics or {}
            }
            
        except Exception as e:
            logger.error(f"Error getting test results: {e}")
            raise
    
    def cancel_test(self, test_id: str, user_id: str) -> bool:
        """Cancel a running test"""
        try:
            # Verify test ownership
            test_session = LLMModelTest.query.filter_by(
                id=test_id,
                user_id=user_id
            ).first()
            
            if not test_session:
                raise ValueError("Test session not found or access denied")
            
            if test_session.status not in ['running', 'pending']:
                raise ValueError("Test cannot be cancelled in current state")
            
            self._cancelled_tests.add(test_id)
            
            # Update status
            test_session.status = 'cancelled'
            test_session.completed_at = datetime.utcnow()
            db.session.commit()
            
            # Clean up thread reference
            if test_id in self._running_tests:
                del self._running_tests[test_id]
            
            logger.info(f"Cancelled test {test_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling test: {e}")
            return False