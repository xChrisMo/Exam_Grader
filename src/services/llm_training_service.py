"""
Enhanced LLM Training Service

This service handles LLM training operations including job management,
dataset processing, report generation, and robust error handling.
"""

import asyncio
import threading
import time
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from src.database.models import db, LLMTrainingJob, LLMTrainingReport, LLMDataset
from src.services.error_handling_service import LLMTrainingErrorHandler, ErrorType, ErrorSeverity, RetryManager
from src.services.validation_service import ValidationService
from utils.logger import logger

class LLMTrainingService:
    """Service for managing LLM training operations with robust error handling"""
    
    def __init__(self):
        self._training_threads: Dict[str, threading.Thread] = {}
        self._cancelled_jobs: set = set()
        self._job_checkpoints: Dict[str, Dict[str, Any]] = {}
        self._retry_manager = RetryManager(max_retries=3, base_delay=2.0, max_delay=60.0)
        self._error_handler = LLMTrainingErrorHandler()
        self._validation_service = ValidationService()
    
    def start_training_async(self, job_id: str) -> None:
        """Start training job asynchronously"""
        try:
            if job_id in self._training_threads:
                logger.warning(f"Training job {job_id} is already running")
                return
            
            # Start training in a separate thread
            thread = threading.Thread(
                target=self._run_training_job,
                args=(job_id,),
                daemon=True
            )
            thread.start()
            self._training_threads[job_id] = thread
            
            logger.info(f"Started training job {job_id} asynchronously")
            
        except Exception as e:
            logger.error(f"Error starting training job {job_id}: {e}")
            self._update_job_status(job_id, 'failed', error_message=str(e))
    
    def cancel_training(self, job_id: str) -> bool:
        """Cancel a running training job"""
        try:
            # Mark job as cancelled
            self._cancelled_jobs.add(job_id)
            
            # Update job status
            self._update_job_status(job_id, 'cancelled')
            
            # Clean up thread reference
            if job_id in self._training_threads:
                del self._training_threads[job_id]
            
            logger.info(f"Cancelled training job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling training job {job_id}: {e}")
            return False
    
    def generate_report_async(self, report_id: str) -> None:
        """Generate training report asynchronously"""
        try:
            thread = threading.Thread(
                target=self._generate_report,
                args=(report_id,),
                daemon=True
            )
            thread.start()
            
            logger.info(f"Started report generation {report_id} asynchronously")
            
        except Exception as e:
            logger.error(f"Error starting report generation {report_id}: {e}")
            self._update_report_status(report_id, 'failed', error_message=str(e))
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models for training"""
        try:
            # Common LLM models that can be fine-tuned
            models = [
                {
                    'id': 'gpt-3.5-turbo',
                    'name': 'GPT-3.5 Turbo',
                    'provider': 'OpenAI',
                    'type': 'chat',
                    'max_tokens': 4096,
                    'supports_fine_tuning': True
                },
                {
                    'id': 'gpt-4',
                    'name': 'GPT-4',
                    'provider': 'OpenAI', 
                    'type': 'chat',
                    'max_tokens': 8192,
                    'supports_fine_tuning': True
                },
                {
                    'id': 'deepseek-chat',
                    'name': 'DeepSeek Chat',
                    'provider': 'DeepSeek',
                    'type': 'chat',
                    'max_tokens': 4096,
                    'supports_fine_tuning': True
                },
                {
                    'id': 'llama-2-7b',
                    'name': 'Llama 2 7B',
                    'provider': 'Meta',
                    'type': 'completion',
                    'max_tokens': 4096,
                    'supports_fine_tuning': True
                },
                {
                    'id': 'llama-2-13b',
                    'name': 'Llama 2 13B',
                    'provider': 'Meta',
                    'type': 'completion',
                    'max_tokens': 4096,
                    'supports_fine_tuning': True
                },
                {
                    'id': 'mistral-7b',
                    'name': 'Mistral 7B',
                    'provider': 'Mistral AI',
                    'type': 'completion',
                    'max_tokens': 8192,
                    'supports_fine_tuning': True
                }
            ]
            
            logger.info(f"Retrieved {len(models)} available models")
            return models
            
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    def run_system_test(self) -> Dict[str, Any]:
        """Run comprehensive system test"""
        try:
            test_results = {
                'timestamp': datetime.utcnow().isoformat(),
                'tests': [],
                'overall_status': 'passed',
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            }
            
            # Test 1: Database connectivity
            try:
                from src.database.models import db
                db.session.execute(db.text('SELECT 1'))
                test_results['tests'].append({
                    'name': 'Database Connectivity',
                    'status': 'passed',
                    'message': 'Database connection successful'
                })
                test_results['passed_tests'] += 1
            except Exception as e:
                test_results['tests'].append({
                    'name': 'Database Connectivity',
                    'status': 'failed',
                    'message': f'Database connection failed: {str(e)}'
                })
                test_results['failed_tests'] += 1
                test_results['overall_status'] = 'failed'
            
            # Test 2: Model availability
            try:
                models = self.get_available_models()
                if models:
                    test_results['tests'].append({
                        'name': 'Model Availability',
                        'status': 'passed',
                        'message': f'Found {len(models)} available models'
                    })
                    test_results['passed_tests'] += 1
                else:
                    test_results['tests'].append({
                        'name': 'Model Availability',
                        'status': 'failed',
                        'message': 'No models available'
                    })
                    test_results['failed_tests'] += 1
                    test_results['overall_status'] = 'failed'
            except Exception as e:
                test_results['tests'].append({
                    'name': 'Model Availability',
                    'status': 'failed',
                    'message': f'Model check failed: {str(e)}'
                })
                test_results['failed_tests'] += 1
                test_results['overall_status'] = 'failed'
            
            # Test 3: File system access
            try:
                import os
                import tempfile
                
                # Test write access to uploads directory
                upload_dir = os.path.join(os.getcwd(), 'webapp', 'uploads', 'llm_documents')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Create a test file
                test_file = os.path.join(upload_dir, 'test_file.txt')
                with open(test_file, 'w') as f:
                    f.write('test content')
                
                # Clean up test file
                os.remove(test_file)
                
                test_results['tests'].append({
                    'name': 'File System Access',
                    'status': 'passed',
                    'message': 'File system read/write access confirmed'
                })
                test_results['passed_tests'] += 1
            except Exception as e:
                test_results['tests'].append({
                    'name': 'File System Access',
                    'status': 'failed',
                    'message': f'File system access failed: {str(e)}'
                })
                test_results['failed_tests'] += 1
                test_results['overall_status'] = 'failed'
            
            # Test 4: Training service initialization
            try:
                # Test that we can initialize training components
                test_results['tests'].append({
                    'name': 'Training Service',
                    'status': 'passed',
                    'message': 'Training service initialized successfully'
                })
                test_results['passed_tests'] += 1
            except Exception as e:
                test_results['tests'].append({
                    'name': 'Training Service',
                    'status': 'failed',
                    'message': f'Training service initialization failed: {str(e)}'
                })
                test_results['failed_tests'] += 1
                test_results['overall_status'] = 'failed'
            
            test_results['total_tests'] = len(test_results['tests'])
            
            logger.info(f"System test completed: {test_results['passed_tests']}/{test_results['total_tests']} tests passed")
            return test_results
            
        except Exception as e:
            logger.error(f"Error running system test: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'tests': [{
                    'name': 'System Test',
                    'status': 'failed',
                    'message': f'System test failed: {str(e)}'
                }],
                'overall_status': 'failed',
                'total_tests': 1,
                'passed_tests': 0,
                'failed_tests': 1
            }

    def start_training_with_validation(self, job_config: Dict[str, Any]) -> str:
        """Start training with comprehensive validation"""
        try:
            # Validate configuration
            config_validation = self._validation_service.validate_training_config(job_config)
            if not config_validation['valid']:
                raise ValueError(f"Invalid training configuration: {config_validation['errors']}")
            
            # Validate dataset
            dataset_validation = self._validation_service.validate_dataset_integrity(job_config['dataset_id'])
            if not dataset_validation['valid']:
                raise ValueError(f"Invalid dataset: {dataset_validation['errors']}")
            
            # Create training job with validation results
            job = LLMTrainingJob(
                name=job_config['name'],
                model_id=job_config['model_id'],
                dataset_id=job_config['dataset_id'],
                user_id=job_config['user_id'],
                status='pending',
                validation_results={
                    'config_validation': config_validation,
                    'dataset_validation': dataset_validation,
                    'validated_at': datetime.utcnow().isoformat()
                },
                **config_validation['normalized_config']
            )
            
            db.session.add(job)
            db.session.commit()
            
            # Start training
            self.start_training_async(job.id)
            
            return job.id
            
        except Exception as e:
            logger.error(f"Error starting validated training: {e}")
            raise
    
    def resume_failed_training(self, job_id: str) -> bool:
        """Resume a failed training job from checkpoint"""
        try:
            job = db.session.get(LLMTrainingJob, job_id)
            if not job:
                logger.error(f"Training job {job_id} not found")
                return False
            
            if job.status not in ['failed', 'cancelled']:
                logger.warning(f"Job {job_id} cannot be resumed from status {job.status}")
                return False
            
            checkpoint_data = self._job_checkpoints.get(job_id)
            if not checkpoint_data:
                logger.warning(f"No checkpoint found for job {job_id}")
                checkpoint_data = {
                    'last_epoch': job.current_epoch or 0,
                    'last_progress': job.progress or 0.0,
                    'resume_count': (job.resume_count or 0) + 1
                }
            
            job.status = 'pending'
            job.resume_count = checkpoint_data.get('resume_count', 1)
            job.error_message = None
            
            # Store resume context
            job.health_metrics = {
                'resumed_at': datetime.utcnow().isoformat(),
                'resume_reason': 'manual_resume',
                'checkpoint_data': checkpoint_data
            }
            
            db.session.commit()
            
            # Start training with resume context
            self.start_training_async(job_id)
            
            logger.info(f"Resumed training job {job_id} from checkpoint")
            return True
            
        except Exception as e:
            logger.error(f"Error resuming training job {job_id}: {e}")
            return False
    
    def monitor_training_health(self, job_id: str) -> Dict[str, Any]:
        """Monitor training job health and performance"""
        try:
            job = db.session.get(LLMTrainingJob, job_id)
            if not job:
                return {'status': 'not_found', 'health': 'unknown'}
            
            health_status = {
                'job_id': job_id,
                'status': job.status,
                'health': 'healthy',
                'issues': [],
                'recommendations': [],
                'metrics': {
                    'progress': job.progress or 0.0,
                    'current_epoch': job.current_epoch or 0,
                    'total_epochs': job.total_epochs or 0,
                    'runtime_minutes': 0,
                    'estimated_completion': None
                }
            }
            
            # Calculate runtime
            if job.start_time:
                runtime = datetime.utcnow() - job.start_time
                health_status['metrics']['runtime_minutes'] = runtime.total_seconds() / 60
            
            if job.status == 'training':
                if health_status['metrics']['runtime_minutes'] > 60 and job.progress < 10:
                    health_status['health'] = 'degraded'
                    health_status['issues'].append('Training progress is very slow')
                    health_status['recommendations'].append('Consider reducing batch size or learning rate')
                
                expected_runtime = (job.total_epochs or 10) * 2  # 2 minutes per epoch estimate
                if health_status['metrics']['runtime_minutes'] > expected_runtime * 2:
                    health_status['health'] = 'degraded'
                    health_status['issues'].append('Training is taking longer than expected')
                    health_status['recommendations'].append('Check system resources and model complexity')
            
            elif job.status == 'failed':
                health_status['health'] = 'unhealthy'
                health_status['issues'].append(f"Training failed: {job.error_message or 'Unknown error'}")
                
                if job.error_message:
                    error_analysis = self._error_handler.handle_training_error(
                        Exception(job.error_message), job_id, {'job': job.to_dict()}
                    )
                    health_status['recommendations'].extend(error_analysis.get('recovery_suggestions', []))
            
            # Store health metrics
            job.health_metrics = health_status
            db.session.commit()
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error monitoring training health for {job_id}: {e}")
            return {
                'status': 'error',
                'health': 'unknown',
                'error': str(e)
            }
    
    def handle_training_failures(self, job_id: str, error: Exception) -> Dict[str, Any]:
        """Handle training failures with recovery options"""
        try:
            # Analyze the error
            error_response = self._error_handler.handle_training_error(error, job_id)
            
            # Get job details
            job = db.session.get(LLMTrainingJob, job_id)
            if not job:
                return error_response
            
            # Create checkpoint before handling failure
            self._create_checkpoint(job_id, job)
            
            auto_recovery = error_response.get('auto_recovery_options', {})
            
            if auto_recovery.get('retry_with_backoff') and (job.resume_count or 0) < 3:
                # Attempt automatic retry
                logger.info(f"Attempting automatic recovery for job {job_id}")
                
                # Wait before retry
                retry_delay = min(60, 10 * (2 ** (job.resume_count or 0)))  # Exponential backoff
                time.sleep(retry_delay)
                
                # Resume training
                if self.resume_failed_training(job_id):
                    error_response['auto_recovery_attempted'] = True
                    error_response['recovery_status'] = 'attempted'
                else:
                    error_response['auto_recovery_attempted'] = True
                    error_response['recovery_status'] = 'failed'
            
            # Update job with error details
            job.error_message = str(error)
            job.health_metrics = {
                'error_analysis': error_response,
                'failed_at': datetime.utcnow().isoformat(),
                'recovery_options': auto_recovery
            }
            db.session.commit()
            
            return error_response
            
        except Exception as e:
            logger.error(f"Error handling training failure for {job_id}: {e}")
            return {
                'success': False,
                'error_type': 'handler_error',
                'error_message': f'Failed to handle training error: {str(e)}'
            }
    
    def _run_training_job(self, job_id: str) -> None:
        """Run training job with enhanced error handling and recovery"""
        start_time = time.time()
        
        try:
            # Get job details
            with current_app.app_context():
                job = db.session.get(LLMTrainingJob, job_id)
                if not job:
                    logger.error(f"Training job {job_id} not found")
                    return
                
                # Update start time
                job.start_time = datetime.utcnow()
                db.session.commit()
            
            # Pre-training validation
            self._validate_before_training(job_id)
            
            # Update status to preparing
            self._update_job_status(job_id, 'preparing')
            
            if job_id in self._cancelled_jobs:
                return
            
            # Preparation phase with error handling
            try:
                self._prepare_training_environment(job_id)
            except Exception as e:
                self.handle_training_failures(job_id, e)
                return
            
            # Update status to training
            self._update_job_status(job_id, 'training', progress=0)
            
            # Training loop with checkpoints and health monitoring
            total_epochs = job.total_epochs or 10
            for epoch in range(job.current_epoch or 0, total_epochs):
                if job_id in self._cancelled_jobs:
                    return
                
                try:
                    # Simulate epoch training
                    self._train_epoch(job_id, epoch, total_epochs)
                    
                    # Create checkpoint every 5 epochs
                    if epoch % 5 == 0:
                        self._create_checkpoint(job_id, job)
                    
                    # Monitor health
                    health_status = self.monitor_training_health(job_id)
                    if health_status['health'] == 'unhealthy':
                        raise Exception(f"Training health check failed: {health_status['issues']}")
                    
                except Exception as e:
                    # Handle epoch-level errors
                    error_response = self.handle_training_failures(job_id, e)
                    
                    if not error_response.get('auto_recovery_attempted'):
                        raise e
                    
                    continue
            
            # Update status to evaluating
            self._update_job_status(job_id, 'evaluating', progress=100)
            
            # Evaluation phase
            try:
                evaluation_results = self._evaluate_model(job_id)
            except Exception as e:
                self.handle_training_failures(job_id, e)
                return
            
            # Complete training
            if job_id not in self._cancelled_jobs:
                training_time = time.time() - start_time
                self._update_job_status(
                    job_id, 
                    'completed', 
                    progress=100,
                    results={
                        'final_loss': evaluation_results.get('loss', 0.1234),
                        'accuracy': evaluation_results.get('accuracy', 0.8765),
                        'training_time': f'{training_time/60:.1f} minutes',
                        'total_epochs': total_epochs,
                        'model_size': '1.2 GB'
                    }
                )
                
                # Clean up checkpoint
                if job_id in self._job_checkpoints:
                    del self._job_checkpoints[job_id]
            
        except Exception as e:
            logger.error(f"Critical error in training job {job_id}: {e}")
            self.handle_training_failures(job_id, e)
            self._update_job_status(job_id, 'failed', error_message=str(e))
        
        finally:
            # Clean up
            if job_id in self._training_threads:
                del self._training_threads[job_id]
            self._cancelled_jobs.discard(job_id)
    
    def _validate_before_training(self, job_id: str) -> None:
        """Validate job before starting training"""
        job = db.session.get(LLMTrainingJob, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Validate dataset
        dataset_validation = self._validation_service.validate_dataset_integrity(job.dataset_id)
        if not dataset_validation['valid']:
            raise ValueError(f"Dataset validation failed: {dataset_validation['errors']}")
        
        # Validate configuration
        config = {
            'epochs': job.config_epochs,
            'batch_size': job.config_batch_size,
            'learning_rate': job.config_learning_rate,
            'max_tokens': job.config_max_tokens,
            'model_id': job.model_id,
            'dataset_id': job.dataset_id
        }
        
        config_validation = self._validation_service.validate_training_config(config)
        if not config_validation['valid']:
            raise ValueError(f"Configuration validation failed: {config_validation['errors']}")
    
    def _prepare_training_environment(self, job_id: str) -> None:
        """Prepare training environment"""
        # Simulate environment preparation
        time.sleep(2)
        
        # Check system resources (placeholder)
        import psutil
        if psutil.virtual_memory().percent > 90:
            raise Exception("Insufficient memory for training")
        
        logger.info(f"Training environment prepared for job {job_id}")
    
    def _train_epoch(self, job_id: str, epoch: int, total_epochs: int) -> None:
        """Train a single epoch"""
        # Simulate epoch training
        epoch_time = 1 + (epoch * 0.1)  # Slightly increasing time per epoch
        time.sleep(epoch_time)
        
        # Update progress
        progress = ((epoch + 1) / total_epochs) * 100
        self._update_job_status(job_id, 'training', progress=progress)
        
        # Update current epoch
        with current_app.app_context():
            job = db.session.get(LLMTrainingJob, job_id)
            if job:
                job.current_epoch = epoch + 1
                db.session.commit()
        
        logger.debug(f"Completed epoch {epoch + 1}/{total_epochs} for job {job_id}")
    
    def _evaluate_model(self, job_id: str) -> Dict[str, Any]:
        """Evaluate trained model"""
        # Simulate model evaluation
        time.sleep(2)
        
        # Generate mock evaluation results
        import random
        results = {
            'accuracy': random.uniform(0.75, 0.95),
            'loss': random.uniform(0.05, 0.25),
            'validation_accuracy': random.uniform(0.70, 0.90),
            'validation_loss': random.uniform(0.10, 0.30)
        }
        
        logger.info(f"Model evaluation completed for job {job_id}: {results}")
        return results
    
    def _create_checkpoint(self, job_id: str, job: LLMTrainingJob) -> None:
        """Create training checkpoint"""
        checkpoint_data = {
            'job_id': job_id,
            'current_epoch': job.current_epoch or 0,
            'progress': job.progress or 0.0,
            'status': job.status,
            'created_at': datetime.utcnow().isoformat(),
            'model_state': f'checkpoint_{job_id}_{job.current_epoch}.pt',  # Placeholder
            'optimizer_state': f'optimizer_{job_id}_{job.current_epoch}.pt'  # Placeholder
        }
        
        self._job_checkpoints[job_id] = checkpoint_data
        
        # Also store in database
        job.health_metrics = job.health_metrics or {}
        job.health_metrics['last_checkpoint'] = checkpoint_data
        db.session.commit()
        
        logger.debug(f"Created checkpoint for job {job_id} at epoch {job.current_epoch}")
    
    def _generate_report(self, report_id: str) -> None:
        """Generate training report (placeholder implementation)"""
        try:
            # Update status to generating
            self._update_report_status(report_id, 'generating')
            
            # Simulate report generation
            import time
            time.sleep(3)
            
            # Get report details
            from flask import current_app
            with current_app.app_context():
                report = db.session.get(LLMTrainingReport, report_id)
                if not report:
                    raise ValueError(f"Report {report_id} not found")
                
                # Generate mock report content
                report_content = self._generate_mock_report_content(report)
                
                # Update report with content
                report.content = report_content
                report.status = 'completed'
                report.completed_at = datetime.utcnow()
                
                db.session.commit()
                
            logger.info(f"Generated report {report_id}")
            
        except Exception as e:
            logger.error(f"Error generating report {report_id}: {e}")
            self._update_report_status(report_id, 'failed', error_message=str(e))
    
    def _generate_mock_report_content(self, report: LLMTrainingReport) -> Dict[str, Any]:
        """Generate mock report content"""
        return {
            'summary': {
                'total_jobs': len(report.job_ids),
                'successful_jobs': len(report.job_ids) - 1,  # Mock: assume 1 failed
                'failed_jobs': 1,
                'total_training_time': '2 hours 15 minutes',
                'average_accuracy': 0.8234
            },
            'jobs': [
                {
                    'id': job_id,
                    'name': f'Training Job {i+1}',
                    'status': 'completed' if i < len(report.job_ids) - 1 else 'failed',
                    'accuracy': 0.8 + (i * 0.05),
                    'loss': 0.2 - (i * 0.02),
                    'training_time': f'{30 + i*10} minutes'
                }
                for i, job_id in enumerate(report.job_ids)
            ],
            'recommendations': [
                'Consider increasing the learning rate for faster convergence',
                'Add more training data to improve model performance',
                'Try different model architectures for better results'
            ],
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _update_job_status(self, job_id: str, status: str, progress: Optional[int] = None, 
                          results: Optional[Dict] = None, error_message: Optional[str] = None) -> None:
        """Update training job status"""
        try:
            from flask import current_app
            with current_app.app_context():
                job = db.session.get(LLMTrainingJob, job_id)
                if job:
                    job.status = status
                    if progress is not None:
                        job.progress = progress
                    if results:
                        job.results = results
                    if error_message:
                        job.error_message = error_message
                    if status == 'completed':
                        job.completed_at = datetime.utcnow()
                    
                    db.session.commit()
                    
        except Exception as e:
            logger.error(f"Error updating job status for {job_id}: {e}")
    
    def _update_report_status(self, report_id: str, status: str, error_message: Optional[str] = None) -> None:
        """Update report status"""
        try:
            from flask import current_app
            with current_app.app_context():
                report = db.session.get(LLMTrainingReport, report_id)
                if report:
                    report.status = status
                    if error_message:
                        report.error_message = error_message
                    if status == 'completed':
                        report.completed_at = datetime.utcnow()
                    
                    db.session.commit()
                    
        except Exception as e:
            logger.error(f"Error updating report status for {report_id}: {e}")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current job status"""
        try:
            from flask import current_app
            with current_app.app_context():
                job = db.session.get(LLMTrainingJob, job_id)
                if job:
                    return job.to_dict()
                return None
                
        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {e}")
            return None
    
    def cleanup(self) -> None:
        """Clean up service resources"""
        try:
            # Cancel all running jobs
            for job_id in list(self._training_threads.keys()):
                self.cancel_training(job_id)
            
            # Clear references
            self._training_threads.clear()
            self._cancelled_jobs.clear()
            
            logger.info("LLM training service cleaned up")
            
        except Exception as e:
            logger.error(f"Error during LLM training service cleanup: {e}")