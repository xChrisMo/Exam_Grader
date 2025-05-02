"""
Web interface for the Exam Grader application.
"""
import os
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from typing import Dict, Optional, Tuple

from flask import (
    Flask, 
    render_template, 
    request, 
    jsonify, 
    send_from_directory,
    flash, 
    redirect, 
    url_for,
    session
)
from werkzeug.utils import secure_filename
from markupsafe import Markup

from src.config.config_manager import ConfigManager
from src.parsing.parse_submission import parse_student_submission
from src.parsing.parse_guide import parse_marking_guide
from src.services.ocr_service import OCRServiceError
from src.storage.submission_storage import SubmissionStorage
from src.storage.guide_storage import GuideStorage
from utils.logger import Logger
from utils.validator import Validator

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-replace-in-production')

# Initialize logger
logger = Logger().get_logger()

# Initialize configuration and storage
config = ConfigManager()
submission_storage = SubmissionStorage()
guide_storage = GuideStorage()
validator = Validator()

# Configure upload settings
UPLOAD_FOLDER = Path('temp/uploads')
ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'doc', 
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff',
    'txt'
}

GUIDE_EXTENSIONS = {'docx', 'txt'}

# Create upload directory
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = config.config.max_file_size_mb * 1024 * 1024  # MB to bytes

@app.template_filter('nl2br')
def nl2br(value):
    """Convert newlines to <br> tags."""
    if not value:
        return ''
    return Markup(value.replace('\n', '<br>\n'))

def allowed_file(filename: str, allowed_extensions: set = ALLOWED_EXTENSIONS) -> bool:
    """Check if a filename has an allowed extension."""
    return validator.validate_file_extension(filename, [f".{ext}" for ext in allowed_extensions])

def validate_input(file, allowed_extensions: set = ALLOWED_EXTENSIONS) -> Tuple[bool, Optional[str], Optional[bytes]]:
    """
    Validate file input and return file content if valid.
    
    Args:
        file: The uploaded file object
        allowed_extensions: Set of allowed file extensions
        
    Returns:
        Tuple containing:
        - bool: True if input is valid, False otherwise
        - Optional[str]: Error message if validation fails, None if successful
        - Optional[bytes]: File content if validation is successful, None otherwise
    """
    # Check if file exists
    if not file:
        return False, "No file provided", None
        
    # Check if filename is valid
    if file.filename == '':
        return False, "Empty filename", None
        
    # Check file extension
    if not allowed_file(file.filename, allowed_extensions):
        allowed_exts = ', '.join(f'.{ext}' for ext in allowed_extensions)
        return False, f"Invalid file type. Supported formats: {allowed_exts}", None
        
    # Read file content
    try:
        file_content = file.read()
        file.seek(0)  # Reset file pointer
        
        # Check if file is empty
        if not file_content:
            return False, "File is empty", None
            
        return True, None, file_content
    except Exception as e:
        logger.error(f"Error reading file content: {str(e)}")
        return False, f"Error reading file: {str(e)}", None

def process_submission(file_path: str, file_content: bytes) -> Tuple[Dict[str, str], str, Optional[str]]:
    """
    Process a submission file and return results.
    
    Args:
        file_path: Path to the submission file
        file_content: Raw bytes of the file
        
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
            
        # Log file information
        file_size = os.path.getsize(file_path)
        file_type = Path(file_path).suffix.lower()
        logger.info(f"Processing file: {Path(file_path).name}, Size: {file_size} bytes, Type: {file_type}")
        
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
        elif "file size" in error_msg.lower() and "exceed" in error_msg.lower():
            error_msg = "The file is too large for OCR processing. Please try a smaller file."
        elif "connection" in error_msg.lower():
            error_msg = "Could not connect to the OCR service. Please check your internet connection and try again."
        
        logger.error(f"OCR service error: {str(e)}")
        return {}, "", f"OCR processing failed: {error_msg}"
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Exception details: {str(e.__class__.__name__)}")
        
        # Provide better error messages for common exceptions
        error_msg = str(e)
        if isinstance(e, OSError):
            error_msg = "File system error. The file may be corrupted or inaccessible."
        elif isinstance(e, MemoryError):
            error_msg = "Not enough memory to process this file. Please try a smaller file."
        elif isinstance(e, TimeoutError):
            error_msg = "Operation timed out. Please try again later."
        
        return {}, "", f"Processing failed: {error_msg}"

@app.route('/')
def index():
    """Render the main page."""
    guide_data = None
    if session.get('guide_uploaded'):
        guide_data = session.get('marking_guide')
    
    # Get storage statistics
    storage_stats = submission_storage.get_storage_stats()
    guide_stats = guide_storage.get_storage_stats()
    
    # Calculate expiration days from cache TTL (24 hours by default)
    guide_stats['expiration_days'] = 1  # 24 hours = 1 day
    
    return render_template('index.html', 
                         guide_data=guide_data,
                         storage_stats=storage_stats,
                         guide_stats=guide_stats)

@app.route('/clear-cache', methods=['POST'])
def clear_cache():
    """Clear all cached submission results."""
    try:
        submission_storage.clear_storage()
        flash('Cache cleared successfully')
    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        flash(f'Failed to clear cache: {str(e)}')
    
    return redirect(url_for('index'))

@app.route('/upload_guide', methods=['POST'])
def upload_guide():
    """Handle marking guide upload."""
    try:
        if 'guide' not in request.files:
            flash('No file selected')
            return redirect(request.url)
            
        file = request.files['guide']
        
        # Validate file input
        is_valid, error_message, file_content = validate_input(file, GUIDE_EXTENSIONS)
        if not is_valid:
            flash(error_message)
            return redirect(request.url)
            
        # Check if we have this guide stored
        stored_guide = guide_storage.get_guide(file_content)
        if stored_guide:
            guide_data, _ = stored_guide
            
            # Validate guide data
            if not validator.validate_marking_guide_format(guide_data):
                flash('Stored guide data is invalid')
                guide_storage.remove(file_content)
                return redirect(url_for('index'))
            
            session['guide_uploaded'] = True
            session['marking_guide'] = guide_data
            flash('Marking guide loaded from cache')
            return redirect(url_for('index'))
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        if not filename:
            flash('Invalid filename')
            return redirect(request.url)
            
        file_path = Path(app.config['UPLOAD_FOLDER']) / filename
        try:
            file.save(str(file_path))
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {str(e)}")
            flash('Failed to save uploaded file. Please try again.')
            return redirect(request.url)
        
        # Validate file exists and is readable
        if not validator.validate_file_path(str(file_path)):
            flash('Error accessing uploaded file')
            return redirect(url_for('index'))
        
        # Parse marking guide
        guide, error = parse_marking_guide(str(file_path))
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to remove uploaded guide file: {str(e)}")
        
        if error:
            flash(f'Failed to parse marking guide: {error}')
            return redirect(url_for('index'))
        
        if not guide or not guide.questions:
            flash('No questions found in marking guide')
            return redirect(url_for('index'))
        
        # Convert to dictionary for session storage
        guide_data = {
            'total_marks': guide.total_marks,
            'questions': guide.questions
        }
        
        # Validate guide data
        if not validator.validate_marking_guide_format(guide_data):
            flash('Generated guide data is invalid')
            return redirect(url_for('index'))
        
        # Store guide in cache
        try:
            guide_storage.store_guide(file_content, filename, guide_data)
            logger.info(f"Stored marking guide in cache: {filename}")
        except Exception as e:
            logger.error(f"Failed to store guide in cache: {str(e)}")
        
        # Store in session
        session['guide_uploaded'] = True
        session['marking_guide'] = guide_data
        flash('Marking guide uploaded successfully')
        
        return redirect(url_for('index'))
            
    except MemoryError:
        flash('File is too large to process')
        return redirect(request.url)
    except Exception as e:
        logger.error(f"Guide upload failed: {str(e)}")
        flash(f"Guide upload failed: {str(e)}")
        return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle student submission upload."""
    try:
        if not session.get('guide_uploaded'):
            flash('Please upload a marking guide first')
            return redirect(url_for('index'))
            
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(url_for('index'))
            
        file = request.files['file']
        
        # Validate file input
        is_valid, error_message, file_content = validate_input(file, ALLOWED_EXTENSIONS)
        if not is_valid:
            flash(error_message)
            return redirect(url_for('index'))
            
        # Save uploaded file
        filename = secure_filename(file.filename)
        if not filename:
            flash('Invalid filename')
            return redirect(url_for('index'))
            
        file_path = Path(app.config['UPLOAD_FOLDER']) / filename
        try:
            file.save(str(file_path))
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {str(e)}")
            flash('Failed to save uploaded file. Please try again.')
            return redirect(url_for('index'))
        
        # Check if file exists and is readable
        if not os.path.exists(file_path):
            flash('File was not saved properly')
            return redirect(url_for('index'))
            
        if not os.access(file_path, os.R_OK):
            flash('File cannot be read')
            return redirect(url_for('index'))
        
        # Process submission
        results, raw_text, error = process_submission(str(file_path), file_content)
        
        # Debug logging
        logger.info(f"Raw text length: {len(raw_text) if raw_text else 0}")
        logger.info(f"Results: {bool(results)}")
        logger.info(f"Error: {error if error else 'None'}")
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to remove uploaded file: {str(e)}")
        
        if error:
            flash(error)
            return redirect(url_for('index'))
            
        if not results:
            flash('No questions or answers were identified in the submission')
            return redirect(url_for('index'))
            
        # Store results in session for viewing
        session['last_submission'] = {
            'filename': filename,
            'results': results,
            'raw_text': raw_text
        }
        
        # Get marking guide from session
        marking_guide = session.get('marking_guide', {})
        
        return render_template(
            'submission_view.html',
            filename=filename,
            results=results,
            raw_text=raw_text,
            marking_guide=marking_guide
        )
            
    except MemoryError:
        flash('File is too large to process')
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        flash(f"Upload failed: {str(e)}")
        return redirect(url_for('index'))

@app.route('/view-submission')
def view_submission():
    """View the last processed submission."""
    try:
        submission = session.get('last_submission')
        if not submission:
            flash('No submission results available. Please upload a submission first.')
            return redirect(url_for('index'))
            
        # Validate submission data format
        required_keys = ['filename', 'results', 'raw_text']
        for key in required_keys:
            if key not in submission:
                flash(f'Submission data is missing required information: {key}')
                return redirect(url_for('index'))
                
        # Check if results is empty
        if not submission['results']:
            flash('The submission contains no results. Please try uploading again.')
            return redirect(url_for('index'))
            
        marking_guide = session.get('marking_guide', {})
        
        return render_template(
            'submission_view.html',
            filename=submission['filename'],
            results=submission['results'],
            raw_text=submission['raw_text'],
            marking_guide=marking_guide
        )
    except Exception as e:
        logger.error(f"Error viewing submission: {str(e)}")
        flash('An error occurred while trying to view the submission.')
        return redirect(url_for('index'))

@app.route('/clear-guide-cache', methods=['POST'])
def clear_guide_cache():
    """Clear all cached marking guides."""
    try:
        guide_storage.clear_storage()
        flash('Guide cache cleared successfully')
    except Exception as e:
        logger.error(f"Failed to clear guide cache: {str(e)}")
        flash(f'Failed to clear guide cache: {str(e)}')
    
    return redirect(url_for('index'))

@app.route('/api/process', methods=['POST'])
def process_api():
    """API endpoint for file processing."""
    try:
        # Validate request headers
        content_type = request.headers.get('Content-Type', '')
        if not content_type.startswith('multipart/form-data'):
            return jsonify({'error': 'Content-Type must be multipart/form-data'}), 415
        
        if not session.get('guide_uploaded'):
            return jsonify({'error': 'No marking guide uploaded. Upload a guide before processing submissions.'}), 400
            
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided in the request.'}), 400
            
        file = request.files['file']
        
        # Validate file input
        is_valid, error_message, file_content = validate_input(file, ALLOWED_EXTENSIONS)
        if not is_valid:
            return jsonify({'error': error_message}), 400
            
        # Save uploaded file
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({'error': 'Invalid filename provided.'}), 400
            
        file_path = Path(app.config['UPLOAD_FOLDER']) / filename
        
        try:
            file.save(str(file_path))
        except Exception as e:
            logger.error(f"API: Failed to save uploaded file: {str(e)}")
            return jsonify({'error': 'Failed to save uploaded file.'}), 500
            
        # Validate file was saved successfully
        if not os.path.exists(file_path):
            return jsonify({'error': 'File was not saved properly.'}), 500
            
        # Process submission
        results, raw_text, error = process_submission(str(file_path), file_content)
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"API: Failed to remove uploaded file: {str(e)}")
        
        if error:
            return jsonify({'error': error}), 400
            
        if not results:
            return jsonify({'error': 'No questions or answers were identified in the submission.'}), 400
            
        # Get marking guide from session
        marking_guide = session.get('marking_guide', {})
            
        return jsonify({
            'filename': filename,
            'results': results,
            'raw_text': raw_text,
            'marking_guide': marking_guide
        })
            
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/guide')
def view_guide():
    """View the currently loaded marking guide."""
    try:
        if not session.get('guide_uploaded'):
            flash('No marking guide has been uploaded')
            return redirect(url_for('index'))
            
        guide_data = session.get('marking_guide')
        if not guide_data:
            flash('Marking guide data not found in session')
            return redirect(url_for('index'))
            
        # Validate guide data has required keys
        required_keys = ['questions', 'total_marks']
        for key in required_keys:
            if key not in guide_data:
                flash(f'Marking guide data is missing required information: {key}')
                session.pop('guide_uploaded', None)
                session.pop('marking_guide', None)
                return redirect(url_for('index'))
        
        # Validate questions exist
        if not guide_data['questions']:
            flash('Marking guide contains no questions')
            return redirect(url_for('index'))
            
        return render_template(
            'guide_view.html',
            guide=guide_data
        )
    except Exception as e:
        logger.error(f"Error viewing guide: {str(e)}")
        flash('An error occurred while trying to view the marking guide.')
        return redirect(url_for('index'))

@app.route('/clear_data', methods=['POST'])
def clear_data():
    """Clear uploaded marking guide and submission data from session and cache."""
    try:
        # Remove session variables
        session.pop('guide_uploaded', None)
        session.pop('marking_guide', None)
        session.pop('last_submission', None)
        
        # Clear storage
        errors = []
        try:
            guide_storage.clear_storage()
        except Exception as e:
            errors.append(f"Failed to clear guide storage: {str(e)}")
            logger.error(f"Failed to clear guide storage: {str(e)}")
            
        try:
            submission_storage.clear_storage()
        except Exception as e:
            errors.append(f"Failed to clear submission storage: {str(e)}")
            logger.error(f"Failed to clear submission storage: {str(e)}")
            
        if errors:
            flash(f'Data cleared from session but encountered errors: {"; ".join(errors)}')
        else:
            flash('All uploaded data has been cleared.', 'success')
            
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error clearing data: {str(e)}")
        flash(f'An error occurred while clearing data: {str(e)}')
        return redirect(url_for('index'))

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    logger.error(f"File upload too large: {error}")
    flash(f'File too large. Maximum size is {config.config.max_file_size_mb}MB')
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(error):
    """Handle page not found error."""
    logger.error(f"Page not found: {request.path}")
    flash(f'Page not found: {request.path}')
    return redirect(url_for('index'))

@app.errorhandler(400)
def bad_request(error):
    """Handle bad request error."""
    logger.error(f"Bad request: {error}")
    flash('Invalid request. Please check your input and try again.')
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server error."""
    logger.error(f"Internal server error: {error}")
    flash('An internal server error occurred. Please try again later.')
    return redirect(url_for('index'))

@app.errorhandler(403)
def forbidden(error):
    """Handle forbidden error."""
    logger.error(f"Forbidden access: {request.path}")
    flash('You do not have permission to access this resource.')
    return redirect(url_for('index'))

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle method not allowed error."""
    logger.error(f"Method not allowed: {request.method} for {request.path}")
    flash(f'Method {request.method} is not allowed for this URL.')
    return redirect(url_for('index'))

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all unhandled exceptions."""
    # Log the error
    logger.error(f"Unhandled exception: {str(error)}")
    logger.error(f"Exception type: {error.__class__.__name__}")
    
    # Display user-friendly message
    flash('An unexpected error occurred. Our team has been notified.')
    
    # Return to index page
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Run the app
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 8501))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting web server on {host}:{port}")
    app.run(host=host, port=port, debug=debug) 