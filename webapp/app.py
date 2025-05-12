"""
Exam Grader web application.
This module contains the Flask application factory and registers all blueprints.
"""

import os
import sys
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

    # Initialize services (always available with patched versions)
    llm_service = None
    grading_service = None
    mapping_service = None
    ocr_status = False
    llm_status = True  # Always set to True to enable features

    try:
        # Initialize LLM service first
        from src.services.llm_service import LLMService
        llm_service = LLMService()

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

    # Initialize progress tracker with the correct directory
    try:
        from src.services.progress_tracker import initialize_progress_tracker
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        progress_dir = os.path.join(app_root, "temp", "progress")
        initialize_progress_tracker(progress_dir)
        logger.info(f"Progress tracker initialized with directory: {progress_dir}")
    except Exception as e:
        logger.error(f"Error initializing progress tracker: {str(e)}")

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
        """Handle student submission upload."""
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
            if not allowed_file(file.filename):
                flash(f'Invalid file format. Supported formats: {", ".join(config.supported_formats)}', 'error')
                return redirect(url_for('index'))

            # Save file temporarily
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Process submission
            results, raw_text, error = process_submission(file_path, file.read(), submission_storage)
            if error:
                flash(f'Failed to process submission: {error}', 'error')
                return redirect(url_for('index'))

            if not results:
                flash('Failed to extract submission content', 'error')
                return redirect(url_for('index'))

            # Store in session
            submission_data = {
                'filename': filename,
                'results': results,
                'raw_text': raw_text,
                'upload_time': datetime.now().isoformat()
            }

            # We don't want to show progress bar, so don't add OCR tracker ID
            # if 'ocr_tracker_id' in results:
            #     submission_data['ocr_tracker_id'] = results['ocr_tracker_id']

            session['last_submission'] = submission_data

            flash('Student submission uploaded successfully', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            logger.error(f"Submission upload error: {str(e)}")
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('index'))
        finally:
            # Clean up temporary file
            try:
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file: {str(e)}")

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
        """View the most recent student submission."""
        submission = session.get('last_submission')
        if not submission:
            flash('No submission available', 'warning')
            return redirect(url_for('index'))

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
            submission_copy = submission.copy()
            submission_copy.pop('ocr_tracker_id', None)
            submission = submission_copy

        return render_template('submission.html', submission=submission)

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

            # Get submission content
            submission_content = session.get('last_submission', {}).get('raw_text', '')
            if not submission_content:
                flash("Student submission content is not available", 'error')
                session['mapping_in_progress'] = False
                return redirect(url_for('index'))

            # Map the submission to the guide
            logger.info("Mapping submission to marking guide criteria...")
            mapping_result, error = mapping_service.map_submission_to_guide(
                marking_guide_content=guide_content,
                student_submission_content=submission_content
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

            # Save to session
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

    @app.route('/view_mapping')
    def view_mapping():
        """View the mapping results."""
        mapping_result = session.get('last_mapping_result')
        if not mapping_result:
            flash('No mapping results available', 'warning')
            return redirect(url_for('index'))

        return render_template('mapping.html', mapping_result=mapping_result)

    @app.route('/grade_submission', methods=['POST'])
    def grade_submission():
        """Grade a student submission against the marking guide using the mapping result."""
        try:
            # Check if we have a mapping result
            mapping_result = session.get('last_mapping_result')
            if not mapping_result:
                flash("Please map the submission to the guide first", 'warning')
                return redirect(url_for('index'))

            # Set grading in progress
            session['grading_in_progress'] = True

            # Get submission filename
            submission_id = session.get('last_submission', {}).get('filename', 'unknown_submission')

            # Extract grading information from the mapping result
            overall_grade = mapping_result.get('overall_grade', {})

            if not overall_grade:
                flash("No grading information found in the mapping result", 'error')
                session['grading_in_progress'] = False
                return redirect(url_for('view_mapping'))

            # Create a grading result structure similar to what the grading service would produce
            grading_result = {
                "status": "success",
                "overall_score": overall_grade.get('total_score', 0),
                "max_possible_score": overall_grade.get('max_possible_score', 0),
                "percent_score": overall_grade.get('percentage', 0),
                "letter_grade": overall_grade.get('letter_grade', 'F'),
                "criteria_scores": [],
                "detailed_feedback": {
                    "strengths": [],
                    "weaknesses": [],
                    "improvement_suggestions": []
                },
                "metadata": mapping_result.get('metadata', {})
            }

            # Process each mapping to create criteria scores
            all_strengths = []
            all_weaknesses = []

            for mapping in mapping_result.get('mappings', []):
                # Extract grading information
                criteria_score = {
                    "question_id": mapping.get("guide_id", ""),
                    "description": mapping.get("guide_text", ""),
                    "points_earned": mapping.get("grade_score", 0),
                    "points_possible": mapping.get("max_score", 0),
                    "similarity": mapping.get("match_score", 0),
                    "feedback": mapping.get("grade_feedback", ""),
                    "guide_answer": mapping.get("guide_answer", ""),
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

            # Save to session
            session['last_grading_result'] = grading_result
            session['last_score'] = grading_result.get('percent_score', 0)

            # Save results permanently if grading service is available
            if grading_service:
                output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
                grading_service.save_grading_result(
                    grading_result=grading_result,
                    output_path=output_dir,
                    filename=submission_id
                )

            # Clear grading in progress
            session['grading_in_progress'] = False

            logger.info(f"Grading completed for {submission_id} with score: {grading_result.get('percent_score', 0)}%")
            flash(f"Grading completed with score: {grading_result.get('percent_score', 0)}%", 'success')
            return redirect(url_for('view_results'))

        except Exception as e:
            logger.error(f"Error in grade_submission: {str(e)}")
            flash(f"An unexpected error occurred: {str(e)}", 'error')
            session['grading_in_progress'] = False
            return redirect(url_for('index'))

    @app.route('/view_results')
    def view_results():
        """View the grading results summary."""
        grading_result = session.get('last_grading_result')
        if not grading_result:
            flash('No grading results available', 'warning')
            return redirect(url_for('index'))

        return render_template('results.html', result=grading_result)

    @app.route('/view_detailed_results')
    def view_detailed_results():
        """View detailed grading results with comprehensive feedback."""
        grading_result = session.get('last_grading_result')
        if not grading_result:
            flash('No grading results available', 'warning')
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

        return render_template('detailed_results.html', result=grading_result)

    @app.route('/clear_guide', methods=['POST'])
    def clear_guide():
        """Clear the current marking guide."""
        session.pop('guide_content', None)
        session.pop('guide_uploaded', None)
        session.pop('guide_data', None)
        flash('Marking guide cleared', 'info')
        return redirect(url_for('index'))

    @app.route('/clear_submission', methods=['POST'])
    def clear_submission():
        """Clear the current submission."""
        session.pop('last_submission', None)
        session.pop('last_mapping_result', None)
        session.pop('last_grading_result', None)
        session.pop('mapping_done', None)
        session.pop('last_score', None)
        flash('Submission cleared', 'info')
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

            # Clear general cache
            from utils.cache import Cache
            cache = Cache()
            cache.clear()

            # Clear progress tracking files
            from src.services.progress_tracker import progress_tracker
            progress_dir = progress_tracker.progress_dir
            if os.path.exists(progress_dir):
                for file in os.listdir(progress_dir):
                    if file.endswith('.json'):
                        file_path = os.path.join(progress_dir, file)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                                logger.debug(f"Removed progress file: {file}")
                        except Exception as e:
                            logger.error(f"Error deleting progress file {file_path}: {str(e)}")

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

    @app.route('/download_excel')
    def download_excel():
        """Download grading results as Excel file."""
        grading_result = session.get('last_grading_result')
        if not grading_result:
            flash('No grading results available', 'warning')
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

    @app.route('/api/progress/<tracker_id>', methods=['GET', 'DELETE'])
    def get_progress(tracker_id):
        """Get progress information for a specific tracker or delete it."""
        try:
            from src.services.progress_tracker import progress_tracker, initialize_progress_tracker

            # Ensure progress tracker is using the correct directory
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            progress_dir = os.path.join(app_root, "temp", "progress")
            initialize_progress_tracker(progress_dir)

            # Handle DELETE request to clean up a specific tracker
            if request.method == 'DELETE':
                logger.info(f"Request to delete progress tracker {tracker_id}")
                success = progress_tracker.cleanup_specific_tracker(tracker_id)
                if success:
                    return jsonify({"status": "success", "message": f"Tracker {tracker_id} deleted successfully"})
                else:
                    return jsonify({"status": "warning", "message": f"Tracker {tracker_id} not found or could not be deleted"})

            # For GET requests, proceed with getting progress data
            # Log the tracker ID and directory for debugging
            logger.debug(f"Looking for progress tracker {tracker_id} in {progress_dir}")

            # Get progress data - this will now return a default object if tracker not found
            progress_data = progress_tracker.get_progress(tracker_id)

            # Check if the tracker was not found
            if progress_data and progress_data.get("status") == "not_found":
                logger.warning(f"Progress tracker {tracker_id} not found in {progress_dir}")
                # Return a 200 response with the default data instead of 404
                # This prevents the client from showing connection errors
                return jsonify(progress_data)

            return jsonify(progress_data)

        except Exception as e:
            logger.error(f"Error getting progress for tracker {tracker_id}: {str(e)}")
            # Return a valid response even on error to prevent client-side errors
            return jsonify({
                "id": tracker_id,
                "status": "error",
                "message": "Error retrieving progress data",
                "percent_complete": 0,
                "completed": True,
                "success": False,
                "error": f"Server error: {str(e)}"
            })

    @app.route('/api/progress', methods=['GET', 'POST'])
    def get_all_progress():
        """Get all active progress trackers or create a new one."""
        try:
            from src.services.progress_tracker import progress_tracker, initialize_progress_tracker

            # Ensure progress tracker is using the correct directory
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            progress_dir = os.path.join(app_root, "temp", "progress")
            initialize_progress_tracker(progress_dir)

            # Log the directory for debugging
            logger.debug(f"Using progress directory: {progress_dir}")

            # Create a new progress tracker
            if request.method == 'POST':
                try:
                    data = request.get_json()
                    if not data:
                        return jsonify({"error": "Invalid JSON data"}), 400

                    operation_type = data.get('operation_type', 'unknown')
                    task_name = data.get('task_name', 'Task')
                    total_steps = data.get('total_steps', 100)

                    tracker_id = progress_tracker.create_tracker(
                        operation_type=operation_type,
                        task_name=task_name,
                        total_steps=total_steps
                    )

                    return jsonify({
                        "id": tracker_id,
                        "operation_type": operation_type,
                        "task_name": task_name,
                        "message": "Progress tracker created successfully"
                    })
                except Exception as e:
                    logger.error(f"Error creating progress tracker: {str(e)}")
                    return jsonify({"error": str(e)}), 500

            # Get all active progress trackers
            operation_type = request.args.get('type')
            progress_data = progress_tracker.get_all_active_progress(operation_type)

            return jsonify({"trackers": progress_data})

        except Exception as e:
            logger.error(f"Error in progress API: {str(e)}")
            if request.method == 'POST':
                return jsonify({"error": f"Server error: {str(e)}"}), 500
            else:
                return jsonify({"trackers": []})

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