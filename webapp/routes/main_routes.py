"""
Main Application Routes

This module contains the core application routes including dashboard,
file uploads, and basic functionality.
"""

import asyncio
import os
from datetime import datetime, timezone

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from src.database.models import MarkingGuide, Submission, db
from src.services.app_config_service import app_config, get_template_context
from src.services.core_service import core_service
from utils.logger import logger


def get_actual_service_status():
    """Check actual service status by testing API connections."""
    status = {
        "ocr_status": False,
        "llm_status": False,
        "ai_status": False,  # Alias for llm_status
    }
    
    try:
        # Check OCR service
        try:
            from src.services.consolidated_ocr_service import ConsolidatedOCRService
            ocr_service = ConsolidatedOCRService()
            status["ocr_status"] = ocr_service.is_available()
        except Exception as e:
            logger.debug(f"OCR service check failed: {e}")
            status["ocr_status"] = False
            
        # Check LLM service
        try:
            from src.services.consolidated_llm_service import ConsolidatedLLMService
            llm_service = ConsolidatedLLMService()
            status["llm_status"] = llm_service.is_available()
            status["ai_status"] = status["llm_status"]  # Alias
        except Exception as e:
            logger.debug(f"LLM service check failed: {e}")
            status["llm_status"] = False
            status["ai_status"] = False
            
    except Exception as e:
        logger.error(f"Error checking service status: {e}")
        
    return status

main_bp = Blueprint("main", __name__)

# In-memory progress store (in production, use Redis or database)
progress_store = {}


@main_bp.route("/")
def index():
    """Landing page."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    template_context = get_template_context()
    return render_template(
        "landing.html",
        **template_context,
    )


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """User dashboard."""
    try:
        if not current_user or not current_user.is_authenticated:
            logger.warning("Dashboard accessed by unauthenticated user")
            flash("Please log in to access the dashboard", "warning")
            return redirect(url_for("auth.login"))

        # Get recent guides and submissions
        recent_guides = (
            MarkingGuide.query.filter_by(user_id=current_user.id)
            .order_by(MarkingGuide.created_at.desc())
            .limit(5)
            .all()
        )

        recent_submissions = (
            Submission.query.filter_by(user_id=current_user.id)
            .order_by(Submission.created_at.desc())
            .limit(5)
            .all()
        )

        # Get statistics
        stats = {
            "total_guides": MarkingGuide.query.filter_by(
                user_id=current_user.id
            ).count(),
            "total_submissions": Submission.query.filter_by(
                user_id=current_user.id
            ).count(),
            "processed_submissions": Submission.query.filter_by(
                user_id=current_user.id, processing_status="completed"
            ).count(),
        }

        template_context = get_template_context()
        return render_template(
            "dashboard.html",
            recent_guides=recent_guides,
            recent_submissions=recent_submissions,
            stats=stats,
            total_submissions=stats["total_submissions"],
            processed_submissions=stats["processed_submissions"],
            guide_uploaded=stats["total_guides"] > 0,
            last_score=None,
            submissions=recent_submissions,
            recent_activity=[],
            **template_context,
        )

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash("Error loading dashboard", "error")
        template_context = get_template_context()
        return render_template(
            "dashboard.html",
            recent_guides=[],
            recent_submissions=[],
            stats={},
            total_submissions=0,
            processed_submissions=0,
            guide_uploaded=False,
            last_score=None,
            submissions=[],
            recent_activity=[],
            **template_context,
        )


@main_bp.route("/guides")
@login_required
def guides():
    """Marking guides management."""
    try:
        from flask import session

        page = request.args.get("page", 1, type=int)
        logger.info(f"Loading guides for user: {current_user.id}")

        guides = MarkingGuide.query.filter_by(user_id=current_user.id).paginate(
            page=page, per_page=10, error_out=False
        )

        logger.info(f"Found {len(guides.items)} guides for user")
        for guide in guides.items:
            logger.info(f"Guide: {guide.title} (ID: {guide.id})")

        saved_guides_list = []
        if guides and guides.items:
            for guide in guides.items:
                guide_dict = guide.to_dict()
                saved_guides_list.append(guide_dict)

        active_guide_id = session.get("active_guide_id")
        current_guide = None
        if active_guide_id:
            current_guide = MarkingGuide.query.filter_by(
                id=active_guide_id, user_id=current_user.id
            ).first()

        logger.info(f"Passing {len(saved_guides_list)} guides to template")

        template_context = get_template_context()
        return render_template(
            "marking_guides.html",
            guides=guides,
            saved_guides=saved_guides_list,
            current_guide=current_guide,
            **template_context,
        )

    except Exception as e:
        logger.error(f"Guides page error: {e}", exc_info=True)
        flash("Error loading guides", "error")
        template_context = get_template_context()
        return render_template(
            "marking_guides.html",
            guides=None,
            saved_guides=[],
            **template_context,
        )


@main_bp.route("/submissions")
@login_required
def submissions():
    """Submissions management."""
    try:
        page = request.args.get("page", 1, type=int)
        submissions = Submission.query.filter_by(user_id=current_user.id).paginate(
            page=page, per_page=10, error_out=False
        )

        template_context = get_template_context()
        return render_template(
            "submissions.html",
            submissions=submissions,
            **template_context,
        )

    except Exception as e:
        logger.error(f"Submissions page error: {e}")
        flash("Error loading submissions", "error")
        template_context = get_template_context()
        return render_template(
            "submissions.html",
            submissions=None,
            **template_context,
        )


@main_bp.route("/upload-guide", methods=["GET", "POST"])
@login_required
def upload_guide():
    """Upload marking guide page and handler."""
    if request.method == "POST":
        # Handle file upload
        try:
            logger.info(f"Upload guide request from user: {current_user.id}")

            if "guide_file" not in request.files:
                logger.warning("No file in request")
                flash("No file selected", "error")
                return redirect(request.url)

            file = request.files["guide_file"]
            if file.filename == "":
                logger.warning("Empty filename")
                flash("No file selected", "error")
                return redirect(request.url)

            # Secure the filename
            filename = secure_filename(file.filename)
            logger.info(f"Processing file: {filename}")

            upload_dir = os.path.join(current_app.root_path, "..", "uploads", "guides")
            os.makedirs(upload_dir, exist_ok=True)
            logger.info(f"Upload directory: {upload_dir}")

            # Save the file
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            logger.info(f"File saved to: {file_path}")

            # Get file info
            file_size = os.path.getsize(file_path)
            file_type = (
                filename.split(".")[-1].lower() if "." in filename else "unknown"
            )
            logger.info(f"File info - Size: {file_size}, Type: {file_type}")

            auto_process = request.form.get("auto_process") == "on"
            logger.info(f"Auto-processing enabled: {auto_process}")

            # Get title and validate for duplicates
            title = request.form.get("title", filename).strip()
            description = request.form.get("description", "").strip()

            # Check for duplicate titles
            existing_title = MarkingGuide.query.filter(
                MarkingGuide.user_id == current_user.id,
                MarkingGuide.title == title,
                MarkingGuide.is_active == True,
            ).first()

            if existing_title:
                logger.warning(f"Duplicate title found: {title}")
                flash(
                    f'A guide with the title "{title}" already exists. Please choose a different title.',
                    "error",
                )
                # Clean up uploaded file
                if os.path.exists(file_path):
                    os.remove(file_path)
                return redirect(request.url)

            # Extract text content for duplicate detection
            content_text = ""
            try:
                from src.parsing.parse_guide import parse_marking_guide

                guide_result, parse_error = parse_marking_guide(file_path)
                if guide_result and not parse_error:
                    content_text = guide_result.raw_content
                elif parse_error:
                    logger.warning(f"Could not extract text for duplicate detection: {parse_error}")
            except Exception as e:
                logger.warning(f"Could not extract text for duplicate detection: {e}")

            # Check for duplicate content using text content hash
            content_hash = ""
            if content_text:
                from src.utils.content_deduplication import (
                    calculate_content_hash,
                    check_marking_guide_duplicate,
                )

                is_duplicate, existing_guide = check_marking_guide_duplicate(
                    user_id=current_user.id, content=content_text, db_session=db.session
                )

                if is_duplicate:
                    logger.warning(
                        f"Duplicate content found, existing guide: {existing_guide.title}"
                    )
                    flash(
                        f'A guide with identical content already exists: "{existing_guide.title}". Please upload a different file.',
                        "error",
                    )
                    # Clean up uploaded file
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return redirect(request.url)

                # Calculate content hash for the new guide
                content_hash = calculate_content_hash(content_text)

            # Create a new marking guide with all required fields
            guide = MarkingGuide(
                user_id=current_user.id,
                title=title,
                description=description,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                content_text=content_text,
                content_hash=content_hash,
                questions=[],  # Initialize as empty list
                total_marks=0.0,
                is_active=True,
            )

            logger.info(
                f"Created guide object: {guide.title} with hash: {content_hash[:8]}..."
            )

            db.session.add(guide)
            db.session.commit()

            logger.info(f"Guide saved successfully with ID: {guide.id}")

            if auto_process:
                try:
                    logger.info(
                        f"Starting automatic LLM processing for guide {guide.id}"
                    )

                    # Import the processing functions
                    from webapp.routes.guide_processing_routes import (
                        extract_questions_with_llm,
                        extract_text_from_file,
                    )

                    # Extract text content
                    content_text = extract_text_from_file(file_path, file_type)
                    if content_text:
                        guide.content_text = content_text

                        # Extract questions using LLM
                        questions_data = extract_questions_with_llm(content_text)
                        if questions_data:
                            guide.questions = questions_data
                            guide.total_marks = sum(
                                q.get("marks", 0) for q in questions_data
                            )

                            db.session.commit()
                            logger.info(
                                f"Successfully processed guide {guide.id} - extracted {len(questions_data)} questions"
                            )
                            flash(
                                f"Marking guide uploaded and processed successfully! Extracted {len(questions_data)} questions.",
                                "success",
                            )
                        else:
                            logger.warning(
                                f"Could not extract questions from guide {guide.id}"
                            )
                            flash(
                                "Marking guide uploaded successfully, but question extraction failed. You can process it manually later.",
                                "warning",
                            )
                    else:
                        logger.warning(f"Could not extract text from guide {guide.id}")
                        flash(
                            "Marking guide uploaded successfully, but text extraction failed. You can process it manually later.",
                            "warning",
                        )

                except Exception as e:
                    logger.error(
                        f"Error during automatic processing of guide {guide.id}: {e}"
                    )
                    flash(
                        "Marking guide uploaded successfully, but automatic processing failed. You can process it manually later.",
                        "warning",
                    )
            else:
                flash("Marking guide uploaded successfully!", "success")

            return redirect(url_for("main.guides"))

        except Exception as e:
            logger.error(f"Error uploading guide: {e}", exc_info=True)
            db.session.rollback()
            flash("Error uploading guide. Please try again.", "error")
            return redirect(request.url)

    template_context = get_template_context()
    return render_template(
        "upload_guide.html",
        **template_context,
    )


@main_bp.route("/upload-submission", methods=["GET", "POST"])
@login_required
def upload_submission():
    """Upload submission page and handler."""
    if request.method == "POST":
        is_ajax = request.headers.get(
            "X-Requested-With"
        ) == "XMLHttpRequest" or request.headers.get("Content-Type", "").startswith(
            "multipart/form-data"
        )

        # Handle file upload
        try:
            files = (
                request.files.getlist("submission_files")
                if "submission_files" in request.files
                else []
            )
            if not files or all(f.filename == "" for f in files):
                if is_ajax:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "error": "No files selected",
                                "uploaded_count": 0,
                                "failed_count": 0,
                                "errors": [],
                            }
                        ),
                        400,
                    )
                flash("No file selected", "error")
                return redirect(request.url)

            guide_id = request.form.get("guide_id")
            if not guide_id:
                if is_ajax:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "error": "Please select a marking guide",
                                "uploaded_count": 0,
                                "failed_count": 0,
                                "errors": [],
                            }
                        ),
                        400,
                    )
                flash("Please select a marking guide", "error")
                return redirect(request.url)

            uploaded_count = 0
            failed_count = 0
            errors = []

            # Process each file
            for file in files:
                if file.filename == "":
                    continue

                try:
                    # Secure the filename
                    filename = secure_filename(file.filename)

                    upload_dir = os.path.join(
                        current_app.root_path, "..", "uploads", "submissions"
                    )
                    os.makedirs(upload_dir, exist_ok=True)

                    # Handle duplicate filenames by adding timestamp
                    import time

                    base_name, ext = os.path.splitext(filename)
                    timestamp = str(int(time.time()))
                    unique_filename = f"{base_name}_{timestamp}{ext}"

                    # Save the file
                    file_path = os.path.join(upload_dir, unique_filename)
                    file.save(file_path)

                    # Update filename to the unique one
                    filename = unique_filename

                    # Get file info
                    file_size = os.path.getsize(file_path)
                    file_type = (
                        filename.split(".")[-1].lower()
                        if "." in filename
                        else "unknown"
                    )

                    # Process the file to extract text with OCR fallback
                    extracted_text = ""
                    ocr_confidence = 0.0
                    processing_status = "completed"
                    processing_error = None

                    try:
                        logger.info(f"Processing uploaded file: {filename}")

                        # Import the parsing function
                        from src.parsing.parse_submission import (
                            parse_student_submission,
                        )

                        # Parse the submission with OCR fallback
                        result, raw_text, error = parse_student_submission(file_path)

                        if error:
                            logger.warning(
                                f"Text extraction failed for {filename}: {error}"
                            )
                            processing_status = "failed"
                            processing_error = error
                        elif raw_text:
                            extracted_text = raw_text
                            logger.info(
                                f"Successfully extracted {len(extracted_text)} characters from {filename}"
                            )

                            # Set confidence based on file type and extraction method
                            if file_type.lower() in [
                                "jpg",
                                "jpeg",
                                "png",
                                "bmp",
                                "tiff",
                                "gif",
                            ]:
                                ocr_confidence = 0.8  # Image files always use OCR
                            elif len(extracted_text.strip()) < 50:
                                ocr_confidence = (
                                    0.7  # Low confidence for very short text
                                )
                            else:
                                ocr_confidence = (
                                    0.95  # Direct text extraction from PDF/DOCX
                                )
                        else:
                            logger.warning(f"No text extracted from {filename}")
                            processing_status = (
                                "completed"  # File processed but no text found
                            )

                    except Exception as processing_error_ex:
                        logger.error(
                            f"Error processing file {filename}: {processing_error_ex}"
                        )
                        processing_status = "failed"
                        processing_error = str(processing_error_ex)

                    # Check for duplicate content if text was extracted successfully
                    content_hash = ""
                    if extracted_text and processing_status == "completed":
                        from src.utils.content_deduplication import (
                            calculate_content_hash,
                            check_submission_duplicate,
                        )

                        is_duplicate, existing_submission = check_submission_duplicate(
                            user_id=current_user.id,
                            content=extracted_text,
                            db_session=db.session,
                        )

                        if is_duplicate:
                            logger.warning(
                                f"Duplicate content found for {filename}, existing submission: {existing_submission.filename}"
                            )
                            # Clean up uploaded file since it's a duplicate
                            try:
                                os.remove(file_path)
                            except OSError:
                                pass

                            failed_count += 1
                            errors.append(
                                {
                                    "filename": file.filename,
                                    "error": f'A submission with identical content already exists: "{existing_submission.filename}"',
                                }
                            )
                            continue  # Skip creating this submission

                        # Calculate content hash for the new submission
                        content_hash = calculate_content_hash(extracted_text)

                    # Create a new submission with extracted text
                    submission = Submission(
                        user_id=current_user.id,
                        marking_guide_id=guide_id,
                        filename=filename,
                        file_path=file_path,
                        file_size=file_size,
                        file_type=file_type,
                        student_name=request.form.get("student_name", ""),
                        content_text=extracted_text,
                        content_hash=content_hash,
                        ocr_confidence=ocr_confidence,
                        processing_status=processing_status,
                        processing_error=processing_error,
                    )

                    db.session.add(submission)
                    db.session.commit()
                    uploaded_count += 1

                    logger.info(
                        f"Successfully uploaded and processed {filename} (Status: {processing_status})"
                    )

                except Exception as e:
                    logger.error(f"Error uploading file {file.filename}: {e}")
                    failed_count += 1
                    errors.append({"filename": file.filename, "error": str(e)})

            if is_ajax:
                if uploaded_count > 0 and failed_count == 0:
                    return jsonify(
                        {
                            "status": "success",
                            "message": f"{uploaded_count} submission(s) uploaded successfully!",
                            "uploaded_count": uploaded_count,
                            "failed_count": failed_count,
                            "errors": errors,
                        }
                    )
                elif uploaded_count > 0:
                    return jsonify(
                        {
                            "status": "partial_failure",
                            "message": f"{uploaded_count} submission(s) uploaded, {failed_count} failed",
                            "uploaded_count": uploaded_count,
                            "failed_count": failed_count,
                            "errors": errors,
                        }
                    )
                else:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "error": "All uploads failed",
                                "uploaded_count": uploaded_count,
                                "failed_count": failed_count,
                                "errors": errors,
                            }
                        ),
                        400,
                    )
            else:
                # Traditional form submission
                if uploaded_count > 0:
                    flash(
                        f"{uploaded_count} submission(s) uploaded successfully!",
                        "success",
                    )
                else:
                    flash("Error uploading submissions. Please try again.", "error")
                return redirect(url_for("main.submissions"))

        except Exception as e:
            logger.error(f"Error uploading submission: {e}")
            if is_ajax:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "Error uploading submission. Please try again.",
                            "uploaded_count": 0,
                            "failed_count": 1,
                            "errors": [{"filename": "unknown", "error": str(e)}],
                        }
                    ),
                    500,
                )
            flash("Error uploading submission. Please try again.", "error")
            return redirect(request.url)

    guides = MarkingGuide.query.filter_by(user_id=current_user.id).all()

    guide_id = request.args.get("guide_id")
    if not guide_id:
        from flask import session

        guide_id = session.get("active_guide_id")

    template_context = get_template_context()
    return render_template(
        "upload_submission.html",
        guides=guides,
        guide_id=guide_id,
        **template_context,
    )


@main_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """General upload page - redirects to appropriate upload based on context"""
    try:
        # Check if user has any marking guides
        guides = MarkingGuide.query.filter_by(user_id=current_user.id).all()
        
        if request.method == "GET":
            # Show upload selection page
            return render_template('upload_selection.html', guides=guides)
        
        # Handle POST - determine upload type
        upload_type = request.form.get('upload_type', 'submission')
        
        if upload_type == 'guide':
            return redirect(url_for('main.upload_guide'))
        else:
            return redirect(url_for('main.upload_submission'))
            
    except Exception as e:
        logger.error(f"Error in upload route: {e}")
        flash("An error occurred while accessing the upload page.", "error")
        return redirect(url_for('main.dashboard'))


@main_bp.route("/results")
@login_required
def results():
    """Results page."""
    try:
        from src.database.models import GradingResult

        page = request.args.get("page", 1, type=int)
        results = (
            GradingResult.query.join(Submission)
            .filter(Submission.user_id == current_user.id)
            .paginate(page=page, per_page=10, error_out=False)
        )

        # Calculate batch summary
        results_list = results.items if results else []
        has_results = len(results_list) > 0

        # Helper function to calculate letter grade
        def calculate_letter_grade(percentage):
            if percentage >= 90:
                return "A"
            elif percentage >= 80:
                return "B"
            elif percentage >= 70:
                return "C"
            elif percentage >= 60:
                return "D"
            else:
                return "F"

        # Enhanced result list with submission data
        results_list_dict = []
        for result in results_list:
            result_dict = result.to_dict()
            submission = result.submission
            if submission:
                result_dict.update(
                    {
                        "filename": submission.filename,
                        "student_name": submission.student_name,
                        "total_questions": 0,  # Can be calculated from detailed_feedback if needed
                        "letter_grade": (
                            calculate_letter_grade(result.percentage)
                            if result.percentage
                            else "N/A"
                        ),
                    }
                )
            results_list_dict.append(result_dict)

        batch_summary = None
        if has_results:
            scores = [r.score for r in results_list if r.score is not None]
            if scores:
                batch_summary = {
                    "total_submissions": len(results_list),
                    "average_score": round(sum(scores) / len(scores), 1),
                    "highest_score": max(scores),
                    "lowest_score": min(scores),
                }
            else:
                batch_summary = {
                    "total_submissions": len(results_list),
                    "average_score": 0,
                    "highest_score": 0,
                    "lowest_score": 0,
                }
        else:
            batch_summary = {
                "total_submissions": 0,
                "average_score": 0,
                "highest_score": 0,
                "lowest_score": 0,
            }

        template_context = get_template_context()
        return render_template(
            "results.html",
            results=results,
            results_list=results_list,
            results_list_dict=results_list_dict,
            has_results=has_results,
            batch_summary=batch_summary,
            successful_grades=len(results_list),
            **template_context,
        )

    except Exception as e:
        logger.error(f"Results page error: {e}")
        flash("Error loading results", "error")
        template_context = get_template_context()
        return render_template(
            "results.html",
            results=None,
            results_list=[],
            results_list_dict=[],
            has_results=False,
            batch_summary={
                "total_submissions": 0,
                "average_score": 0,
                "highest_score": 0,
                "lowest_score": 0,
            },
            successful_grades=0,
            **template_context,
        )


@main_bp.route("/get-csrf-token")
def get_csrf_token():
    """Get CSRF token for JavaScript requests."""
    try:
        from flask_wtf.csrf import generate_csrf

        token = generate_csrf()
        return jsonify({"csrf_token": token})
    except Exception as e:
        logger.error(f"Error generating CSRF token: {e}")
        return jsonify({"error": "Failed to generate CSRF token"}), 500


@main_bp.route("/api/dashboard-stats")
@login_required
def dashboard_stats():
    """Get dashboard statistics for AJAX updates."""
    try:
        if not current_user or not current_user.is_authenticated:
            return jsonify({"error": "Not authenticated"}), 401

        stats = {
            "total_guides": MarkingGuide.query.filter_by(
                user_id=current_user.id
            ).count(),
            "total_submissions": Submission.query.filter_by(
                user_id=current_user.id
            ).count(),
            "processed_submissions": Submission.query.filter_by(
                user_id=current_user.id, processing_status="completed"
            ).count(),
        }

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({"error": "Failed to get stats"}), 500


@main_bp.route("/api/delete-guide", methods=["POST"])
@login_required
def api_delete_guide():
    """API endpoint to delete a marking guide."""
    try:
        data = request.get_json()
        if not data or "guide_id" not in data:
            return jsonify({"success": False, "message": "Guide ID is required"}), 400

        guide_id = data["guide_id"]
        logger.info(f"Attempting to delete guide {guide_id} for user {current_user.id}")

        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            logger.warning(f"Guide {guide_id} not found for user {current_user.id}")
            return jsonify({"success": False, "message": "Guide not found"}), 404

        # Delete the guide
        db.session.delete(guide)
        db.session.commit()

        logger.info(f"Successfully deleted guide {guide_id}")
        return jsonify({"success": True, "message": "Guide deleted successfully"})

    except Exception as e:
        logger.error(f"Failed to delete guide: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"success": False, "message": "Failed to delete guide"}), 500


@main_bp.route("/api/submission-details/<submission_id>", methods=["GET"])
@login_required
def api_submission_details(submission_id):
    """API endpoint to get submission details."""
    try:
        submission = Submission.query.filter_by(
            id=submission_id, user_id=current_user.id
        ).first()

        if not submission:
            return jsonify({"success": False, "error": "Submission not found"}), 404

        # Get related data
        from src.database.models import GradingResult, MarkingGuide

        grading_results = GradingResult.query.filter_by(
            submission_id=submission_id
        ).all()

        marking_guide = MarkingGuide.query.filter_by(
            id=submission.marking_guide_id
        ).first()

        # Format the response
        data = {
            "success": True,
            "submission": {
                "id": submission.id,
                "filename": submission.filename,
                "student_name": submission.student_name or "Unknown",
                "processing_status": submission.processing_status,
                "file_size": submission.file_size,
                "file_type": submission.file_type,
                "created_at": (
                    submission.created_at.isoformat() if submission.created_at else None
                ),
                "updated_at": (
                    submission.updated_at.isoformat() if submission.updated_at else None
                ),
                "extracted_text": (
                    submission.content_text[:app_config.get_text_preview_length()] + "..."
                    if submission.content_text and len(submission.content_text) > app_config.get_text_preview_length()
                    else submission.content_text
                ),
            },
            "marking_guide": (
                {
                    "id": marking_guide.id if marking_guide else None,
                    "title": marking_guide.title if marking_guide else "Unknown Guide",
                    "total_marks": marking_guide.total_marks if marking_guide else 0,
                }
                if marking_guide
                else None
            ),
            "grading_results": [
                {
                    "id": result.id,
                    "score": result.score,
                    "letter_grade": result.letter_grade,
                    "feedback": result.feedback,
                    "graded_at": (
                        result.graded_at.isoformat() if result.graded_at else None
                    ),
                }
                for result in grading_results
            ],
        }

        return jsonify(data)

    except Exception as e:
        logger.error(f"Error getting submission details: {e}")
        return (
            jsonify({"success": False, "error": "Failed to get submission details"}),
            500,
        )


@main_bp.route("/api/export-results", methods=["GET"])
@login_required
def api_export_results():
    """API endpoint to export grading results."""
    try:
        from datetime import datetime

        from src.database.models import GradingResult

        results = (
            GradingResult.query.join(Submission)
            .filter(Submission.user_id == current_user.id)
            .all()
        )

        if not results:
            return (
                jsonify({"success": False, "error": "No results found to export"}),
                404,
            )

        export_data = []
        for result in results:
            submission = result.submission
            export_data.append(
                {
                    "submission_id": result.submission_id,
                    "filename": submission.filename if submission else "Unknown",
                    "student_name": (
                        submission.student_name if submission else "Unknown"
                    ),
                    "score": result.score,
                    "letter_grade": result.letter_grade,
                    "feedback": result.feedback,
                    "total_questions": result.total_questions,
                    "graded_at": (
                        result.graded_at.isoformat() if result.graded_at else None
                    ),
                    "created_at": (
                        result.created_at.isoformat() if result.created_at else None
                    ),
                }
            )

        # Calculate summary statistics
        scores = [r.score for r in results if r.score is not None]
        summary = {
            "total_submissions": len(results),
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
            "highest_score": max(scores) if scores else 0,
            "lowest_score": min(scores) if scores else 0,
            "export_date": datetime.now().isoformat(),
            "exported_by": (
                current_user.username
                if hasattr(current_user, "username")
                else str(current_user.id)
            ),
        }

        # Create export package
        export_package = {"summary": summary, "results": export_data}

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"grading_results_{timestamp}.json"

        return jsonify(
            {
                "success": True,
                "data": export_package,
                "filename": filename,
                "message": f"Successfully exported {len(results)} results",
            }
        )

    except Exception as e:
        logger.error(f"Error exporting results: {e}")
        return jsonify({"success": False, "error": "Failed to export results"}), 500


@main_bp.route("/view-submission-content/<submission_id>")
@login_required
def view_submission_content(submission_id):
    """View detailed submission content page."""
    try:
        submission = Submission.query.filter_by(
            id=submission_id, user_id=current_user.id
        ).first()

        if not submission:
            flash("Submission not found", "error")
            return redirect(url_for("main.results"))
        # Get related grading results
        from src.database.models import GradingResult

        grading_results = GradingResult.query.filter_by(
            submission_id=submission_id
        ).all()

        template_context = get_template_context()
        return render_template(
            "view_submission.html",
            submission=submission,
            grading_results=grading_results,
            page_title="View Submission",
            **template_context,
        )

    except Exception as e:
        logger.error(f"Error viewing submission content: {e}")
        flash("Error loading submission content", "error")
        return redirect(url_for("main.results"))


@main_bp.route("/api/cache/stats", methods=["GET"])
@login_required
def api_cache_stats():
    """API endpoint to get cache statistics."""
    try:
        # Return basic cache stats - can be expanded later
        stats = {
            "success": True,
            "cache_enabled": True,
            "cache_size": 0,
            "hit_rate": 0.0,
            "miss_rate": 0.0,
            "total_requests": 0,
        }
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return (
            jsonify({"success": False, "error": "Failed to load cache statistics"}),
            500,
        )


@main_bp.route("/api/submission-statuses", methods=["GET"])
@login_required
def api_submission_statuses():
    """API endpoint to get submission statuses."""
    try:
        submissions = Submission.query.filter_by(user_id=current_user.id).all()

        submissions_list = []
        for submission in submissions:
            submissions_list.append(
                {
                    "id": submission.id,
                    "status": submission.processing_status,
                    "filename": submission.filename,
                    "updated_at": (
                        submission.updated_at.isoformat()
                        if submission.updated_at
                        else None
                    ),
                }
            )

        return jsonify(
            {
                "success": True,
                "submissions": submissions_list,
                "total_count": len(submissions),
            }
        )

    except Exception as e:
        logger.error(f"Failed to get submission statuses: {e}")
        return (
            jsonify({"success": False, "error": "Failed to load submission statuses"}),
            500,
        )


@main_bp.route("/view-submission/<submission_id>", methods=["GET"])
@login_required
def view_submission(submission_id):
    """View/download submission content."""
    try:
        submission = Submission.query.filter_by(
            id=submission_id, user_id=current_user.id
        ).first()

        if not submission:
            return jsonify({"success": False, "error": "Submission not found"}), 404

        if submission.file_path and os.path.exists(submission.file_path):
            from flask import send_file

            return send_file(
                submission.file_path,
                as_attachment=True,
                download_name=submission.filename,
            )
        else:
            return jsonify(
                {
                    "success": True,
                    "submission": {
                        "id": submission.id,
                        "filename": submission.filename,
                        "student_name": submission.student_name,
                        "content_text": submission.content_text,
                        "processing_status": submission.processing_status,
                        "created_at": (
                            submission.created_at.isoformat()
                            if submission.created_at
                            else None
                        ),
                    },
                }
            )

    except Exception as e:
        logger.error(f"Failed to view submission {submission_id}: {e}")
        return (
            jsonify({"success": False, "error": "Failed to fetch submission content"}),
            500,
        )


@main_bp.route("/api/delete-submission", methods=["POST"])
@login_required
def api_delete_submission():
    """API endpoint to delete a submission."""
    try:
        data = request.get_json()
        if not data or "submission_id" not in data:
            return (
                jsonify({"success": False, "error": "Submission ID is required"}),
                400,
            )

        submission_id = data["submission_id"]

        submission = Submission.query.filter_by(
            id=submission_id, user_id=current_user.id
        ).first()

        if not submission:
            return jsonify({"success": False, "error": "Submission not found"}), 404

        # Delete associated grading results first
        from src.database.models import GradingResult

        GradingResult.query.filter_by(submission_id=submission_id).delete()

        if submission.file_path and os.path.exists(submission.file_path):
            try:
                os.remove(submission.file_path)
            except OSError as e:
                logger.warning(f"Could not delete file {submission.file_path}: {e}")

        # Delete the submission record
        db.session.delete(submission)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f'Submission "{submission.filename}" deleted successfully',
            }
        )

    except Exception as e:
        logger.error(f"Failed to delete submission: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": "Failed to delete submission"}), 500


@main_bp.route("/api/delete-grading-result", methods=["POST"])
@login_required
def api_delete_grading_result():
    """API endpoint to delete a grading result."""
    try:
        data = request.get_json()
        if not data or "result_id" not in data:
            return jsonify({"success": False, "error": "Result ID is required"}), 400

        result_id = data["result_id"]

        from src.database.models import GradingResult

        result = GradingResult.query.filter_by(id=result_id).first()

        if not result:
            return jsonify({"success": False, "error": "Grading result not found"}), 404

        # Verify the result belongs to the current user's submission
        submission = Submission.query.filter_by(
            id=result.submission_id, user_id=current_user.id
        ).first()

        if not submission:
            return jsonify({"success": False, "error": "Access denied"}), 403

        db.session.delete(result)
        db.session.commit()

        return jsonify(
            {"success": True, "message": "Grading result deleted successfully"}
        )

    except Exception as e:
        logger.error(f"Failed to delete grading result: {e}")
        db.session.rollback()
        return (
            jsonify({"success": False, "error": "Failed to delete grading result"}),
            500,
        )


@main_bp.route("/refactored/api/marking-guides", methods=["GET"])
@login_required
def api_refactored_marking_guides():
    """API endpoint to get marking guides for refactored interface."""
    try:
        guides = MarkingGuide.query.filter_by(user_id=current_user.id).all()

        guides_list = []
        for guide in guides:
            questions = guide.questions or []
            questions_count = len(questions) if questions else 0

            guides_list.append(
                {
                    "id": guide.id,
                    "title": guide.title or guide.name or "Untitled Guide",
                    "description": guide.description or "",
                    "total_marks": guide.total_marks or 0,
                    "questions": questions,
                    "questions_count": questions_count,
                    "max_questions_to_answer": guide.max_questions_to_answer
                    or questions_count,
                    "created_at": (
                        guide.created_at.isoformat() if guide.created_at else None
                    ),
                    "updated_at": (
                        guide.updated_at.isoformat() if guide.updated_at else None
                    ),
                    "is_active": (
                        guide.is_active if hasattr(guide, "is_active") else True
                    ),
                }
            )

        return jsonify(
            {"success": True, "guides": guides_list, "total_count": len(guides_list)}
        )

    except Exception as e:
        logger.error(f"Failed to get marking guides: {e}")
        return (
            jsonify({"success": False, "error": "Failed to load marking guides"}),
            500,
        )


@main_bp.route("/refactored/api/submissions", methods=["GET"])
@login_required
def api_refactored_submissions():
    """API endpoint to get submissions for refactored interface."""
    try:
        submissions = Submission.query.filter_by(user_id=current_user.id).all()

        submissions_list = []
        for submission in submissions:
            submissions_list.append(
                {
                    "id": submission.id,
                    "filename": submission.filename,
                    "student_name": submission.student_name or "",
                    "processing_status": submission.processing_status,
                    "file_size": submission.file_size,
                    "file_type": submission.file_type,
                    "marking_guide_id": submission.marking_guide_id,
                    "content_text": submission.content_text or "",
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
                    "processed": submission.processing_status == "completed",
                }
            )

        return jsonify(
            {
                "success": True,
                "submissions": submissions_list,
                "total_count": len(submissions_list),
            }
        )

    except Exception as e:
        logger.error(f"Failed to get submissions: {e}")
        return jsonify({"success": False, "error": "Failed to load submissions"}), 500


@main_bp.route("/api/enhanced-processing/start", methods=["POST"])
@login_required
def api_enhanced_processing_start():
    """API endpoint to start enhanced processing."""
    try:
        data = request.get_json()

        guide_id = data.get("guide_id") or data.get("marking_guide_id")
        submission_ids = data.get("submission_ids", [])
        max_questions_to_answer = data.get("max_questions_to_answer")

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

        import uuid

        task_id = str(uuid.uuid4())

        # Log the processing request
        logger.info(
            f"Starting enhanced processing - Guide: {guide_id}, Submissions: {len(submission_ids)}, Max Questions: {max_questions_to_answer}"
        )

        # Verify submissions belong to user with enhanced error handling
        try:
            valid_submissions = Submission.query.filter(
                Submission.id.in_(submission_ids), Submission.user_id == current_user.id
            ).all()

            # Filter out any None submissions and validate objects
            valid_submissions = [
                sub
                for sub in valid_submissions
                if sub is not None and hasattr(sub, "id") and hasattr(sub, "filename")
            ]

            if len(valid_submissions) != len(submission_ids):
                missing_ids = set(submission_ids) - {
                    sub.id for sub in valid_submissions
                }
                logger.error(f"Missing or invalid submissions: {missing_ids}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Some submissions not found or access denied. Missing IDs: {list(missing_ids)}",
                        }
                    ),
                    404,
                )

        except Exception as e:
            logger.error(f"Error loading submissions: {e}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Failed to load submissions from database",
                    }
                ),
                500,
            )

        # Initialize progress tracking
        import time

        progress_store[task_id] = {
            "status": "starting",
            "progress": 0,
            "created_at": time.time(),
            "message": "Initializing processing...",
            "total_count": len(valid_submissions),
            "processed_count": 0,
            "successful_count": 0,
            "failed_count": 0,
            "current_file": "",
            "results": [],
            "guide_title": guide.title,
        }

        # Start background processing
        import threading

        app = current_app._get_current_object()
        user_id = current_user.id

        def background_processing():
            # Run within Flask application context
            with app.app_context():
                try:
                    # Import the ProcessingRequest class
                    from src.services.core_service import ProcessingRequest

                    processing_results = []
                    successful_count = 0
                    failed_count = 0
                    total_count = len(valid_submissions)

                    for i, submission in enumerate(valid_submissions):
                        if (
                            not submission
                            or not hasattr(submission, "id")
                            or not hasattr(submission, "filename")
                        ):
                            logger.error(
                                f"Invalid submission object at index {i}: {submission}"
                            )
                            failed_count += 1
                            processing_results.append(
                                {
                                    "submission_id": "unknown",
                                    "filename": f"unknown_file_{i}",
                                    "success": False,
                                    "error": "Invalid submission object - submission not found in database",
                                }
                            )
                            continue

                        # Update progress
                        progress_store[task_id].update(
                            {
                                "status": "processing",
                                "progress": int((i / total_count) * 100),
                                "message": f"Processing {submission.filename}...",
                                "current_file": submission.filename,
                                "processed_count": i,
                            }
                        )

                        try:
                            # Double-check submission still exists in database
                            db_submission = db.session.get(Submission, submission.id)
                            if not db_submission:
                                logger.error(
                                    f"Submission {submission.id} no longer exists in database"
                                )
                                failed_count += 1
                                processing_results.append(
                                    {
                                        "submission_id": submission.id,
                                        "filename": submission.filename,
                                        "success": False,
                                        "error": "Submission was deleted or no longer exists",
                                    }
                                )
                                continue

                            # Create processing request
                            processing_request = ProcessingRequest(
                                guide_id=guide_id,
                                submission_id=submission.id,
                                user_id=user_id,
                                options={
                                    "max_questions_to_answer": max_questions_to_answer
                                },
                            )

                            # Process submission with LLM
                            logger.info(
                                f"Processing submission {submission.id} with guide {guide_id}"
                            )
                            result = asyncio.run(
                                core_service.process_submission(processing_request)
                            )

                            if result.success:
                                successful_count += 1
                                processing_results.append(
                                    {
                                        "submission_id": submission.id,
                                        "filename": submission.filename,
                                        "success": True,
                                        "score": result.score,
                                        "result_id": result.result_id,
                                    }
                                )
                                logger.info(
                                    f"Successfully processed {submission.filename} - Score: {result.score}"
                                )
                            else:
                                failed_count += 1
                                processing_results.append(
                                    {
                                        "submission_id": submission.id,
                                        "filename": submission.filename,
                                        "success": False,
                                        "error": result.error,
                                    }
                                )
                                logger.error(
                                    f"Failed to process {submission.filename}: {result.error}"
                                )

                        except Exception as e:
                            failed_count += 1
                            # Safe access to submission attributes with fallbacks
                            submission_id = getattr(submission, "id", "unknown")
                            filename = getattr(
                                submission, "filename", f"unknown_file_{i}"
                            )

                            processing_results.append(
                                {
                                    "submission_id": submission_id,
                                    "filename": filename,
                                    "success": False,
                                    "error": str(e),
                                }
                            )
                            logger.error(f"Exception processing {filename}: {e}")

                        # Update counts
                        progress_store[task_id].update(
                            {
                                "successful_count": successful_count,
                                "failed_count": failed_count,
                                "processed_count": i + 1,
                            }
                        )

                    # Mark as completed
                    progress_store[task_id].update(
                        {
                            "status": "completed",
                            "progress": 100,
                            "message": f"Processing completed: {successful_count} successful, {failed_count} failed",
                            "current_file": "",
                            "results": processing_results,
                        }
                    )

                    logger.info(f"Enhanced processing completed for task {task_id}")

                except Exception as e:
                    logger.error(f"Background processing failed: {e}")
                    progress_store[task_id].update(
                        {
                            "status": "failed",
                            "progress": 0,
                            "message": f"Processing failed: {str(e)}",
                            "error": str(e),
                        }
                    )

        # Start background thread
        thread = threading.Thread(target=background_processing)
        thread.daemon = True
        thread.start()

        return jsonify(
            {
                "success": True,
                "task_id": task_id,
                "message": "Processing started successfully",
                "guide_title": guide.title,
                "submission_count": len(valid_submissions),
            }
        )

    except Exception as e:
        logger.error(f"Failed to start enhanced processing: {e}")
        return jsonify({"success": False, "error": "Failed to start processing"}), 500


@main_bp.route("/api/enhanced-processing/progress/<task_id>", methods=["GET"])
@login_required
def api_enhanced_processing_progress(task_id):
    """API endpoint to get enhanced processing progress."""
    try:
        if task_id not in progress_store:
            return jsonify({"success": False, "error": "Task not found"}), 404

        progress_data = progress_store[task_id]

        # Clean up completed tasks after some time (optional)
        if progress_data["status"] in ["completed", "failed"]:
            pass

        return jsonify(
            {
                "success": True,
                "task_id": task_id,
                "status": progress_data["status"],
                "progress": progress_data["progress"],
                "message": progress_data["message"],
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
        logger.error(f"Failed to get processing progress: {e}")
        return jsonify({"success": False, "error": "Failed to get progress"}), 500


@main_bp.route("/api/select-guide", methods=["POST"])
@login_required
def api_select_guide():
    """API endpoint to select an active marking guide with duplicate verification."""
    try:
        data = request.get_json()
        if not data or "guide_id" not in data:
            return jsonify({"success": False, "message": "Guide ID is required"}), 400

        guide_id = data["guide_id"]
        guide_name = data.get("guide_name", "Unknown Guide")

        logger.info(
            f"Selecting guide {guide_id} ({guide_name}) for user {current_user.id}"
        )

        # Verify the guide exists and belongs to the user
        guide = MarkingGuide.query.filter_by(
            id=guide_id,
            user_id=current_user.id,
            is_active=True,  # Only allow selection of active guides
        ).first()

        if not guide:
            logger.warning(
                f"Guide {guide_id} not found or inactive for user {current_user.id}"
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Guide not found or has been deactivated",
                    }
                ),
                404,
            )

        # Check for duplicate guides before setting as active
        duplicate_guides = MarkingGuide.query.filter(
            MarkingGuide.user_id == current_user.id,
            MarkingGuide.content_hash == guide.content_hash,
            MarkingGuide.id != guide_id,
            MarkingGuide.is_active == True,
        ).all()

        if duplicate_guides:
            duplicate_names = [dupe.title for dupe in duplicate_guides]
            logger.warning(
                f"Duplicate guides found for user {current_user.id}: {duplicate_names}"
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f'Duplicate guides detected: {", ".join(duplicate_names)}. Please remove duplicates before selecting this guide.',
                        "duplicates": duplicate_names,
                    }
                ),
                409,
            )

        # Verify guide has valid content and questions
        if not guide.questions or len(guide.questions) == 0:
            logger.warning(
                f"Guide {guide_id} has no questions for user {current_user.id}"
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "This guide has no questions defined. Please edit the guide to add questions before using it.",
                    }
                ),
                400,
            )

        # Check if guide has valid total marks
        if not guide.total_marks or guide.total_marks <= 0:
            logger.warning(
                f"Guide {guide_id} has invalid total marks for user {current_user.id}"
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "This guide has invalid total marks. Please edit the guide to set proper mark allocations.",
                    }
                ),
                400,
            )

        # Store the selected guide in the session
        from flask import session

        session["active_guide_id"] = guide_id
        session["active_guide_name"] = guide.title
        session["active_guide_total_marks"] = guide.total_marks
        session["active_guide_questions_count"] = len(guide.questions)

        # Update guide's last used timestamp
        guide.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info(
            f"Successfully selected guide {guide_id} for user {current_user.id}"
        )
        return jsonify(
            {
                "success": True,
                "message": f'"{guide.title}" is now your active marking guide',
                "guide_info": {
                    "id": guide.id,
                    "title": guide.title,
                    "total_marks": guide.total_marks,
                    "questions_count": len(guide.questions),
                    "description": guide.description,
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to select guide: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"success": False, "message": "Failed to select guide"}), 500


@main_bp.route("/api/clear-guide", methods=["POST"])
@login_required
def api_clear_guide():
    """API endpoint to clear the active marking guide."""
    try:
        logger.info(f"Clearing active guide for user {current_user.id}")

        from flask import session

        session.pop("active_guide_id", None)
        session.pop("active_guide_name", None)
        session.pop("active_guide_total_marks", None)
        session.pop("active_guide_questions_count", None)

        logger.info(f"Successfully cleared active guide for user {current_user.id}")
        return jsonify(
            {"success": True, "message": "Active guide cleared successfully"}
        )

    except Exception as e:
        logger.error(f"Failed to clear guide: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to clear guide"}), 500


@main_bp.route("/api/check-guide-duplicates/<guide_id>")
@login_required
def api_check_guide_duplicates(guide_id):
    """API endpoint to check for duplicate guides before selection."""
    try:
        # Get the guide to check
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id, is_active=True
        ).first()

        if not guide:
            return (
                jsonify({"success": False, "message": "Guide not found or inactive"}),
                404,
            )

        # Check for duplicates based on content hash
        duplicates = []
        if guide.content_hash:
            duplicate_guides = MarkingGuide.query.filter(
                MarkingGuide.user_id == current_user.id,
                MarkingGuide.content_hash == guide.content_hash,
                MarkingGuide.id != guide_id,
                MarkingGuide.is_active == True,
            ).all()

            duplicates = [
                {
                    "id": dupe.id,
                    "title": dupe.title,
                    "created_at": (
                        dupe.created_at.isoformat() if dupe.created_at else None
                    ),
                }
                for dupe in duplicate_guides
            ]

        # Check for similar titles (potential duplicates)
        similar_guides = MarkingGuide.query.filter(
            MarkingGuide.user_id == current_user.id,
            MarkingGuide.title.ilike(f"%{guide.title}%"),
            MarkingGuide.id != guide_id,
            MarkingGuide.is_active == True,
        ).all()

        similar = [
            {
                "id": sim.id,
                "title": sim.title,
                "created_at": sim.created_at.isoformat() if sim.created_at else None,
            }
            for sim in similar_guides
            if sim.id not in [d["id"] for d in duplicates]  # Exclude exact duplicates
        ]

        return jsonify(
            {
                "success": True,
                "guide": {
                    "id": guide.id,
                    "title": guide.title,
                    "total_marks": guide.total_marks,
                    "questions_count": len(guide.questions) if guide.questions else 0,
                },
                "duplicates": duplicates,
                "similar": similar,
                "has_duplicates": len(duplicates) > 0,
                "has_similar": len(similar) > 0,
            }
        )

    except Exception as e:
        logger.error(f"Error checking guide duplicates: {e}", exc_info=True)
        return (
            jsonify({"success": False, "message": "Failed to check for duplicates"}),
            500,
        )


@main_bp.route("/api/validate-guide-before-save", methods=["POST"])
@login_required
def api_validate_guide_before_save():
    """API endpoint to validate guide before saving to prevent duplicates."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        title = data.get("title", "").strip()
        content_hash = data.get("content_hash", "").strip()
        guide_id = data.get("guide_id")  # For updates

        if not title:
            return (
                jsonify({"success": False, "message": "Guide title is required"}),
                400,
            )

        validation_errors = []
        warnings = []

        # Check for duplicate titles
        title_query = MarkingGuide.query.filter(
            MarkingGuide.user_id == current_user.id,
            MarkingGuide.title == title,
            MarkingGuide.is_active == True,
        )

        if guide_id:
            title_query = title_query.filter(MarkingGuide.id != guide_id)

        existing_title = title_query.first()
        if existing_title:
            validation_errors.append(
                {
                    "field": "title",
                    "message": f'A guide with the title "{title}" already exists',
                    "existing_guide_id": existing_title.id,
                }
            )

        # Check for duplicate content
        if content_hash:
            content_query = MarkingGuide.query.filter(
                MarkingGuide.user_id == current_user.id,
                MarkingGuide.content_hash == content_hash,
                MarkingGuide.is_active == True,
            )

            if guide_id:
                content_query = content_query.filter(MarkingGuide.id != guide_id)

            existing_content = content_query.first()
            if existing_content:
                validation_errors.append(
                    {
                        "field": "content",
                        "message": f'A guide with identical content already exists: "{existing_content.title}"',
                        "existing_guide_id": existing_content.id,
                    }
                )

        # Check for similar titles (warnings)
        similar_titles = MarkingGuide.query.filter(
            MarkingGuide.user_id == current_user.id,
            MarkingGuide.title.ilike(f"%{title}%"),
            MarkingGuide.title != title,
            MarkingGuide.is_active == True,
        ).all()

        if similar_titles:
            similar_names = [guide.title for guide in similar_titles[:3]]  # Limit to 3
            warnings.append(
                {
                    "field": "title",
                    "message": f'Similar guide titles found: {", ".join(similar_names)}',
                    "similar_guides": [
                        {"id": guide.id, "title": guide.title}
                        for guide in similar_titles[:3]
                    ],
                }
            )

        return jsonify(
            {
                "success": len(validation_errors) == 0,
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "warnings": warnings,
                "message": (
                    "Validation completed"
                    if len(validation_errors) == 0
                    else "Validation failed"
                ),
            }
        )

    except Exception as e:
        logger.error(f"Error validating guide: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to validate guide"}), 500


@main_bp.route("/api/download-guide/<guide_id>")
@login_required
def api_download_guide(guide_id):
    """API endpoint to download the original marking guide file."""
    try:
        logger.info(
            f"Download request for guide {guide_id} from user {current_user.id}"
        )

        # Get the guide
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            logger.warning(f"Guide {guide_id} not found for user {current_user.id}")
            flash("Guide not found", "error")
            return redirect(url_for("main.guides"))

        if not guide.file_path or not os.path.exists(guide.file_path):
            logger.warning(f"File not found for guide {guide_id}: {guide.file_path}")
            flash("Original file not found", "error")
            return redirect(url_for("main.guide_details", guide_id=guide_id))

        logger.info(f"Serving file: {guide.file_path}")

        # Send the file
        from flask import send_file

        return send_file(
            guide.file_path,
            as_attachment=True,
            download_name=guide.filename,
            mimetype="application/octet-stream",
        )

    except Exception as e:
        logger.error(f"Error downloading guide {guide_id}: {e}", exc_info=True)
        flash("Error downloading file", "error")
        return redirect(url_for("main.guide_details", guide_id=guide_id))


@main_bp.route("/guides/<guide_id>/edit", methods=["GET", "POST"])
@login_required
def edit_guide(guide_id):
    """Edit a marking guide."""
    try:
        # Get the guide
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            logger.warning(f"Guide {guide_id} not found for user {current_user.id}")
            flash("Guide not found", "error")
            return redirect(url_for("main.guides"))

        if request.method == "POST":
            # Handle form submission
            try:
                # Update basic information
                guide.title = request.form.get("title", guide.title)
                guide.description = request.form.get("description", guide.description)

                # Handle questions update
                questions_data = []
                question_count = int(request.form.get("question_count", 0))

                for i in range(question_count):
                    question_text = request.form.get(f"question_{i}_text", "")
                    question_marks = float(request.form.get(f"question_{i}_marks", 0))
                    question_criteria = request.form.get(f"question_{i}_criteria", "")
                    question_answer = request.form.get(f"question_{i}_answer", "")

                    if question_text:  # Only add non-empty questions
                        questions_data.append(
                            {
                                "number": i + 1,
                                "text": question_text,
                                "marks": question_marks,
                                "criteria": question_criteria,
                                "answer": question_answer,
                            }
                        )

                guide.questions = questions_data
                guide.total_marks = sum(q.get("marks", 0) for q in questions_data)

                db.session.commit()

                logger.info(f"Successfully updated guide {guide_id}")
                flash("Guide updated successfully!", "success")
                return redirect(url_for("main.guide_details", guide_id=guide_id))

            except Exception as e:
                logger.error(f"Error updating guide {guide_id}: {e}", exc_info=True)
                db.session.rollback()
                flash("Error updating guide. Please try again.", "error")

        return render_template("edit_guide.html", guide=guide)

    except Exception as e:
        logger.error(f"Error loading edit guide page: {e}", exc_info=True)
        flash("Error loading guide editor", "error")
        return redirect(url_for("main.guides"))


@main_bp.route("/guides/<guide_id>/details")
@login_required
def guide_details(guide_id):
    """Display detailed view of a specific marking guide."""
    try:
        logger.info(
            f"Loading guide details for guide {guide_id} and user {current_user.id}"
        )

        # Get the specific guide
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            logger.warning(f"Guide {guide_id} not found for user {current_user.id}")
            flash("Guide not found", "error")
            return redirect(url_for("main.guides"))

        logger.info(f"Found guide: {guide.title}")

        return render_template(
            "guide_details.html",
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
        )

    except Exception as e:
        logger.error(f"Error loading guide details: {e}", exc_info=True)
        flash("Error loading guide details", "error")
        return redirect(url_for("main.guides"))


@main_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Settings page."""
    try:
        from src.database.models import UserSettings

        if request.method == "POST":
            # Handle settings form submission
            try:
                # Get or create user settings
                user_settings = UserSettings.get_or_create_for_user(current_user.id)

                # Get form data with validation
                max_file_size = request.form.get("max_file_size", 100, type=int)
                if max_file_size < 1 or max_file_size > 500:
                    max_file_size = 100

                allowed_formats = request.form.getlist("allowed_formats")
                if not allowed_formats:
                    allowed_formats = [
                        ".pdf",
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".docx",
                        ".doc",
                        ".txt",
                    ]

                llm_api_key = request.form.get("llm_api_key", "").strip()
                llm_model = request.form.get("llm_model", "deepseek-chat").strip()
                ocr_api_key = request.form.get("ocr_api_key", "").strip()
                ocr_api_url = request.form.get("ocr_api_url", "").strip()
                theme = request.form.get("theme", "light")
                language = request.form.get("language", "en")
                notification_level = request.form.get("notification_level", "info")

                # Additional settings
                auto_save = request.form.get("auto_save") == "on"
                show_tooltips = request.form.get("show_tooltips") == "on"
                results_per_page = request.form.get("results_per_page", 10, type=int)
                if results_per_page < 5 or results_per_page > 100:
                    results_per_page = 10

                # Update settings
                user_settings.max_file_size = max_file_size
                user_settings.allowed_formats_list = allowed_formats
                user_settings.set_llm_api_key(llm_api_key)
                user_settings.llm_model = llm_model
                user_settings.set_ocr_api_key(ocr_api_key)
                user_settings.ocr_api_url = ocr_api_url
                user_settings.theme = theme
                user_settings.language = language
                user_settings.notification_level = notification_level
                user_settings.auto_save = auto_save
                user_settings.show_tooltips = show_tooltips
                user_settings.results_per_page = results_per_page

                # Save to database
                db.session.commit()

                flash("Settings saved successfully!", "success")
                return redirect(url_for("main.settings"))

            except Exception as e:
                logger.error(f"Error saving settings: {e}")
                db.session.rollback()
                flash("Error saving settings. Please try again.", "error")
                return redirect(url_for("main.settings"))

        # GET request - load user settings
        user_settings = UserSettings.get_or_create_for_user(current_user.id)
        settings_data = user_settings.to_dict()

        # Get configuration from service
        themes = app_config.get_available_themes()
        languages = app_config.get_available_languages()
        notification_levels = app_config.get_notification_levels()
        available_formats = app_config.get_allowed_file_types()

        # Check service status
        service_status = get_actual_service_status()

        return render_template(
            "settings.html",
            settings=settings_data,
            themes=themes,
            languages=languages,
            notification_levels=notification_levels,
            available_formats=available_formats,
            service_status=service_status,
            csrf_token=generate_csrf_token(),
        )

    except Exception as e:
        logger.error(f"Settings page error: {e}")
        flash("Error loading settings", "error")
    # Get configuration from service (fallback case)
    themes = app_config.get_available_themes()
    languages = app_config.get_available_languages()
    notification_levels = app_config.get_notification_levels()
    available_formats = app_config.get_allowed_file_types()

    return render_template(
        "settings.html",
        settings=UserSettings.get_default_settings(),
        themes=themes,
        languages=languages,
        notification_levels=notification_levels,
        available_formats=available_formats,
        service_status=get_actual_service_status(),
        csrf_token=generate_csrf_token(),
    )


def generate_csrf_token():
    """Generate CSRF token for forms."""
    try:
        from flask_wtf.csrf import generate_csrf

        return generate_csrf()
    except Exception:
        return None


def check_service_status():
    """Check the status of various services."""
    try:
        status = {}

        # Check database
        try:
            db.session.execute(db.text("SELECT 1"))
            db.session.commit()
            status["database"] = True
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            status["database"] = False

        # Check LLM service
        status["llm_service"] = check_llm_service_status()

        # Check OCR service
        status["ocr_service"] = check_ocr_service_status()

        # Check AI service (general AI functionality)
        status["ai_service"] = check_ai_service_status()

        # Check file storage
        try:
            upload_dir = os.path.join(current_app.root_path, "..", "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            status["file_storage"] = os.path.exists(upload_dir) and os.access(
                upload_dir, os.W_OK
            )
        except Exception as e:
            logger.error(f"File storage check failed: {e}")
            status["file_storage"] = False

        return status

    except Exception as e:
        logger.error(f"Error checking service status: {e}")
        return {}


def check_llm_service_status():
    """Check if LLM service is available."""
    try:
        from src.database.models import UserSettings
        from src.services.consolidated_llm_service import ConsolidatedLLMService

        # Try to initialize LLM service
        ConsolidatedLLMService()

        # Check if we have API configuration
        try:
            default_settings = UserSettings.get_default_settings()
            if not default_settings.get("llm_api_key"):
                # Check if there are any user settings with API keys
                user_with_key = UserSettings.query.filter(
                    UserSettings.llm_api_key_encrypted.isnot(None)
                ).first()
                if not user_with_key:
                    return False
        except AttributeError:
            # If get_default_settings doesn't exist, just check for any user with API key
            user_with_key = UserSettings.query.filter(
                UserSettings.llm_api_key_encrypted.isnot(None)
            ).first()
            if not user_with_key:
                return False

        return True

    except Exception as e:
        logger.error(f"LLM service check failed: {e}")
        return False


def check_ocr_service_status():
    """Check if OCR service is available."""
    try:
        from src.services.consolidated_ocr_service import ConsolidatedOCRService

        # Try to initialize OCR service
        ConsolidatedOCRService()

        # Check if Tesseract is available (fallback OCR)
        import subprocess

        try:
            result = subprocess.run(
                ["tesseract", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Check if we have API configuration for external OCR
        from src.database.models import UserSettings

        user_with_ocr = UserSettings.query.filter(
            UserSettings.ocr_api_key_encrypted.isnot(None)
        ).first()

        return user_with_ocr is not None

    except Exception as e:
        logger.error(f"OCR service check failed: {e}")
        return False


def check_ai_service_status():
    """Check if AI service is available."""
    try:
        # AI service is available if either LLM or OCR is available
        return check_llm_service_status() or check_ocr_service_status()

    except Exception as e:
        logger.error(f"AI service check failed: {e}")
        return False


@main_bp.route("/api/settings", methods=["GET", "POST"])
@login_required
def api_settings():
    """API endpoint for settings management."""
    try:
        from src.database.models import UserSettings

        if request.method == "GET":
            # Get user settings
            user_settings = UserSettings.get_or_create_for_user(current_user.id)
            return jsonify({"success": True, "settings": user_settings.to_dict()})

        elif request.method == "POST":
            # Update user settings
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "No data provided"}), 400

            user_settings = UserSettings.get_or_create_for_user(current_user.id)

            # Update settings with validation
            if "max_file_size" in data:
                max_file_size = int(data["max_file_size"])
                if 1 <= max_file_size <= 500:
                    user_settings.max_file_size = max_file_size

            if "allowed_formats" in data:
                if isinstance(data["allowed_formats"], list):
                    user_settings.allowed_formats_list = data["allowed_formats"]

            if "llm_api_key" in data:
                user_settings.set_llm_api_key(data["llm_api_key"])

            if "llm_model" in data:
                user_settings.llm_model = data["llm_model"]

            if "ocr_api_key" in data:
                user_settings.set_ocr_api_key(data["ocr_api_key"])

            if "ocr_api_url" in data:
                user_settings.ocr_api_url = data["ocr_api_url"]

            if "theme" in data:
                if data["theme"] in ["light", "dark", "auto"]:
                    user_settings.theme = data["theme"]

            if "language" in data:
                if data["language"] in ["en", "es", "fr", "de"]:
                    user_settings.language = data["language"]

            if "notification_level" in data:
                if data["notification_level"] in ["error", "warning", "info"]:
                    user_settings.notification_level = data["notification_level"]

            if "auto_save" in data:
                user_settings.auto_save = bool(data["auto_save"])

            if "show_tooltips" in data:
                user_settings.show_tooltips = bool(data["show_tooltips"])

            if "results_per_page" in data:
                results_per_page = int(data["results_per_page"])
                if 5 <= results_per_page <= 100:
                    user_settings.results_per_page = results_per_page

            # Save to database
            db.session.commit()

            return jsonify(
                {
                    "success": True,
                    "message": "Settings updated successfully",
                    "settings": user_settings.to_dict(),
                }
            )

    except Exception as e:
        logger.error(f"Error in settings API: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": "Failed to update settings"}), 500


@main_bp.route("/api/settings/reset", methods=["POST"])
@login_required
def api_settings_reset():
    """API endpoint to reset settings to defaults."""
    try:
        from src.database.models import UserSettings

        user_settings = UserSettings.get_or_create_for_user(current_user.id)

        # Reset to defaults
        defaults = UserSettings.get_default_settings()
        user_settings.max_file_size = defaults["max_file_size"]
        user_settings.allowed_formats_list = defaults["allowed_formats"]
        user_settings.set_llm_api_key("")
        user_settings.llm_model = defaults["llm_model"]
        user_settings.set_ocr_api_key("")
        user_settings.ocr_api_url = ""
        user_settings.theme = defaults["theme"]
        user_settings.language = defaults["language"]
        user_settings.notification_level = defaults["notification_level"]
        user_settings.auto_save = defaults["auto_save"]
        user_settings.show_tooltips = defaults["show_tooltips"]
        user_settings.results_per_page = defaults["results_per_page"]

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Settings reset to defaults",
                "settings": user_settings.to_dict(),
            }
        )

    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": "Failed to reset settings"}), 500


@main_bp.route("/api/settings/export", methods=["GET"])
@login_required
def api_settings_export():
    """API endpoint to export user settings."""
    try:
        from datetime import datetime

        from src.database.models import UserSettings

        user_settings = UserSettings.get_or_create_for_user(current_user.id)
        settings_data = user_settings.to_dict()

        export_data = {
            k: v
            for k, v in settings_data.items()
            if k not in ["llm_api_key", "ocr_api_key"]
        }

        # Add metadata
        export_package = {
            "export_date": datetime.now().isoformat(),
            "user_id": current_user.id,
            "settings": export_data,
        }

        return jsonify(
            {
                "success": True,
                "data": export_package,
                "filename": f'settings_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
            }
        )

    except Exception as e:
        logger.error(f"Error exporting settings: {e}")
        return jsonify({"success": False, "error": "Failed to export settings"}), 500


@main_bp.route("/api/service-status", methods=["GET"])
@login_required
def api_service_status():
    """API endpoint to get service status."""
    try:
        status = check_service_status()
        return jsonify({"success": True, "status": status})

    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        return jsonify({"success": False, "error": "Failed to get service status"}), 500


@main_bp.route("/health")
def health():
    """Health check endpoint."""
    try:
        # Check database
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))

        # Check core service
        service_health = "available" if hasattr(core_service, 'get_health_status') else "unavailable"

        return jsonify(
            {
                "status": "healthy",
                "database": "connected",
                "core_service": service_health,
            }
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503



@main_bp.route("/guide/<guide_id>")
@login_required
def guide_detail(guide_id):
    """Display detailed view of a specific marking guide."""
    try:
        guide = MarkingGuide.query.filter_by(
            id=guide_id, user_id=current_user.id
        ).first()

        if not guide:
            flash("Guide not found", "error")
            return redirect(url_for("main.guides"))

        return render_template("guide_details.html", guide=guide)

    except Exception as e:
        logger.error(f"Error loading guide details for {guide_id}: {e}")
        flash("Error loading guide details", "error")
        return redirect(url_for("main.guides"))