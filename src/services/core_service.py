"""
Core Service Layer - Unified Service Architecture

This module provides the single, unified service layer that consolidates all
AI processing functionality into a clean, maintainable architecture.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.config.processing_config import ProcessingConfigManager
from src.database.models import GradingResult, Mapping, MarkingGuide, Submission, db
from src.services.base_service import BaseService, ServiceStatus
from src.services.enhanced_logging_service import (
    LogCategory,
    enhanced_logging_service,
    log_operation,
)
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
        self._ultra_fast_processor = None
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
                ("ultra_fast", self._initialize_ultra_fast_service),
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

            self._llm_engine = ConsolidatedLLMService()
            self._register_service("llm", self._llm_engine)
            return True
        except ImportError as e:
            logger.warning(f"LLM service not available: {e}")
            self._llm_engine = None
            return False
        except Exception as e:
            logger.error(f"LLM service initialization failed: {e}")
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

    def _initialize_ultra_fast_service(self) -> bool:
        """Initialize ultra-fast processing service."""
        try:
            from src.services.ultra_fast_processing import get_ultra_fast_processor

            self._ultra_fast_processor = get_ultra_fast_processor()
            self._register_service("ultra_fast", self._ultra_fast_processor)
            return True
        except ImportError as e:
            logger.info(f"Ultra-fast processing not available: {e}")
            self._ultra_fast_processor = None
            return False
        except Exception as e:
            logger.warning(f"Ultra-fast processing initialization failed: {e}")
            self._ultra_fast_processor = None
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
            "core_service": self.status.value,
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
            mappings = await self._map_answers(guide, submission_text)
            if not mappings:
                return ProcessingResponse(
                    success=False, error="Failed to map answers to questions"
                )

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
            return ProcessingResponse(
                success=False, error=str(e), processing_time=time.time() - start_time
            )

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

            if result.success and result.data and result.data.get("success"):
                extracted_text = result.data.get("text", "")

                # Update submission with extracted text
                submission.content_text = extracted_text
                db.session.commit()

                logger.info(
                    f"OCR extraction successful for {submission.id} ({len(extracted_text)} chars)"
                )
                return extracted_text
            else:
                logger.warning(
                    f"OCR extraction failed for {submission.id}: {result.error_message}"
                )

        logger.warning(f"No text content available for submission {submission.id}")
        return None

    async def _map_answers(
        self, guide: MarkingGuide, submission_text: str
    ) -> Optional[List[Dict]]:
        """Map submission answers to guide questions using ultra-fast processing."""
        try:
            if not guide or not hasattr(guide, "id"):
                logger.error("Invalid guide object passed to _map_answers")
                return None

            guide_content = guide.content_text or ""

            logger.info(f"Starting ultra-fast mapping for guide {guide.id}")

            # Try ultra-fast processing first
            try:
                from src.services.ultra_fast_processing import get_ultra_fast_processor

                processor = get_ultra_fast_processor()

                questions_data = guide.questions if guide.questions else None
                max_questions = min(10, len(questions_data) if questions_data else 5)

                mappings = processor.mapper.ultra_fast_map(
                    guide_content,
                    submission_text,
                    max_questions=max_questions,
                    questions_data=questions_data,
                )

                if mappings:
                    logger.info(f"Ultra-fast mapping returned {len(mappings)} mappings")
                    return mappings

            except Exception as e:
                logger.warning(f"Ultra-fast mapping failed, using fallback: {e}")

            # Fallback to original mapping service
            if hasattr(self, "_mapping_service") and self._mapping_service:
                try:
                    mapping_result, error = (
                        self._mapping_service.map_submission_to_guide(
                            guide_content, submission_text, 5  # Limit to 5 for speed
                        )
                    )

                    if mapping_result and mapping_result.get("mappings"):
                        logger.info(
                            f"Fallback mapping service returned {len(mapping_result['mappings'])} mappings"
                        )
                        return mapping_result["mappings"]

                except Exception as e:
                    logger.error(f"Fallback mapping service error: {e}")

            # Final fallback
            logger.info("Using simple fallback mapping")
            return self._simple_answer_mapping(guide.questions or [], submission_text)

        except Exception as e:
            logger.error(f"Answer mapping failed: {e}")
            return None

    def _simple_answer_mapping(self, questions: List[Dict], text: str) -> List[Dict]:
        """Simple fallback answer mapping."""
        mappings = []

        for i, question in enumerate(questions):
            question_text = question.get("question", "")

            # Simple keyword-based matching
            # This is a basic implementation - in practice, you'd want more sophisticated matching
            mapping = {
                "question_number": i + 1,
                "question_text": question_text,
                "student_answer": text[:500],  # First 500 chars as fallback
                "confidence": 0.5,  # Low confidence for fallback method
            }
            mappings.append(mapping)

        return mappings

    async def _grade_submission(
        self, guide: MarkingGuide, mappings: List[Dict]
    ) -> Optional[Dict]:
        """Grade the submission using ultra-fast AI processing."""
        try:
            if not guide or not hasattr(guide, "id"):
                logger.error("Invalid guide object passed to _grade_submission")
                return None

            logger.info(
                f"Starting ultra-fast grading for {len(mappings)} mapped answers"
            )

            # Try ultra-fast grading first
            try:
                from src.services.ultra_fast_processing import get_ultra_fast_processor

                processor = get_ultra_fast_processor()

                grading_result = processor.grader.ultra_fast_grade(
                    mappings, guide.content_text or ""
                )

                if grading_result and grading_result.get("total_score") is not None:
                    logger.info("Ultra-fast grading completed successfully")
                    return grading_result

            except Exception as e:
                logger.warning(f"Ultra-fast grading failed, using fallback: {e}")

            # Fallback to original grading service
            if hasattr(self, "_grading_service") and self._grading_service:
                try:
                    logger.info("Using fallback grading service")

                    submission_content = "\n\n".join(
                        [
                            f"Question {mapping.get('question_number', i+1)}: {mapping.get('question_text', '')}\n"
                            f"Answer: {mapping.get('student_answer', '')}"
                            for i, mapping in enumerate(mappings)
                        ]
                    )

                    # Use the grading service with timeout
                    grading_result = self._grading_service.grade_submission_optimized(
                        submission_content=submission_content,
                        marking_guide=guide.content_text or "",
                        mapped_data={"mappings": mappings},
                    )

                    if grading_result and grading_result.get("total_score") is not None:
                        logger.info("Fallback grading service completed successfully")
                        return grading_result

                except Exception as e:
                    logger.error(f"Fallback grading service error: {e}")

            # Final fallback
            logger.info("Using simple fallback grading")
            return self._fallback_grading(guide, mappings)

        except Exception as e:
            logger.error(f"Grading failed: {e}")
            return self._fallback_grading(guide, mappings)

    def _fallback_grading(self, guide: MarkingGuide, mappings: List[Dict]) -> Dict:
        """Fallback grading when LLM is not available."""
        total_questions = len(mappings)
        total_marks = guide.total_marks or 100

        # Simple fallback: give partial credit based on answer length
        total_score = 0
        question_results = []

        for mapping in mappings:
            answer = mapping.get("student_answer", "")
            question_marks = total_marks / total_questions if total_questions > 0 else 0

            # Simple scoring: longer answers get more points (up to 80% max)
            answer_length = len(answer.strip())
            if answer_length > 100:
                score = question_marks * 0.8
            elif answer_length > 50:
                score = question_marks * 0.6
            elif answer_length > 20:
                score = question_marks * 0.4
            else:
                score = question_marks * 0.2

            total_score += score
            question_results.append(
                {
                    "question_number": mapping.get("question_number", 0),
                    "marks_awarded": score,
                    "max_marks": question_marks,
                    "feedback": f"Answer provided ({answer_length} characters)",
                }
            )

        return {
            "total_score": total_score,
            "max_score": total_marks,
            "feedback": f"Graded {total_questions} questions using fallback scoring",
            "question_results": question_results,
            "grading_method": "fallback",
        }

    async def _save_results(
        self, request: ProcessingRequest, grading_result: Dict, mappings: List[Dict]
    ) -> Optional[str]:
        """Save processing results to database."""
        try:
            # Import Mapping at the top of the method to avoid variable scope issues
            from src.database.models import Mapping
            
            # Check for existing results and remove them to prevent duplicates
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
                
                db.session.flush()  # Flush to ensure deletions are processed

            # Create grading result record
            total_score = grading_result.get("total_score", 0)
            max_score = grading_result.get("max_score", 100)
            percentage = (total_score / max_score * 100) if max_score > 0 else 0

            result = GradingResult(
                id=f"result_{int(time.time())}_{request.submission_id}",
                submission_id=request.submission_id,
                marking_guide_id=request.guide_id,
                score=total_score,
                max_score=max_score,
                percentage=percentage,
                feedback=grading_result.get("feedback", ""),
                detailed_feedback=grading_result,
                grading_method="llm",
            )

            # Save mappings with unique IDs
            import uuid

            for i, mapping_data in enumerate(mappings):
                # Generate truly unique ID
                unique_id = f"mapping_{uuid.uuid4().hex[:8]}_{int(time.time())}_{i}"

                mapping_record = Mapping(
                    id=unique_id,
                    submission_id=request.submission_id,
                    guide_question_id=mapping_data.get("question_id", f"Q{i+1}"),
                    guide_question_text=mapping_data.get("question_text", ""),
                    guide_answer=mapping_data.get("guide_answer", ""),
                    max_score=mapping_data.get("max_score", 10.0),
                    submission_answer=mapping_data.get(
                        "student_answer", mapping_data.get("answer_text", "")
                    ),
                    match_score=mapping_data.get("confidence", 0.0),
                    match_reason=mapping_data.get("match_reason", "LLM mapping"),
                    mapping_method="llm",
                )
                db.session.add(mapping_record)

            db.session.add(result)
            db.session.commit()

            return result.id

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
                "ultra_fast": self._ultra_fast_processor is not None,
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
            "ultra_fast": self._initialize_ultra_fast_service,
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
