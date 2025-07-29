"""
Reporting API Routes
Provides endpoints for generating and managing training reports
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from datetime import datetime, timedelta
from typing import Dict, Any
import logging
import os
import tempfile

from src.services.reporting_service import (
    ReportingService, ReportConfig, ReportFormat, ReportType
)
from flask_login import login_required
from utils.error_handler import handle_api_error

logger = logging.getLogger(__name__)

reporting_bp = Blueprint('reporting', __name__, url_prefix='/api/reporting')
reporting_service = ReportingService()

@reporting_bp.route('/generate', methods=['POST'])
@login_required
def generate_report():
    """Generate a new report based on configuration"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Report title is required'}), 400
        
        if not data.get('report_type'):
            return jsonify({'error': 'Report type is required'}), 400
        
        if not data.get('format'):
            return jsonify({'error': 'Report format is required'}), 400
        
        date_range = None
        if data.get('date_range'):
            date_range = {}
            if data['date_range'].get('start'):
                date_range['start'] = datetime.fromisoformat(data['date_range']['start'])
            if data['date_range'].get('end'):
                date_range['end'] = datetime.fromisoformat(data['date_range']['end'])
        
        # Create report configuration
        config = ReportConfig(
            report_type=ReportType(data['report_type']),
            format=ReportFormat(data['format']),
            title=data['title'],
            description=data.get('description'),
            include_charts=data.get('include_charts', True),
            include_metrics=data.get('include_metrics', True),
            include_logs=data.get('include_logs', False),
            include_model_testing=data.get('include_model_testing', False),
            date_range=date_range,
            job_ids=data.get('job_ids'),
            test_ids=data.get('test_ids'),
            custom_sections=data.get('custom_sections'),
            template_name=data.get('template_name'),
            output_path=data.get('output_path')
        )
        
        # Generate report
        result = reporting_service.generate_report(config)
        
        # Return appropriate response based on format
        if config.format in [ReportFormat.HTML, ReportFormat.JSON, ReportFormat.CSV]:
            return jsonify({
                'success': True,
                'report': {
                    'content': result['content'],
                    'format': result['format'],
                    'size': result['size'],
                    'file_path': result.get('file_path')
                }
            })
        else:
            # For binary formats (PDF, Excel), return file info
            return jsonify({
                'success': True,
                'report': {
                    'format': result['format'],
                    'size': result['size'],
                    'file_path': result.get('file_path'),
                    'download_url': f"/api/reporting/download/{os.path.basename(result['file_path'])}" if result.get('file_path') else None
                }
            })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return handle_api_error(e)

@reporting_bp.route('/download/<filename>', methods=['GET'])
@login_required
def download_report(filename):
    """Download a generated report file"""
    try:
        # Security check - ensure filename is safe
        if not filename or '..' in filename or '/' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        file_path = os.path.join(reporting_service.output_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Report file not found'}), 404
        
        # Determine mimetype based on extension
        mimetype = 'application/octet-stream'
        if filename.endswith('.pdf'):
            mimetype = 'application/pdf'
        elif filename.endswith('.html'):
            mimetype = 'text/html'
        elif filename.endswith('.json'):
            mimetype = 'application/json'
        elif filename.endswith('.csv'):
            mimetype = 'text/csv'
        elif filename.endswith('.xlsx'):
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        return handle_api_error(e)

@reporting_bp.route('/templates', methods=['GET'])
@login_required
def get_templates():
    """Get list of available report templates"""
    try:
        templates = reporting_service.get_available_templates()
        
        return jsonify({
            'success': True,
            'templates': templates
        })
        
    except Exception as e:
        logger.error(f"Error getting templates: {str(e)}")
        return handle_api_error(e)

@reporting_bp.route('/history', methods=['GET'])
@login_required
def get_report_history():
    """Get history of generated reports"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = reporting_service.get_report_history(limit)
        
        return jsonify({
            'success': True,
            'reports': history
        })
        
    except Exception as e:
        logger.error(f"Error getting report history: {str(e)}")
        return handle_api_error(e)

@reporting_bp.route('/schedule', methods=['POST'])
@login_required
def schedule_report():
    """Schedule a report to be generated automatically"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('config'):
            return jsonify({'error': 'Report configuration is required'}), 400
        
        if not data.get('schedule'):
            return jsonify({'error': 'Schedule configuration is required'}), 400
        
        # Parse report configuration
        config_data = data['config']
        date_range = None
        if config_data.get('date_range'):
            date_range = {}
            if config_data['date_range'].get('start'):
                date_range['start'] = datetime.fromisoformat(config_data['date_range']['start'])
            if config_data['date_range'].get('end'):
                date_range['end'] = datetime.fromisoformat(config_data['date_range']['end'])
        
        config = ReportConfig(
            report_type=ReportType(config_data['report_type']),
            format=ReportFormat(config_data['format']),
            title=config_data['title'],
            description=config_data.get('description'),
            include_charts=config_data.get('include_charts', True),
            include_metrics=config_data.get('include_metrics', True),
            include_logs=config_data.get('include_logs', False),
            include_model_testing=config_data.get('include_model_testing', False),
            date_range=date_range,
            job_ids=config_data.get('job_ids'),
            test_ids=config_data.get('test_ids'),
            custom_sections=config_data.get('custom_sections'),
            template_name=config_data.get('template_name'),
            output_path=config_data.get('output_path')
        )
        
        # Schedule report
        schedule_id = reporting_service.schedule_report(config, data['schedule'])
        
        return jsonify({
            'success': True,
            'schedule_id': schedule_id,
            'message': 'Report scheduled successfully'
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error scheduling report: {str(e)}")
        return handle_api_error(e)

@reporting_bp.route('/preview', methods=['POST'])
@login_required
def preview_report():
    """Generate a preview of a report without saving"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Report title is required'}), 400
        
        if not data.get('report_type'):
            return jsonify({'error': 'Report type is required'}), 400
        
        date_range = None
        if data.get('date_range'):
            date_range = {}
            if data['date_range'].get('start'):
                date_range['start'] = datetime.fromisoformat(data['date_range']['start'])
            if data['date_range'].get('end'):
                date_range['end'] = datetime.fromisoformat(data['date_range']['end'])
        
        config = ReportConfig(
            report_type=ReportType(data['report_type']),
            format=ReportFormat.HTML,  # Always HTML for preview
            title=data['title'],
            description=data.get('description'),
            include_charts=data.get('include_charts', True),
            include_metrics=data.get('include_metrics', True),
            include_logs=data.get('include_logs', False),
            include_model_testing=data.get('include_model_testing', False),
            date_range=date_range,
            job_ids=data.get('job_ids'),
            test_ids=data.get('test_ids'),
            custom_sections=data.get('custom_sections'),
            template_name=data.get('template_name'),
            output_path=None  # No file output for preview
        )
        
        # Generate report preview
        result = reporting_service.generate_report(config)
        
        return jsonify({
            'success': True,
            'preview': {
                'content': result['content'],
                'size': result['size']
            }
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error generating report preview: {str(e)}")
        return handle_api_error(e)

@reporting_bp.route('/formats', methods=['GET'])
@login_required
def get_supported_formats():
    """Get list of supported report formats"""
    try:
        formats = [
            {
                'value': format.value,
                'name': format.name,
                'description': _get_format_description(format)
            }
            for format in ReportFormat
        ]
        
        return jsonify({
            'success': True,
            'formats': formats
        })
        
    except Exception as e:
        logger.error(f"Error getting supported formats: {str(e)}")
        return handle_api_error(e)

@reporting_bp.route('/types', methods=['GET'])
@login_required
def get_report_types():
    """Get list of available report types"""
    try:
        types = [
            {
                'value': report_type.value,
                'name': report_type.name,
                'description': _get_type_description(report_type)
            }
            for report_type in ReportType
        ]
        
        return jsonify({
            'success': True,
            'types': types
        })
        
    except Exception as e:
        logger.error(f"Error getting report types: {str(e)}")
        return handle_api_error(e)

@reporting_bp.route('/config/validate', methods=['POST'])
@login_required
def validate_config():
    """Validate a report configuration"""
    try:
        data = request.get_json()
        
        errors = []
        
        # Validate required fields
        if not data.get('title'):
            errors.append('Report title is required')
        
        if not data.get('report_type'):
            errors.append('Report type is required')
        elif data['report_type'] not in [t.value for t in ReportType]:
            errors.append('Invalid report type')
        
        if not data.get('format'):
            errors.append('Report format is required')
        elif data['format'] not in [f.value for f in ReportFormat]:
            errors.append('Invalid report format')
        
        # Validate date range
        if data.get('date_range'):
            try:
                if data['date_range'].get('start'):
                    datetime.fromisoformat(data['date_range']['start'])
                if data['date_range'].get('end'):
                    datetime.fromisoformat(data['date_range']['end'])
            except ValueError:
                errors.append('Invalid date format in date_range')
        
        if data.get('job_ids') and not isinstance(data['job_ids'], list):
            errors.append('job_ids must be a list')
        
        if data.get('test_ids') and not isinstance(data['test_ids'], list):
            errors.append('test_ids must be a list')
        
        return jsonify({
            'success': len(errors) == 0,
            'errors': errors,
            'valid': len(errors) == 0
        })
        
    except Exception as e:
        logger.error(f"Error validating config: {str(e)}")
        return handle_api_error(e)

def _get_format_description(format: ReportFormat) -> str:
    """Get description for a report format"""
    descriptions = {
        ReportFormat.HTML: 'Interactive web page with charts and tables',
        ReportFormat.PDF: 'Printable document with embedded charts',
        ReportFormat.JSON: 'Machine-readable data format',
        ReportFormat.CSV: 'Spreadsheet-compatible comma-separated values',
        ReportFormat.EXCEL: 'Microsoft Excel workbook with multiple sheets'
    }
    return descriptions.get(format, 'Unknown format')

def _get_type_description(report_type: ReportType) -> str:
    """Get description for a report type"""
    descriptions = {
        ReportType.TRAINING_SUMMARY: 'Overview of training jobs and their performance',
        ReportType.MODEL_TESTING: 'Results from model testing with student submissions',
        ReportType.PERFORMANCE_ANALYSIS: 'Detailed analysis of training performance metrics',
        ReportType.COMPARATIVE_ANALYSIS: 'Comparison between multiple training jobs or models',
        ReportType.SYSTEM_HEALTH: 'System resource usage and health metrics',
        ReportType.CUSTOM: 'Custom report with user-defined sections'
    }
    return descriptions.get(report_type, 'Unknown report type')

# Error handlers
@reporting_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@reporting_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@reporting_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error in reporting routes: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500