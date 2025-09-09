"""
Core Service Layer - Unified Service Architecture

This module provides the single, unified service layer that consolidates all
AI processing functionality into a clean, maintainable architecture.
"""

import time
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.config.processing_config import ProcessingConfigManager
from src.database.models import GradingResult, Mapping, MarkingGuide, Submission, db
from src.services.base_service import BaseService, ServiceStatus
from src.services.enhanced_logging_service import (
    LogCategory,
    enhanced_logging_service,
    log_operation,
)
from src.services.processing_error_handler import ErrorContext
from src.services.monitoring.monitoring_service import monitoring_service
from src.services.core.error_service import error_service
from src.services.retry_manager import retry_manager
from src.services.service_registry import service_registry
from utils.logger import logger

@dataclass
class ProcessingRequest:
    """Unified processing request structure."""

    guide_id: str
    submission_id: str
    user_id: str
    options: Dict[str, Any] = None

    def __post_init__(self):
        if self.options is None:
            self.options = {}

@dataclass
class ProcessingResponse:
    """Unified processing response structure."""

    success: bool
    result_id: Optional[str] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    mappings: Optional[List[Dict]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class CoreService(BaseService):
    """
    Unified Core Service that consolidates all AI processing functionality.

    This service replaces multiple redundant services with a single, clean interface
    that handles the complete processing pipeline from OCR to final grading.
    """

    def __init__(self):
        super().__init__("core_service", health_check_interval=30)
        self._ocr_engine = None
        self._llm_engine = None
        self._mapping_service = None
        self._grading_service = None
        self._processing_cache = {}
        self._service_registry = {}
        self._service_health = {}
        self._initialization_status = {}
        self._dependency_errors = []

        # Initialize processing configuration
        self._config = ProcessingConfigManager()

        # Initialize with proper error handling
        self._initialized = False

    def _initialize_engines(self):
        """Initialize the core processing engines with enhanced error handling and service registration."""
        with log_operation(
            LogCategory.SYSTEM, "core_service", "initialize_engines"
        ) as op:
            enhanced_logging_service.log_info(
                LogCategory.SYSTEM,
                "core_service",
                "initialize_engines",
                "Starting core service engine initialization...",
            )

            # Reset initialization status
            self._initialization_status = {}
            self._dependency_errors = []

            # Register core service with global service registry
            service_registry.register_service("core_service", self)

            # Initialize services with enhanced error handling
            services_to_initialize = [
                ("ocr", self._initialize_ocr_service),
                ("llm", self._initialize_llm_service),
                ("mapping", self._initialize_mapping_service),
                ("grading", self._initialize_grading_service),
            ]

            for service_name, init_func in services_to_initialize:
                error_context = ErrorContext(
                    operation=f"initialize_{service_name}_service",
                    service="core_service",
                    timestamp=datetime.now(timezone.utc),
                    user_id=None,
                    request_id=f"init_{service_name}_{int(time.time())}",
                    additional_data={"service_name": service_name},
                )

                try:
                    enhanced_logging_service.log_info(
                        LogCategory.SYSTEM,
                        "core_service",
                        f"initialize_{service_name}",
                        f"Initializing {service_name} service...",
                    )

                    success = retry_manager.execute_with_retry(
                        init_func,
                        f"initialize_{service_name}",
                        error_context,
                        max_attempts=2,
                        base_delay=1.0,
                    )

                    self._initialization_status[service_name] = {
                        "success": success,
                        "timestamp": datetime.now(timezone.utc),
                        "error": None,
                    }

                    if success:
                        enhanced_logging_service.log_info(
                            LogCategory.SYSTEM,
                            "core_service",
                            f"initialize_{service_name}",
                            f"✓ {service_name} service initialized successfully",
                        )
                        op.metadata[f"{service_name}_initialized"] = True
                    else:
                        enhanced_logging_service.log_warning(
                            LogCategory.SYSTEM,
                            "core_service",
                            f"initialize_{service_name}",
                            f"✗ {service_name} service initialization failed",
                        )
                        op.metadata[f"{service_name}_initialized"] = False

                except Exception as e:
                    error_msg = f"Failed to initialize {service_name} service: {str(e)}"

                    # Use enhanced error handler
                    error_service.handle_error(e, error_context)

                    enhanced_logging_service.log_error(
                        LogCategory.ERROR,
                        "core_service",
                        f"initialize_{service_name}",
                        error_msg,
                        metadata={"service_name": service_name},
                    )

                    self._initialization_status[service_name] = {
                        "success": False,
                        "timestamp": datetime.now(timezone.utc),
                        "error": error_msg,
                    }
                    self._dependency_errors.append(error_msg)
                    op.metadata[f"{service_name}_error"] = error_msg

            # Perform initial health checks
            self._perform_health_checks()

            # Register with health monitor
            monitoring_service.register_service("core_service", self.health_check)

            # Determine overall initialization success
            successful_services = sum(
                1
                for status in self._initialization_status.values()
                if status["success"]
            )
            total_services = len(self._initialization_status)

            enhanced_logging_service.log_info(
                LogCategory.SYSTEM,
                "core_service",
                "initialize_engines",
                f"Core service initialization completed: {successful_services}/{total_services} services initialized",
                metadata={
                    "successful_services": successful_services,
                    "total_services": total_services,
                    "success_rate": (
                        successful_services / total_services
                        if total_services > 0
                        else 0
                    ),
                },
            )

            # Set service status based on initialization results
            if successful_services == total_services:
                self.metrics.status = ServiceStatus.HEALTHY
            elif (
                successful_services >= total_services * 0.5
            ):  # At least 50% services working
                self.metrics.status = ServiceStatus.DEGRADED
            else:
                self.metrics.status = ServiceStatus.UNHEALTHY

            # Track performance metrics
            monitoring_service.track_operation(
                "core_service_initialization",
                op.metadata.get("duration_ms", 0) / 1000.0,
                successful_services > 0,
                metadata={
                    "services_initialized": successful_services,
                    "total_services": total_services,
                },
            )

            self._initialized = successful_services > 0
            return self._initialized

    def _initialize_ocr_service(self) -> bool:
        """Initialize OCR service with graceful error handling."""
        try:
            from src.services.consolidated_ocr_service import ConsolidatedOCRService

            self._ocr_engine = ConsolidatedOCRService(allow_no_key=True)
            self._register_service("ocr", self._ocr_engine)
            return True
        except ImportError as e:
            logger.warning(f"OCR service not available: {e}")
            self._ocr_engine = None
            return False
        except Exception as e:
            logger.error(f"OCR service initialization failed: {e}")
            self._ocr_engine = None
            return False

    def _initialize_llm_service(self) -> bool:
        """Initialize LLM service with graceful error handling."""
        try:
            from src.services.consolidated_llm_service import ConsolidatedLLMService

            logger.info("Initializing LLM service...")
            self._llm_engine = ConsolidatedLLMService()
            logger.info("LLM service initialized successfully")
            self._register_service("llm", self._llm_engine)
            return True
        except ImportError as e:
            logger.warning(f"LLM service not available: {e}")
            self._llm_engine = None
            return False
        except Exception as e:
            logger.error(f"LLM service initialization failed: {e}")
            import traceback
            logger.error(f"LLM initialization traceback: {traceback.format_exc()}")
            self._llm_engine = None
            return False

    def _initialize_mapping_service(self) -> bool:
        """Initialize mapping service with dependency injection."""
        try:
            from src.services.consolidated_mapping_service import (
                ConsolidatedMappingService,
            )

            if self._llm_engine is None:
                logger.warning(
                    "Mapping service requires LLM service - initializing without LLM dependency"
                )
                self._mapping_service = ConsolidatedMappingService(llm_service=None)
            else:
                self._mapping_service = ConsolidatedMappingService(
                    llm_service=self._llm_engine
                )

            self._register_service("mapping", self._mapping_service)
            return True
        except ImportError as e:
            logger.warning(f"Mapping service not available: {e}")
            self._mapping_service = None
            return False
        except Exception as e:
            logger.error(f"Mapping service initialization failed: {e}")
            self._mapping_service = None
            return False

    def _initialize_grading_service(self) -> bool:
        """Initialize grading service with dependency injection."""
        try:
            from src.services.consolidated_grading_service import (
                ConsolidatedGradingService,
            )

            # Check dependencies
            missing_deps = []
            if self._llm_engine is None:
                missing_deps.append("LLM")
            if self._mapping_service is None:
                missing_deps.append("Mapping")

            if missing_deps:
                logger.warning(
                    f"Grading service missing dependencies: {', '.join(missing_deps)} - initializing with available services"
                )

            self._grading_service = ConsolidatedGradingService(
                llm_service=self._llm_engine, mapping_service=self._mapping_service
            )
            self._register_service("grading", self._grading_service)
            return True
        except ImportError as e:
            logger.warning(f"Grading service not available: {e}")
            self._grading_service = None
            return False
        except Exception as e:
            logger.error(f"Grading service initialization failed: {e}")
            self._grading_service = None
            return False


    def _register_service(self, name: str, service):
        """Register a service with enhanced health monitoring and global registry."""
        # Register with local registry
        self._service_registry[name] = service
        self._service_health[name] = {
            "status": ServiceStatus.UNKNOWN,
            "last_check": None,
            "error_count": 0,
        }

        # Register with global service registry
        try:
            service_registry.register_service(f"core_service_{name}", service)
            enhanced_logging_service.log_info(
                LogCategory.SYSTEM,
                "core_service",
                "register_service",
                f"Registered {name} service with global registry",
            )
        except Exception as e:
            enhanced_logging_service.log_warning(
                LogCategory.SYSTEM,
                "core_service",
                "register_service",
                f"Failed to register {name} with global registry: {e}",
            )

        try:
            if hasattr(service, "health_check"):
                monitoring_service.register_service(
                    f"core_service_{name}", service.health_check
                )
            elif hasattr(service, "is_available"):
                monitoring_service.register_service(
                    f"core_service_{name}", service.is_available
                )
        except Exception as e:
            enhanced_logging_service.log_warning(
                LogCategory.SYSTEM,
                "core_service",
                "register_service",
                f"Failed to register {name} health check: {e}",
            )

        # Perform initial health check
        try:
            if hasattr(service, "health_check"):
                is_healthy = service.health_check()
                self._service_health[name]["status"] = (
                    ServiceStatus.HEALTHY if is_healthy else ServiceStatus.UNHEALTHY
                )
            elif hasattr(service, "is_available"):
                is_available = service.is_available()
                self._service_health[name]["status"] = (
                    ServiceStatus.HEALTHY if is_available else ServiceStatus.DEGRADED
                )
            else:
                self._service_health[name]["status"] = ServiceStatus.HEALTHY

            self._service_health[name]["last_check"] = time.time()

            enhanced_logging_service.log_info(
                LogCategory.SYSTEM,
                "core_service",
                "register_service",
                f"Service {name} registered with status: {self._service_health[name]['status'].value}",
            )

        except Exception as e:
            enhanced_logging_service.log_error(
                LogCategory.ERROR,
                "core_service",
                "register_service",
                f"Health check failed for service {name}: {e}",
            )
            self._service_health[name]["status"] = ServiceStatus.UNHEALTHY
            self._service_health[name]["error_count"] += 1

    def _perform_health_checks(self):
        """Perform health checks on all registered services."""
        for name, service in self._service_registry.items():
            try:
                if hasattr(service, "health_check"):
                    is_healthy = service.health_check()
                    status = (
                        ServiceStatus.HEALTHY if is_healthy else ServiceStatus.UNHEALTHY
                    )
                elif hasattr(service, "is_available"):
                    is_available = service.is_available()
                    status = (
                        ServiceStatus.HEALTHY
                        if is_available
                        else ServiceStatus.DEGRADED
                    )
                else:
                    status = ServiceStatus.HEALTHY

                self._service_health[name]["status"] = status
                self._service_health[name]["last_check"] = time.time()

                if status == ServiceStatus.UNHEALTHY:
                    self._service_health[name]["error_count"] += 1
                else:
                    self._service_health[name]["error_count"] = 0

            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                self._service_health[name]["status"] = ServiceStatus.UNHEALTHY
                self._service_health[name]["error_count"] += 1

    def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all services."""
        return {
            "core_service": "healthy",
            "services": {
                name: {
                    "status": health["status"].value,
                    "last_check": health["last_check"],
                    "error_count": health["error_count"],
                }
                for name, health in self._service_health.items()
            },
            "overall_healthy": all(
                health["status"] in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]
                for health in self._service_health.values()
            ),
        }

    async def process_submission(
        self, request: ProcessingRequest
    ) -> ProcessingResponse:
        """
        Main processing method that handles the complete pipeline.

        Args:
            request: Processing request with guide and submission IDs

        Returns:
            ProcessingResponse with results or error information
        """
        start_time = time.time()

        # Create a unique lock key for this submission-guide pair
        lock_key = f"{request.submission_id}_{request.guide_id}"

        # Check if this submission is already being processed using database-based locking
        from src.database.models import db, Submission
        
        # Check submission processing status in database
        submission = db.session.get(Submission, request.submission_id)
        if submission and submission.processing_status == "processing":
            logger.warning(f"Submission {request.submission_id} is already being processed (status: {submission.processing_status}), skipping duplicate request")
            return ProcessingResponse(
                success=False,
                error="Submission is already being processed"
            )

        # Set processing status in database
        if submission:
            submission.processing_status = "processing"
            submission.processing_error = None
            db.session.commit()
            logger.info(f"Set processing status for submission {request.submission_id}")

        # Also maintain in-memory locks for additional safety
        if not hasattr(self, '_processing_locks'):
            self._processing_locks = set()
        self._processing_locks.add(lock_key)

        try:
            # Validate request
            if not self._validate_request(request):
                return ProcessingResponse(
                    success=False, error="Invalid processing request"
                )

            # Get database records with enhanced validation and error handling
            try:
                guide = db.session.get(MarkingGuide, request.guide_id)
                submission = db.session.get(Submission, request.submission_id)

                # Comprehensive validation
                if not guide:
                    logger.error(f"Guide not found: {request.guide_id}")
                    return ProcessingResponse(
                        success=False,
                        error=f"Marking guide not found (ID: {request.guide_id})",
                    )

                if not submission:
                    logger.error(f"Submission not found: {request.submission_id}")
                    return ProcessingResponse(
                        success=False,
                        error=f"Submission not found (ID: {request.submission_id})",
                    )

                # Validate object integrity
                if not hasattr(guide, "id") or guide.id is None:
                    logger.error(f"Invalid guide object: {guide}")
                    return ProcessingResponse(
                        success=False, error="Invalid guide object - missing ID"
                    )

                if not hasattr(submission, "id") or submission.id is None:
                    logger.error(f"Invalid submission object: {submission}")
                    return ProcessingResponse(
                        success=False, error="Invalid submission object - missing ID"
                    )

                # Validate required attributes
                required_guide_attrs = ["id", "content_text", "questions"]
                required_submission_attrs = ["id", "filename", "content_text"]

                for attr in required_guide_attrs:
                    if not hasattr(guide, attr):
                        logger.error(f"Guide missing required attribute: {attr}")
                        return ProcessingResponse(
                            success=False,
                            error=f"Guide object missing required attribute: {attr}",
                        )

                for attr in required_submission_attrs:
                    if not hasattr(submission, attr):
                        logger.error(f"Submission missing required attribute: {attr}")
                        return ProcessingResponse(
                            success=False,
                            error=f"Submission object missing required attribute: {attr}",
                        )

                logger.info(
                    f"Successfully loaded and validated guide {guide.id} and submission {submission.id}"
                )

            except Exception as db_error:
                logger.error(f"Database error loading guide/submission: {db_error}")
                return ProcessingResponse(
                    success=False,
                    error=f"Database error loading submission data: {str(db_error)}",
                )

            submission_text = await self._extract_text(submission)
            if not submission_text:
                return ProcessingResponse(
                    success=False, error="Failed to extract text from submission"
                )

            # Step 2: Answer Mapping
            mappings = await self._map_answers(guide, submission_text, submission.id)
            if not mappings:
                return ProcessingResponse(
                    success=False, error="Failed to map answers to questions"
                )
            
            # Validate mappings before proceeding
            mappings = self._validate_mappings(mappings, submission.id)
            
            # Check if we have enough valid mappings (should be at least 3-5 for a typical exam)
            expected_min_mappings = min(3, guide.max_questions_to_answer or 5)
            if not mappings or len(mappings) < expected_min_mappings:
                # If too few valid mappings found, try to regenerate them
                logger.warning(f"Only {len(mappings) if mappings else 0} valid mappings found for submission {submission.id} (expected at least {expected_min_mappings}), attempting to regenerate...")
                
                # Clear existing invalid mappings
                await self._clear_invalid_mappings(submission.id)
                
                # Regenerate mappings with fresh LLM call
                mappings = await self._regenerate_mappings(guide, submission_text, submission.id)
                if not mappings:
                    return ProcessingResponse(
                        success=False, error="Failed to regenerate valid mappings"
                    )
                
                # Validate the new mappings
                mappings = self._validate_mappings(mappings, submission.id)
                if not mappings or len(mappings) < expected_min_mappings:
                    logger.warning(f"Still only {len(mappings) if mappings else 0} valid mappings after regeneration")
                    # Continue with what we have rather than failing completely

            # Step 3: AI Grading
            grading_result = await self._grade_submission(guide, mappings)
            if not grading_result:
                return ProcessingResponse(
                    success=False, error="Failed to grade submission"
                )

            # Step 4: Save results
            result_id = await self._save_results(request, grading_result, mappings)

            processing_time = time.time() - start_time

            return ProcessingResponse(
                success=True,
                result_id=result_id,
                score=grading_result.get("total_score", 0),
                feedback=grading_result.get("feedback", ""),
                mappings=mappings,
                processing_time=processing_time,
                metadata={
                    "guide_id": request.guide_id,
                    "submission_id": request.submission_id,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            self._processing_error = e  # Store error for cleanup
            return ProcessingResponse(
                success=False, error=str(e), processing_time=time.time() - start_time
            )
        finally:
            # Always remove the lock when processing is complete
            if hasattr(self, '_processing_locks') and lock_key in self._processing_locks:
                self._processing_locks.remove(lock_key)
                logger.debug(f"Removed processing lock for {lock_key}")
            
            # Update database status
            try:
                submission = db.session.get(Submission, request.submission_id)
                if submission:
                    if submission.processing_status == "processing":
                        # Only update if still in processing state (not already completed/failed)
                        submission.processing_status = "completed" if not hasattr(self, '_processing_error') else "failed"
                        if hasattr(self, '_processing_error'):
                            submission.processing_error = str(self._processing_error)
                        db.session.commit()
                        logger.info(f"Updated processing status for submission {request.submission_id} to {submission.processing_status}")
            except Exception as cleanup_error:
                logger.error(f"Error updating submission status during cleanup: {cleanup_error}")

    async def _extract_text(self, submission: Submission) -> Optional[str]:
        """Extract text from submission using OCR if needed."""
        if not submission or not hasattr(submission, "id"):
            logger.error("Invalid submission object passed to _extract_text")
            return None

        if submission.content_text:
            logger.info(
                f"Using pre-extracted text for submission {submission.id} ({len(submission.content_text)} chars)"
            )
            return submission.content_text

        if self._ocr_engine and submission.file_path:
            logger.info(f"Attempting OCR extraction for submission {submission.id}")

            try:
                extracted_text = self._ocr_engine.extract_text(submission.file_path)
                if extracted_text and extracted_text.get("success"):
                    text_content = extracted_text.get("text", "")

                    # Update submission with extracted text
                    submission.content_text = text_content
                    db.session.commit()

                    logger.info(
                        f"OCR extraction successful for {submission.id} ({len(text_content)} chars)"
                    )
                    return text_content
                else:
                    logger.warning(f"OCR extraction failed for {submission.id}")
            except Exception as e:
                logger.error(f"OCR extraction error for {submission.id}: {e}")

        logger.warning(f"No text content available for submission {submission.id}")
        return None

    async def _map_answers(
        self, guide: MarkingGuide, submission_text: str, submission_id: str = None
    ) -> Optional[List[Dict]]:
        """Map submission answers to guide questions using LLM processing."""
        try:
            if not guide or not hasattr(guide, "id"):
                logger.error("Invalid guide object passed to _map_answers")
                return None

            # First, validate that the guide has proper questions and scores
            if not self._validate_guide_questions_and_scores(guide):
                logger.warning(f"Guide {guide.id} has incomplete questions/scores, proceeding with LLM mapping")

            # Check if we already have mappings in the database for this specific submission
            if submission_id:
                existing_mappings = self._get_existing_mappings_from_db(guide.id, submission_id)
                if existing_mappings:
                    logger.info(f"Using {len(existing_mappings)} existing mappings from database for submission {submission_id}")
                    return existing_mappings

            # Use LLM for mapping guide and submission
            logger.info(f"Using LLM for mapping guide {guide.id} and submission")
            
            try:
                questions_data = guide.questions if guide.questions else None
                if not questions_data:
                    logger.error("No questions data available in guide")
                    return None

                # Use LLM mapping with guide and submission data
                mappings = await self._map_with_llm(
                    guide.content_text or "",
                    submission_text,
                    max_questions=len(questions_data),
                    questions_data=questions_data,
                )

                if mappings:
                    logger.info(f"LLM mapping returned {len(mappings)} mappings")
                    return mappings
                else:
                    logger.error("LLM mapping returned no results")
                    return None

            except Exception as e:
                logger.error(f"LLM mapping failed: {e}")
                return None

        except Exception as e:
            logger.error(f"Error in _map_answers: {str(e)}")
            return None

    def _validate_guide_questions_and_scores(self, guide: MarkingGuide) -> bool:
        """Check if the guide has proper questions and scores stored."""
        try:
            if not guide.questions:
                logger.warning(f"Guide {guide.id} has no questions stored")
                return False
            
            questions_with_marks = 0
            questions_without_marks = 0
            
            for question in guide.questions:
                if isinstance(question, dict):
                    marks = question.get('marks', 0)
                    if marks > 0:
                        questions_with_marks += 1
                    else:
                        questions_without_marks += 1
                        logger.warning(f"Question {question.get('number', 'unknown')} has no marks")
            
            logger.info(f"Guide {guide.id}: {questions_with_marks} questions with marks, {questions_without_marks} without marks")
            
            # Consider guide valid if at least 50% of questions have marks
            return questions_with_marks > questions_without_marks
            
        except Exception as e:
            logger.error(f"Error validating guide questions and scores: {e}")
            return False

    def _create_mappings_from_guide(self, questions_data: List[Dict], submission_text: str) -> List[Dict]:
        """Create mappings directly from guide structure without LLM."""
        try:
            mappings = []
            
            for question in questions_data:
                if not isinstance(question, dict):
                    continue
                
                question_number = question.get('number', '')
                question_text = question.get('text', '')
                question_marks = question.get('marks', 0)
                question_type = question.get('type', 'single')
                sub_parts = question.get('sub_parts', [])
                criteria = question.get('criteria', '')
                
                if question_type == 'grouped' and sub_parts:
                    # For grouped questions, create mappings for each sub-part
                    for sub_part in sub_parts:
                        # Extract exact marks from criteria for this sub-part
                        exact_marks = self._extract_marks_from_criteria(criteria, sub_part)
                        
                        if exact_marks > 0:
                            max_score = exact_marks
                            logger.info(f"Question {sub_part}: {max_score} marks (extracted from criteria)")
                        else:
                            # Fallback: distribute marks among sub-parts
                            max_score = question_marks / len(sub_parts) if sub_parts else question_marks
                            logger.warning(f"Question {sub_part}: No exact marks found, using calculated: {max_score}")
                        
                        # Create mapping for this sub-part
                        mapping = {
                            'question_id': f'Q{sub_part}',
                            'question_text': f"{question_text} (Part {sub_part})",
                            'student_answer': self._extract_student_answer_for_question(submission_text, sub_part),
                            'max_score': max_score,
                            'confidence': 1.0,  # Direct from guide = 100% confidence
                            'match_reason': 'Direct from guide structure',
                            'mapping_method': 'guide_direct'
                        }
                        mappings.append(mapping)
                else:
                    # For single questions
                    max_score = question_marks
                    logger.info(f"Question {question_number}: {max_score} marks (single question)")
                    
                    mapping = {
                        'question_id': f'Q{question_number}',
                        'question_text': question_text,
                        'student_answer': self._extract_student_answer_for_question(submission_text, question_number),
                        'max_score': max_score,
                        'confidence': 1.0,  # Direct from guide = 100% confidence
                        'match_reason': 'Direct from guide structure',
                        'mapping_method': 'guide_direct'
                    }
                    mappings.append(mapping)
            
            logger.info(f"Created {len(mappings)} mappings directly from guide structure")
            return mappings
            
        except Exception as e:
            logger.error(f"Error creating mappings from guide: {e}")
            return []

    def _extract_student_answer_for_question(self, submission_text: str, question_id: str) -> str:
        """Extract student answer for a specific question from submission text."""
        try:
            # Simple pattern matching to find answers
            patterns = [
                f"Question {question_id}:",
                f"Q{question_id}:",
                f"{question_id}:",
                f"Part {question_id}:",
            ]
            
            for pattern in patterns:
                if pattern in submission_text:
                    # Find the answer after the pattern
                    start_idx = submission_text.find(pattern)
                    if start_idx != -1:
                        # Look for the next question or end of text
                        next_question_idx = len(submission_text)
                        for next_pattern in ["Question ", "Q", "\n\n"]:
                            next_idx = submission_text.find(next_pattern, start_idx + len(pattern))
                            if next_idx != -1 and next_idx < next_question_idx:
                                next_question_idx = next_idx
                        
                        answer = submission_text[start_idx + len(pattern):next_question_idx].strip()
                        return answer[:200]  # Limit length
            
            # If no specific pattern found, return a generic response
            return f"Answer for {question_id} not found in submission"
            
        except Exception as e:
            logger.error(f"Error extracting student answer for {question_id}: {e}")
            return f"Error extracting answer for {question_id}"

    def _get_existing_mappings_from_db(self, guide_id: str, submission_id: str = None) -> Optional[List[Dict]]:
        """Check if mappings already exist in database for this guide and optionally specific submission."""
        try:
            from src.database.models import Mapping, Submission, db
            
            # Get existing mappings for this guide and optionally specific submission
            if submission_id:
                # Get mappings for specific submission
                existing_mappings = db.session.query(Mapping).filter(
                    Mapping.submission_id == submission_id
                ).all()
            else:
                # Get mappings for all submissions using this guide (legacy behavior)
                existing_mappings = db.session.query(Mapping).filter(
                    Mapping.submission_id.in_(
                        db.session.query(Submission.id).filter(Submission.marking_guide_id == guide_id)
                    )
                ).all()
            
            if existing_mappings:
                if submission_id:
                    logger.info(f"Found {len(existing_mappings)} existing mappings in database for submission {submission_id}")
                else:
                    logger.info(f"Found {len(existing_mappings)} existing mappings in database for guide {guide_id}")
                
                # Check for excessive mappings (more than 50 suggests a problem)
                if len(existing_mappings) > 50:
                    logger.warning(f"Found {len(existing_mappings)} mappings for submission {submission_id}, which seems excessive. Cleaning up duplicates.")
                    existing_mappings = self._cleanup_duplicate_mappings(existing_mappings, submission_id)
                    logger.info(f"After cleanup: {len(existing_mappings)} mappings remaining")
                
                # Check for poor quality mappings (too few unique questions)
                unique_questions = set(m.guide_question_id for m in existing_mappings)
                if len(unique_questions) < 3:  # Should have at least 3 different questions
                    logger.warning(f"Found only {len(unique_questions)} unique questions in existing mappings, forcing regeneration")
                    return None  # Force regeneration
                
                # Check if existing mappings have valid max_scores
                valid_mappings = []
                invalid_mappings = []
                
                for mapping in existing_mappings:
                    if mapping.max_score > 0:
                        valid_mappings.append(mapping)
                    else:
                        invalid_mappings.append(mapping)
                
                if invalid_mappings:
                    logger.warning(f"Found {len(invalid_mappings)} mappings with invalid max_scores (0.0), will regenerate")
                    return None  # Return None to force regeneration
                
                # Convert to the format expected by the mapping system
                mappings = []
                for mapping in valid_mappings:
                    mappings.append({
                        'question_id': mapping.guide_question_id,
                        'question_text': mapping.guide_question_text,
                        'student_answer': mapping.submission_answer,
                        'max_score': mapping.max_score,
                        'confidence': mapping.match_score,
                        'match_reason': mapping.match_reason,
                        'mapping_method': mapping.mapping_method
                    })
                
                return mappings
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking existing mappings from database: {e}")
            return None

    def _cleanup_duplicate_mappings(self, mappings: List, submission_id: str) -> List:
        """Clean up duplicate mappings for a submission."""
        try:
            from src.database.models import db, Mapping
            
            # Group mappings by question_id to find duplicates
            question_mappings = {}
            for mapping in mappings:
                question_id = mapping.guide_question_id
                if question_id not in question_mappings:
                    question_mappings[question_id] = []
                question_mappings[question_id].append(mapping)
            
            # Keep only the best mapping for each question
            cleaned_mappings = []
            duplicates_removed = 0
            
            for question_id, question_maps in question_mappings.items():
                if len(question_maps) > 1:
                    # Sort by match_score (descending) and created_at (descending) to get the best one
                    # Also prefer mappings with actual student answers over empty ones
                    best_mapping = max(question_maps, key=lambda m: (
                        len(m.submission_answer or "") > 0,  # Prefer non-empty answers
                        m.match_score or 0, 
                        m.created_at
                    ))
                    cleaned_mappings.append(best_mapping)
                    
                    # Remove the duplicate mappings from database
                    for mapping in question_maps:
                        if mapping.id != best_mapping.id:
                            db.session.delete(mapping)
                            duplicates_removed += 1
                else:
                    cleaned_mappings.append(question_maps[0])
            
            if duplicates_removed > 0:
                db.session.commit()
                logger.info(f"Removed {duplicates_removed} duplicate mappings for submission {submission_id}")
            
            return cleaned_mappings
            
        except Exception as e:
            logger.error(f"Error cleaning up duplicate mappings: {e}")
            return mappings  # Return original mappings if cleanup fails

    def _validate_mappings(self, mappings: List[Dict], submission_id: str) -> List[Dict]:
        """Validate and clean up mappings to ensure quality."""
        try:
            if not mappings:
                return []
            
            validated_mappings = []
            seen_questions = set()
            
            for mapping in mappings:
                question_id = mapping.get('question_id', '')
                student_answer = mapping.get('student_answer', '')
                max_score = mapping.get('max_score', 0)
                
                # Skip if we've already seen this question
                if question_id in seen_questions:
                    logger.warning(f"Duplicate question_id {question_id} found in mappings, skipping")
                    continue
                
                # Skip if no student answer (but be more lenient)
                if not student_answer or student_answer.strip() == '':
                    logger.warning(f"No student answer found for {question_id}, skipping")
                    continue
                
                # Skip if explicitly says no answer provided
                if 'no answer provided' in student_answer.lower() or 'no answer' in student_answer.lower():
                    logger.warning(f"Explicitly no answer for {question_id}, skipping")
                    continue
                
                # Skip if invalid max_score
                if max_score <= 0:
                    logger.warning(f"Invalid max_score {max_score} for {question_id}, skipping")
                    continue
                
                # Add to validated mappings
                validated_mappings.append(mapping)
                seen_questions.add(question_id)
            
            logger.info(f"Validated {len(validated_mappings)}/{len(mappings)} mappings for submission {submission_id}")
            return validated_mappings
            
        except Exception as e:
            logger.error(f"Error validating mappings: {e}")
            return mappings  # Return original mappings if validation fails

    async def _clear_invalid_mappings(self, submission_id: str):
        """Clear invalid mappings for a submission."""
        try:
            from src.database.models import db, Mapping
            
            # Delete all mappings for this submission
            deleted_count = db.session.query(Mapping).filter(
                Mapping.submission_id == submission_id
            ).delete()
            
            db.session.commit()
            logger.info(f"Cleared {deleted_count} invalid mappings for submission {submission_id}")
            
        except Exception as e:
            logger.error(f"Error clearing invalid mappings: {e}")

    async def _regenerate_mappings(self, guide, submission_text: str, submission_id: str):
        """Regenerate mappings with fresh LLM call."""
        try:
            logger.info(f"Regenerating mappings for submission {submission_id} with improved logic")
            
            # Use the improved LLM mapping directly
            mappings = await self._map_with_llm(
                guide.content_text or "",
                submission_text,
                max_questions=guide.max_questions_to_answer,
                questions_data=guide.questions
            )
            
            if mappings:
                # Save the new mappings to database
                await self._save_mappings_to_db(mappings, guide.id, submission_id)
                logger.info(f"Successfully regenerated and saved {len(mappings)} mappings for submission {submission_id}")
            
            return mappings
            
        except Exception as e:
            logger.error(f"Error regenerating mappings: {e}")
            return None

    async def _save_mappings_to_db(self, mappings: List[Dict], guide_id: str, submission_id: str):
        """Save mappings to database."""
        try:
            from src.database.models import db, Mapping
            
            for mapping in mappings:
                db_mapping = Mapping(
                    submission_id=submission_id,
                    guide_question_id=mapping.get('question_id', ''),
                    guide_question_text=mapping.get('question_text', ''),
                    submission_answer=mapping.get('student_answer', ''),
                    max_score=mapping.get('max_score', 0),
                    match_score=mapping.get('confidence', 0.5),
                    match_reason=mapping.get('match_reason', 'LLM mapping'),
                    mapping_method='llm_regenerated'
                )
                db.session.add(db_mapping)
            
            db.session.commit()
            logger.info(f"Saved {len(mappings)} mappings to database for submission {submission_id}")
            
        except Exception as e:
            logger.error(f"Error saving mappings to database: {e}")
            db.session.rollback()

    async def _map_with_llm(self, guide_content: str, submission_text: str, max_questions: int = None, questions_data=None) -> Optional[List[Dict]]:
        """Map submission answers to guide questions using LLM."""
        try:
            # First, check if we already have mappings in the database for this guide
            # Note: We need the guide_id to check, but this method doesn't have it
            # We'll need to modify the calling code to pass the guide_id
            
            # Ensure LLM engine is available
            if not self._llm_engine:
                logger.warning("LLM engine not available, attempting to initialize...")
                if not self._initialize_llm_service():
                    logger.error("Failed to initialize LLM engine for mapping")
                    return None

            # Prepare mapping prompt - simplified and focused
            system_prompt = """You are an expert at finding student answers in exam submissions.

TASK: Find the student's answer for each question in the marking guide.

OUTPUT FORMAT: Return ONLY valid JSON in this exact format:
{"mappings":[{"question_id":"Q1a","question_text":"What is...?","student_answer":"The student's actual answer text"}]}

CRITICAL INSTRUCTIONS:
1. **FIND ALL STUDENT ANSWERS**: The student has written clear answers in the submission
2. **STUDENT ANSWERS ARE THERE**: Look for any explanatory text that shows understanding
3. **EXTRACT COMPLETE ANSWERS**: Copy the entire student response, including explanations
4. **BE FLEXIBLE**: Students may use different wording but still answer correctly
5. **BE THOROUGH**: Search the entire submission text for each answer
6. **FIND ALL QUESTIONS**: You must find answers for ALL questions in the guide

STUDENT ANSWER PATTERNS TO LOOK FOR:
- "Human factors and ergonomics: This involves..."
- "Quality engineering: This involves..."
- "Operations research: This includes..."
- "Systems engineering: Systems Theory: This involves..."
- "Quality planning: This involves identifying..."
- "Quality assurance: This is the process of auditing..."
- "Quality control: This is the process of monitoring..."
- "Method Study: is the systematic recording..."
- "Work Breakdown Structure: This is the structure..."
- "Engineering design is both effective and cyclic"
- Mathematical calculations and formulas
- Any explanatory text that shows understanding

IMPORTANT: The student has clearly answered the questions in the submission. Find their actual responses. Do not return "No answer provided" - the answers are there!"""

            # Build questions context with proper sub-part handling
            questions_context = ""
            if questions_data:
                questions_to_process = questions_data
                for i, q in enumerate(questions_to_process):
                    if isinstance(q, dict):
                        q_text = q.get('text', q.get('question_text', ''))
                        q_marks = q.get('marks', 0)
                        q_type = q.get('type', 'single')
                        sub_parts = q.get('sub_parts', [])
                        criteria = q.get('criteria', '')
                        
                        if q_type == 'grouped' and sub_parts:
                            # For grouped questions, provide full context including criteria
                            questions_context += f"Question {i+1} (Total: {q_marks} points, {len(sub_parts)} sub-parts): {q_text}\n"
                            questions_context += f"Sub-parts: {', '.join(sub_parts)}\n"
                            questions_context += f"Marking Criteria: {criteria}\n"
                            questions_context += f"IMPORTANT: Extract the INDIVIDUAL marks for each sub-part from the criteria above.\n"
                            questions_context += f"Each sub-part (Q{i+1}a, Q{i+1}b, etc.) should have its own specific score.\n"
                        else:
                            # For single questions
                            questions_context += f"Question {i+1} (Max: {q_marks} points): {q_text}\n"
                            if criteria:
                                questions_context += f"Marking Criteria: {criteria}\n"
                    else:
                        questions_context += f"Question {i+1}: {str(q)}\n"
            else:
                questions_context = guide_content  # Use full guide content if no structured questions

            user_prompt = f"""Find the student's answers for each question in the marking guide:

MARKING GUIDE:
{questions_context}

STUDENT SUBMISSION:
{submission_text}

TASK: 
1. For each question in the guide, find the student's answer in the submission
2. Return JSON with the actual student answer text (not "No answer provided")

CRITICAL: The student has clearly written answers in the submission. Find them!

STUDENT ANSWERS TO LOOK FOR:
- "Human factors and ergonomics: This involves the general management of the human resources involved in the chain of production."
- "Quality engineering: This involves the Six Sigma, Total quality management (TQM) and statistical process Control (CSPC) to ensure products and processes meet quality standards."
- "Operations research: This includes mathematical modeling, statistical analysis, and optimization techniques to solve complex decision-making problems."
- "Systems engineering: Systems Theory: This involves understanding and analyzing the entire system, including all its components and interaction."
- "Quality planning: This involves identifying the quality standards relevant to the project and determining how to meet them."
- "Quality assurance: This is the process of auditing the quality requirements and the results of quality control measure to show ascertain that appropriate standards are being met."
- "Quality control: This is the process of monitoring and recording the results of executing the quality activities to assess performance and recommend necessary changes."

IMPORTANT: The student has answered multiple questions. Find ALL their answers. Do not skip any questions. The answers are clearly written in the submission text above.

SEARCH INSTRUCTIONS:
1. Look for any text that explains concepts or processes
2. Look for numbered lists or bullet points
3. Look for explanatory sentences that show understanding
4. Look for mathematical calculations or formulas
5. Look for any text that demonstrates knowledge of the subject

DO NOT return "No answer provided" - the answers are there!"""

            # Make LLM call
            response = self._llm_engine.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,  # Low temperature for consistent mapping
                use_cache=True
            )

            # Parse response
            return self._parse_llm_mapping_response(response, max_questions, questions_data)

        except Exception as e:
            logger.error(f"LLM mapping failed: {e}")
            return None

    def _parse_llm_mapping_response(self, response: str, max_questions: int = None, questions_data=None) -> Optional[List[Dict]]:
        """Parse LLM mapping response and return structured mappings with correct max_scores."""
        try:
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                logger.error("No JSON found in LLM mapping response")
                return None
            
            try:
                mapping_data = json.loads(json_match.group())
            except json.JSONDecodeError:
                logger.error("Invalid JSON in LLM mapping response")
                return None
            
            mappings = mapping_data.get('mappings', [])
            if not mappings:
                logger.error("No mappings found in LLM response")
                return None
            
            # Process and validate mappings with correct max_scores
            processed_mappings = []
            mappings_to_process = mappings
            
            for i, mapping in enumerate(mappings_to_process):
                question_id = mapping.get('question_id', f'Q{i+1}')
                
                # Always use predefined max_score for consistency
                max_score = self._calculate_correct_max_score(question_id, questions_data)
                logger.info(f"Using predefined max_score for {question_id}: {max_score}")
                
                processed_mapping = {
                    'question_id': question_id,
                    'question_text': mapping.get('question_text', f'Question {i+1}'),
                    'student_answer': mapping.get('student_answer', ''),
                    'max_score': max_score,
                    'confidence': 0.9,  # High confidence for LLM mapping
                    'match_reason': 'LLM mapping'
                }
                processed_mappings.append(processed_mapping)
            
            return processed_mappings
            
        except Exception as e:
            logger.error(f"Error parsing LLM mapping response: {e}")
            return None
    
    def _extract_marks_from_criteria(self, criteria_text: str, sub_part: str) -> float:
        """Extract exact marks for a specific sub-part from criteria text."""
        try:
            if not criteria_text or not sub_part:
                return 0.0
            
            import re
            
            # Find the specific part section in the criteria
            part_section_pattern = rf"Part\s+{sub_part.lower()}:.*?(?=Part\s+[a-z]:|$)"
            part_section_match = re.search(part_section_pattern, criteria_text, re.IGNORECASE | re.DOTALL)
            
            if part_section_match:
                part_section = part_section_match.group(0)
                
                # Look for marks in this specific part section
                # Pattern 1: "1 mark", "2 marks", etc.
                mark_patterns = [
                    r"(\d+(?:\.\d+)?)\s*mark(?:s)?",
                    r"(\d+(?:\.\d+)?)\s*Mark(?:s)?",
                ]
                
                for pattern in mark_patterns:
                    matches = re.findall(pattern, part_section, re.IGNORECASE)
                    if matches:
                        # Take the first mark found in this part
                        marks = float(matches[0])
                        logger.info(f"Found marks for {sub_part}: {marks} from criteria section")
                        return marks
            
            # Fallback: Look for marks anywhere in the criteria for this part
            # Pattern: "Part a: ... (1 mark)" or "Part a: ... – 1 mark"
            fallback_pattern = rf"Part\s+{sub_part.lower()}.*?[–-]?\s*(\d+(?:\.\d+)?)\s*mark"
            fallback_match = re.search(fallback_pattern, criteria_text, re.IGNORECASE | re.DOTALL)
            if fallback_match:
                marks = float(fallback_match.group(1))
                logger.info(f"Found marks for {sub_part}: {marks} from fallback pattern")
                return marks
            
            logger.warning(f"No specific marks found for {sub_part} in criteria")
            return 0.0
            
        except Exception as e:
            logger.error(f"Error extracting marks for {sub_part} from criteria: {e}")
            return 0.0

    def _calculate_correct_max_score(self, question_id: str, questions_data: List[Dict]) -> float:
        """Calculate the correct max_score for a question based on the marking guide structure."""
        try:
            if not questions_data:
                logger.error(f"No questions_data provided for {question_id}")
                return 10.0  # Default fallback
            
            # Extract main question number from question_id (e.g., "Q1a" -> "1")
            main_question_num = question_id
            if question_id.startswith('Q'):
                main_question_num = question_id[1:]
            
            # Extract sub-part suffix (e.g., "1a" -> "a")
            sub_part_suffix = ""
            for suffix in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']:
                if main_question_num.endswith(suffix):
                    sub_part_suffix = suffix
                    main_question_num = main_question_num[:-1]
                    break
            
            # Find the corresponding guide question
            for question in questions_data:
                if isinstance(question, dict) and question.get('number') == main_question_num:
                    q_marks = question.get('marks', 0)
                    q_type = question.get('type', 'single')
                    sub_parts = question.get('sub_parts', [])
                    criteria = question.get('criteria', '')
                    
                    if q_marks == 0:
                        logger.warning(f"Question {main_question_num} has 0 marks in guide")
                        return 10.0
                    
                    if q_type == 'grouped' and sub_parts and sub_part_suffix:
                        # Try to extract specific marks from criteria for this sub-part
                        specific_marks = self._extract_marks_from_criteria(criteria, sub_part_suffix)
                        if specific_marks > 0:
                            logger.info(f"Question {question_id}: {specific_marks} marks (extracted from criteria for part {sub_part_suffix})")
                            return float(specific_marks)
                        else:
                            # Fallback: distribute marks evenly among sub-parts
                            marks_per_sub_part = q_marks / len(sub_parts) if sub_parts else q_marks
                            logger.warning(f"Question {question_id}: No specific marks found in criteria, using calculated: {marks_per_sub_part} marks")
                            return float(marks_per_sub_part)
                    else:
                        # For single questions
                        logger.info(f"Question {question_id}: {q_marks} marks (single question)")
                        return float(q_marks)
            
            # Question not found in guide
            logger.warning(f"Question {question_id} not found in guide questions, using default")
            return 10.0
            
        except Exception as e:
            logger.error(f"Error calculating max_score for {question_id}: {e}")
            return 10.0



    async def _grade_submission(
        self, guide: MarkingGuide, mappings: List[Dict]
    ) -> Optional[Dict]:
        """Grade the submission using LLM-based processing."""
        try:
            if not guide or not hasattr(guide, "id"):
                logger.error("Invalid guide object passed to _grade_submission")
                return None

            logger.info(
                f"Starting LLM grading for {len(mappings)} mapped answers"
            )

            # Use direct LLM grading service
            try:
                grading_result = await self._grade_with_llm(mappings, guide.content_text or "")
                
                if grading_result and grading_result.get("total_score") is not None:
                    logger.info("LLM grading completed successfully")
                    return grading_result
                else:
                    logger.error("LLM grading returned invalid result")
                    return None

            except Exception as e:
                logger.error(f"LLM grading failed: {e}")
                return None

        except Exception as e:
            logger.error(f"Error in _grade_submission: {str(e)}")
            return None

    async def _grade_with_llm(self, mappings: List[Dict], guide_content: str) -> Optional[Dict]:
        """Grade mappings using LLM service directly."""
        try:
            # Ensure LLM engine is available
            if not self._llm_engine:
                logger.warning("LLM engine not available, attempting to initialize...")
                if not self._initialize_llm_service():
                    logger.error("Failed to initialize LLM engine for grading")
                    return None

            # Prepare grading prompt
            questions_text = ""
            max_scores = {}
            
            for i, mapping in enumerate(mappings):
                q_text = mapping.get('question_text', f"Question {i+1}")
                a_text = mapping.get('student_answer', '')
                max_score = mapping.get('max_score', 10.0)
                question_id = mapping.get('question_id', f"Q{i+1}")
                
                max_scores[question_id] = max_score
                questions_text += f"\nQuestion {i+1} (ID: {question_id}): {q_text}\n"
                questions_text += f"Max Score: {max_score} points\n"
                questions_text += f"Student Answer: {a_text}\n"
                questions_text += "---\n"

            system_prompt = """You are an expert grader. Grade each student answer fairly and accurately.

Return ONLY valid JSON in this exact format:
{"grades":[{"id":"Q1a","score":1.5,"feedback":"Good understanding of the concept, but missing some details"}]}

GRADING GUIDELINES:
1. **Be Fair**: Award partial credit for partially correct answers
2. **Be Accurate**: Score based on what the student actually wrote
3. **Provide Feedback**: Give specific, constructive feedback
4. **Consider Context**: Student answers may use different terminology but show understanding
5. **Award Credit**: If a student demonstrates knowledge, give them credit

IMPORTANT: 
- Score can be 0 to max_score (inclusive)
- Give partial credit for partially correct answers
- Focus on understanding, not just exact wording
- Provide helpful feedback for improvement"""

            user_prompt = f"""Grade these answers based on the marking guide and question requirements:

{questions_text}

Marking Guide Context:
{guide_content}

Return JSON with grades for each question."""

            # Make LLM call
            response = self._llm_engine.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0,  # Deterministic grading
                use_cache=True
            )

            # Parse response and calculate results
            return self._parse_llm_grading_response(response, mappings, max_scores)

        except Exception as e:
            logger.error(f"LLM grading failed: {e}")
            return None

    def _parse_llm_grading_response(self, response: str, mappings: List[Dict], max_scores: Dict) -> Dict:
        """Parse LLM grading response and calculate final results."""
        try:
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                logger.error("No JSON found in LLM response")
                return self._create_fallback_grades(mappings, max_scores)
            
            try:
                grading_data = json.loads(json_match.group())
            except json.JSONDecodeError:
                logger.error("Invalid JSON in LLM response")
                return self._create_fallback_grades(mappings, max_scores)
            
            grades = grading_data.get('grades', [])
            if not grades:
                logger.error("No grades found in LLM response")
                return self._create_fallback_grades(mappings, max_scores)
            
            # Calculate totals
            total_score = 0
            total_possible = 0
            processed_grades = []
            
            for grade in grades:
                question_id = grade.get('id', '')
                score = float(grade.get('score', 0))
                max_score = max_scores.get(question_id)
                if max_score is None:
                    logger.error(f"No max_score found for question {question_id} in guide")
                    raise ValueError(f"Question {question_id} not found in guide max_scores")
                max_score = float(max_score)
                feedback = grade.get('feedback', 'No feedback provided')
                
                # Ensure score doesn't exceed max
                score = min(score, max_score)
                
                total_score += score
                total_possible += max_score
                
                processed_grades.append({
                    'question_id': question_id,
                    'score': score,
                    'max_score': max_score,
                    'feedback': feedback,
                    'percentage': (score / max_score * 100) if max_score > 0 else 0
                })
            
            # Calculate final percentage
            final_percentage = (total_score / total_possible * 100) if total_possible > 0 else 0
            
            return {
                'total_score': total_score,
                'total_possible': total_possible,
                'percentage': final_percentage,
                'grades': processed_grades,
                'summary': {
                    'total_questions': len(processed_grades),
                    'average_score': final_percentage,
                    'grading_method': 'LLM'
                }
            }
            
        except Exception as e:
            logger.error(f"Error parsing LLM grading response: {e}")
            return self._create_fallback_grades(mappings, max_scores)

    def _create_fallback_grades(self, mappings: List[Dict], max_scores: Dict) -> Dict:
        """Create basic grades when LLM parsing fails."""
        grades = []
        total_score = 0
        total_possible = 0
        
        for i, mapping in enumerate(mappings):
            question_id = mapping.get('question_id', f"Q{i+1}")
            max_score = max_scores.get(question_id)
            
            if max_score is None:
                logger.error(f"No max_score found for question {question_id} in guide")
                raise ValueError(f"Question {question_id} not found in guide - cannot create fallback grade")
            
            max_score = float(max_score)
            # Give partial credit when parsing fails
            score = max_score * 0.5
            
            grades.append({
                'question_id': question_id,
                'score': score,
                'max_score': max_score,
                'feedback': 'Grading failed - partial credit given',
                'percentage': 50.0
            })
            
            total_score += score
            total_possible += max_score
        
        return {
            'total_score': total_score,
            'total_possible': total_possible,
            'percentage': (total_score / total_possible * 100) if total_possible > 0 else 0,
            'grades': grades,
            'summary': {
                'total_questions': len(grades),
                'average_score': 50.0,
                'grading_method': 'Fallback'
            }
        }

    async def _save_results(
        self, request: ProcessingRequest, grading_result: Dict, mappings: List[Dict]
    ) -> Optional[str]:
        """Save processing results to database."""
        try:
            # Import Mapping at the top of the method to avoid variable scope issues
            from src.database.models import Mapping

            # Check for existing results and remove them to prevent duplicates
            # Use a more robust approach with explicit transaction control
            try:
                existing_results = GradingResult.query.filter_by(
                    submission_id=request.submission_id,
                    marking_guide_id=request.guide_id
                ).all()

                if existing_results:
                    logger.info(f"Removing {len(existing_results)} existing results for submission {request.submission_id} to prevent duplicates")
                    for existing_result in existing_results:
                        db.session.delete(existing_result)

                    # Also remove existing mappings for this submission
                    existing_mappings = Mapping.query.filter_by(
                        submission_id=request.submission_id
                    ).all()
                    for existing_mapping in existing_mappings:
                        db.session.delete(existing_mapping)

                    # Commit the deletions immediately
                    db.session.commit()
                    logger.info(f"Successfully removed existing results and mappings")

            except Exception as delete_error:
                logger.error(f"Error removing existing results: {delete_error}")
                db.session.rollback()
                # Continue with processing even if deletion fails

            # Save mappings and create individual grading results
            import uuid

            # Get detailed grades from grading result
            detailed_grades = grading_result.get("grades", [])

            # Calculate totals from individual mappings
            total_score = 0.0
            total_max_score = 0.0

            for i, mapping_data in enumerate(mappings):
                # Generate truly unique ID
                unique_id = f"mapping_{uuid.uuid4().hex[:8]}_{int(time.time())}_{i}"

                # Get max score from mapping data
                mapping_max_score = mapping_data.get("max_score")
                if mapping_max_score is None:
                    logger.error(f"No max_score found for mapping {i}")
                    raise ValueError(f"Mapping {i} has no max_score - cannot process result")

                # Get individual score from detailed grades
                individual_score = 0.0
                if i < len(detailed_grades):
                    individual_score = detailed_grades[i].get("score", 0.0)

                # Create mapping record
                mapping_record = Mapping(
                    id=unique_id,
                    submission_id=request.submission_id,
                    guide_question_id=mapping_data.get("question_id", f"Q{i+1}"),
                    guide_question_text=mapping_data.get("question_text", ""),
                    guide_answer=mapping_data.get("guide_answer", ""),
                    max_score=float(mapping_max_score),
                    submission_answer=mapping_data.get(
                        "student_answer", mapping_data.get("answer_text", "")
                    ),
                    match_score=mapping_data.get("confidence", 0.0),
                    match_reason=mapping_data.get("match_reason", "LLM mapping"),
                    mapping_method="llm",
                )
                db.session.add(mapping_record)

                # Don't create individual results - only create mappings
                # Individual results will be created as one summary result below

                # Add to totals
                total_score += individual_score
                total_max_score += mapping_max_score

            # Create ONE summary result instead of multiple individual results
            overall_percentage = (total_score / total_max_score * 100) if total_max_score > 0 else 0

            # Generate unique ID to prevent duplicates
            unique_result_id = f"result_{uuid.uuid4().hex[:12]}_{request.submission_id}"

            summary_result = GradingResult(
                id=unique_result_id,
                submission_id=request.submission_id,
                marking_guide_id=request.guide_id,
                mapping_id=None,  # This is a summary, not linked to specific mapping
                score=total_score,
                max_score=total_max_score,
                percentage=overall_percentage,
                feedback=grading_result.get("feedback", ""),
                detailed_feedback=grading_result,
                grading_method="llm",
            )
            db.session.add(summary_result)
            db.session.commit()

            return summary_result.id

        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            db.session.rollback()
            return None

    def _validate_request(self, request: ProcessingRequest) -> bool:
        """Validate processing request."""
        return request.guide_id and request.submission_id and request.user_id

    def initialize(self) -> bool:
        """Initialize the service with enhanced error handling."""
        try:
            logger.info("Initializing CoreService...")
            success = self._initialize_engines()
            self._initialized = success

            if success:
                logger.info("CoreService initialization completed successfully")
            else:
                logger.warning(
                    "CoreService initialization completed with some failures"
                )

            return success
        except Exception as e:
            logger.error(f"Failed to initialize core service: {e}")
            self._initialized = False
            self.metrics.status = ServiceStatus.UNHEALTHY
            return False

    def health_check(self) -> bool:
        """Perform comprehensive health check."""
        try:
            if not self._initialized:
                return False

            # Perform health checks on all registered services
            self._perform_health_checks()

            # Count healthy services
            healthy_services = sum(
                1
                for health in self._service_health.values()
                if health["status"] in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]
            )
            total_services = len(self._service_health)

            is_healthy = (
                healthy_services >= total_services * 0.5
                if total_services > 0
                else False
            )

            # Update overall status
            if healthy_services == total_services:
                self.metrics.status = ServiceStatus.HEALTHY
            elif is_healthy:
                self.metrics.status = ServiceStatus.DEGRADED
            else:
                self.metrics.status = ServiceStatus.UNHEALTHY

            return is_healthy

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.metrics.status = ServiceStatus.UNHEALTHY
            return False

    def cleanup(self) -> None:
        """Clean up service resources."""
        try:
            logger.info("Cleaning up CoreService resources...")

            # Clear processing cache
            if hasattr(self, "_processing_cache"):
                self._processing_cache.clear()

            # Cleanup registered services
            for name, service in self._service_registry.items():
                try:
                    if hasattr(service, "cleanup"):
                        service.cleanup()
                    logger.debug(f"Cleaned up service: {name}")
                except Exception as e:
                    logger.warning(f"Error cleaning up service {name}: {e}")

            # Clear registries
            self._service_registry.clear()
            self._service_health.clear()
            self._initialization_status.clear()
            self._dependency_errors.clear()

            self._initialized = False
            logger.info("CoreService cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during core service cleanup: {e}")

    def get_service_initialization_status(self) -> Dict[str, Any]:
        """Get detailed service initialization status."""
        return {
            "core_service_initialized": self._initialized,
            "initialization_timestamp": datetime.now(timezone.utc).isoformat(),
            "services": self._initialization_status.copy(),
            "dependency_errors": self._dependency_errors.copy(),
            "service_health": {
                name: {
                    "status": health["status"].value,
                    "last_check": health["last_check"],
                    "error_count": health["error_count"],
                }
                for name, health in self._service_health.items()
            },
            "overall_status": self.metrics.status.value,
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive service health status."""
        return {
            "service": self.service_name,
            "status": self.metrics.status.value,
            "initialized": self._initialized,
            "engines": {
                "ocr": self._ocr_engine is not None,
                "llm": self._llm_engine is not None,
                "mapping": self._mapping_service is not None,
                "grading": self._grading_service is not None,
            },
            "service_health": self.get_service_health(),
            "cache_size": len(self._processing_cache),
            "dependency_errors": len(self._dependency_errors),
            "last_check": datetime.now(timezone.utc).isoformat(),
            "metrics": self.metrics.to_dict(),
        }

    def handle_missing_service_dependency(
        self, service_name: str, dependency_name: str
    ) -> bool:
        """Handle missing service dependencies gracefully."""
        error_msg = f"Service {service_name} missing dependency: {dependency_name}"
        logger.warning(error_msg)

        # Add to dependency errors
        if error_msg not in self._dependency_errors:
            self._dependency_errors.append(error_msg)

        if service_name in self._service_health:
            if self._service_health[service_name]["status"] == ServiceStatus.HEALTHY:
                self._service_health[service_name]["status"] = ServiceStatus.DEGRADED
                self._service_health[service_name]["error_count"] += 1

        # Try to continue with reduced functionality
        return True  # Return True to indicate we can continue with degraded service

    def get_available_services(self) -> List[str]:
        """Get list of available (successfully initialized) services."""
        return [
            name
            for name, status in self._initialization_status.items()
            if status["success"]
        ]

    def is_service_available(self, service_name: str) -> bool:
        """Check if a specific service is available."""
        return (
            service_name in self._initialization_status
            and self._initialization_status[service_name]["success"]
        )

    def restart_failed_services(self) -> Dict[str, bool]:
        """Attempt to restart failed services."""
        logger.info("Attempting to restart failed services...")
        restart_results = {}

        # Get list of failed services
        failed_services = [
            name
            for name, status in self._initialization_status.items()
            if not status["success"]
        ]

        # Attempt to restart each failed service
        service_init_map = {
            "ocr": self._initialize_ocr_service,
            "llm": self._initialize_llm_service,
            "mapping": self._initialize_mapping_service,
            "grading": self._initialize_grading_service,
        }

        for service_name in failed_services:
            if service_name in service_init_map:
                try:
                    logger.info(f"Restarting {service_name} service...")
                    success = service_init_map[service_name]()
                    restart_results[service_name] = success

                    # Update initialization status
                    self._initialization_status[service_name] = {
                        "success": success,
                        "timestamp": datetime.now(timezone.utc),
                        "error": None if success else f"Restart failed",
                    }

                    if success:
                        logger.info(f"✓ {service_name} service restarted successfully")
                    else:
                        logger.warning(f"✗ {service_name} service restart failed")

                except Exception as e:
                    error_msg = f"Error restarting {service_name}: {str(e)}"
                    logger.error(error_msg)
                    restart_results[service_name] = False
                    self._initialization_status[service_name]["error"] = error_msg

        # Update overall service status
        self.health_check()

        return restart_results

# Global service instance
core_service = CoreService()
