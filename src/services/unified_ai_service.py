"""Unified AI Processing Service with Progress Tracking
Combines OCR, LLM, mapping and grading into a single streamlined workflow with real-time progress updates.
Integrates with consolidated services and provides comprehensive AI processing capabilities.
"""

import json
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field

from src.config.unified_config import config
from src.services.base_service import BaseService, ServiceStatus
from utils.cache import cache_get, cache_set, cache_clear
from utils.logger import logger


@dataclass
class ProcessingProgress:
    """Enhanced data class for tracking processing progress"""
    progress_id: str
    total_submissions: int
    current_submission: int = 0
    current_stage: str = "initializing"
    progress_percentage: float = 0.0
    start_time: float = field(default_factory=time.time)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stage_details: Dict[str, Any] = field(default_factory=dict)
    estimated_completion: Optional[float] = None
    
    # Legacy compatibility fields
    current_step: int = 0
    total_steps: int = 0
    current_operation: str = ""
    submission_index: int = 0
    percentage: float = 0.0
    estimated_time_remaining: Optional[float] = None
    status: str = "processing"
    details: Optional[str] = None
    
    def update_stage(self, stage: str, percentage: float, message: str = ""):
        """Update processing stage and percentage."""
        self.current_stage = stage
        self.progress_percentage = percentage
        self.percentage = percentage  # Legacy compatibility
        self.current_operation = message or stage  # Legacy compatibility
        if message:
            self.stage_details[stage] = message
        
        # Estimate completion time
        if percentage > 0:
            elapsed = time.time() - self.start_time
            total_estimated = elapsed / (percentage / 100)
            self.estimated_completion = self.start_time + total_estimated
            self.estimated_time_remaining = max(0.0, total_estimated - elapsed)
    
    def update_submission(self, submission_index: int, message: str = ""):
        """Update current submission being processed."""
        self.current_submission = submission_index
        self.submission_index = submission_index  # Legacy compatibility
        if message:
            self.stage_details[f"submission_{submission_index}"] = message
    
    def add_error(self, error: str):
        """Add an error to the progress tracking."""
        self.errors.append(error)
        logger.error(f"Processing error: {error}")
    
    def add_warning(self, warning: str):
        """Add a warning to the progress tracking."""
        self.warnings.append(warning)
        logger.warning(f"Processing warning: {warning}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert progress to dictionary for serialization."""
        return {
            'progress_id': self.progress_id,
            'total_submissions': self.total_submissions,
            'current_submission': self.current_submission,
            'current_stage': self.current_stage,
            'progress_percentage': self.progress_percentage,
            'start_time': self.start_time,
            'elapsed_time': time.time() - self.start_time,
            'estimated_completion': self.estimated_completion,
            'errors': self.errors,
            'warnings': self.warnings,
            'stage_details': self.stage_details,
            # Legacy compatibility
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'current_operation': self.current_operation,
            'submission_index': self.submission_index,
            'percentage': self.percentage,
            'estimated_time_remaining': self.estimated_time_remaining,
            'status': self.status,
            'details': self.details
        }


class UnifiedAIService(BaseService):
    """
    Unified AI Processing Service that combines OCR, LLM, mapping and grading into a single workflow
    with comprehensive progress tracking and real-time status updates.
    Integrates with consolidated services and base service architecture.
    """

    def __init__(
        self,
        ocr_service=None,
        llm_service=None,
        mapping_service=None,
        grading_service=None,
        cache_ttl: int = 3600,  # 1 hour
        batch_size: int = 10,
        max_retries: int = 3
    ):
        """
        Initialize the unified AI service.
        
        Args:
            ocr_service: OCR service instance
            llm_service: LLM service instance
            mapping_service: Mapping service instance
            grading_service: Grading service instance
            cache_ttl: Cache time-to-live in seconds
            batch_size: Batch size for processing
            max_retries: Maximum retry attempts for failed operations
        """
        super().__init__("unified_ai_service")
        
        # Initialize services with fallback imports if needed
        self.ocr_service = ocr_service
        self.llm_service = llm_service
        self.mapping_service = mapping_service
        self.grading_service = grading_service
        
        # Initialize services if not provided
        self._initialize_fallback_services()
        
        self.cache_ttl = cache_ttl
        self.batch_size = batch_size
        self.max_retries = max_retries
        
        # Progress tracking
        self.progress_callback: Optional[Callable] = None
        self._active_progress: Optional[ProcessingProgress] = None
        self.start_time: Optional[float] = None
        self.processing_times: List[float] = []
        self.total_submissions: int = 0
        
        # Optimization: Cache for guide type determination to avoid redundant LLM calls
        self._guide_type_cache: Dict[str, Tuple[str, float]] = {}
        
        # Optimization: Cache for content deduplication
        self._content_hash_cache: Dict[str, Dict] = {}
        
        # Set initial status based on available services
        self._update_service_status()
        
        logger.info("Unified AI Service initialized with consolidated services")
    
    def _initialize_fallback_services(self):
        """Initialize services with fallback imports if not provided."""
        try:
            if not self.ocr_service:
                from src.services.consolidated_ocr_service import ConsolidatedOCRService
                self.ocr_service = ConsolidatedOCRService()
                
            if not self.llm_service:
                from src.services.consolidated_llm_service import ConsolidatedLLMService
                self.llm_service = ConsolidatedLLMService()
                
            if not self.mapping_service:
                from src.services.consolidated_mapping_service import ConsolidatedMappingService
                self.mapping_service = ConsolidatedMappingService(llm_service=self.llm_service)
                
            if not self.grading_service:
                from src.services.consolidated_grading_service import ConsolidatedGradingService
                self.grading_service = ConsolidatedGradingService(
                    llm_service=self.llm_service,
                    mapping_service=self.mapping_service
                )
        except ImportError as e:
            logger.warning(f"Could not import consolidated services: {str(e)}")
    
    def _update_service_status(self):
        """Update service status based on available services."""
        available_services = sum([
            self.ocr_service is not None,
            self.llm_service is not None,
            self.mapping_service is not None,
            self.grading_service is not None
        ])
        
        if available_services >= 3:
            self.status = ServiceStatus.HEALTHY
        elif available_services >= 2:
            self.status = ServiceStatus.DEGRADED
        else:
            self.status = ServiceStatus.UNHEALTHY
    
    async def initialize(self) -> bool:
        """Initialize the unified AI service."""
        try:
            with self.track_request("initialize"):
                initialization_results = []
                
                # Initialize all available services
                for service_name, service in [
                    ("OCR", self.ocr_service),
                    ("LLM", self.llm_service),
                    ("Mapping", self.mapping_service),
                    ("Grading", self.grading_service)
                ]:
                    if service and hasattr(service, 'initialize'):
                        try:
                            result = await service.initialize()
                            initialization_results.append((service_name, result))
                            logger.info(f"{service_name} service initialized: {result}")
                        except Exception as e:
                            logger.error(f"Failed to initialize {service_name} service: {str(e)}")
                            initialization_results.append((service_name, False))
                
                # Update status based on initialization results
                successful_inits = sum(1 for _, result in initialization_results if result)
                total_services = len(initialization_results)
                
                if successful_inits == total_services:
                    self.status = ServiceStatus.HEALTHY
                    logger.info("Unified AI service fully initialized")
                elif successful_inits >= total_services // 2:
                    self.status = ServiceStatus.DEGRADED
                    logger.warning(f"Unified AI service partially initialized ({successful_inits}/{total_services})")
                else:
                    self.status = ServiceStatus.UNHEALTHY
                    logger.error(f"Unified AI service initialization failed ({successful_inits}/{total_services})")
                
                return successful_inits > 0
                
        except Exception as e:
            self.status = ServiceStatus.UNHEALTHY
            logger.error(f"Failed to initialize unified AI service: {str(e)}")
            return False
    
    async def health_check(self) -> bool:
        """Perform comprehensive health check."""
        try:
            health_results = []
            
            for service_name, service in [
                ("OCR", self.ocr_service),
                ("LLM", self.llm_service),
                ("Mapping", self.mapping_service),
                ("Grading", self.grading_service)
            ]:
                if service:
                    try:
                        if hasattr(service, 'health_check'):
                            result = await service.health_check()
                        elif hasattr(service, 'is_available'):
                            result = service.is_available()
                        else:
                            result = True  # Assume healthy if no check method
                        health_results.append(result)
                    except Exception as e:
                        logger.error(f"{service_name} health check failed: {str(e)}")
                        health_results.append(False)
            
            # Service is healthy if at least half of the services are healthy
            healthy_services = sum(health_results)
            return healthy_services >= len(health_results) // 2
            
        except Exception as e:
            logger.error(f"Unified AI service health check failed: {str(e)}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up all services and resources."""
        try:
            # Cleanup all services
            for service_name, service in [
                ("OCR", self.ocr_service),
                ("LLM", self.llm_service),
                ("Mapping", self.mapping_service),
                ("Grading", self.grading_service)
            ]:
                if service and hasattr(service, 'cleanup'):
                    try:
                        await service.cleanup()
                        logger.info(f"{service_name} service cleaned up")
                    except Exception as e:
                        logger.error(f"Error cleaning up {service_name} service: {str(e)}")
            
            # Clear caches
            self.clear_cache()
            
            logger.info("Unified AI service cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during unified AI service cleanup: {str(e)}")

    def set_progress_callback(self, callback: Callable):
        """Set callback function for progress updates"""
        self.progress_callback = callback

    def _update_progress(self, stage: str, percentage: float, message: str = ""):
        """Update progress if callback is set."""
        if self._active_progress:
            self._active_progress.update_stage(stage, percentage, message)
            
        if self.progress_callback:
            progress_data = {
                'stage': stage,
                'percentage': percentage,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            if self._active_progress:
                progress_data.update(self._active_progress.to_dict())
            
            self.progress_callback(progress_data)
        
        logger.info(f"Progress: {percentage:.1f}% - {stage}: {message}")
    
    def _update_progress_legacy(self, progress: ProcessingProgress):
        """Legacy progress update method for backward compatibility"""
        if self.progress_callback:
            self.progress_callback(progress)
        
        logger.info(f"Progress: {progress.percentage:.1f}% - {progress.current_operation}")
    
    def _generate_cache_key(self, content: str, context: str = "") -> str:
        """Generate cache key for content."""
        key_content = f"{context}:{content}"
        return hashlib.md5(key_content.encode()).hexdigest()

    def _get_cached_result(self, cache_type: str, *args) -> Optional[Any]:
        """Get cached result by type and arguments."""
        cache_key = f"{cache_type}:{self._generate_cache_key(''.join(str(arg) for arg in args))}"
        result = cache_get(cache_key)
        if result:
            self.metrics.add_custom_metric("cache_hits", 1)
        else:
            self.metrics.add_custom_metric("cache_misses", 1)
        return result

    def _cache_result(self, cache_type: str, result: Any, *args):
        """Cache result by type and arguments."""
        cache_key = f"{cache_type}:{self._generate_cache_key(''.join(str(arg) for arg in args))}"
        cache_set(cache_key, result, ttl=self.cache_ttl)
    
    def process_document_with_ocr(self, file_path: str, **kwargs) -> Tuple[str, Optional[str]]:
        """Process document with OCR."""
        try:
            with self.track_request("ocr_processing"):
                if not self.ocr_service:
                    return "", "OCR service not available"
                
                # Check cache first
                cached_result = self._get_cached_result("ocr", file_path, str(kwargs))
                if cached_result:
                    return cached_result
                
                # Process with OCR
                if hasattr(self.ocr_service, 'process_document'):
                    result = self.ocr_service.process_document(file_path, **kwargs)
                else:
                    # Fallback method
                    result = self.ocr_service.extract_text(file_path)
                    result = (result, None) if isinstance(result, str) else result
                
                # Cache result
                self._cache_result("ocr", result, file_path, str(kwargs))
                return result
                
        except Exception as e:
            error_msg = f"OCR processing failed: {str(e)}"
            logger.error(error_msg)
            return "", error_msg
    
    def determine_guide_type(self, guide_content: str) -> Tuple[str, float]:
        """Determine guide type with caching."""
        try:
            with self.track_request("guide_type_determination"):
                # Check cache first
                cached_result = self._get_cached_result("guide_type", guide_content[:1000])
                if cached_result:
                    return cached_result
                
                if not self.mapping_service:
                    result = ("questions", 0.5)  # Default fallback
                else:
                    result = self.mapping_service.determine_guide_type(guide_content)
                
                # Cache result
                self._cache_result("guide_type", result, guide_content[:1000])
                return result
                
        except Exception as e:
            logger.error(f"Guide type determination failed: {str(e)}")
            return "questions", 0.5
    
    def map_submission_to_guide(
        self, 
        guide_content: str, 
        submission_content: str, 
        guide_type: str = None
    ) -> Tuple[Dict, Optional[str]]:
        """Map submission to guide with caching."""
        try:
            with self.track_request("mapping"):
                # Determine guide type if not provided
                if not guide_type:
                    guide_type, _ = self.determine_guide_type(guide_content)
                
                # Check cache first
                cached_result = self._get_cached_result(
                    "mapping", guide_content[:1000], submission_content[:1000], guide_type
                )
                if cached_result:
                    return cached_result
                
                if not self.mapping_service:
                    result = ({"mappings": [], "error": "Mapping service not available"}, 
                             "Mapping service not available")
                else:
                    result = self.mapping_service.map_submission_to_guide(
                        guide_content, submission_content
                    )
                
                # Cache result
                self._cache_result(
                    "mapping", result, guide_content[:1000], submission_content[:1000], guide_type
                )
                return result
                
        except Exception as e:
            error_msg = f"Mapping failed: {str(e)}"
            logger.error(error_msg)
            return {"mappings": [], "error": error_msg}, error_msg
    
    def grade_submission(
        self, 
        guide_content: str, 
        submission_content: str, 
        mapping_data: Dict = None
    ) -> Tuple[Dict, Optional[str]]:
        """Grade submission with caching."""
        try:
            with self.track_request("grading"):
                # Get mapping data if not provided
                if not mapping_data:
                    mapping_result, mapping_error = self.map_submission_to_guide(
                        guide_content, submission_content
                    )
                    if mapping_error:
                        return {"error": f"Mapping failed: {mapping_error}"}, mapping_error
                    mapping_data = mapping_result
                
                # Check cache first
                mapping_str = json.dumps(mapping_data, sort_keys=True)
                cached_result = self._get_cached_result(
                    "grading", guide_content[:1000], submission_content[:1000], mapping_str
                )
                if cached_result:
                    return cached_result
                
                if not self.grading_service:
                    result = ({"error": "Grading service not available"}, 
                             "Grading service not available")
                else:
                    mapped_questions = mapping_data.get('mappings', [])
                    result = self.grading_service.grade_submission(
                        guide_content, submission_content, mapped_questions
                    )
                
                # Cache result
                self._cache_result(
                    "grading", result, guide_content[:1000], submission_content[:1000], mapping_str
                )
                return result
                
        except Exception as e:
            error_msg = f"Grading failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}, error_msg
    
    def process_single_submission(
        self, 
        guide_data: Dict, 
        submission: Dict, 
        guide_type: str = None
    ) -> Dict[str, Any]:
        """Process a single submission through the complete pipeline."""
        try:
            with self.track_request("process_single"):
                guide_content = guide_data.get('content', guide_data.get('raw_content', ''))
                submission_content = submission.get('content_text', submission.get('content', ''))
                submission_id = submission.get('id', 'unknown')
                
                logger.info(f"Processing submission {submission_id}")
                
                # Step 1: Determine guide type if not provided
                if not guide_type:
                    guide_type, confidence = self.determine_guide_type(guide_content)
                    logger.info(f"Guide type determined: {guide_type} (confidence: {confidence})")
                
                # Step 2: Map submission to guide
                mapping_result, mapping_error = self.map_submission_to_guide(
                    guide_content, submission_content, guide_type
                )
                
                if mapping_error:
                    return {
                        'submission_id': submission_id,
                        'status': 'error',
                        'error': f"Mapping failed: {mapping_error}",
                        'guide_type': guide_type
                    }
                
                # Step 3: Grade the submission
                grading_result, grading_error = self.grade_submission(
                    guide_content, submission_content, mapping_result
                )
                
                if grading_error:
                    return {
                        'submission_id': submission_id,
                        'status': 'error',
                        'error': f"Grading failed: {grading_error}",
                        'guide_type': guide_type,
                        'mapping_result': mapping_result
                    }
                
                # Return complete result
                return {
                    'submission_id': submission_id,
                    'status': 'success',
                    'guide_type': guide_type,
                    'mapping_result': mapping_result,
                    'grading_result': grading_result,
                    'processed_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            error_msg = f"Single submission processing failed: {str(e)}"
            logger.error(error_msg)
            return {
                'submission_id': submission.get('id', 'unknown'),
                'status': 'error',
                'error': error_msg
            }

    def _estimate_time_remaining(self, current_step: int) -> float:
        if current_step == 0 or not self.start_time or self.total_submissions == 0:
            return 0.0
        elapsed_time = time.time() - self.start_time
        progress_ratio = current_step / self.total_submissions
        if progress_ratio == 0:
            return float('inf')  # Avoid division by zero
        estimated_total_time = elapsed_time / progress_ratio
        return max(0.0, estimated_total_time - elapsed_time) # Ensure non-negative time
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication."""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_cached_guide_type(self, guide_content: str) -> Optional[Tuple[str, float]]:
        """Get cached guide type determination result."""
        content_hash = self._generate_content_hash(guide_content)
        return self._guide_type_cache.get(content_hash)
    
    def _cache_guide_type(self, guide_content: str, guide_type: str, confidence: float):
        """Cache guide type determination result."""
        content_hash = self._generate_content_hash(guide_content)
        self._guide_type_cache[content_hash] = (guide_type, confidence)
        logger.info(f"Cached guide type: {guide_type} (confidence: {confidence})")
    
    def _determine_guide_type_optimized(self, guide_content: str) -> Tuple[str, float]:
        """Determine guide type with caching to avoid redundant LLM calls."""
        # Check cache first
        cached_result = self._get_cached_guide_type(guide_content)
        if cached_result:
            guide_type, confidence = cached_result
            logger.info(f"Using cached guide type: {guide_type} (confidence: {confidence})")
            return guide_type, confidence
        
        # If not cached, determine guide type via LLM
        logger.info("Determining guide type via LLM (not cached)")
        try:
            guide_type, confidence = self.mapping_service.determine_guide_type(guide_content)
            # Cache the result for future use
            self._cache_guide_type(guide_content, guide_type, confidence)
            return guide_type, confidence
        except Exception as e:
            logger.warning(f"Guide type determination failed: {str(e)}, using default")
            return "questions", 0.5
    
    def _group_submissions_by_content(self, submissions: List[Dict]) -> Dict[str, List[Dict]]:
        """Group submissions by content hash to identify duplicates."""
        content_groups = {}
        for submission in submissions:
            content = submission.get('content_text', submission.get('content', ''))
            if not content:
                # Handle empty content separately
                content_hash = 'empty_content'
            else:
                content_hash = self._generate_content_hash(content)
            
            if content_hash not in content_groups:
                content_groups[content_hash] = []
            content_groups[content_hash].append(submission)
        
        unique_count = len(content_groups)
        total_count = len(submissions)
        duplicate_count = total_count - unique_count
        
        if duplicate_count > 0:
            logger.info(f"Content deduplication: {unique_count} unique, {duplicate_count} duplicates from {total_count} total")
        
        return content_groups

    def process_batch(
        self, 
        guide_data: Dict, 
        submissions: List[Dict], 
        progress_id: str = None
    ) -> Dict[str, Any]:
        """Process multiple submissions with enhanced progress tracking."""
        start_time = time.time()
        total_submissions = len(submissions)
        
        # Initialize progress tracking
        progress_id = progress_id or f"batch_{int(start_time)}"
        self._active_progress = ProcessingProgress(
            progress_id=progress_id,
            total_submissions=total_submissions
        )
        
        logger.info(f"Starting batch processing for {total_submissions} submissions")
        
        try:
            with self.track_request("process_batch"):
                # Step 1: Determine guide type (5%)
                self._update_progress("guide_analysis", 5, "Analyzing marking guide")
                guide_type, confidence = self.determine_guide_type(guide_data.get('content', guide_data.get('raw_content', '')))
                logger.info(f"Guide type: {guide_type} (confidence: {confidence})")
                
                # Step 2: Process submissions in batches (5% - 95%)
                results = []
                errors = []
                
                for i in range(0, total_submissions, self.batch_size):
                    batch = submissions[i:i + self.batch_size]
                    batch_start = i
                    batch_end = min(i + self.batch_size, total_submissions)
                    
                    # Update progress
                    progress_percentage = 5 + (batch_start / total_submissions) * 90
                    self._update_progress(
                        "processing", 
                        progress_percentage, 
                        f"Processing submissions {batch_start + 1}-{batch_end}"
                    )
                    
                    # Process batch
                    for j, submission in enumerate(batch):
                        submission_index = batch_start + j
                        self._active_progress.update_submission(
                            submission_index, 
                            f"Processing submission {submission.get('id', submission_index + 1)}"
                        )
                        
                        try:
                            result = self.process_single_submission(
                                guide_data, submission, guide_type
                            )
                            results.append(result)
                            
                            if result.get('status') == 'error':
                                error_msg = f"Submission {submission.get('id')}: {result.get('error')}"
                                errors.append(error_msg)
                                self._active_progress.add_error(error_msg)
                            
                        except Exception as e:
                            error_msg = f"Submission {submission.get('id', submission_index)}: {str(e)}"
                            errors.append(error_msg)
                            self._active_progress.add_error(error_msg)
                            
                            # Add error result
                            results.append({
                                'submission_id': submission.get('id', f'submission_{submission_index}'),
                                'status': 'error',
                                'error': str(e)
                            })
                
                # Step 3: Finalize results (95% - 100%)
                self._update_progress("finalizing", 95, "Finalizing results")
                
                # Calculate summary statistics
                successful_results = [r for r in results if r.get('status') == 'success']
                failed_results = [r for r in results if r.get('status') == 'error']
                
                # Calculate average scores for successful results
                total_scores = []
                for result in successful_results:
                    grading_result = result.get('grading_result', {})
                    if isinstance(grading_result, tuple):
                        grading_result = grading_result[0]
                    score = grading_result.get('percentage', 0)
                    if isinstance(score, (int, float)):
                        total_scores.append(score)
                
                avg_score = sum(total_scores) / len(total_scores) if total_scores else 0
                
                # Final result
                final_result = {
                    'progress_id': progress_id,
                    'total_submissions': total_submissions,
                    'successful_submissions': len(successful_results),
                    'failed_submissions': len(failed_results),
                    'guide_type': guide_type,
                    'guide_type_confidence': confidence,
                    'average_score': round(avg_score, 2),
                    'processing_time': time.time() - start_time,
                    'results': results,
                    'errors': errors,
                    'summary': {
                        'total_processed': len(results),
                        'success_rate': len(successful_results) / len(results) * 100 if results else 0,
                        'average_score': avg_score,
                        'completed_at': datetime.now().isoformat()
                    }
                }
                
                self._update_progress("completed", 100, "Processing completed")
                logger.info(f"Batch processing completed: {len(successful_results)}/{total_submissions} successful")
                
                return final_result
                
        except Exception as e:
            error_msg = f"Batch processing failed: {str(e)}"
            logger.error(error_msg)
            if self._active_progress:
                self._active_progress.add_error(error_msg)
            
            return {
                'progress_id': progress_id,
                'status': 'error',
                'error': error_msg,
                'processing_time': time.time() - start_time,
                'results': [],
                'errors': [error_msg]
            }
        
        finally:
            self._active_progress = None
    
    def process_single_submission(
        self, 
        guide_data: Dict, 
        submission: Dict, 
        guide_type: str = None
    ) -> Dict[str, Any]:
        """Process a single submission through the complete pipeline."""
        submission_id = submission.get('id', 'unknown')
        
        try:
            with self.track_request("process_single_submission"):
                # Step 1: OCR Processing (if needed)
                if 'content' not in submission and 'image_path' in submission:
                    if not self.ocr_service:
                        raise ValueError("OCR service not available for image processing")
                    
                    ocr_result = self.ocr_service.extract_text(submission['image_path'])
                    if ocr_result.get('status') == 'error':
                        return {
                            'submission_id': submission_id,
                            'status': 'error',
                            'error': f"OCR failed: {ocr_result.get('error')}"
                        }
                    
                    submission['content'] = ocr_result.get('text', '')
                
                # Step 2: Determine guide type if not provided
                if not guide_type:
                    guide_type, _ = self.determine_guide_type(
                        guide_data.get('content', guide_data.get('raw_content', ''))
                    )
                
                # Step 3: Mapping (extract Q&A pairs)
                if not self.mapping_service:
                    raise ValueError("Mapping service not available")
                
                mapping_result = self.mapping_service.map_submission_to_guide(
                    submission['content'],
                    guide_data.get('content', guide_data.get('raw_content', '')),
                    guide_type=guide_type
                )
                
                if mapping_result.get('status') == 'error':
                    return {
                        'submission_id': submission_id,
                        'status': 'error',
                        'error': f"Mapping failed: {mapping_result.get('error')}"
                    }
                
                # Step 4: Grading
                if not self.grading_service:
                    raise ValueError("Grading service not available")
                
                grading_result = self.grading_service.grade_submission(
                    mapping_result.get('mapped_questions', []),
                    guide_data.get('content', guide_data.get('raw_content', ''))
                )
                
                if isinstance(grading_result, tuple):
                    grading_data, error = grading_result
                    if error:
                        return {
                            'submission_id': submission_id,
                            'status': 'error',
                            'error': f"Grading failed: {error}"
                        }
                else:
                    grading_data = grading_result
                
                # Step 5: Compile final result
                return {
                    'submission_id': submission_id,
                    'status': 'success',
                    'guide_type': guide_type,
                    'mapping_result': mapping_result,
                    'grading_result': grading_data,
                    'final_score': grading_data.get('percentage', 0),
                    'letter_grade': grading_data.get('letter_grade', 'F'),
                    'processed_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing submission {submission_id}: {str(e)}")
            return {
                'submission_id': submission_id,
                'status': 'error',
                'error': str(e)
            }
    
    def process_unified_ai_grading(
        self,
        marking_guide_content: Dict,
        submissions: List[Dict],
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
        max_questions: Optional[int] = None
    ) -> Tuple[Dict, Optional[str]]:
        """
        Legacy method for backward compatibility. Uses the new process_batch method internally.
        
        Args:
            marking_guide_content: Content of the marking guide
            submissions: List of submission dictionaries
            progress_callback: Optional callback for progress updates
            max_questions: Optional limit on number of questions to process
            
        Returns:
            Tuple[Dict, Optional[str]]: (Results, Error message if any)
        """
        logger.info("Using legacy process_unified_ai_grading method - redirecting to process_batch")
        
        # Set progress callback if provided
        if progress_callback:
            self.set_progress_callback(progress_callback)
        
        try:
            # Use the new process_batch method
            result = self.process_batch(
                guide_data=marking_guide_content,
                submissions=submissions,
                progress_id=f"legacy_{int(time.time())}"
            )
            
            # Check if processing was successful
            if result.get('status') == 'error':
                return result, result.get('error')
            
            # Transform result to match legacy format
            legacy_results = []
            for submission_result in result.get('results', []):
                if submission_result.get('status') == 'success':
                    grading_result = submission_result.get('grading_result', {})
                    if isinstance(grading_result, tuple):
                        grading_result = grading_result[0]
                    
                    legacy_result = {
                        'submission_id': submission_result.get('submission_id'),
                        'filename': submission_result.get('submission_id'),  # Legacy compatibility
                        'status': 'success',
                        'score': grading_result.get('score', 0),
                        'max_score': grading_result.get('max_score', 0),
                        'percentage': grading_result.get('percentage', 0),
                        'letter_grade': grading_result.get('letter_grade', 'F'),
                        'detailed_feedback': grading_result.get('detailed_feedback', {}),
                        'mappings': submission_result.get('mapping_result', {}).get('mapped_questions', []),
                        'guide_type': submission_result.get('guide_type'),
                        'processing_time': result.get('processing_time', 0),
                        'is_duplicate': False,  # Legacy field
                        'content_hash': f"hash_{submission_result.get('submission_id')}"  # Legacy field
                    }
                    
                    # Apply max_questions limit if specified
                    if max_questions and len(legacy_result['mappings']) > max_questions:
                        legacy_result['mappings'] = legacy_result['mappings'][:max_questions]
                        
                else:
                    legacy_result = {
                        'submission_id': submission_result.get('submission_id'),
                        'filename': submission_result.get('submission_id'),  # Legacy compatibility
                        'status': 'error',
                        'error': submission_result.get('error'),
                        'score': 0,
                        'max_score': 0,
                        'percentage': 0,
                        'letter_grade': 'F',
                        'guide_type': result.get('guide_type', 'unknown')
                    }
                
                legacy_results.append(legacy_result)
            
            # Calculate legacy summary statistics
            successful_results = [r for r in legacy_results if r.get('status') == 'success']
            failed_results = [r for r in legacy_results if r.get('status') == 'error']
            
            total_score = sum(r.get('score', 0) for r in successful_results)
            total_max_score = sum(r.get('max_score', 0) for r in successful_results)
            average_percentage = (total_score / total_max_score * 100) if total_max_score > 0 else 0
            
            # Create legacy-compatible result dictionary
            legacy_result_dict = {
                'status': 'success',
                'message': f'Unified AI processing completed: {len(successful_results)} successful, {len(failed_results)} failed',
                'results': legacy_results,
                'summary': {
                    'successful': len(successful_results),
                    'failed': len(failed_results),
                    'total': len(submissions),
                    'unique_contents_processed': len(legacy_results),  # Legacy field
                    'duplicate_submissions_detected': 0,  # Legacy field - not applicable
                    'optimization_ratio': 0.0,  # Legacy field - not applicable
                    'total_score': total_score,
                    'total_max_score': total_max_score,
                    'average_percentage': round(average_percentage, 1),
                    'processing_time': round(result.get('processing_time', 0), 2),
                    'guide_type': result.get('guide_type', 'unknown'),
                    'guide_confidence': result.get('guide_type_confidence', 0.0)
                },
                'metadata': {
                    'processed_at': datetime.now().isoformat(),
                    'processing_method': 'unified_ai_legacy',
                    'guide_analysis': {
                        'type': result.get('guide_type', 'unknown'),
                        'confidence': result.get('guide_type_confidence', 0.0)
                    },
                    'cache_stats': {
                        'guide_type_cache_size': len(self._guide_type_cache),
                        'content_hash_cache_size': len(self._content_hash_cache)
                    }
                }
            }
            
            return legacy_result_dict, None
            
        except Exception as e:
            error_message = f"Legacy unified AI processing failed: {str(e)}"
            logger.error(error_message)
            
            # Update progress with error status
            if self.progress_callback:
                self._update_progress(ProcessingProgress(
                    current_step=0,
                    total_steps=1,
                    current_operation="Processing failed",
                    submission_index=0,
                    total_submissions=len(submissions),
                    percentage=0,
                    status="error",
                    details=str(e)
                ))
            
            partial_result = {
                'status': 'error',
                'message': error_message,
                'processing_time': 0.0,
                'results': [],
                'errors': [error_message]
            }
            
            return partial_result, error_message

    def _get_letter_grade(self, percentage: float) -> str:
        """Convert percentage to letter grade"""
        if percentage >= 97: return "A+"
        elif percentage >= 93: return "A"
        elif percentage >= 90: return "A-"
        elif percentage >= 87: return "B+"
        elif percentage >= 83: return "B"
        elif percentage >= 80: return "B-"
        elif percentage >= 77: return "C+"
        elif percentage >= 73: return "C"
        elif percentage >= 70: return "C-"
        elif percentage >= 67: return "D+"
        elif percentage >= 63: return "D"
        elif percentage >= 60: return "D-"
        else: return "F"
    
    def get_cache_stats(self) -> Dict:
        """Get current cache statistics"""
        return {
            'guide_type_cache': {
                'size': len(self._guide_type_cache),
                'entries': list(self._guide_type_cache.keys()) if len(self._guide_type_cache) < 10 else f"{len(self._guide_type_cache)} entries"
            },
            'content_hash_cache': {
                'size': len(self._content_hash_cache),
                'unique_contents': len(set(self._content_hash_cache.values()))
            }
        }
    
    def clear_cache(self):
        """Clear all caches"""
        self._guide_type_cache.clear()
        self._content_hash_cache.clear()
        logger.info("All caches cleared")
    
    def clear_guide_type_cache(self):
        """Clear only the guide type cache"""
        self._guide_type_cache.clear()
        logger.info("Guide type cache cleared")
    
    def clear_content_cache(self):
        """Clear only the content hash cache"""
        self._content_hash_cache.clear()
        logger.info("Content hash cache cleared")

    def get_processing_stats(self) -> Dict:
        """Get processing statistics"""
        return {
            'service_type': 'unified_ai',
            'mapping_service_available': self.mapping_service is not None,
            'grading_service_available': self.grading_service is not None,
            'llm_service_available': self.llm_service is not None,
            'processing_times': self.processing_times[-10:] if self.processing_times else [],
            'average_processing_time': sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        }
