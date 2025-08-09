"""
Processing Routes

This module handles AI processing operations including OCR, grading,
and result generation.
"""

import asyncio
import time

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from src.database.models import GradingResult, MarkingGuide, Submission, db
from src.services.core_service import ProcessingRequest, core_service
from src.services.enhanced_result_service import enhanced_result_service
from utils.logger import logger

processing_bp = Blueprint("processing", __name__, url_prefix="/processing")


@processing_bp.route("/")
@processing_bp.route("")
@login_required
def processing_page():
    """Main processing page with progress tracking."""
    progress_id = request.args.get("progress_id")

    if progress_id:
        # Render processing page with progress tracking
        return render_template("processing.html", progress_id=progress_id)
    else:
        # No progress ID, redirect to unified processing
        return redirect(url_for("processing.unified_processing"))


@processing_bp.route("/unified")
@login_required
def unified_processing():
    """Unified processing interface."""
    progress_id = request.args.get("progress_id")

    if progress_id:
        # This is a progress tracking request - render the progress page
        guides = MarkingGuide.query.filter_by(user_id=current_user.id).all()
        submissions = Submission.query.filter_by(user_id=current_user.id).all()

        return render_template(
            "unified_processing.html",
            guides=guides,
            submissions=submissions,
            progress_id=progress_id,
            allowed_types=[
                ".pdf",
                ".docx",
                ".doc",
                ".txt",
                ".jpg",
                ".jpeg",
                ".png",
                ".bmp",
                ".tiff",
                ".gif",
            ],
            max_file_size=100 * 1024 * 1024,
        )
    else:
        # No progress_id - show enhanced processing interface
        guides = MarkingGuide.query.filter_by(user_id=current_user.id).all()
        submissions = Submission.query.filter_by(user_id=current_user.id).all()

        return render_template(
            "enhanced_processing.html",
            guides=guides,
            submissions=submissions,
            allowed_types=[
                ".pdf",
                ".docx",
                ".doc",
                ".txt",
                ".jpg",
                ".jpeg",
                ".png",
                ".bmp",
                ".tiff",
                ".gif",
            ],
            max_file_size=100 * 1024 * 1024,
        )


@processing_bp.route("/api/process", methods=["POST"])
@login_required
def api_process_single():
    """Process single submission with marking guide (legacy endpoint)."""
    try:
        data = request.get_json()

        guide_id = data.get("guide_id")
        submission_id = data.get("submission_id")

        if not guide_id or not submission_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Both guide_id and submission_id are required",
                    }
                ),
                400,
            )

        # Verify ownership
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()
        submission = Submission.query.filter_by(
            id=submission_id, user_id=current_user.id
        ).first()

        if not guide or not submission:
            return (
                jsonify({"success": False, "error": "Guide or submission not found"}),
                404,
            )

        # Update submission status
        submission.processing_status = "processing"
        db.session.commit()

        # Create processing request
        processing_request = ProcessingRequest(
            guide_id=guide_id,
            submission_id=submission_id,
            user_id=current_user.id,
            options=data.get("options", {}),
        )

        # Process submission
        result = asyncio.run(core_service.process_submission(processing_request))

        # Update submission status
        if result.success:
            submission.processing_status = "completed"
        else:
            submission.processing_status = "failed"

        db.session.commit()

        return jsonify(
            {
                "success": result.success,
                "result_id": result.result_id if result.success else None,
                "score": result.score if result.success else None,
                "error": result.error if not result.success else None,
            }
        )

    except Exception as e:
        logger.error(f"Processing error: {e}")
        return jsonify({"success": False, "error": "Processing failed"}), 500


@processing_bp.route("/api/status/<progress_id>", methods=["GET"])
@login_required
def api_progress_status(progress_id):
    """Get processing progress status (standardized endpoint)."""
    try:
        from webapp.routes.main_routes import progress_store

        if progress_id not in progress_store:
            return jsonify({"success": False, "error": "Progress ID not found"}), 404

        progress_data = progress_store[progress_id]

        return jsonify(
            {
                "success": True,
                "task_id": progress_id,
                "status": progress_data["status"],
                "progress": {
                    "percentage": progress_data.get("progress", 0),
                    "current_operation": progress_data.get(
                        "current_operation", "Processing..."
                    ),
                    "current_step": progress_data.get("current_step", 1),
                    "total_steps": progress_data.get("total_steps", 3),
                    "submission_index": progress_data.get("submission_index", 1),
                    "total_submissions": progress_data.get("total_submissions", 1),
                    "estimated_time_remaining": progress_data.get(
                        "estimated_time_remaining"
                    ),
                    "details": progress_data.get("details"),
                    "message": progress_data.get(
                        "message", "Processing in progress..."
                    ),
                },
                "message": progress_data.get("message", "Processing in progress..."),
                "current_file": progress_data.get("current_file", ""),
                "guide_title": progress_data.get("guide_title", ""),
                "results": {
                    "total_count": progress_data["total_count"],
                    "processed_count": progress_data["processed_count"],
                    "successful_count": progress_data["successful_count"],
                    "failed_count": progress_data["failed_count"],
                    "details": progress_data.get("results", []),
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to get progress status: {e}")
        return (
            jsonify({"success": False, "error": "Failed to get progress status"}),
            500,
        )


@processing_bp.route("/process", methods=["POST"])
@login_required
def process():
    """Legacy process endpoint - redirects to new API."""
    return api_process_single()


@processing_bp.route("/status/<submission_id>")
@login_required
def processing_status(submission_id):
    """Get processing status for a submission."""
    try:
        submission = Submission.query.filter_by(
            id=submission_id, user_id=current_user.id
        ).first()

        if not submission:
            logger.error(f"Submission not found: {submission_id}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Submission not found (ID: {submission_id})",
                    }
                ),
                404,
            )

        # Validate submission object integrity
        if not hasattr(submission, "id") or not hasattr(submission, "filename"):
            logger.error(f"Invalid submission object: {submission}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid submission object - missing required attributes",
                    }
                ),
                500,
            )

        result = (
            GradingResult.query.filter_by(submission_id=submission_id)
            .order_by(GradingResult.created_at.desc())
            .first()
        )

        response_data = {
            "success": True,
            "status": submission.status,
            "submission_id": submission_id,
            "filename": submission.filename,
        }

        if result:
            response_data.update(
                {
                    "result_id": result.id,
                    "score": result.total_score,
                    "max_score": result.max_score,
                    "percentage": (
                        (result.total_score / result.max_score * 100)
                        if result.max_score > 0
                        else 0
                    ),
                    "feedback": result.feedback,
                    "completed_at": result.created_at.isoformat(),
                }
            )

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({"success": False, "error": "Status check failed"}), 500


@processing_bp.route("/results/<result_id>")
@login_required
def view_result(result_id):
    """View detailed processing result."""
    try:
        # Check if this is a GradingSession ID or a single GradingResult ID
        from src.database.models import GradingSession, Mapping

        # First try to find as a GradingSession
        grading_session = GradingSession.query.filter_by(
            id=result_id, user_id=current_user.id
        ).first()

        if grading_session:
            # This is a grading session - get all related grading results
            grading_results = GradingResult.query.filter_by(
                grading_session_id=result_id
            ).all()

            if not grading_results:
                flash("No grading results found for this session", "error")
                return redirect(url_for("main.results"))

            # Use the first result as the primary result for compatibility
            result = grading_results[0]
            submission = db.session.get(Submission, result.submission_id)
            guide = db.session.get(MarkingGuide, result.marking_guide_id)
            
            # Load mappings for the submission to display mapped questions and answers
            if submission:
                submission.mappings = Mapping.query.filter_by(submission_id=submission.id).all()

            # Calculate session-level totals
            total_score = sum(gr.score for gr in grading_results if gr.score)
            max_score = sum(gr.max_score for gr in grading_results if gr.max_score)

            # Create a session-level result object
            class SessionResult:
                def __init__(self, session, results, submission):
                    self.id = session.id
                    self.submission_id = session.submission_id
                    self.marking_guide_id = session.marking_guide_id
                    self.total_score = total_score
                    self.max_score = max_score
                    self.percentage = (
                        (total_score / max_score * 100) if max_score > 0 else 0
                    )
                    self.feedback = None  # Session doesn't have overall feedback
                    self.detailed_results = None  # Will use grading_results instead
                    self.processing_metadata = None
                    self.created_at = session.created_at
                    self.updated_at = session.updated_at
                    self.grading_results = results  # Individual question results

                    # Load mappings for each result
                    for gr in self.grading_results:
                        if gr.mapping_id:
                            gr.mapping = db.session.get(Mapping, gr.mapping_id)

            result = SessionResult(grading_session, grading_results, submission)

        else:
            # Try to find as a single GradingResult
            result = GradingResult.query.join(Submission).filter(
                GradingResult.id == result_id,
                Submission.user_id == current_user.id
            ).first()

            if not result:
                flash("Result not found", "error")
                return redirect(url_for("main.results"))

            # Get related records
            submission = db.session.get(Submission, result.submission_id)
            guide = db.session.get(MarkingGuide, result.marking_guide_id)
            
            # Load mappings for the submission to display mapped questions and answers
            if submission:
                submission.mappings = Mapping.query.filter_by(submission_id=submission.id).all()

            # For single results, check if it's part of a grading session
            if result.grading_session_id:
                # Get all results from the same session
                session_results = GradingResult.query.filter_by(
                    grading_session_id=result.grading_session_id
                ).all()

                # Load mappings for each result
                for gr in session_results:
                    if gr.mapping_id:
                        gr.mapping = db.session.get(Mapping, gr.mapping_id)

                result.grading_results = session_results

                # Calculate session totals
                result.total_score = sum(gr.score for gr in session_results if gr.score)
                result.max_score = sum(
                    gr.max_score for gr in session_results if gr.max_score
                )
            else:
                # Single result - make it compatible with the template
                result.grading_results = [result]
                if result.mapping_id:
                    result.mapping = db.session.get(Mapping, result.mapping_id)

        # Convert result to dict and enhance with additional analytics
        if hasattr(result, "to_dict"):
            result_dict = result.to_dict()
        else:
            result_dict = {
                "id": result.id,
                "total_score": result.total_score,
                "max_score": result.max_score,
                "percentage": result.percentage,
                "feedback": getattr(result, "feedback", None),
                "detailed_results": getattr(result, "detailed_results", None),
                "processing_metadata": getattr(result, "processing_metadata", None),
                "created_at": (
                    result.created_at.isoformat() if result.created_at else None
                ),
                "updated_at": (
                    result.updated_at.isoformat() if result.updated_at else None
                ),
            }

        # Enhance result with comprehensive analytics and formatting
        enhanced_result = enhanced_result_service.enhance_result(
            result_dict,
            submission.to_dict() if submission else None,
            guide.to_dict() if guide else None,
        )

        logger.info(
            f"Enhanced result {result_id} for detailed view with {len(result.grading_results)} individual results"
        )

        return render_template(
            "result_detail.html",
            result=result,
            enhanced_result=enhanced_result,
            submission=submission,
            guide=guide,
            allowed_types=[
                ".pdf",
                ".docx",
                ".doc",
                ".txt",
                ".jpg",
                ".jpeg",
                ".png",
                ".bmp",
                ".tiff",
                ".gif",
            ],
            max_file_size=100 * 1024 * 1024,
        )

    except Exception as e:
        logger.error(f"Result view failed: {e}")
        flash("Error loading result", "error")
        return redirect(url_for("main.results"))


@processing_bp.route("/batch", methods=["GET", "POST"])
@login_required
def batch_processing():
    """Batch processing interface."""
    if request.method == "POST":
        try:
            data = request.get_json()

            guide_id = data.get("guide_id")
            submission_ids = data.get("submission_ids", [])

            if not guide_id or not submission_ids:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Guide ID and submission IDs are required",
                        }
                    ),
                    400,
                )

            # Verify guide ownership
            guide = MarkingGuide.query.filter_by(
                id=guide_id, user_id=current_user.id
            ).first()

            if not guide:
                return jsonify({"success": False, "error": "Guide not found"}), 404

            # Process each submission
            results = []
            for submission_id in submission_ids:
                submission = Submission.query.filter_by(
                    id=submission_id, user_id=current_user.id
                ).first()

                if not submission:
                    results.append(
                        {
                            "submission_id": submission_id,
                            "success": False,
                            "error": "Submission not found",
                        }
                    )
                    continue

                # Create processing request
                processing_request = ProcessingRequest(
                    guide_id=guide_id,
                    submission_id=submission_id,
                    user_id=current_user.id,
                )

                # Process submission
                result = asyncio.run(
                    core_service.process_submission(processing_request)
                )

                results.append(
                    {
                        "submission_id": submission_id,
                        "success": result.success,
                        "result_id": result.result_id,
                        "score": result.score,
                        "error": result.error,
                    }
                )

            return jsonify(
                {
                    "success": True,
                    "results": results,
                    "total_processed": len(results),
                    "successful": sum(1 for r in results if r["success"]),
                }
            )

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return jsonify({"success": False, "error": "Batch processing failed"}), 500

    # GET request - show batch processing interface
    guides = MarkingGuide.query.filter_by(user_id=current_user.id).all()
    submissions = Submission.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "batch_processing.html",
        guides=guides,
        submissions=submissions,
        allowed_types=[
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
            ".gif",
        ],
        max_file_size=100 * 1024 * 1024,
    )


@processing_bp.route("/api/retry", methods=["POST"])
@login_required
def api_retry_processing():
    """Retry failed processing."""
    try:
        data = request.get_json()
        progress_id = data.get("progress_id")

        if not progress_id:
            return jsonify({"success": False, "error": "Progress ID is required"}), 400

        from webapp.routes.main_routes import progress_store

        if progress_id not in progress_store:
            return (
                jsonify({"success": False, "error": "Progress session not found"}),
                404,
            )

        # Reset the progress status to retry
        progress_data = progress_store[progress_id]
        progress_data.update(
            {
                "status": "retrying",
                "progress": 0,
                "message": "Retrying processing...",
                "current_operation": "Initializing retry...",
            }
        )

        return jsonify(
            {
                "success": True,
                "progress_id": progress_id,
                "message": "Processing retry initiated",
            }
        )

    except Exception as e:
        logger.error(f"Retry processing failed: {e}")
        return jsonify({"success": False, "error": "Failed to retry processing"}), 500


@processing_bp.route("/api/cleanup", methods=["POST"])
@login_required
def api_cleanup_progress():
    """Clean up old progress entries."""
    try:
        import time

        from webapp.routes.main_routes import progress_store

        current_time = time.time()
        cleanup_threshold = 3600  # 1 hour

        # Find old entries to clean up
        old_entries = []
        for progress_id, data in progress_store.items():
            created_time = data.get("created_at", current_time)
            if current_time - created_time > cleanup_threshold:
                old_entries.append(progress_id)

        # Remove old entries
        for progress_id in old_entries:
            del progress_store[progress_id]

        return jsonify(
            {
                "success": True,
                "cleaned_up": len(old_entries),
                "remaining": len(progress_store),
            }
        )

    except Exception as e:
        logger.error(f"Progress cleanup failed: {e}")
        return (
            jsonify({"success": False, "error": "Failed to cleanup progress data"}),
            500,
        )


@processing_bp.route("/export/<result_id>")
@login_required
def export_result(result_id):
    """Export processing result."""
    try:
        from src.database.models import Mapping
        
        result = GradingResult.query.filter_by(
            id=result_id, user_id=current_user.id
        ).first()

        if not result:
            return jsonify({"success": False, "error": "Result not found"}), 404

        # Get related records
        submission = db.session.get(Submission, result.submission_id)
        guide = db.session.get(MarkingGuide, result.marking_guide_id)
        
        # Load mappings for the submission to display mapped questions and answers
        if submission:
            submission.mappings = Mapping.query.filter_by(submission_id=submission.id).all()

        # Prepare export data
        export_data = {
            "result_id": result.id,
            "submission": {
                "id": submission.id,
                "filename": submission.filename,
                "created_at": submission.created_at.isoformat(),
            },
            "guide": {
                "id": guide.id,
                "title": guide.title,
                "description": guide.description,
            },
            "grading": {
                "total_score": result.total_score,
                "max_score": result.max_score,
                "percentage": (
                    (result.total_score / result.max_score * 100)
                    if result.max_score > 0
                    else 0
                ),
                "feedback": result.feedback,
                "detailed_results": result.detailed_results,
            },
            "metadata": result.processing_metadata,
            "exported_at": time.time(),
        }

        return jsonify({"success": True, "data": export_data})

    except Exception as e:
        logger.error(f"Export failed: {e}")
        return jsonify({"success": False, "error": "Export failed"}), 500
