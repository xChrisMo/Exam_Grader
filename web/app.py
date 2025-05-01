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
        logger.error(f"OCR service error: {str(e)}")
        return {}, "", f"OCR processing failed: {str(e)}"
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Exception details: {str(e.__class__.__name__)}")
        return {}, "", f"Processing failed: {str(e)}"

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
        flash('Failed to clear cache')
    
    return redirect(url_for('index'))

@app.route('/upload_guide', methods=['POST'])
def upload_guide():
    """Handle marking guide upload."""
    if 'guide' not in request.files:
        flash('No file selected')
        return redirect(request.url)
        
    file = request.files['guide']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
        
    if not file or not allowed_file(file.filename, GUIDE_EXTENSIONS):
        flash('Invalid file type. Please upload a .docx or .txt file')
        return redirect(request.url)
        
    try:
        # Read file content for storage lookup
        file_content = file.read()
        file.seek(0)  # Reset file pointer
        
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
        file_path = Path(app.config['UPLOAD_FOLDER']) / filename
        file.save(str(file_path))
        
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
            logger.warning(f"Failed to remove uploaded file: {str(e)}")
        
        if error:
            flash(f"Error parsing marking guide: {error}")
            return redirect(url_for('index'))
            
        # Store guide data
        guide_data = {
            'questions': guide.questions,  # Already a list, no conversion needed
            'total_marks': guide.total_marks
        }
        
        # Validate guide data
        if not validator.validate_marking_guide_format(guide_data):
            flash('Generated guide data is invalid')
            return redirect(url_for('index'))
        
        try:
            guide_storage.store_guide(file_content, filename, guide_data)
        except Exception as e:
            logger.warning(f"Failed to cache guide: {str(e)}")
            
        # Store marking guide in session
        session['guide_uploaded'] = True
        session['marking_guide'] = guide_data
        
        flash('Marking guide uploaded successfully')
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Guide upload failed: {str(e)}")
        flash(f"Upload failed: {str(e)}")
        return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle student submission upload and processing."""
    if not session.get('guide_uploaded'):
        flash('Please upload a marking guide first')
        return redirect(url_for('index'))
        
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
        
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
        
    if not file or not allowed_file(file.filename):
        flash('Invalid file type')
        return redirect(request.url)
        
    try:
        # Read file content for storage lookup
        file_content = file.read()
        file.seek(0)  # Reset file pointer for saving
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = Path(app.config['UPLOAD_FOLDER']) / filename
        file.save(str(file_path))
        
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
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        flash(f"Upload failed: {str(e)}")
        return redirect(url_for('index'))

@app.route('/view-submission')
def view_submission():
    """View the last processed submission."""
    submission = session.get('last_submission')
    if not submission:
        flash('No submission results available')
        return redirect(url_for('index'))
        
    marking_guide = session.get('marking_guide', {})
    
    return render_template(
        'submission_view.html',
        filename=submission['filename'],
        results=submission['results'],
        raw_text=submission['raw_text'],
        marking_guide=marking_guide
    )

@app.route('/clear-guide-cache', methods=['POST'])
def clear_guide_cache():
    """Clear all cached marking guides."""
    try:
        guide_storage.clear_storage()
        flash('Guide cache cleared successfully')
    except Exception as e:
        logger.error(f"Failed to clear guide cache: {str(e)}")
        flash('Failed to clear guide cache')
    
    return redirect(url_for('index'))

@app.route('/api/process', methods=['POST'])
def process_api():
    """API endpoint for file processing."""
    if not session.get('guide_uploaded'):
        return jsonify({'error': 'No marking guide uploaded'}), 400
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
        
    try:
        # Read file content for storage lookup
        file_content = file.read()
        file.seek(0)  # Reset file pointer for saving
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = Path(app.config['UPLOAD_FOLDER']) / filename
        file.save(str(file_path))
        
        # Process submission
        results, raw_text, error = process_submission(str(file_path), file_content)
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to remove uploaded file: {str(e)}")
        
        if error:
            return jsonify({'error': error}), 400
            
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
        return jsonify({'error': str(e)}), 500

@app.route('/guide')
def view_guide():
    """View the currently loaded marking guide."""
    if not session.get('guide_uploaded'):
        flash('No marking guide has been uploaded')
        return redirect(url_for('index'))
        
    guide_data = session.get('marking_guide')
    if not guide_data:
        flash('Marking guide data not found in session')
        return redirect(url_for('index'))
        
    return render_template(
        'guide_view.html',
        guide=guide_data
    )

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    flash(f'File too large. Maximum size is {config.config.max_file_size_mb}MB')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Run the app
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 8501))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting web server on {host}:{port}")
    app.run(host=host, port=port, debug=debug) 