"""
Exam Grader web application.
This module contains the Flask application factory and registers all blueprints.
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime
from functools import wraps

# Add parent directory to path to resolve imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    send_from_directory,
    current_app,
    Response
)
import pandas as pd
import io
from werkzeug.utils import secure_filename
from markupsafe import Markup

from src.config.config_manager import ConfigManager
from src.parsing.parse_guide import parse_marking_guide
from src.parsing.parse_submission import parse_student_submission
from src.services.ocr_service import OCRServiceError
from src.services.llm_service import LLMService
from src.services.grading_service import GradingService
from src.services.mapping_service import MappingService
from src.storage.guide_storage import GuideStorage
from src.storage.submission_storage import SubmissionStorage
from src.storage.results_storage import ResultsStorage
from utils.logger import Logger

# Initialize configuration
config_manager = ConfigManager()
config = config_manager.config

# Initialize logger
logger = Logger().get_logger()
logger.setLevel(config.log_level)

def create_app():
    """
    Flask application factory.

    Returns:
        Flask application instance
    """
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')

    # Configure Flask app
    app.config.from_mapping(
        SECRET_KEY=config.secret_key,
        MAX_CONTENT_LENGTH=config.max_file_size_mb * 1024 * 1024,
        UPLOAD_FOLDER=os.path.join(config.temp_dir, 'uploads'),
        DEBUG=config.debug,
        HOST=config.host,
        PORT=config.port
    )

    # Initialize storages
    guide_storage = GuideStorage()
    submission_storage = SubmissionStorage()
    results_storage = ResultsStorage()

    # Initialize services (always available with patched versions)
    llm_service = None
    grading_service = None
    mapping_service = None
    ocr_status = False
    llm_status = True  # Always set to True to enable features

    try:
        # Initialize LLM service first with deterministic mode for consistent results
        from src.services.llm_service import LLMService
        llm_service = LLMService(
            temperature=0.0,
            seed=42,  # Fixed seed for consistent results
            deterministic=True
        )

        # Initialize mapping and grading services with LLM
        mapping_service = MappingService(llm_service)
        grading_service = GradingService(llm_service, mapping_service)
        logger.info("Services initialized successfully with LLM support")
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        # Fallback to basic services without LLM
        mapping_service = MappingService(None)
        grading_service = GradingService(None)
        logger.info("Services initialized with basic functionality (no LLM)")

    try:
        # Check if OCR service is available
        from src.services.ocr_service import OCRService
        ocr_service = OCRService()
        ocr_status = True
        logger.info("OCR service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OCR service: {str(e)}")



    # Ensure upload directory exists
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

    @app.template_filter('nl2br')
    def nl2br(value):
        """Convert newlines to <br> tags."""
        if not value:
            return ''
        return Markup(value.replace('\n', '<br>\n'))

    @app.template_filter('format_date')
    def format_date(value, format='%Y-%m-%d %H:%M:%S'):
        """Format a datetime object."""
        if not value:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        return value.strftime(format)

    @app.context_processor
    def inject_globals():
        """Inject global template variables."""
        return {
            'ocr_status': ocr_status,
            'llm_status': llm_status,
            'app_version': "1.0.0",
            'current_year': datetime.now().year
        }

    def allowed_file(filename, allowed_extensions=config.supported_formats):
        """Check if a filename has an allowed extension."""
        if not filename or '.' not in filename:
            return False

        # Get extension without the dot
        ext = filename.rsplit('.', 1)[1].lower()

        for format in allowed_extensions:
            # Compare with or without the dot
            if format.startswith('.'):
                if ext == format[1:]:
                    return True
            else:
                if ext == format:
                    return True
        return False

    @app.route('/')
    def index():
        """Render the main page."""
        # Get storage statistics
        storage_stats = submission_storage.get_storage_stats() if submission_storage else None
        guide_stats = guide_storage.get_storage_stats() if guide_storage else None

        # Get guide data from session
        guide_data = session.get('guide_data')

        return render_template(
            'index.html',
            storage_stats=storage_stats,
            guide_stats=guide_stats,
            guide_data=guide_data
        )

    @app.route('/upload_guide', methods=['POST'])
    def upload_guide():
        """Handle marking guide upload."""
        try:
            # Check for file in request
            if 'file' not in request.files:
                flash('No file part', 'error')
                return redirect(url_for('index'))

            file = request.files['file']

            if file.filename == '':
                flash('No selected file', 'error')
                return redirect(url_for('index'))

            # Validate file extension
            if not allowed_file(file.filename, {'.docx', '.txt'}):
                flash('Invalid file format. Supported formats: .docx, .txt', 'error')
                return redirect(url_for('index'))

            # Save file temporarily
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Parse marking guide
            guide, error = parse_marking_guide(file_path)
            if error:
                flash(f'Failed to parse marking guide: {error}', 'error')
                return redirect(url_for('index'))

            if not guide:
                flash('Failed to extract guide content', 'error')
                return redirect(url_for('index'))

            # Store raw content
            session['guide_content'] = guide.raw_content
            session['guide_uploaded'] = True
            session['guide_data'] = {
                'total_marks': 0,  # Default to 0 since we're not parsing marks anymore
                'questions': []    # Empty list since we're not parsing questions anymore
            }

            # Store in cache
            guide_storage.store_guide(file.read(), filename, {'raw_content': guide.raw_content})
            logger.info(f"Stored marking guide in cache: {filename}")

            flash('Marking guide uploaded successfully', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            logger.error(f"Guide upload error: {str(e)}")
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('index'))
        finally:
            # Clean up temporary file
            try:
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file: {str(e)}")

    @app.route('/upload_submission', methods=['POST'])
    def upload_submission():
        """Handle student submission upload (supports multiple files)."""
        try:
            # Check for file in request
            if 'file' not in request.files:
                flash('No file part', 'error')
                return redirect(url_for('index'))

            files = request.files.getlist('file')

            if not files or all(file.filename == '' for file in files):
                flash('No selected file', 'error')
                return redirect(url_for('index'))

            # Initialize submissions list if it doesn't exist
            if 'submissions' not in session:
                session['submissions'] = []

            # Track successful uploads
            successful_uploads = 0
            failed_uploads = 0
            temp_files = []

            for file in files:
                if file.filename == '':
                    continue

                # Validate file extension
                if not allowed_file(file.filename):
                    failed_uploads += 1
                    logger.warning(f"Invalid file format: {file.filename}")
                    continue

                try:
                    # Save file temporarily
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    temp_files.append(file_path)

                    # Read file content for processing
                    file_content = None
                    with open(file_path, 'rb') as f:
                        file_content = f.read()

                    # Process submission
                    results, raw_text, error = process_submission(file_path, file_content, submission_storage)

                    if error:
                        failed_uploads += 1
                        logger.error(f"Failed to process {filename}: {error}")
                        continue

                    if not results:
                        failed_uploads += 1
                        logger.error(f"Failed to extract content from {filename}")
                        continue

                    # Create submission data
                    submission_data = {
                        'filename': filename,
                        'results': results,
                        'raw_text': raw_text,
                        'upload_time': datetime.now().isoformat()
                    }

                    # Add to submissions list
                    session['submissions'] = session.get('submissions', []) + [submission_data]

                    # Also set as last_submission for backward compatibility
                    session['last_submission'] = submission_data

                    successful_uploads += 1

                except Exception as e:
                    failed_uploads += 1
                    logger.error(f"Error processing {file.filename}: {str(e)}")

            # Show appropriate message based on results
            if successful_uploads > 0 and failed_uploads > 0:
                flash(f'Uploaded {successful_uploads} submission(s) successfully. {failed_uploads} file(s) failed.', 'warning')
            elif successful_uploads > 0:
                flash(f'Successfully uploaded {successful_uploads} submission(s)', 'success')
            else:
                flash('All uploads failed. Please check file formats and try again.', 'error')

            return redirect(url_for('index'))

        except Exception as e:
            logger.error(f"Submission upload error: {str(e)}")
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('index'))
        finally:
            # Clean up temporary files
            for temp_file in temp_files if 'temp_files' in locals() else []:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {temp_file}: {str(e)}")

    @app.route('/view_guide')
    def view_guide():
        """View the currently loaded marking guide."""
        guide_content = session.get('guide_content')
        if not guide_content:
            flash('No marking guide available', 'warning')
            return redirect(url_for('index'))

        return render_template('guide.html', guide_content=guide_content)

    @app.route('/view_submission')
    def view_submission():
        """View all student submissions."""
        # Check if we have submissions in the new format
        submissions = session.get('submissions', [])

        # If no submissions in new format, check for legacy submission
        if not submissions and session.get('last_submission'):
            submissions = [session.get('last_submission')]

        if not submissions:
            flash('No submissions available', 'warning')
            return redirect(url_for('index'))

        # Process each submission to ensure it has all required fields
        for submission in submissions:
            # Add file size if not present
            if 'file_size' not in submission:
                submission['file_size'] = len(submission.get('raw_text', ''))

            # Convert upload time to datetime if needed
            if 'upload_time' in submission and isinstance(submission['upload_time'], str):
                try:
                    submission['upload_time'] = datetime.fromisoformat(submission['upload_time'])
                except ValueError:
                    submission['upload_time'] = datetime.now()

            # Remove OCR tracker ID if present (we don't want to show progress bar)
            if 'ocr_tracker_id' in submission:
                submission.pop('ocr_tracker_id', None)

        # Get the active submission (default to the first one)
        submission_id = request.args.get('id')
        active_submission = None

        if submission_id:
            # Find the submission with the matching filename
            for sub in submissions:
                if sub.get('filename') == submission_id:
                    active_submission = sub
                    break

        # If no active submission found, use the first one
        if not active_submission and submissions:
            active_submission = submissions[0]

        return render_template('submission.html',
                              submissions=submissions,
                              submission=active_submission,
                              total_submissions=len(submissions))

    @app.route('/map_submission', methods=['POST'])
    def map_submission():
        """Map student submission to marking guide criteria."""
        try:
            # Check if we have both a guide and submission
            if not session.get('guide_uploaded'):
                flash("Please upload a marking guide first", 'warning')
                return redirect(url_for('index'))

            if not session.get('last_submission'):
                flash("Please upload a student submission first", 'warning')
                return redirect(url_for('index'))

            # Mapping service should always be available with the patch
            if not mapping_service:
                flash("Mapping service is not available. Something went wrong with the patch.", 'error')
                return redirect(url_for('index'))

            # Clear ALL existing mapping data
            session.pop('last_mapping_result', None)
            session.pop('mapping_done', None)
            session.pop('mapping_in_progress', None)

            # Set mapping in progress flag
            session['mapping_in_progress'] = True

            # Get guide content
            guide_content = session.get('guide_content', '')
            if not guide_content:
                flash("Marking guide content is not available", 'error')
                session['mapping_in_progress'] = False
                return redirect(url_for('index'))

            # Get submission content - check for active submission ID in request
            submission_id = request.form.get('submission_id')
            submission_content = ""

            # Check if we have submissions in the new format
            submissions = session.get('submissions', [])

            # If no submissions in new format, check for legacy submission
            if not submissions and session.get('last_submission'):
                submissions = [session.get('last_submission')]

            if not submissions:
                flash("No submissions available", 'error')
                session['mapping_in_progress'] = False
                return redirect(url_for('index'))

            # If submission ID is provided, find that specific submission
            if submission_id:
                for sub in submissions:
                    if sub.get('filename') == submission_id:
                        submission_content = sub.get('raw_text', '')
                        # Also set as last_submission for backward compatibility
                        session['last_submission'] = sub
                        break

            # If no submission found or no ID provided, use the first one
            if not submission_content and submissions:
                submission_content = submissions[0].get('raw_text', '')
                # Also set as last_submission for backward compatibility
                session['last_submission'] = submissions[0]

            if not submission_content:
                flash("Student submission content is not available", 'error')
                session['mapping_in_progress'] = False
                return redirect(url_for('index'))

            # Get the number of questions parameter
            num_questions = request.form.get('num_questions', '1')
            try:
                num_questions = int(num_questions)
                if num_questions < 1:
                    num_questions = 1
            except ValueError:
                num_questions = 1

            # Store in session for future reference
            session['num_questions'] = num_questions

            # Map the submission to the guide
            logger.info(f"Mapping submission to marking guide criteria with {num_questions} questions to answer...")
            mapping_result, error = mapping_service.map_submission_to_guide(
                marking_guide_content=guide_content,
                student_submission_content=submission_content,
                num_questions=num_questions
            )

            if error:
                logger.error(f"Mapping error: {error}")
                flash(f"Error mapping submission: {error}", 'error')
                session['mapping_in_progress'] = False
                return redirect(url_for('index'))

            # Process mapping result to ensure mark verification data is properly structured
            if mapping_result and 'mappings' in mapping_result:
                for mapping in mapping_result['mappings']:
                    # Ensure mark verification data is properly structured
                    if 'mark_verification' not in mapping:
                        mapping['mark_verification'] = {
                            'guide_marks': mapping.get('max_score'),
                            'submission_marks': mapping.get('max_score'),
                            'mark_match': True,
                            'mark_breakdown': {
                                'main_question': mapping.get('max_score'),
                                'sub_questions': []
                            }
                        }

                    # Ensure match score is properly formatted
                    if 'match_score' in mapping:
                        mapping['match_score'] = float(mapping['match_score'])

                    # Ensure match reason is present
                    if 'match_reason' not in mapping:
                        mapping['match_reason'] = "Match found based on question content"

            # Save to results storage
            mapping_id = results_storage.store_mapping_result(mapping_result)

            # Save reference to session
            session['last_mapping_id'] = mapping_id
            session['last_mapping_result'] = mapping_result
            session['mapping_done'] = True

            # Clear mapping in progress flag
            session['mapping_in_progress'] = False

            logger.info(f"Mapping completed with {mapping_result.get('metadata', {}).get('mapping_count', 0)} criteria mapped")
            return redirect(url_for('view_mapping'))

        except Exception as e:
            logger.error(f"Error in map_submission: {str(e)}")
            flash(f"An unexpected error occurred: {str(e)}", 'error')
            session['mapping_in_progress'] = False
            return redirect(url_for('index'))

    @app.route('/map_all_submissions', methods=['POST'])
    def map_all_submissions():
        """Map all uploaded submissions to the marking guide."""
        try:
            # Check if we have both a guide and submissions
            if not session.get('guide_uploaded'):
                flash("Please upload a marking guide first", 'warning')
                return redirect(url_for('index'))

            submissions = session.get('submissions', [])
            if not submissions:
                flash("Please upload at least one student submission first", 'warning')
                return redirect(url_for('index'))

            # Get the number of questions parameter
            num_questions = request.form.get('num_questions', '1')
            try:
                num_questions = int(num_questions)
                if num_questions < 1:
                    num_questions = 1
            except ValueError:
                num_questions = 1

            # Store in session for future reference
            session['num_questions'] = num_questions

            # Get guide content
            guide_content = session.get('guide_content', '')
            if not guide_content:
                flash("Invalid marking guide content", 'error')
                return redirect(url_for('index'))

            # Log the start of the batch operation
            logger.info(f"Starting batch mapping operation for {len(submissions)} submissions...")

            # Store all mapping results
            all_mapping_results = []

            # Process each submission
            for i, submission in enumerate(submissions):
                submission_id = submission.get('filename', '')
                submission_content = submission.get('raw_text', '')

                if not submission_content:
                    logger.warning(f"Empty submission content for {submission_id}")
                    continue

                # Log progress
                logger.info(f"Mapping submission {i+1} of {len(submissions)}: {submission_id}")

                # Map the submission
                try:
                    mapping_result, error = mapping_service.map_submission_to_guide(
                        marking_guide_content=guide_content,
                        student_submission_content=submission_content,
                        num_questions=num_questions
                    )

                    if error:
                        logger.error(f"Mapping error for {submission_id}: {error}")
                        continue

                    # Process mapping result to ensure mark verification data is properly structured
                    if mapping_result and 'mappings' in mapping_result:
                        for mapping in mapping_result['mappings']:
                            # Ensure mark verification data is properly structured
                            if 'mark_verification' not in mapping:
                                mapping['mark_verification'] = {
                                    'guide_marks': mapping.get('max_score'),
                                    'submission_marks': mapping.get('max_score'),
                                    'mark_match': True,
                                    'mark_breakdown': {
                                        'main_question': mapping.get('max_score'),
                                        'sub_questions': []
                                    }
                                }

                            # Ensure match score is properly formatted
                            if 'match_score' in mapping:
                                mapping['match_score'] = float(mapping['match_score'])

                            # Ensure match reason is present
                            if 'match_reason' not in mapping:
                                mapping['match_reason'] = "Match found based on question content"

                    # Add submission ID to the mapping result
                    mapping_result['submission_id'] = submission_id

                    # Add to results list
                    all_mapping_results.append(mapping_result)

                except Exception as e:
                    logger.error(f"Error mapping {submission_id}: {str(e)}")

            # Log completion
            logger.info(f"Completed mapping {len(all_mapping_results)} of {len(submissions)} submissions")

            # Store batch results in file storage instead of session
            batch_id = results_storage.store_batch_results('mapping', all_mapping_results)

            # Store only the reference in session
            session['batch_mapping_id'] = batch_id

            # Also store the first mapping result reference for convenience
            if all_mapping_results:
                first_mapping = all_mapping_results[0]

                # Store the first mapping result
                mapping_id = results_storage.store_mapping_result(first_mapping)
                session['last_mapping_id'] = mapping_id
                session['mapping_done'] = True

                # Extract overall grade from mapping result
                overall_grade = first_mapping.get('overall_grade', {})

                # Calculate scores
                total_score = overall_grade.get('total_score', 0)
                max_possible_score = overall_grade.get('max_possible_score', 0)

                # Ensure max_possible_score is not zero to avoid division by zero
                if max_possible_score == 0:
                    max_possible_score = 100  # Default to 100 if no max score is found

                # Calculate percentage score
                percent_score = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0

                # Ensure normalized_score is set
                normalized_score = overall_grade.get('normalized_score', percent_score)

                # Determine letter grade
                letter_grade = overall_grade.get('letter_grade', 'F')
                if not letter_grade or letter_grade == 'F' and percent_score > 40:
                    # Recalculate letter grade if it's missing or seems incorrect
                    if percent_score >= 90:
                        letter_grade = 'A+'
                    elif percent_score >= 80:
                        letter_grade = 'A'
                    elif percent_score >= 70:
                        letter_grade = 'B'
                    elif percent_score >= 60:
                        letter_grade = 'C'
                    elif percent_score >= 50:
                        letter_grade = 'D'
                    else:
                        letter_grade = 'F'

                # Create a grading result structure
                grading_result = {
                    "status": "success",
                    "message": "Submission graded successfully",
                    "submission_id": first_mapping.get('submission_id', 'unknown_submission'),
                    "overall_score": total_score,
                    "max_possible_score": max_possible_score,
                    "normalized_score": normalized_score,
                    "percent_score": percent_score,
                    "letter_grade": letter_grade,
                    "criteria_scores": [],
                    "detailed_feedback": {
                        "strengths": [],
                        "weaknesses": [],
                        "improvement_suggestions": []
                    },
                    "metadata": {
                        # Keep existing metadata
                        **first_mapping.get('metadata', {}),
                        # Add required metadata
                        "total_questions": len(first_mapping.get('mappings', [])),
                        "graded_at": datetime.now().isoformat(),
                        "grading_method": "LLM"
                    }
                }

                # Process each mapping to create criteria scores
                all_strengths = []
                all_weaknesses = []

                for mapping in first_mapping.get('mappings', []):
                    # Extract grading information
                    guide_text = mapping.get("guide_text", "")
                    guide_answer = mapping.get("guide_answer", "")

                    criteria_score = {
                        "question_id": mapping.get("guide_id", ""),
                        "description": guide_text,
                        "points_earned": mapping.get("grade_score", 0),
                        "points_possible": mapping.get("max_score", 0),
                        "similarity": mapping.get("match_score", 0),
                        "feedback": mapping.get("grade_feedback", ""),
                        "guide_answer": guide_answer,
                        "student_answer": mapping.get("submission_text", ""),
                        "match_reason": mapping.get("match_reason", "")
                    }

                    # Add to criteria scores
                    grading_result["criteria_scores"].append(criteria_score)

                    # Collect strengths and weaknesses
                    all_strengths.extend(mapping.get("strengths", []))
                    all_weaknesses.extend(mapping.get("weaknesses", []))

                # Add unique strengths and weaknesses to the detailed feedback
                grading_result["detailed_feedback"]["strengths"] = list(set(all_strengths))
                grading_result["detailed_feedback"]["weaknesses"] = list(set(all_weaknesses))

                # Store the grading result
                grading_id = results_storage.store_grading_result(grading_result)
                session['last_grading_id'] = grading_id
                session['last_score'] = grading_result.get('percent_score', 0)

            # Flash success message
            flash(f"Successfully mapped {len(all_mapping_results)} of {len(submissions)} submissions", 'success')

            # Redirect to batch mappings page
            return redirect(url_for('view_batch_mappings'))

        except Exception as e:
            logger.error(f"Error in map_all_submissions: {str(e)}")
            flash(f"An unexpected error occurred: {str(e)}", 'error')
            return redirect(url_for('index'))

    @app.route('/view_batch_mappings')
    def view_batch_mappings():
        """View all mapping results."""
        batch_mapping_id = session.get('batch_mapping_id')
        if not batch_mapping_id:
            flash('No batch mapping results available', 'warning')
            return redirect(url_for('index'))

        # Get batch results from storage
        batch_data = results_storage.get_batch_results(batch_mapping_id)
        if not batch_data or 'results' not in batch_data:
            flash('Failed to load batch mapping results', 'error')
            return redirect(url_for('index'))

        batch_mapping_results = batch_data.get('results', [])

        # Calculate summary statistics
        summary = {
            'total_submissions': len(batch_mapping_results),
            'total_mappings': sum(len(r.get('mappings', [])) for r in batch_mapping_results),
            'average_mappings': sum(len(r.get('mappings', [])) for r in batch_mapping_results) / len(batch_mapping_results) if batch_mapping_results else 0,
        }

        return render_template('batch_mappings.html', results=batch_mapping_results, summary=summary)

    @app.route('/set_selected_mapping', methods=['POST'])
    def set_selected_mapping():
        """Set the selected mapping from batch mappings for individual viewing."""
        try:
            data = request.get_json()
            if not data or 'index' not in data:
                return jsonify({"success": False, "message": "Invalid request data"})

            index = data['index']
            batch_mapping_id = session.get('batch_mapping_id')

            if not batch_mapping_id:
                return jsonify({"success": False, "message": "No batch mapping results available"})

            # Get batch results from storage
            batch_data = results_storage.get_batch_results(batch_mapping_id)
            if not batch_data or 'results' not in batch_data:
                return jsonify({"success": False, "message": "Failed to load batch mapping results"})

            batch_mapping_results = batch_data.get('results', [])

            if not batch_mapping_results or index < 0 or index >= len(batch_mapping_results):
                return jsonify({"success": False, "message": "Invalid result index"})

            # Get the selected mapping result
            mapping_result = batch_mapping_results[index]

            # Store it in the results storage
            mapping_id = results_storage.store_mapping_result(mapping_result)

            # Store only the reference in session
            session['last_mapping_id'] = mapping_id
            session['mapping_done'] = True

            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Error setting selected mapping: {str(e)}")
            return jsonify({"success": False, "message": str(e)})



    @app.route('/view_mapping')
    def view_mapping():
        """View the mapping results."""
        mapping_id = session.get('last_mapping_id')
        if not mapping_id:
            flash('No mapping results available', 'warning')
            return redirect(url_for('index'))

        # Get mapping result from storage
        mapping_result = results_storage.get_mapping_result(mapping_id)
        if not mapping_result:
            flash('Failed to load mapping results', 'error')
            return redirect(url_for('index'))

        # Ensure raw guide content is available
        if 'raw_guide_content' not in mapping_result or not mapping_result['raw_guide_content']:
            # Get guide content from session and add it to mapping result
            guide_content = session.get('guide_content', '')
            if guide_content:
                mapping_result['raw_guide_content'] = guide_content
                # Store the updated mapping result
                mapping_id = results_storage.store_mapping_result(mapping_result)
                session['last_mapping_id'] = mapping_id
                logger.info("Added missing guide content to mapping result")
            else:
                logger.warning("Guide content not available in session")

        # Ensure raw submission content is available
        if 'raw_submission_content' not in mapping_result or not mapping_result['raw_submission_content']:
            # Get submission content from session and add it to mapping result
            submission_content = session.get('last_submission', {}).get('raw_text', '')
            if submission_content:
                mapping_result['raw_submission_content'] = submission_content
                # Store the updated mapping result
                mapping_id = results_storage.store_mapping_result(mapping_result)
                session['last_mapping_id'] = mapping_id
                logger.info("Added missing submission content to mapping result")
            else:
                logger.warning("Submission content not available in session")

        return render_template('mapping.html', mapping_result=mapping_result)

    @app.route('/grade_submission', methods=['POST'])
    def grade_submission():
        """View grading results from the mapping process (no separate grading step needed)."""
        try:
            # Check if we have a mapping result
            mapping_result = session.get('last_mapping_result')
            if not mapping_result:
                flash("Please map the submission to the guide first", 'warning')
                return redirect(url_for('index'))

            # Get submission filename
            submission_id = session.get('last_submission', {}).get('filename', 'unknown_submission')

            # Extract grading information from the mapping result
            overall_grade = mapping_result.get('overall_grade', {})

            if not overall_grade:
                flash("No grading information found in the mapping result", 'error')
                return redirect(url_for('view_mapping'))

            # Create a grading result structure from the mapping result

            # Calculate total score and max possible score
            total_score = overall_grade.get('total_score', 0)
            max_possible_score = overall_grade.get('max_possible_score', 0)

            # Ensure max_possible_score is not zero to avoid division by zero
            if max_possible_score == 0:
                max_possible_score = 100  # Default to 100 if no max score is found

            # Calculate percentage score
            percent_score = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0

            # Ensure normalized_score is set
            normalized_score = overall_grade.get('normalized_score', percent_score)

            # Determine letter grade
            letter_grade = overall_grade.get('letter_grade', 'F')
            if not letter_grade or letter_grade == 'F' and percent_score > 40:
                # Recalculate letter grade if it's missing or seems incorrect
                if percent_score >= 90:
                    letter_grade = 'A+'
                elif percent_score >= 80:
                    letter_grade = 'A'
                elif percent_score >= 70:
                    letter_grade = 'B'
                elif percent_score >= 60:
                    letter_grade = 'C'
                elif percent_score >= 50:
                    letter_grade = 'D'
                else:
                    letter_grade = 'F'

            grading_result = {
                "status": "success",
                "message": "Submission graded successfully",
                "submission_id": submission_id,
                "overall_score": total_score,
                "max_possible_score": max_possible_score,
                "normalized_score": normalized_score,
                "percent_score": percent_score,
                "letter_grade": letter_grade,
                "criteria_scores": [],
                "detailed_feedback": {
                    "strengths": [],
                    "weaknesses": [],
                    "improvement_suggestions": []
                },
                "metadata": {
                    # Keep existing metadata
                    **mapping_result.get('metadata', {}),
                    # Add required metadata
                    "total_questions": len(mapping_result.get('mappings', [])),
                    "graded_at": datetime.now().isoformat(),
                    "grading_method": "LLM"
                }
            }

            # Process each mapping to create criteria scores
            all_strengths = []
            all_weaknesses = []

            for mapping in mapping_result.get('mappings', []):
                # Extract grading information
                guide_text = mapping.get("guide_text", "")
                guide_answer = mapping.get("guide_answer", "")

                # If guide_answer is empty, try to extract it from the guide text
                if not guide_answer and guide_text:
                    # Look for patterns that indicate an answer section
                    answer_patterns = [
                        r'(?:Answer|Solution):\s*(.*?)(?=\n\n|\Z)',
                        r'(?:A|Ans):\s*(.*?)(?=\n\n|\Z)',
                        r'(?<=\n\n)(.*?)(?=\n\n|\Z)'  # Fallback: take content after double newline
                    ]

                    for pattern in answer_patterns:
                        match = re.search(pattern, guide_text, re.DOTALL | re.IGNORECASE)
                        if match:
                            guide_answer = match.group(1).strip()
                            logger.info(f"Extracted guide answer from guide text: {guide_answer[:50]}...")
                            break

                # If still empty and we have raw guide content, try to find a section that matches the question
                if not guide_answer and 'raw_guide_content' in mapping_result:
                    raw_guide = mapping_result['raw_guide_content']
                    # Extract a question identifier if possible
                    question_id_match = re.search(r'(?:Question|Q)\s*(\d+)', guide_text, re.IGNORECASE)
                    if question_id_match:
                        question_num = question_id_match.group(1)
                        # Look for the answer to this question in the raw guide
                        answer_pattern = rf'(?:Answer|Solution|A|Ans)(?:\s*{question_num})?\s*:\s*(.*?)(?=(?:Question|Q)\s*\d+|\Z)'
                        match = re.search(answer_pattern, raw_guide, re.DOTALL | re.IGNORECASE)
                        if match:
                            guide_answer = match.group(1).strip()
                            logger.info(f"Extracted guide answer from raw guide content: {guide_answer[:50]}...")

                criteria_score = {
                    "question_id": mapping.get("guide_id", ""),
                    "description": guide_text,
                    "points_earned": mapping.get("grade_score", 0),
                    "points_possible": mapping.get("max_score", 0),
                    "similarity": mapping.get("match_score", 0),
                    "feedback": mapping.get("grade_feedback", ""),
                    "guide_answer": guide_answer,
                    "student_answer": mapping.get("submission_text", ""),
                    "match_reason": mapping.get("match_reason", "")
                }

                # Add to criteria scores
                grading_result["criteria_scores"].append(criteria_score)

                # Collect strengths and weaknesses
                all_strengths.extend(mapping.get("strengths", []))
                all_weaknesses.extend(mapping.get("weaknesses", []))

            # Add unique strengths and weaknesses to the detailed feedback
            grading_result["detailed_feedback"]["strengths"] = list(set(all_strengths))
            grading_result["detailed_feedback"]["weaknesses"] = list(set(all_weaknesses))

            # Store in results storage instead of session
            grading_id = results_storage.store_grading_result(grading_result)
            session['last_grading_id'] = grading_id
            session['last_score'] = grading_result.get('percent_score', 0)

            # Save results permanently if grading service is available
            if grading_service:
                output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
                grading_service.save_grading_result(
                    grading_result=grading_result,
                    output_path=output_dir,
                    filename=submission_id
                )

            # Format the score to display as a whole number
            display_score = int(round(grading_result.get('percent_score', 0)))
            logger.info(f"Viewing grading results with score: {display_score}%")
            flash(f"Grading completed with score: {display_score}%", 'success')
            return redirect(url_for('view_results'))

        except Exception as e:
            logger.error(f"Error in grade_submission: {str(e)}")
            flash(f"An unexpected error occurred: {str(e)}", 'error')
            return redirect(url_for('view_mapping'))

    @app.route('/view_results')
    def view_results():
        """View the grading results summary."""
        grading_id = session.get('last_grading_id')
        if not grading_id:
            flash('No grading results available', 'warning')
            return redirect(url_for('index'))

        # Get grading result from storage
        grading_result = results_storage.get_grading_result(grading_id)
        if not grading_result:
            flash('Failed to load grading results', 'error')
            return redirect(url_for('index'))

        return render_template('results.html', result=grading_result)

    @app.route('/view_detailed_results')
    def view_detailed_results():
        """View detailed grading results with comprehensive feedback."""
        grading_id = session.get('last_grading_id')
        if not grading_id:
            flash('No grading results available', 'warning')
            return redirect(url_for('index'))

        # Get grading result from storage
        grading_result = results_storage.get_grading_result(grading_id)
        if not grading_result:
            flash('Failed to load grading results', 'error')
            return redirect(url_for('index'))

        # Calculate performance metrics for visualization
        if 'detailed_feedback' in grading_result:
            strengths_count = len(grading_result.get('detailed_feedback', {}).get('strengths', []))
            weaknesses_count = len(grading_result.get('detailed_feedback', {}).get('weaknesses', []))
            total_feedback = max(strengths_count + weaknesses_count, 1)  # Avoid division by zero

            # Add performance metrics to the result
            grading_result['performance_metrics'] = {
                'strengths_percentage': round((strengths_count / total_feedback) * 100),
                'weaknesses_percentage': round((weaknesses_count / total_feedback) * 100)
            }

            # Store the updated grading result
            grading_id = results_storage.store_grading_result(grading_result)
            session['last_grading_id'] = grading_id

        return render_template('detailed_results.html', result=grading_result)

    @app.route('/clear_guide', methods=['POST'])
    def clear_guide():
        """Clear the current marking guide."""
        session.pop('guide_content', None)
        session.pop('guide_uploaded', None)
        session.pop('guide_data', None)
        flash('Marking guide cleared', 'info')
        return redirect(url_for('index'))

    @app.route('/remove_submission/<filename>', methods=['POST'])
    def remove_submission(filename):
        """Remove a specific submission."""
        try:
            # Get current submissions
            submissions = session.get('submissions', [])

            # Find the submission with the matching filename
            submission_index = None
            for i, sub in enumerate(submissions):
                if sub.get('filename') == filename:
                    submission_index = i
                    break

            if submission_index is not None:
                # Remove the submission
                removed_submission = submissions.pop(submission_index)

                # Update the session
                session['submissions'] = submissions

                # If we removed the last_submission, update it to the first available submission
                if session.get('last_submission', {}).get('filename') == filename:
                    if submissions:
                        session['last_submission'] = submissions[0]
                    else:
                        session.pop('last_submission', None)

                # Clear related results if needed
                if session.get('last_mapping_result', {}).get('submission_id') == filename:
                    session.pop('last_mapping_result', None)
                    session.pop('mapping_done', None)

                if session.get('last_grading_result', {}).get('submission_id') == filename:
                    session.pop('last_grading_result', None)
                    session.pop('last_score', None)

                # Remove from batch results if present
                if 'batch_mapping_results' in session:
                    batch_mapping_results = session.get('batch_mapping_results', [])
                    session['batch_mapping_results'] = [r for r in batch_mapping_results if r.get('submission_id') != filename]

                if 'batch_results' in session:
                    batch_results = session.get('batch_results', [])
                    session['batch_results'] = [r for r in batch_results if r.get('submission_id') != filename]

                flash(f'Submission "{filename}" removed successfully', 'success')
            else:
                flash(f'Submission "{filename}" not found', 'warning')

            # Redirect to the appropriate page
            if submissions:
                return redirect(url_for('view_submission'))
            else:
                return redirect(url_for('index'))

        except Exception as e:
            logger.error(f"Error removing submission {filename}: {str(e)}")
            flash(f'An error occurred while removing the submission: {str(e)}', 'error')
            return redirect(url_for('view_submission'))

    @app.route('/clear_submission', methods=['POST'])
    def clear_submission():
        """Clear all submissions."""
        session.pop('last_submission', None)
        session.pop('submissions', None)
        session.pop('last_mapping_result', None)
        session.pop('last_grading_result', None)
        session.pop('mapping_done', None)
        session.pop('last_score', None)

        # Clear batch results
        session.pop('batch_mapping_results', None)
        session.pop('batch_results', None)

        flash('All submissions cleared', 'info')
        return redirect(url_for('index'))

    @app.route('/clear_all', methods=['POST'])
    def clear_all():
        """Clear all session data and cache files."""
        # Clear session data
        session.clear()

        # Clear cache files
        try:
            # Clear guide storage cache
            from src.storage.guide_storage import GuideStorage
            guide_storage = GuideStorage()
            guide_storage.clear()

            # Clear submission storage cache
            from src.storage.submission_storage import SubmissionStorage
            submission_storage = SubmissionStorage()
            submission_storage.clear()

            # Clear mapping storage cache
            try:
                from src.storage.mapping_storage import MappingStorage
                mapping_storage = MappingStorage()
                mapping_storage.clear()
                logger.debug("Cleared mapping storage cache")
            except Exception as e:
                logger.error(f"Error clearing mapping storage: {str(e)}")

            # Clear results storage cache
            try:
                results_storage.clear()
                logger.debug("Cleared results storage cache")
            except Exception as e:
                logger.error(f"Error clearing results storage: {str(e)}")

            # Clear general cache
            from utils.cache import Cache
            cache = Cache()
            cache.clear()

            # Progress tracking has been removed

            # Clear temporary files
            from src.config.config_manager import ConfigManager
            config = ConfigManager().config
            temp_dir = config.temp_dir

            # Clear temp/uploads directory
            uploads_dir = os.path.join(temp_dir, 'uploads')
            if os.path.exists(uploads_dir):
                for file in os.listdir(uploads_dir):
                    file_path = os.path.join(uploads_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                            logger.debug(f"Removed upload file: {file}")
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {str(e)}")

            # Clear cache directory
            cache_dir = os.path.join(temp_dir, 'cache')
            if os.path.exists(cache_dir):
                for file in os.listdir(cache_dir):
                    file_path = os.path.join(cache_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                            logger.debug(f"Removed cache file: {file}")
                    except Exception as e:
                        logger.error(f"Error deleting cache file {file_path}: {str(e)}")

            # Clear client-side progress tracking
            flash('All data and cache files cleared. Please refresh the page to clear any active progress trackers.', 'info')
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            flash('Session data cleared, but there was an error clearing some cache files', 'warning')

        return redirect(url_for('index'))

    @app.route('/download_results/<filename>')
    def download_results(filename):
        """Download results file."""
        results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
        return send_from_directory(results_dir, filename)

    @app.route('/batch_grade', methods=['POST'])
    def batch_grade():
        """Grade all uploaded submissions against the marking guide."""
        try:
            # Check if we have both a guide and submissions
            if not session.get('guide_uploaded'):
                flash("Please upload a marking guide first", 'warning')
                return redirect(url_for('index'))

            submissions = session.get('submissions', [])
            if not submissions:
                flash("Please upload at least one student submission first", 'warning')
                return redirect(url_for('index'))

            # Get the number of questions parameter
            num_questions = request.form.get('num_questions', '1')
            try:
                num_questions = int(num_questions)
                if num_questions < 1:
                    num_questions = 1
            except ValueError:
                num_questions = 1

            # Store in session for future reference
            session['num_questions'] = num_questions

            # Get guide content
            guide_content = session.get('guide_content', '')
            if not guide_content:
                flash("Invalid marking guide content", 'error')
                return redirect(url_for('index'))

            # Log the start of the batch operation
            logger.info(f"Starting batch grading operation for {len(submissions)} submissions...")

            # Store all grading results
            all_results = []

            # Process each submission
            for i, submission in enumerate(submissions):
                submission_id = submission.get('filename', '')
                submission_content = submission.get('raw_text', '')

                if not submission_content:
                    logger.warning(f"Empty submission content for {submission_id}")
                    continue

                # Log progress
                logger.info(f"Grading submission {i+1} of {len(submissions)}: {submission_id}")

                # Map and grade the submission
                try:
                    mapping_result, error = mapping_service.map_submission_to_guide(
                        marking_guide_content=guide_content,
                        student_submission_content=submission_content,
                        num_questions=num_questions
                    )

                    if error:
                        logger.error(f"Mapping error for {submission_id}: {error}")
                        continue

                    # Extract overall grade from mapping result
                    overall_grade = mapping_result.get('overall_grade', {})

                    # Calculate scores
                    total_score = overall_grade.get('total_score', 0)
                    max_possible_score = overall_grade.get('max_possible_score', 0)

                    # Ensure max_possible_score is not zero to avoid division by zero
                    if max_possible_score == 0:
                        max_possible_score = 100  # Default to 100 if no max score is found

                    # Calculate percentage score
                    percent_score = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0

                    # Ensure normalized_score is set
                    normalized_score = overall_grade.get('normalized_score', percent_score)

                    # Determine letter grade
                    letter_grade = overall_grade.get('letter_grade', 'F')
                    if not letter_grade or letter_grade == 'F' and percent_score > 40:
                        # Recalculate letter grade if it's missing or seems incorrect
                        if percent_score >= 90:
                            letter_grade = 'A+'
                        elif percent_score >= 80:
                            letter_grade = 'A'
                        elif percent_score >= 70:
                            letter_grade = 'B'
                        elif percent_score >= 60:
                            letter_grade = 'C'
                        elif percent_score >= 50:
                            letter_grade = 'D'
                        else:
                            letter_grade = 'F'

                    # Create a grading result structure
                    grading_result = {
                        "status": "success",
                        "message": "Submission graded successfully",
                        "submission_id": submission_id,
                        "overall_score": total_score,
                        "max_possible_score": max_possible_score,
                        "normalized_score": normalized_score,
                        "percent_score": percent_score,
                        "letter_grade": letter_grade,
                        "criteria_scores": [],
                        "detailed_feedback": {
                            "strengths": [],
                            "weaknesses": [],
                            "improvement_suggestions": []
                        },
                        "metadata": {
                            **mapping_result.get('metadata', {}),
                            "total_questions": len(mapping_result.get('mappings', [])),
                            "graded_at": datetime.now().isoformat(),
                            "grading_method": "LLM"
                        }
                    }

                    # Process each mapping to create criteria scores
                    all_strengths = []
                    all_weaknesses = []

                    for mapping in mapping_result.get('mappings', []):
                        # Extract guide text and answer
                        guide_text = mapping.get("guide_text", "")
                        guide_answer = mapping.get("guide_answer", "")

                        # Extract answer if needed using existing code
                        if not guide_answer and guide_text:
                            # Look for patterns that indicate an answer section
                            answer_patterns = [
                                r'(?:Answer|Solution):\s*(.*?)(?=\n\n|\Z)',
                                r'(?:A|Ans):\s*(.*?)(?=\n\n|\Z)',
                                r'(?<=\n\n)(.*?)(?=\n\n|\Z)'  # Fallback: take content after double newline
                            ]

                            for pattern in answer_patterns:
                                match = re.search(pattern, guide_text, re.DOTALL | re.IGNORECASE)
                                if match:
                                    guide_answer = match.group(1).strip()
                                    break

                        # Create criteria score
                        criteria_score = {
                            "question_id": mapping.get("guide_id", ""),
                            "description": guide_text,
                            "points_earned": mapping.get("grade_score", 0),
                            "points_possible": mapping.get("max_score", 0),
                            "similarity": mapping.get("match_score", 0),
                            "feedback": mapping.get("grade_feedback", ""),
                            "guide_answer": guide_answer,
                            "student_answer": mapping.get("submission_text", ""),
                            "match_reason": mapping.get("match_reason", "")
                        }

                        # Add to criteria scores
                        grading_result["criteria_scores"].append(criteria_score)

                        # Collect strengths and weaknesses
                        all_strengths.extend(mapping.get("strengths", []))
                        all_weaknesses.extend(mapping.get("weaknesses", []))

                    # Add unique strengths and weaknesses to the detailed feedback
                    grading_result["detailed_feedback"]["strengths"] = list(set(all_strengths))
                    grading_result["detailed_feedback"]["weaknesses"] = list(set(all_weaknesses))

                    # Add to results list
                    all_results.append(grading_result)

                    # Save results permanently if grading service is available
                    if grading_service:
                        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
                        grading_service.save_grading_result(
                            grading_result=grading_result,
                            output_path=output_dir,
                            filename=submission_id
                        )

                except Exception as e:
                    logger.error(f"Error grading {submission_id}: {str(e)}")

            # Log completion
            logger.info(f"Completed grading {len(all_results)} of {len(submissions)} submissions")

            # Store results in session
            session['batch_results'] = all_results

            # Flash success message
            flash(f"Successfully graded {len(all_results)} of {len(submissions)} submissions", 'success')

            # Redirect to batch results page
            return redirect(url_for('view_batch_results'))

        except Exception as e:
            logger.error(f"Error in batch_grade: {str(e)}")
            flash(f"An unexpected error occurred: {str(e)}", 'error')
            return redirect(url_for('index'))

    @app.route('/view_batch_results')
    def view_batch_results():
        """View the batch grading results summary."""
        batch_results = session.get('batch_results')
        if not batch_results:
            flash('No batch grading results available', 'warning')
            return redirect(url_for('index'))

        # Calculate summary statistics
        summary = {
            'total_submissions': len(batch_results),
            'average_score': sum(r.get('percent_score', 0) for r in batch_results) / len(batch_results) if batch_results else 0,
            'highest_score': max((r.get('percent_score', 0) for r in batch_results), default=0),
            'lowest_score': min((r.get('percent_score', 0) for r in batch_results), default=0),
            'grade_distribution': {
                'A+': sum(1 for r in batch_results if r.get('letter_grade') == 'A+'),
                'A': sum(1 for r in batch_results if r.get('letter_grade') == 'A'),
                'B': sum(1 for r in batch_results if r.get('letter_grade') == 'B'),
                'C': sum(1 for r in batch_results if r.get('letter_grade') == 'C'),
                'D': sum(1 for r in batch_results if r.get('letter_grade') == 'D'),
                'F': sum(1 for r in batch_results if r.get('letter_grade') == 'F')
            }
        }

        return render_template('batch_results.html', results=batch_results, summary=summary)

    @app.route('/set_selected_result', methods=['POST'])
    def set_selected_result():
        """Set the selected result from batch results for individual viewing."""
        try:
            data = request.get_json()
            if not data or 'index' not in data:
                return jsonify({"success": False, "message": "Invalid request data"})

            index = data['index']
            batch_results = session.get('batch_results', [])

            if not batch_results or index < 0 or index >= len(batch_results):
                return jsonify({"success": False, "message": "Invalid result index"})

            # Set the selected result as the last_grading_result
            session['last_grading_result'] = batch_results[index]

            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Error setting selected result: {str(e)}")
            return jsonify({"success": False, "message": str(e)})

    @app.route('/download_batch_excel')
    def download_batch_excel():
        """Download all batch grading results as a single Excel file."""
        batch_results = session.get('batch_results')
        if not batch_results:
            flash('No batch grading results available', 'warning')
            return redirect(url_for('index'))

        # Create a pandas DataFrame for the summary
        summary_data = []
        for result in batch_results:
            summary_data.append({
                'Student ID': result.get('submission_id', ''),
                'Overall Score': f"{result.get('percent_score', 0):.1f}%",
                'Points Earned': result.get('overall_score', 0),
                'Max Possible': result.get('max_possible_score', 0),
                'Letter Grade': result.get('letter_grade', 'N/A'),
                'Graded At': result.get('metadata', {}).get('graded_at', ''),
                'Strengths Count': len(result.get('detailed_feedback', {}).get('strengths', [])),
                'Weaknesses Count': len(result.get('detailed_feedback', {}).get('weaknesses', []))
            })

        summary_df = pd.DataFrame(summary_data)

        # Create an Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # Create a sheet for each student with their detailed scores
            for i, result in enumerate(batch_results):
                student_id = result.get('submission_id', f'Student_{i+1}')

                # Create a DataFrame for this student's criteria scores
                criteria_data = []
                for criteria in result.get('criteria_scores', []):
                    criteria_data.append({
                        'Question': criteria.get('description', ''),
                        'Score': criteria.get('points_earned', 0),
                        'Max Score': criteria.get('points_possible', 0),
                        'Match %': f"{(criteria.get('similarity', 0) * 100):.1f}%",
                        'Feedback': criteria.get('feedback', '')
                    })

                # Create a DataFrame and write to Excel
                if criteria_data:
                    df = pd.DataFrame(criteria_data)
                    sheet_name = f"{student_id[:28]}"  # Limit sheet name length
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Add statistics sheet
            stats_data = [{
                'Total Submissions': len(batch_results),
                'Average Score': f"{sum(r.get('percent_score', 0) for r in batch_results) / len(batch_results):.1f}%",
                'Highest Score': f"{max((r.get('percent_score', 0) for r in batch_results), default=0):.1f}%",
                'Lowest Score': f"{min((r.get('percent_score', 0) for r in batch_results), default=0):.1f}%",
                'A+ Count': sum(1 for r in batch_results if r.get('letter_grade') == 'A+'),
                'A Count': sum(1 for r in batch_results if r.get('letter_grade') == 'A'),
                'B Count': sum(1 for r in batch_results if r.get('letter_grade') == 'B'),
                'C Count': sum(1 for r in batch_results if r.get('letter_grade') == 'C'),
                'D Count': sum(1 for r in batch_results if r.get('letter_grade') == 'D'),
                'F Count': sum(1 for r in batch_results if r.get('letter_grade') == 'F')
            }]
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)

            # Auto-adjust column width for all sheets
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                        adjusted_width = (max_length + 2)
                        worksheet.column_dimensions[column_letter].width = min(adjusted_width, 50)

        # Seek to the beginning of the stream
        output.seek(0)

        # Generate a filename based on timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"batch_grading_results_{timestamp}.xlsx"

        # Return the Excel file as a response
        return Response(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )

    @app.route('/download_excel')
    def download_excel():
        """Download grading results as Excel file."""
        grading_id = session.get('last_grading_id')
        if not grading_id:
            flash('No grading results available', 'warning')
            return redirect(url_for('index'))

        # Get grading result from storage
        grading_result = results_storage.get_grading_result(grading_id)
        if not grading_result:
            flash('Failed to load grading results', 'error')
            return redirect(url_for('index'))

        # Create a pandas DataFrame for the criteria scores
        criteria_data = []
        for criteria in grading_result.get('criteria_scores', []):
            criteria_data.append({
                'Question': criteria.get('description', ''),
                'Score': criteria.get('points_earned', 0),
                'Max Score': criteria.get('points_possible', 0),
                'Match %': f"{(criteria.get('similarity', 0) * 100):.1f}%",
                'Answer Score': f"{(criteria.get('answer_score', 0) * 100):.1f}%",
                'Keyword Score': f"{(criteria.get('keyword_score', 0) * 100):.1f}%",
                'Match Reason': criteria.get('match_reason', ''),
                'Feedback': criteria.get('feedback', ''),
                'Guide Answer': criteria.get('guide_answer', ''),
                'Student Answer': criteria.get('student_answer', '')
            })

        df = pd.DataFrame(criteria_data)

        # Create a summary DataFrame
        summary_data = [{
            'Overall Score': f"{grading_result.get('percent_score', 0):.1f}%",
            'Points Earned': grading_result.get('overall_score', 0),
            'Max Possible': grading_result.get('max_possible_score', 0),
            'Letter Grade': grading_result.get('letter_grade', 'N/A'),
            'Graded At': grading_result.get('metadata', {}).get('graded_at', ''),
            'Grading Method': grading_result.get('metadata', {}).get('grading_method', 'Similarity'),
            'Guide Type': grading_result.get('metadata', {}).get('guide_type', 'Unknown')
        }]
        summary_df = pd.DataFrame(summary_data)

        # Create an Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            df.to_excel(writer, sheet_name='Detailed Scores', index=False)

            # Get the workbook and the worksheet
            workbook = writer.book

            # Auto-adjust column width for both sheets
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column_letter].width = min(adjusted_width, 50)

        # Seek to the beginning of the stream
        output.seek(0)

        # Generate a filename based on timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"grading_results_{timestamp}.xlsx"

        # Return the Excel file as a response
        return Response(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )



    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def request_entity_too_large(e):
        flash(f'File too large. Maximum size is {config.max_file_size_mb}MB', 'error')
        return redirect(url_for('index'))

    return app

def process_submission(file_path, file_content, submission_storage):
    """
    Process a submission file and return results.

    Args:
        file_path: Path to the submission file
        file_content: Raw bytes of the file
        submission_storage: Storage instance for submissions

    Returns:
        Tuple containing:
        - Dict of question numbers to answers
        - Raw extracted text
        - Error message if any
    """
    try:
        # Check if we have stored results
        stored_results = submission_storage.get_results(file_content)
        if stored_results:
            logger.info(f"Using cached results for {Path(file_path).name}")
            results, raw_text, _ = stored_results
            return results, raw_text, None

        # Process submission
        results, raw_text, error = parse_student_submission(file_path)

        # Log processing results
        logger.info(f"Text extraction results:")
        logger.info(f"- Raw text extracted: {bool(raw_text)}")
        logger.info(f"- Raw text length: {len(raw_text) if raw_text else 0}")
        logger.info(f"- Questions found: {len(results) if results else 0}")

        if error:
            logger.error(f"Processing Error: {error}")
            return {}, raw_text or "", error

        if not results and raw_text:
            # If we have raw text but no questions found, return it as a single result
            results = {'raw': raw_text}

        if not results:
            return {}, raw_text or "", "No text could be extracted from the document"

        # Store successful results
        if results and raw_text:
            submission_storage.store_results(
                file_content,
                Path(file_path).name,
                results,
                raw_text
            )

        return results, raw_text or "", None

    except OCRServiceError as e:
        error_msg = str(e)

        # Provide more user-friendly messages for common OCR errors
        if "API key" in error_msg.lower():
            error_msg = "OCR service configuration error. Please contact the administrator."
        elif "timeout" in error_msg.lower():
            error_msg = "OCR processing timed out. The document may be too complex or the service is busy. Please try again later."
        elif "unsupported file format" in error_msg.lower():
            error_msg = "The file format is not supported by the OCR service. Please try a different format."

        logger.error(f"OCR service error: {str(e)}")
        return {}, "", f"OCR processing failed: {error_msg}"

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

        # Provide better error messages for common exceptions
        error_msg = str(e)
        if isinstance(e, OSError):
            error_msg = "File system error. The file may be corrupted or inaccessible."
        elif isinstance(e, MemoryError):
            error_msg = "Not enough memory to process this file. Please try a smaller file."
        elif isinstance(e, TimeoutError):
            error_msg = "Operation timed out. Please try again later."

        return {}, "", f"Processing failed: {error_msg}"