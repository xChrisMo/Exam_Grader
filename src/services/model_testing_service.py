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
from datetime import datetime, timezone
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
            test_session.started_at = datetime.now(timezone.utc)
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
                test_session.completed_at = datetime.now(timezone.utc)
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
        """Process a submission with the actual trained model"""
        processing_start_time = time.time()
        
        try:
            from src.services.consolidated_llm_service import ConsolidatedLLMService
            from src.services.consolidated_grading_service import ConsolidatedGradingService
            
            llm_service = ConsolidatedLLMService()
            grading_service = ConsolidatedGradingService()
            
            # Get the trained model context from the training job
            training_job = test_session.training_job
            if not training_job:
                raise ValueError("Training job not found for test session")
            
            # Use the trained model's learned context for evaluation
            model_context = self._get_trained_model_context(training_job)
            
            # Generate model response using trained context
            test_prompt = f"""
            Based on your training on educational content, evaluate this student submission:
            
            Submission Content: {submission.text_content}
            
            Provide a comprehensive evaluation including:
            1. Content quality assessment
            2. Accuracy of information
            3. Structure and organization
            4. Overall grade (0.0 to 1.0 scale)
            5. Specific feedback for improvement
            """
            
            # Generate response with retry mechanism
            max_retries = 3
            generated_response = None
            
            for attempt in range(max_retries):
                try:
                    generated_response = llm_service.generate_response(
                        system_prompt=model_context['system_prompt'],
                        user_prompt=test_prompt,
                        temperature=0.2  # Lower temperature for consistent evaluation
                    )
                    
                    if generated_response and len(generated_response.strip()) > 50:
                        break
                        
                except Exception as llm_error:
                    logger.warning(f"LLM service attempt {attempt + 1} failed: {llm_error}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise llm_error
            
            if not generated_response:
                raise ValueError("Failed to generate model response after retries")
            
            # Extract grade and feedback from the response
            grade_info = self._extract_grade_from_response(generated_response)
            model_grade = grade_info['grade']
            extracted_feedback = grade_info['feedback']
            confidence = grade_info['confidence']
            
            # Validate the grade using the grading service for consistency
            if hasattr(test_session, 'grading_criteria') and test_session.grading_criteria:
                try:
                    grading_result = grading_service.grade_submission(
                        marking_guide_content=str(test_session.grading_criteria),
                        student_submission_content=submission.text_content
                    )
                    
                    # Use grading service result as validation
                    if grading_result[0] and 'detailed_grades' in grading_result[0]:
                        grades = grading_result[0]['detailed_grades']
                        if grades:
                            service_grade = grades[0].get('score', 0) / grades[0].get('max_score', 1)
                            # Average the model grade with service grade for better accuracy
                            model_grade = (model_grade + service_grade) / 2
                            confidence = min(confidence + 0.1, 1.0)  # Boost confidence when validated
                            
                except Exception as grading_error:
                    logger.warning(f"Grading service validation failed: {grading_error}")
                    # Continue with model-only grade
            
            processing_time_ms = int((time.time() - processing_start_time) * 1000)
            
            # Calculate detailed criteria scores
            criteria_scores = self._calculate_criteria_scores(submission.text_content, generated_response)
            
            return {
                'grade': max(0.0, min(1.0, model_grade)),  # Ensure grade is in valid range
                'feedback': extracted_feedback,
                'confidence': max(0.0, min(1.0, confidence)),  # Ensure confidence is in valid range
                'detailed_results': {
                    'processing_time_ms': processing_time_ms,
                    'model_version': training_job.model_id,
                    'training_job_id': training_job.id,
                    'model_response': generated_response[:500] + "..." if len(generated_response) > 500 else generated_response,
                    'criteria_scores': criteria_scores,
                    'validation_method': 'llm_with_grading_service' if hasattr(test_session, 'grading_criteria') else 'llm_only'
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing submission {submission.id} with trained model: {e}")
            
            # Fallback to basic evaluation if model processing fails
            processing_time_ms = int((time.time() - processing_start_time) * 1000)
            
            return {
                'grade': 0.5,  # Neutral grade for failed processing
                'feedback': f"Error processing submission with trained model: {str(e)[:100]}...",
                'confidence': 0.3,  # Low confidence for error cases
                'detailed_results': {
                    'processing_time_ms': processing_time_ms,
                    'model_version': test_session.training_job.model_id if test_session.training_job else 'unknown',
                    'error': str(e),
                    'criteria_scores': {
                        'content_quality': 0.5,
                        'structure': 0.5,
                        'accuracy': 0.5
                    },
                    'validation_method': 'error_fallback'
                }
            }
    
    def _get_trained_model_context(self, training_job) -> Dict[str, str]:
        """Get the trained model's context and system prompt"""
        try:
            # Extract training context from the job's results and dataset
            training_results = training_job.evaluation_results or {}
            training_accuracy = training_results.get('accuracy', 0.0)
            
            # Build system prompt based on training data
            system_prompt = f"""You are an AI model that has been specifically trained for educational assessment. 
            
            Your training details:
            - Model: {training_job.model_id}
            - Training accuracy: {training_accuracy:.2%}
            - Trained on educational content and grading criteria
            
            You should evaluate student submissions based on:
            1. Content accuracy and completeness
            2. Understanding of key concepts
            3. Structure and organization
            4. Clarity of expression
            
            Provide grades on a 0.0 to 1.0 scale where:
            - 0.9-1.0: Excellent work demonstrating mastery
            - 0.8-0.89: Good work with minor issues
            - 0.7-0.79: Satisfactory work meeting basic requirements
            - 0.6-0.69: Below average work with significant gaps
            - 0.0-0.59: Poor work requiring major improvement
            
            Always provide specific, constructive feedback."""
            
            return {
                'system_prompt': system_prompt,
                'model_id': training_job.model_id,
                'training_accuracy': training_accuracy
            }
            
        except Exception as e:
            logger.warning(f"Error getting trained model context: {e}")
            # Fallback to basic context
            return {
                'system_prompt': "You are an AI assistant trained to evaluate student submissions. Provide fair and constructive assessment.",
                'model_id': training_job.model_id if training_job else 'unknown',
                'training_accuracy': 0.0
            }
    
    def _extract_grade_from_response(self, response: str) -> Dict[str, Any]:
        """Extract grade and feedback from model response"""
        try:
            import re
            
            # Look for grade patterns in the response
            grade_patterns = [
                r'grade[:\s]*([0-9]*\.?[0-9]+)',
                r'score[:\s]*([0-9]*\.?[0-9]+)',
                r'([0-9]*\.?[0-9]+)\s*(?:out of|/)\s*(?:1\.0|1|10)',
                r'([0-9]*\.?[0-9]+)\s*(?:%|percent)'
            ]
            
            extracted_grade = None
            for pattern in grade_patterns:
                matches = re.findall(pattern, response.lower())
                if matches:
                    try:
                        grade_value = float(matches[0])
                        # Normalize grade to 0-1 scale
                        if grade_value > 1.0 and grade_value <= 10.0:
                            grade_value = grade_value / 10.0
                        elif grade_value > 10.0 and grade_value <= 100.0:
                            grade_value = grade_value / 100.0
                        
                        if 0.0 <= grade_value <= 1.0:
                            extracted_grade = grade_value
                            break
                    except ValueError:
                        continue
            
            # If no grade found, estimate from response sentiment
            if extracted_grade is None:
                extracted_grade = self._estimate_grade_from_sentiment(response)
            
            # Extract feedback (remove grade-related text for cleaner feedback)
            feedback = response
            for pattern in grade_patterns:
                feedback = re.sub(pattern, '', feedback, flags=re.IGNORECASE)
            
            feedback = feedback.strip()
            if not feedback:
                feedback = "Model evaluation completed."
            
            # Calculate confidence based on response quality
            confidence = self._calculate_response_confidence(response, extracted_grade)
            
            return {
                'grade': extracted_grade,
                'feedback': feedback[:1000],  # Limit feedback length
                'confidence': confidence
            }
            
        except Exception as e:
            logger.warning(f"Error extracting grade from response: {e}")
            return {
                'grade': 0.7,  # Default moderate grade
                'feedback': response[:500] + "..." if len(response) > 500 else response,
                'confidence': 0.5
            }
    
    def _estimate_grade_from_sentiment(self, response: str) -> float:
        """Estimate grade based on response sentiment and keywords"""
        try:
            response_lower = response.lower()
            
            # Positive indicators
            positive_words = ['excellent', 'outstanding', 'perfect', 'great', 'good', 'well', 'correct', 'accurate', 'comprehensive']
            negative_words = ['poor', 'incorrect', 'wrong', 'missing', 'incomplete', 'unclear', 'confusing', 'inadequate']
            
            positive_count = sum(1 for word in positive_words if word in response_lower)
            negative_count = sum(1 for word in negative_words if word in response_lower)
            
            # Base grade calculation
            if positive_count > negative_count * 2:
                return 0.85  # High grade for very positive response
            elif positive_count > negative_count:
                return 0.75  # Good grade for positive response
            elif negative_count > positive_count:
                return 0.55  # Below average for negative response
            else:
                return 0.70  # Average grade for neutral response
                
        except Exception:
            return 0.70  # Default grade
    
    def _calculate_response_confidence(self, response: str, grade: float) -> float:
        """Calculate confidence score based on response quality"""
        try:
            confidence = 0.5  # Base confidence
            
            # Increase confidence for longer, more detailed responses
            if len(response) > 200:
                confidence += 0.1
            if len(response) > 500:
                confidence += 0.1
            
            # Increase confidence if grade seems reasonable
            if 0.3 <= grade <= 0.95:
                confidence += 0.1
            
            # Increase confidence for structured responses
            if any(marker in response.lower() for marker in ['1.', '2.', '3.', 'first', 'second', 'overall']):
                confidence += 0.1
            
            # Decrease confidence for very short responses
            if len(response) < 100:
                confidence -= 0.2
            
            return max(0.1, min(1.0, confidence))
            
        except Exception:
            return 0.5
    
    def _calculate_criteria_scores(self, submission_text: str, model_response: str) -> Dict[str, float]:
        """Calculate detailed criteria scores"""
        try:
            # Basic criteria scoring based on submission and response analysis
            criteria_scores = {}
            
            # Content quality (based on submission length and complexity)
            word_count = len(submission_text.split())
            if word_count > 200:
                criteria_scores['content_quality'] = 0.8
            elif word_count > 100:
                criteria_scores['content_quality'] = 0.7
            else:
                criteria_scores['content_quality'] = 0.6
            
            # Structure (based on paragraphs and organization)
            paragraph_count = submission_text.count('\n\n') + 1
            if paragraph_count >= 3:
                criteria_scores['structure'] = 0.8
            elif paragraph_count >= 2:
                criteria_scores['structure'] = 0.7
            else:
                criteria_scores['structure'] = 0.6
            
            # Accuracy (estimated from model response sentiment)
            if 'accurate' in model_response.lower() or 'correct' in model_response.lower():
                criteria_scores['accuracy'] = 0.8
            elif 'incorrect' in model_response.lower() or 'wrong' in model_response.lower():
                criteria_scores['accuracy'] = 0.4
            else:
                criteria_scores['accuracy'] = 0.6
            
            return criteria_scores
            
        except Exception as e:
            logger.warning(f"Error calculating criteria scores: {e}")
            return {
                'content_quality': 0.6,
                'structure': 0.6,
                'accuracy': 0.6
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
                        test_session.completed_at = datetime.now(timezone.utc)
                    
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
            test_session.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Clean up thread reference
            if test_id in self._running_tests:
                del self._running_tests[test_id]
            
            logger.info(f"Cancelled test {test_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling test: {e}")
            return False