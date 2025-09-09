"""
Processing Routes

This module handles AI processing operations including OCR, grading,
and result generation.
"""

import time
import asyncio

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import validate_csrf
from werkzeug.exceptions import BadRequest

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
    """Unified processing interface with guide-filtered submissions."""
    progress_id = request.args.get("progress_id")
    selected_guide_id = request.args.get("guide_id")

    if progress_id:
        # This is a progress tracking request - render the progress page
        guides = MarkingGuide.query.filter_by(user_id=current_user.id).all()

        # Filter submissions by selected guide if provided
        if selected_guide_id:
            submissions = Submission.query.filter_by(
                user_id=current_user.id,
                marking_guide_id=selected_guide_id
            ).all()
        else:
            # Load all submissions but indicate they should be filtered by guide selection
            submissions = []

        return render_template(
            "unified_processing.html",
            guides=guides,
            submissions=submissions,
            selected_guide_id=selected_guide_id,
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
        # No progress_id - show enhanced processing interface with submissions grouped by guide
        guides = MarkingGuide.query.filter_by(user_id=current_user.id).all()

        # Group submissions by marking guide
        submissions_by_guide = {}

        for guide in guides:
            guide_submissions = Submission.query.filter_by(
                user_id=current_user.id,
                marking_guide_id=guide.id
            ).order_by(Submission.created_at.desc()).all()

            if guide_submissions:  # Only include guides that have submissions
                submissions_by_guide[guide.id] = {
                    'guide': guide,
                    'submissions': guide_submissions,
                    'count': len(guide_submissions)
                }

        # Also get submissions without a guide
        unassigned_submissions = Submission.query.filter_by(
            user_id=current_user.id,
            marking_guide_id=None
        ).order_by(Submission.created_at.desc()).all()

        if unassigned_submissions:
            submissions_by_guide['unassigned'] = {
                'guide': None,
                'submissions': unassigned_submissions,
                'count': len(unassigned_submissions)
            }

        # For backward compatibility, also provide the old format
        if selected_guide_id:
            submissions = Submission.query.filter_by(
                user_id=current_user.id,
                marking_guide_id=selected_guide_id
            ).all()
        else:
            submissions = []

        return render_template(
            "enhanced_processing.html",
            guides=guides,
            submissions=submissions,
            submissions_by_guide=submissions_by_guide,
            selected_guide_id=selected_guide_id,
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
        # Check CSRF token first
        from flask_wtf.csrf import validate_csrf
        try:
            csrf_token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
            validate_csrf(csrf_token)
        except Exception as csrf_error:
            logger.warning(f"CSRF validation failed for processing API: {csrf_error}")
            return jsonify({'success': False, 'error': 'Security validation failed'}), 400

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
    selected_guide_id = request.args.get("guide_id")
    guides = MarkingGuide.query.filter_by(user_id=current_user.id).all()

    # Filter submissions by selected guide if provided
    if selected_guide_id:
        submissions = Submission.query.filter_by(
            user_id=current_user.id,
            marking_guide_id=selected_guide_id
        ).all()
    else:
        # Load all submissions but indicate they should be filtered by guide selection
        submissions = []

    return render_template(
        "batch_processing.html",
        guides=guides,
        submissions=submissions,
        selected_guide_id=selected_guide_id,
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

@processing_bp.route("/api/submissions", methods=["GET"])
@login_required
def api_get_submissions():
    """Get submissions filtered by guide ID or grouped by guide."""
    try:
        guide_id = request.args.get("guide_id")
        grouped = request.args.get("grouped", "false").lower() == "true"

        if grouped:
            # Return submissions grouped by marking guide
            guides = MarkingGuide.query.filter_by(user_id=current_user.id).all()
            submissions_by_guide = {}

            for guide in guides:
                guide_submissions = Submission.query.filter_by(
                    user_id=current_user.id,
                    marking_guide_id=guide.id
                ).order_by(Submission.created_at.desc()).all()

                if guide_submissions:  # Only include guides that have submissions
                    submissions_list = []
                    for submission in guide_submissions:
                        submissions_list.append({
                            "id": submission.id,
                            "filename": submission.filename,
                            "student_name": submission.student_name or "",
                            "student_id": submission.student_id or "",
                            "processing_status": submission.processing_status,
                            "file_size": submission.file_size,
                            "file_type": submission.file_type,
                            "marking_guide_id": submission.marking_guide_id,
                            "ocr_confidence": submission.ocr_confidence,
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
                        })

                    submissions_by_guide[guide.id] = {
                        "guide": {
                            "id": guide.id,
                            "title": guide.title,
                            "description": guide.description
                        },
                        "submissions": submissions_list,
                        "count": len(submissions_list)
                    }

            # Also get submissions without a guide
            unassigned_submissions = Submission.query.filter_by(
                user_id=current_user.id,
                marking_guide_id=None
            ).order_by(Submission.created_at.desc()).all()

            if unassigned_submissions:
                submissions_list = []
                for submission in unassigned_submissions:
                    submissions_list.append({
                        "id": submission.id,
                        "filename": submission.filename,
                        "student_name": submission.student_name or "",
                        "student_id": submission.student_id or "",
                        "processing_status": submission.processing_status,
                        "file_size": submission.file_size,
                        "file_type": submission.file_type,
                        "marking_guide_id": submission.marking_guide_id,
                        "ocr_confidence": submission.ocr_confidence,
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
                    })

                submissions_by_guide["unassigned"] = {
                    "guide": None,
                    "submissions": submissions_list,
                    "count": len(submissions_list)
                }

            return jsonify({
                "success": True,
                "grouped": True,
                "submissions_by_guide": submissions_by_guide,
                "total_guides": len(submissions_by_guide)
            })

        elif guide_id:
            # Return submissions for a specific guide
            # Verify guide ownership
            guide = MarkingGuide.query.filter_by(
                id=guide_id, user_id=current_user.id
            ).first()

            if not guide:
                return jsonify({
                    "success": False,
                    "error": "Guide not found or access denied"
                }), 404

            # Get submissions linked to this guide
            submissions = Submission.query.filter_by(
                user_id=current_user.id,
                marking_guide_id=guide_id
            ).order_by(Submission.created_at.desc()).all()

            submissions_list = []
            for submission in submissions:
                submissions_list.append({
                    "id": submission.id,
                    "filename": submission.filename,
                    "student_name": submission.student_name or "",
                    "student_id": submission.student_id or "",
                    "processing_status": submission.processing_status,
                    "file_size": submission.file_size,
                    "file_type": submission.file_type,
                    "marking_guide_id": submission.marking_guide_id,
                    "ocr_confidence": submission.ocr_confidence,
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
                })

            return jsonify({
                "success": True,
                "guide": {
                    "id": guide.id,
                    "title": guide.title,
                    "description": guide.description
                },
                "submissions": submissions_list,
                "total_count": len(submissions_list)
            })

        else:
            return jsonify({
                "success": False,
                "error": "Either guide_id parameter or grouped=true is required"
            }), 400

    except Exception as e:
        logger.error(f"Failed to get submissions: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve submissions"
        }), 500

@processing_bp.route("/api/submissions/all", methods=["GET"])
@login_required
def api_get_all_submissions():
    """Get all submissions for the current user (fallback endpoint)."""
    try:
        submissions = Submission.query.filter_by(user_id=current_user.id).order_by(
            Submission.created_at.desc()
        ).all()

        submissions_list = []
        for submission in submissions:
            # Get guide info if linked
            guide_info = None
            if submission.marking_guide_id:
                guide = MarkingGuide.query.get(submission.marking_guide_id)
                if guide:
                    guide_info = {
                        "id": guide.id,
                        "title": guide.title
                    }

            submissions_list.append({
                "id": submission.id,
                "filename": submission.filename,
                "student_name": submission.student_name or "",
                "student_id": submission.student_id or "",
                "processing_status": submission.processing_status,
                "file_size": submission.file_size,
                "file_type": submission.file_type,
                "marking_guide_id": submission.marking_guide_id,
                "guide": guide_info,
                "ocr_confidence": submission.ocr_confidence,
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
            })

        return jsonify({
            "success": True,
            "submissions": submissions_list,
            "total_count": len(submissions_list)
        })

    except Exception as e:
        logger.error(f"Failed to get all submissions: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve submissions"
        }), 500

@processing_bp.route("/api/submissions/assign", methods=["POST"])
@login_required
def api_assign_submissions_to_guide():
    """Assign submissions to a marking guide."""
    try:
        # Validate CSRF token
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except BadRequest:
            return jsonify({
                "success": False,
                "error": "CSRF token missing or invalid"
            }), 400

        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400

        guide_id = data.get("guide_id")
        submission_ids = data.get("submission_ids", [])

        if not guide_id:
            return jsonify({
                "success": False,
                "error": "guide_id is required"
            }), 400

        if not submission_ids or not isinstance(submission_ids, list):
            return jsonify({
                "success": False,
                "error": "submission_ids must be a non-empty list"
            }), 400

        # Verify guide ownership
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            return jsonify({
                "success": False,
                "error": "Guide not found or access denied"
            }), 404

        # Update submissions
        updated_count = 0
        for submission_id in submission_ids:
            submission = Submission.query.filter_by(
                id=submission_id, user_id=current_user.id
            ).first()

            if submission:
                submission.marking_guide_id = guide_id
                updated_count += 1

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Successfully assigned {updated_count} submission(s) to guide '{guide.title}'",
            "updated_count": updated_count,
            "guide": {
                "id": guide.id,
                "title": guide.title
            }
        })

    except Exception as e:
        logger.error(f"Failed to assign submissions to guide: {e}")
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Failed to assign submissions"
        }), 500

@processing_bp.route("/api/submissions/unassign", methods=["POST"])
@login_required
def api_unassign_submissions_from_guide():
    """Unassign submissions from their marking guide."""
    try:
        # Validate CSRF token
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except BadRequest:
            return jsonify({
                "success": False,
                "error": "CSRF token missing or invalid"
            }), 400

        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400

        submission_ids = data.get("submission_ids", [])

        if not submission_ids or not isinstance(submission_ids, list):
            return jsonify({
                "success": False,
                "error": "submission_ids must be a non-empty list"
            }), 400

        # Update submissions
        updated_count = 0
        for submission_id in submission_ids:
            submission = Submission.query.filter_by(
                id=submission_id, user_id=current_user.id
            ).first()

            if submission:
                submission.marking_guide_id = None
                updated_count += 1

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Successfully unassigned {updated_count} submission(s) from their guides",
            "updated_count": updated_count
        })

    except Exception as e:
        logger.error(f"Failed to unassign submissions: {e}")
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Failed to unassign submissions"
        }), 500

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
