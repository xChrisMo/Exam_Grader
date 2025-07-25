"""
LLM Training Service - Handles model training and fine-tuning operations.

This service manages the complete training pipeline from dataset preparation
to model fine-tuning and evaluation.
"""

import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

from src.config.unified_config import config
from src.services.base_service import BaseService, ServiceStatus
from src.services.model_manager_service import model_manager_service, TrainingConfig
from src.services.consolidated_llm_service import ConsolidatedLLMService
from utils.logger import logger


class TrainingStatus(Enum):
    """Training job status"""
    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrainingJob:
    """Training job data structure"""
    id: str
    name: str
    model_id: str
    dataset_id: str
    config: TrainingConfig
    status: TrainingStatus = TrainingStatus.PENDING
    progress: float = 0.0
    current_epoch: int = 0
    total_epochs: int = 0
    loss: Optional[float] = None
    accuracy: Optional[float] = None
    validation_loss: Optional[float] = None
    validation_accuracy: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    logs: List[str] = None
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.logs is None:
            self.logs = []
        if self.metrics is None:
            self.metrics = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        result['config'] = self.config.to_dict()
        if self.start_time:
            result['start_time'] = self.start_time.isoformat()
        if self.end_time:
            result['end_time'] = self.end_time.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainingJob':
        """Create from dictionary"""
        if 'status' in data:
            data['status'] = TrainingStatus(data['status'])
        if 'config' in data:
            data['config'] = TrainingConfig.from_dict(data['config'])
        if 'start_time' in data and isinstance(data['start_time'], str):
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if 'end_time' in data and isinstance(data['end_time'], str):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        return cls(**data)


class TrainingService(BaseService):
    """Service for managing LLM training operations"""

    def __init__(self):
        super().__init__("training_service")
        self.jobs: Dict[str, TrainingJob] = {}
        self.executor = ThreadPoolExecutor(max_workers=2)  # Limit concurrent training jobs
        self.llm_service = None
        self._job_lock = threading.Lock()
        self._db_update_callback = None
        
    async def initialize(self) -> bool:
        """Initialize the training service"""
        try:
            # Initialize LLM service for training operations
            self.llm_service = ConsolidatedLLMService()
            if hasattr(self.llm_service, 'initialize'):
                try:
                    await self.llm_service.initialize()
                except Exception as llm_error:
                    logger.warning(f"LLM service initialization failed: {str(llm_error)}")
                    # Continue without LLM service - training can work in simulation mode
                    self.llm_service = None
            
            self.status = ServiceStatus.HEALTHY
            logger.info("Training service initialized successfully")
            return True
            
        except Exception as e:
            self.status = ServiceStatus.UNHEALTHY
            logger.error(f"Failed to initialize training service: {str(e)}")
            return False

    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            # Training service can work without LLM service (in simulation mode)
            executor_healthy = self.executor is not None
            llm_healthy = self.llm_service is None or self.llm_service.is_available()
            return executor_healthy and llm_healthy
        except Exception as e:
            logger.error(f"Training service health check failed: {str(e)}")
            return False

    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            if self.executor:
                self.executor.shutdown(wait=True)
            
            if self.llm_service and hasattr(self.llm_service, 'cleanup'):
                await self.llm_service.cleanup()
                
            logger.info("Training service cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during training service cleanup: {str(e)}")

    def create_training_job(
        self,
        name: str,
        model_id: str,
        dataset_id: str,
        config: TrainingConfig,
        job_id: str = None
    ) -> str:
        """Create a new training job"""
        try:
            with self.track_request("create_training_job"):
                # Validate model
                model = model_manager_service.get_model_by_id(model_id)
                if not model:
                    raise ValueError(f"Model {model_id} not found")
                
                if not model_manager_service.check_model_availability(model_id):
                    raise ValueError(f"Model {model_id} is not available for training")
                
                # Validate configuration
                validation_result = model_manager_service.validate_configuration(model_id, config)
                if not validation_result.is_valid:
                    raise ValueError(f"Invalid configuration: {validation_result.get_error_summary()}")
                
                # Create job
                if job_id is None:
                    job_id = str(uuid.uuid4())
                job = TrainingJob(
                    id=job_id,
                    name=name,
                    model_id=model_id,
                    dataset_id=dataset_id,
                    config=config,
                    total_epochs=config.epochs
                )
                
                with self._job_lock:
                    self.jobs[job_id] = job
                
                logger.info(f"Created training job: {job_id} ({name})")
                return job_id
                
        except Exception as e:
            logger.error(f"Error creating training job: {str(e)}")
            raise

    def start_training_job(self, job_id: str) -> bool:
        """Start a training job"""
        try:
            with self.track_request("start_training_job"):
                job = self.get_training_job(job_id)
                if not job:
                    raise ValueError(f"Training job {job_id} not found")
                
                if job.status not in [TrainingStatus.PENDING, TrainingStatus.PREPARING]:
                    raise ValueError(f"Job {job_id} cannot be started from {job.status.value} status")
                
                # Submit job to executor
                future = self.executor.submit(self._run_training_job, job_id)
                
                logger.info(f"Started training job: {job_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error starting training job {job_id}: {str(e)}")
            return False

    def _run_training_job(self, job_id: str) -> None:
        """Run training job in background thread"""
        try:
            job = self.get_training_job(job_id)
            if not job:
                return
            
            # Update job status
            self._update_job_status(job_id, TrainingStatus.PREPARING)
            self._add_job_log(job_id, "Starting training job preparation...")
            
            # Prepare dataset
            self._prepare_training_data(job_id)
            
            # Start training
            self._update_job_status(job_id, TrainingStatus.TRAINING)
            self._add_job_log(job_id, "Starting model training...")
            
            # Simulate training process (replace with actual training logic)
            self._simulate_training(job_id)
            
            # Evaluate model
            self._update_job_status(job_id, TrainingStatus.EVALUATING)
            self._add_job_log(job_id, "Evaluating trained model...")
            
            self._evaluate_model(job_id)
            
            # Complete job
            self._update_job_status(job_id, TrainingStatus.COMPLETED)
            self._add_job_log(job_id, "Training completed successfully!")
            
            with self._job_lock:
                job = self.jobs[job_id]
                job.end_time = datetime.now()
                job.progress = 100.0
            
        except Exception as e:
            logger.error(f"Training job {job_id} failed: {str(e)}")
            self._update_job_status(job_id, TrainingStatus.FAILED, str(e))
            self._add_job_log(job_id, f"Training failed: {str(e)}")

    def _prepare_training_data(self, job_id: str) -> None:
        """Prepare training data from dataset"""
        job = self.get_training_job(job_id)
        if not job:
            return
        
        self._add_job_log(job_id, "Loading dataset...")
        
        # TODO: Load actual dataset from dataset_id
        # For now, simulate data preparation
        time.sleep(2)
        
        self._add_job_log(job_id, "Preprocessing training data...")
        time.sleep(1)
        
        self._add_job_log(job_id, "Data preparation completed")

    def _simulate_training(self, job_id: str) -> None:
        """Simulate training process (replace with actual training)"""
        job = self.get_training_job(job_id)
        if not job:
            return
        
        total_epochs = job.config.epochs
        
        for epoch in range(1, total_epochs + 1):
            # Check if job was cancelled
            current_job = self.get_training_job(job_id)
            if not current_job or current_job.status == TrainingStatus.CANCELLED:
                return
            
            # Simulate epoch training
            self._add_job_log(job_id, f"Training epoch {epoch}/{total_epochs}")
            
            # Simulate training time
            time.sleep(3)
            
            # Simulate metrics (replace with actual training metrics)
            import random
            loss = max(0.1, 2.0 - (epoch * 0.3) + random.uniform(-0.1, 0.1))
            accuracy = min(0.95, 0.3 + (epoch * 0.15) + random.uniform(-0.05, 0.05))
            val_loss = loss + random.uniform(0, 0.2)
            val_accuracy = accuracy - random.uniform(0, 0.1)
            
            # Update job progress
            with self._job_lock:
                job = self.jobs[job_id]
                job.current_epoch = epoch
                job.progress = (epoch / total_epochs) * 80  # 80% for training, 20% for evaluation
                job.loss = loss
                job.accuracy = accuracy
                job.validation_loss = val_loss
                job.validation_accuracy = val_accuracy
                
                # Update metrics
                job.metrics[f'epoch_{epoch}'] = {
                    'loss': loss,
                    'accuracy': accuracy,
                    'val_loss': val_loss,
                    'val_accuracy': val_accuracy
                }
                
                # Update database with progress
                if hasattr(self, '_db_update_callback') and self._db_update_callback:
                    try:
                        self._db_update_callback(job_id, job.status.value, None, {
                            'progress': job.progress,
                            'current_epoch': job.current_epoch,
                            'accuracy': job.accuracy,
                            'loss': job.loss
                        })
                    except Exception as e:
                        logger.warning(f"Failed to update database progress for job {job_id}: {str(e)}")
            
            self._add_job_log(
                job_id, 
                f"Epoch {epoch} - Loss: {loss:.4f}, Acc: {accuracy:.4f}, "
                f"Val Loss: {val_loss:.4f}, Val Acc: {val_accuracy:.4f}"
            )

    def _evaluate_model(self, job_id: str) -> None:
        """Evaluate trained model"""
        job = self.get_training_job(job_id)
        if not job:
            return
        
        self._add_job_log(job_id, "Running model evaluation...")
        
        # Simulate evaluation
        time.sleep(2)
        
        # Generate final evaluation metrics
        import random
        final_accuracy = random.uniform(0.85, 0.95)
        final_loss = random.uniform(0.1, 0.3)
        
        with self._job_lock:
            job = self.jobs[job_id]
            job.progress = 100.0
            job.metrics['final_evaluation'] = {
                'test_accuracy': final_accuracy,
                'test_loss': final_loss,
                'precision': random.uniform(0.8, 0.9),
                'recall': random.uniform(0.8, 0.9),
                'f1_score': random.uniform(0.8, 0.9)
            }
        
        self._add_job_log(
            job_id,
            f"Final evaluation - Accuracy: {final_accuracy:.4f}, Loss: {final_loss:.4f}"
        )

    def _update_job_status(self, job_id: str, status: TrainingStatus, error_message: str = None) -> None:
        """Update job status"""
        with self._job_lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = status
                if error_message:
                    job.error_message = error_message
                if status == TrainingStatus.TRAINING and not job.start_time:
                    job.start_time = datetime.now()
                
                # Update database if callback is available
                if hasattr(self, '_db_update_callback') and self._db_update_callback:
                    try:
                        self._db_update_callback(job_id, status.value, error_message, None)
                    except Exception as e:
                        logger.warning(f"Failed to update database for job {job_id}: {str(e)}")

    def _add_job_log(self, job_id: str, message: str) -> None:
        """Add log entry to job"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        with self._job_lock:
            if job_id in self.jobs:
                self.jobs[job_id].logs.append(log_entry)
        
        logger.info(f"Job {job_id}: {message}")

    def get_training_job(self, job_id: str) -> Optional[TrainingJob]:
        """Get training job by ID"""
        with self._job_lock:
            return self.jobs.get(job_id)

    def get_all_training_jobs(self) -> List[TrainingJob]:
        """Get all training jobs"""
        with self._job_lock:
            return list(self.jobs.values())

    def cancel_training_job(self, job_id: str) -> bool:
        """Cancel a training job"""
        try:
            with self.track_request("cancel_training_job"):
                job = self.get_training_job(job_id)
                if not job:
                    return False
                
                if job.status in [TrainingStatus.COMPLETED, TrainingStatus.FAILED, TrainingStatus.CANCELLED]:
                    return False
                
                self._update_job_status(job_id, TrainingStatus.CANCELLED)
                self._add_job_log(job_id, "Training job cancelled by user")
                
                logger.info(f"Cancelled training job: {job_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error cancelling training job {job_id}: {str(e)}")
            return False

    def delete_training_job(self, job_id: str) -> bool:
        """Delete a training job"""
        try:
            with self.track_request("delete_training_job"):
                job = self.get_training_job(job_id)
                if not job:
                    return False
                
                # Can only delete completed, failed, or cancelled jobs
                if job.status in [TrainingStatus.PREPARING, TrainingStatus.TRAINING, TrainingStatus.EVALUATING]:
                    return False
                
                with self._job_lock:
                    del self.jobs[job_id]
                
                logger.info(f"Deleted training job: {job_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting training job {job_id}: {str(e)}")
            return False

    def get_training_stats(self) -> Dict[str, Any]:
        """Get training statistics"""
        with self._job_lock:
            jobs = list(self.jobs.values())
        
        stats = {
            'total_jobs': len(jobs),
            'pending_jobs': len([j for j in jobs if j.status == TrainingStatus.PENDING]),
            'running_jobs': len([j for j in jobs if j.status in [
                TrainingStatus.PREPARING, TrainingStatus.TRAINING, TrainingStatus.EVALUATING
            ]]),
            'completed_jobs': len([j for j in jobs if j.status == TrainingStatus.COMPLETED]),
            'failed_jobs': len([j for j in jobs if j.status == TrainingStatus.FAILED]),
            'cancelled_jobs': len([j for j in jobs if j.status == TrainingStatus.CANCELLED])
        }
        
        return stats

    def set_database_update_callback(self, callback):
        """Set callback function to update database when job status changes"""
        self._db_update_callback = callback


# Global instance
training_service = TrainingService()


class ValidationResult:
    """Validation result helper class"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
    
    def add_error(self, field: str, message: str, code: str, value: Any = None):
        self.errors.append({
            'field': field,
            'message': message,
            'code': code,
            'value': value
        })
    
    def add_warning(self, field: str, message: str, suggestion: str = None):
        self.warnings.append({
            'field': field,
            'message': message,
            'suggestion': suggestion
        })
    
    def get_error_summary(self) -> str:
        if not self.errors:
            return ""
        return "; ".join([error['message'] for error in self.errors])