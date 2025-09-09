"""
Unified API Endpoints

This module provides unified API endpoints with standardized error handling,
request tracking, and performance monitoring for all processing operations.
"""

import time
from datetime import datetime, timezone
import asyncio
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from src.database.models import GradingResult, MarkingGuide, Submission, db
from src.services.core_service import ProcessingRequest, core_service
from src.services.file_processing_service import FileProcessingService
from src.services.monitoring.monitoring_service import track_operation
from utils.logger import logger

from .error_handlers import api_error_handler

unified_api_bp = Blueprint("unified_api", __name__, url_prefix="/api/v1")

def validate_request_data(
    data: Dict[str, Any], required_fields: list
) -> Optional[Dict[str, Any]]:
    """Validate request data and return validation errors if any"""
    errors = {}

    for field in required_fields:
        if field not in data:
            errors[field] = f"Field '{field}' is required"
        elif not data[field]:
            errors[field] = f"Field '{field}' cannot be empty"

    return errors if errors else None

@unified_api_bp.route("/process/single", methods=["POST"])
@login_required
def process_single_submission():
    """Process a single submission with comprehensive error handling and tracking"""
    request_id = f"proc_single_{int(time.time() * 1000)}"

    try:
        with track_operation("api_process_single", metadata={"request_id": request_id}):
            # Validate request data
            data = request.get_json()
            if not data:
                response, status = api_error_handler.create_error_response(
                    error=ValueError("No JSON data provided"),
                    status_code=400,
                    message="Request body must contain JSON data",
                    request_id=request_id,
                )
                return jsonify(response), status

            # Validate required fields
            validation_errors = validate_request_data(
                data, ["guide_id", "submission_id"]
            )
            if validation_errors:
                response, status = api_error_handler.handle_validation_error(
                    validation_errors, request_id
                )
                return jsonify(response), status

            guide_id = data["guide_id"]
            submission_id = data["submission_id"]
            options = data.get("options", {})

            # Verify resource ownership and existence
            guide = MarkingGuide.query.filter_by(
                id=guide_id, user_id=current_user.id
            ).first()

            if not guide:
                response, status = api_error_handler.handle_not_found_error(
                    resource="Marking guide", request_id=request_id
                )
                return jsonify(response), status

            submission = Submission.query.filter_by(
                id=submission_id, user_id=current_user.id
            ).first()

            if not submission:
                response, status = api_error_handler.handle_not_found_error(
                    resource="Submission", request_id=request_id
                )
                return jsonify(response), status

            # Update submission status
            submission.processing_status = "processing"
            submission.updated_at = datetime.now(timezone.utc)
            db.session.commit()

            # Create processing request
            processing_request = ProcessingRequest(
                guide_id=guide_id,
                submission_id=submission_id,
                user_id=current_user.id,
                options=options,
                request_id=request_id,
            )

            # Process submission with error handling
            try:
                result = asyncio.run(
                    core_service.process_submission(processing_request)
                )

                # Update submission status based on result
                if result.success:
                    submission.processing_status = "completed"
                    submission.processing_error = None
                else:
                    submission.processing_status = "failed"
                    submission.processing_error = result.error

                submission.updated_at = datetime.now(timezone.utc)
                db.session.commit()

                # Prepare response data
                response_data = {
                    "processing": {
                        "request_id": request_id,
                        "guide_id": guide_id,
                        "submission_id": submission_id,
                        "status": "completed" if result.success else "failed",
                        "processing_time_ms": getattr(result, "processing_time_ms", 0),
                    },
                    "result": {
                        "success": result.success,
                        "result_id": result.result_id if result.success else None,
                        "score": result.score if result.success else None,
                        "max_score": getattr(result, "max_score", None),
                        "percentage": getattr(result, "percentage", None),
                        "feedback": getattr(result, "feedback", None),
                        "detailed_results": getattr(result, "detailed_results", None),
                    },
                    "error": (
                        {
                            "message": result.error if not result.success else None,
                            "code": getattr(result, "error_code", None),
                            "details": getattr(result, "error_details", None),
                        }
                        if not result.success
                        else None
                    ),
                }

                if result.success:
                    response = api_error_handler.create_success_response(
                        data=response_data,
                        message="Submission processed successfully",
                        request_id=request_id,
                    )
                    return jsonify(response), 200
                else:
                    response, status = api_error_handler.create_error_response(
                        error=Exception(result.error),
                        status_code=422,
                        message="Processing failed",
                        details=response_data,
                        request_id=request_id,
                    )
                    return jsonify(response), status

            except Exception as processing_error:
                # Handle processing errors
                submission.processing_status = "failed"
                submission.processing_error = str(processing_error)
                submission.updated_at = datetime.now(timezone.utc)
                db.session.commit()

                response, status = api_error_handler.create_error_response(
                    error=processing_error,
                    status_code=500,
                    message="Processing failed due to internal error",
                    request_id=request_id,
                )
                return jsonify(response), status

    except Exception as e:
        logger.error(f"API error in process_single_submission: {e}")
        response, status = api_error_handler.create_error_response(
            error=e,
            status_code=500,
            message="API request failed",
            request_id=request_id,
        )
        return jsonify(response), status

@unified_api_bp.route("/process/batch", methods=["POST"])
@login_required
def process_batch_submissions():
    """Process multiple submissions in batch with progress tracking"""
    request_id = f"proc_batch_{int(time.time() * 1000)}"

    try:
        with track_operation("api_process_batch", metadata={"request_id": request_id}):
            # Validate request data
            data = request.get_json()
            if not data:
                response, status = api_error_handler.create_error_response(
                    error=ValueError("No JSON data provided"),
                    status_code=400,
                    message="Request body must contain JSON data",
                    request_id=request_id,
                )
                return jsonify(response), status

            # Validate required fields
            validation_errors = validate_request_data(
                data, ["guide_id", "submission_ids"]
            )
            if validation_errors:
                response, status = api_error_handler.handle_validation_error(
                    validation_errors, request_id
                )
                return jsonify(response), status

            guide_id = data["guide_id"]
            submission_ids = data["submission_ids"]
            options = data.get("options", {})

            if not isinstance(submission_ids, list) or not submission_ids:
                response, status = api_error_handler.handle_validation_error(
                    {"submission_ids": "Must be a non-empty list"}, request_id
                )
                return jsonify(response), status

            # Verify guide ownership
            guide = MarkingGuide.query.filter_by(
                id=guide_id, user_id=current_user.id
            ).first()

            if not guide:
                response, status = api_error_handler.handle_not_found_error(
                    resource="Marking guide", request_id=request_id
                )
                return jsonify(response), status

            # Process each submission
            results = []
            successful_count = 0
            failed_count = 0

            for i, submission_id in enumerate(submission_ids):
                try:
                    # Verify submission ownership
                    submission = Submission.query.filter_by(
                        id=submission_id, user_id=current_user.id
                    ).first()

                    if not submission:
                        results.append(
                            {
                                "submission_id": submission_id,
                                "success": False,
                                "error": "Submission not found or access denied",
                                "index": i,
                            }
                        )
                        failed_count += 1
                        continue

                    # Update submission status
                    submission.processing_status = "processing"
                    submission.updated_at = datetime.now(timezone.utc)
                    db.session.commit()

                    # Create processing request
                    processing_request = ProcessingRequest(
                        guide_id=guide_id,
                        submission_id=submission_id,
                        user_id=current_user.id,
                        options=options,
                        request_id=f"{request_id}_sub_{i}",
                    )

                    # Process submission
                    result = asyncio.run(
                        core_service.process_submission(processing_request)
                    )

                    # Update submission status
                    if result.success:
                        submission.processing_status = "completed"
                        submission.processing_error = None
                        successful_count += 1
                    else:
                        submission.processing_status = "failed"
                        submission.processing_error = result.error
                        failed_count += 1

                    submission.updated_at = datetime.now(timezone.utc)
                    db.session.commit()

                    # Add result
                    results.append(
                        {
                            "submission_id": submission_id,
                            "success": result.success,
                            "result_id": result.result_id if result.success else None,
                            "score": result.score if result.success else None,
                            "error": result.error if not result.success else None,
                            "index": i,
                        }
                    )

                except Exception as sub_error:
                    logger.error(
                        f"Error processing submission {submission_id}: {sub_error}"
                    )

                    # Update submission status
                    try:
                        submission = Submission.query.filter_by(
                            id=submission_id, user_id=current_user.id
                        ).first()
                        if submission:
                            submission.processing_status = "failed"
                            submission.processing_error = str(sub_error)
                            submission.updated_at = datetime.now(timezone.utc)
                            db.session.commit()
                    except:
                        pass

                    results.append(
                        {
                            "submission_id": submission_id,
                            "success": False,
                            "error": str(sub_error),
                            "index": i,
                        }
                    )
                    failed_count += 1

            # Prepare batch response
            batch_data = {
                "batch": {
                    "request_id": request_id,
                    "guide_id": guide_id,
                    "total_submissions": len(submission_ids),
                    "successful_count": successful_count,
                    "failed_count": failed_count,
                    "success_rate": (
                        successful_count / len(submission_ids) if submission_ids else 0
                    ),
                },
                "results": results,
                "summary": {
                    "completed": successful_count,
                    "failed": failed_count,
                    "total": len(submission_ids),
                },
            }

            response = api_error_handler.create_success_response(
                data=batch_data,
                message=f"Batch processing completed: {successful_count} successful, {failed_count} failed",
                request_id=request_id,
            )

            return jsonify(response), 200

    except Exception as e:
        logger.error(f"API error in process_batch_submissions: {e}")
        response, status = api_error_handler.create_error_response(
            error=e,
            status_code=500,
            message="Batch processing failed",
            request_id=request_id,
        )
        return jsonify(response), status

@unified_api_bp.route("/submissions/<int:submission_id>/status", methods=["GET"])
@login_required
def get_submission_status(submission_id):
    """Get detailed status of a submission"""
    request_id = f"sub_status_{int(time.time() * 1000)}"

    try:
        with track_operation(
            "api_submission_status", metadata={"request_id": request_id}
        ):
            # Verify submission ownership
            submission = Submission.query.filter_by(
                id=submission_id, user_id=current_user.id
            ).first()

            if not submission:
                response, status = api_error_handler.handle_not_found_error(
                    resource="Submission", request_id=request_id
                )
                return jsonify(response), status

            # Get latest grading result
            latest_result = (
                GradingResult.query.filter_by(submission_id=submission_id)
                .order_by(GradingResult.created_at.desc())
                .first()
            )

            # Get marking guide
            guide = MarkingGuide.query.filter_by(id=submission.marking_guide_id).first()

            # Prepare status data
            status_data = {
                "submission": {
                    "id": submission.id,
                    "filename": submission.filename,
                    "student_name": submission.student_name,
                    "processing_status": submission.processing_status,
                    "processing_error": submission.processing_error,
                    "file_size": submission.file_size,
                    "file_type": submission.file_type,
                    "created_at": (
                        submission.created_at.isoformat()
                        if submission.created_at
                        else None
                    ),
                    "updated_at": (
                        submission.updated_at.isoformat()
                        if submission.updated_at
                        else None
                    ),
                },
                "guide": (
                    {
                        "id": guide.id if guide else None,
                        "title": guide.title if guide else None,
                        "total_marks": guide.total_marks if guide else None,
                    }
                    if guide
                    else None
                ),
                "latest_result": (
                    {
                        "id": latest_result.id,
                        "score": latest_result.total_score,
                        "max_score": latest_result.max_score,
                        "percentage": (
                            (latest_result.total_score / latest_result.max_score * 100)
                            if latest_result.max_score > 0
                            else 0
                        ),
                        "feedback": latest_result.feedback,
                        "detailed_results": latest_result.detailed_results,
                        "created_at": latest_result.created_at.isoformat(),
                        "processing_metadata": latest_result.processing_metadata,
                    }
                    if latest_result
                    else None
                ),
            }

            response = api_error_handler.create_success_response(
                data=status_data,
                message="Submission status retrieved",
                request_id=request_id,
            )

            return jsonify(response), 200

    except Exception as e:
        logger.error(f"API error in get_submission_status: {e}")
        response, status = api_error_handler.create_error_response(
            error=e,
            status_code=500,
            message="Failed to retrieve submission status",
            request_id=request_id,
        )
        return jsonify(response), status

@unified_api_bp.route("/results/<int:result_id>", methods=["GET"])
@login_required
def get_result_details(result_id):
    """Get detailed grading result information"""
    request_id = f"result_{int(time.time() * 1000)}"

    try:
        with track_operation("api_result_details", metadata={"request_id": request_id}):
            # Get result with ownership verification
            result = (
                GradingResult.query.join(Submission)
                .filter(
                    GradingResult.id == result_id, Submission.user_id == current_user.id
                )
                .first()
            )

            if not result:
                response, status = api_error_handler.handle_not_found_error(
                    resource="Grading result", request_id=request_id
                )
                return jsonify(response), status

            # Get related records
            submission = Submission.query.get(result.submission_id)
            guide = MarkingGuide.query.get(result.marking_guide_id)

            # Prepare detailed result data
            result_data = {
                "result": {
                    "id": result.id,
                    "total_score": result.total_score,
                    "max_score": result.max_score,
                    "percentage": (
                        (result.total_score / result.max_score * 100)
                        if result.max_score > 0
                        else 0
                    ),
                    "feedback": result.feedback,
                    "detailed_results": result.detailed_results,
                    "processing_metadata": result.processing_metadata,
                    "created_at": result.created_at.isoformat(),
                    "updated_at": (
                        result.updated_at.isoformat() if result.updated_at else None
                    ),
                },
                "submission": (
                    {
                        "id": submission.id,
                        "filename": submission.filename,
                        "student_name": submission.student_name,
                        "file_type": submission.file_type,
                        "file_size": submission.file_size,
                    }
                    if submission
                    else None
                ),
                "guide": (
                    {
                        "id": guide.id,
                        "title": guide.title,
                        "description": guide.description,
                        "total_marks": guide.total_marks,
                        "questions": guide.questions,
                    }
                    if guide
                    else None
                ),
            }

            response = api_error_handler.create_success_response(
                data=result_data,
                message="Result details retrieved",
                request_id=request_id,
            )

            return jsonify(response), 200

    except Exception as e:
        logger.error(f"API error in get_result_details: {e}")
        response, status = api_error_handler.create_error_response(
            error=e,
            status_code=500,
            message="Failed to retrieve result details",
            request_id=request_id,
        )
        return jsonify(response), status

@unified_api_bp.route("/system/info", methods=["GET"])
def system_info():
    """Get system information and capabilities"""
    request_id = f"sys_info_{int(time.time() * 1000)}"

    try:
        with track_operation("api_system_info", metadata={"request_id": request_id}):
            # Get system capabilities
            file_service = FileProcessingService()

            system_data = {
                "api": {
                    "version": "1.0",
                    "endpoints": [
                        "/api/v1/process/single",
                        "/api/v1/process/batch",
                        "/api/v1/submissions/<id>/status",
                        "/api/v1/results/<id>",
                        "/api/v1/system/info",
                    ],
                },
                "capabilities": {
                    "supported_file_types": file_service.get_supported_formats(),
                    "max_file_size_mb": 100,
                    "batch_processing": True,
                    "real_time_status": True,
                    "detailed_feedback": True,
                },
                "services": {
                    "llm_service": "available",
                    "file_processing": "available",
                    "ocr_processing": "available",
                    "caching": "available",
                    "monitoring": "available",
                },
                "limits": {
                    "max_batch_size": 100,
                    "rate_limit_per_minute": 60,
                    "concurrent_processing": 5,
                },
            }

            response = api_error_handler.create_success_response(
                data=system_data,
                message="System information retrieved",
                request_id=request_id,
            )

            return jsonify(response), 200

    except Exception as e:
        logger.error(f"API error in system_info: {e}")
        response, status = api_error_handler.create_error_response(
            error=e,
            status_code=500,
            message="Failed to retrieve system information",
            request_id=request_id,
        )
        return jsonify(response), status
