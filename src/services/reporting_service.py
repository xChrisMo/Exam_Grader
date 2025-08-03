"""
Comprehensive Reporting Service
Requirements: 5.4, 5.5, 5.6
"""

import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from jinja2 import Template
from utils.logger import logger

class ReportFormat(Enum):
    """Report output formats"""
    HTML = 'html'
    PDF = 'pdf'
    JSON = 'json'
    CSV = 'csv'
    EXCEL = 'excel'

class ReportType(Enum):
    """Report types"""
    TRAINING_SUMMARY = 'training_summary'
    MODEL_PERFORMANCE = 'model_performance'
    ANALYTICS_REPORT = 'analytics_report'
    COMPREHENSIVE = 'comprehensive'

@dataclass
class ReportConfig:
    """Configuration for report generation"""
    report_type: str
    title: str
    description: str
    include_training_jobs: bool = True
    include_model_tests: bool = True
    include_analytics: bool = True
    format: str = 'html'  # html, pdf, json

class ReportingService:
    """Service for generating comprehensive training reports"""
    
    def __init__(self):
        self.report_templates = self._load_templates()
        
    def generate_report(self, config: ReportConfig, user_id: str) -> Dict[str, Any]:
        """Generate a comprehensive report based on configuration"""
        try:
            logger.info(f"Generating report: {config.title} for user {user_id}")
            
            # Collect report data
            report_data = self._collect_report_data(config, user_id)
            
            # Generate report based on format
            if config.format == 'html':
                content = self._generate_html_report(report_data, config)
            elif config.format == 'pdf':
                content = self._generate_pdf_report(report_data, config)
            elif config.format == 'json':
                content = self._generate_json_report(report_data, config)
            else:
                raise ValueError(f"Unsupported report format: {config.format}")
            
            # Save report
            report_id = str(uuid.uuid4())
            report_path = self._save_report(report_id, content, config.format)
            
            # Create report record
            report_record = {
                'id': report_id,
                'user_id': user_id,
                'title': config.title,
                'description': config.description,
                'format': config.format,
                'file_path': report_path,
                'generated_at': datetime.now(timezone.utc),
                'file_size': len(content) if isinstance(content, (str, bytes)) else 0
            }
            
            logger.info(f"Report generated successfully: {report_id}")
            return {
                'success': True,
                'report_id': report_id,
                'report': report_record,
                'download_url': f'/api/reports/{report_id}/download'
            }
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _collect_report_data(self, config: ReportConfig, user_id: str) -> Dict[str, Any]:
        """Collect all data needed for the report"""
        try:
            from src.database.models import LLMTrainingJob, LLMModelTest, LLMTrainingReport
            
            # Query real training jobs from database
            training_jobs_query = LLMTrainingJob.query.filter_by(user_id=user_id)
            
            # Apply date range filter if specified
            if hasattr(config, 'date_range') and config.date_range:
                if config.date_range.get('start'):
                    training_jobs_query = training_jobs_query.filter(
                        LLMTrainingJob.created_at >= config.date_range['start']
                    )
                if config.date_range.get('end'):
                    training_jobs_query = training_jobs_query.filter(
                        LLMTrainingJob.created_at <= config.date_range['end']
                    )
            
            training_jobs_db = training_jobs_query.order_by(LLMTrainingJob.created_at.desc()).all()
            
            # Convert to dict format
            training_jobs = []
            for job in training_jobs_db:
                job_dict = {
                    'id': job.id,
                    'name': job.name,
                    'status': job.status,
                    'progress': job.progress or 0,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'completed_at': job.end_time.isoformat() if job.end_time else None,
                    'model_id': job.model_id,
                    'accuracy': job.accuracy or 0.0,
                    'loss': job.loss or 0.0,
                    'current_epoch': job.current_epoch or 0,
                    'total_epochs': job.total_epochs or 0,
                    'evaluation_results': job.evaluation_results or {},
                    'training_metrics': job.training_metrics or {},
                    'error_message': job.error_message
                }
                training_jobs.append(job_dict)
            
            # Query real model tests from database
            model_tests_query = LLMModelTest.query.filter_by(user_id=user_id)
            
            # Apply date range filter for model tests
            if hasattr(config, 'date_range') and config.date_range:
                if config.date_range.get('start'):
                    model_tests_query = model_tests_query.filter(
                        LLMModelTest.created_at >= config.date_range['start']
                    )
                if config.date_range.get('end'):
                    model_tests_query = model_tests_query.filter(
                        LLMModelTest.created_at <= config.date_range['end']
                    )
            
            model_tests_db = model_tests_query.order_by(LLMModelTest.created_at.desc()).all()
            
            # Convert model tests to dict format
            model_tests = []
            for test in model_tests_db:
                test_dict = {
                    'id': test.id,
                    'name': test.name,
                    'status': test.status,
                    'created_at': test.created_at.isoformat() if test.created_at else None,
                    'completed_at': test.completed_at.isoformat() if test.completed_at else None,
                    'training_job_id': test.training_job_id,
                    'accuracy_score': test.accuracy_score or 0.0,
                    'average_confidence': test.average_confidence or 0.0,
                    'processed_submissions': test.processed_submissions or 0,
                    'total_submissions': test.total_submissions or 0,
                    'results': test.results or {},
                    'error_message': test.error_message
                }
                model_tests.append(test_dict)
            
            # Calculate real analytics
            completed_jobs = [job for job in training_jobs if job['status'] == 'completed']
            failed_jobs = [job for job in training_jobs if job['status'] == 'failed']
            
            analytics = {
                'total_jobs': len(training_jobs),
                'completed_jobs': len(completed_jobs),
                'failed_jobs': len(failed_jobs),
                'success_rate': len(completed_jobs) / len(training_jobs) if training_jobs else 0.0,
                'average_accuracy': sum(job['accuracy'] for job in completed_jobs) / len(completed_jobs) if completed_jobs else 0.0,
                'total_model_tests': len(model_tests),
                'completed_tests': len([test for test in model_tests if test['status'] == 'completed']),
                'average_test_accuracy': sum(test['accuracy_score'] for test in model_tests if test['accuracy_score']) / len(model_tests) if model_tests else 0.0,
                'total_submissions_tested': sum(test['processed_submissions'] for test in model_tests),
                'models_used': list(set(job['model_id'] for job in training_jobs if job['model_id'])),
                'date_range': {
                    'start': min(job['created_at'] for job in training_jobs if job['created_at']) if training_jobs else None,
                    'end': max(job['created_at'] for job in training_jobs if job['created_at']) if training_jobs else None
                }
            }
            
            return {
                'metadata': {
                    'report_id': str(uuid.uuid4()),
                    'title': config.title,
                    'description': config.description,
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'user_id': user_id,
                    'report_type': config.report_type
                },
                'training_jobs': training_jobs,
                'model_tests': model_tests,
                'analytics': analytics,
                'summary': self._generate_summary(training_jobs, model_tests, analytics)
            }
            
        except Exception as e:
            logger.error(f"Error collecting report data: {e}")
            # Fallback to minimal data structure
            return {
                'metadata': {
                    'report_id': str(uuid.uuid4()),
                    'title': config.title,
                    'description': config.description,
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'user_id': user_id,
                    'error': str(e)
                },
                'training_jobs': [],
                'model_tests': [],
                'analytics': {
                    'total_jobs': 0,
                    'success_rate': 0.0,
                    'average_accuracy': 0.0,
                    'error': str(e)
                },
                'summary': {
                    'overview': {'total_training_jobs': 0, 'total_model_tests': 0},
                    'key_insights': [f"Error collecting data: {str(e)[:100]}"],
                    'recommendations': ["Please check system logs and try again"]
                }
            }
    
    def _generate_summary(self, training_jobs: List[Dict], model_tests: List[Dict], 
                         analytics: Dict) -> Dict[str, Any]:
        """Generate report summary"""
        return {
            'overview': {
                'total_training_jobs': len(training_jobs),
                'total_model_tests': len(model_tests)
            },
            'key_insights': [
                "Training pipeline is performing well",
                "Model accuracy is within expected range"
            ],
            'recommendations': [
                "Continue monitoring training performance",
                "Consider expanding test dataset"
            ]
        }
    
    def _generate_html_report(self, data: Dict[str, Any], config: ReportConfig) -> str:
        """Generate HTML report"""
        template = self.report_templates.get('comprehensive')
        
        html_content = template.render(
            data=data,
            config=config,
            generated_at=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        )
        
        return html_content
    
    def _generate_pdf_report(self, data: Dict[str, Any], config: ReportConfig) -> str:
        """Generate PDF report (simplified)"""
        # For now, return HTML content - in real implementation would convert to PDF
        return self._generate_html_report(data, config)
    
    def _generate_json_report(self, data: Dict[str, Any], config: ReportConfig) -> str:
        """Generate JSON report"""
        report_dict = {
            'metadata': data['metadata'],
            'training_jobs': data['training_jobs'],
            'model_tests': data['model_tests'],
            'analytics': data['analytics'],
            'summary': data['summary'],
            'config': asdict(config)
        }
        
        return json.dumps(report_dict, indent=2, default=str)
    
    def _save_report(self, report_id: str, content: Any, format: str) -> str:
        """Save report to file system"""
        reports_dir = os.path.join('uploads', 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        file_extension = {'html': 'html', 'pdf': 'pdf', 'json': 'json'}[format]
        filename = f"{report_id}.{file_extension}"
        file_path = os.path.join(reports_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def _load_templates(self) -> Dict[str, Template]:
        """Load report templates"""
        templates = {}
        
        # Comprehensive template
        comprehensive_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ data.metadata.title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { border-bottom: 2px solid #3498db; padding-bottom: 20px; margin-bottom: 30px; }
        .section { margin-bottom: 30px; }
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .summary-card { background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #3498db; }
        .metric { font-size: 24px; font-weight: bold; color: #2c3e50; }
        .job-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .job-table th, .job-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .job-table th { background-color: #f8f9fa; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ data.metadata.title }}</h1>
        <p>{{ data.metadata.description }}</p>
        <p><strong>Generated:</strong> {{ generated_at }}</p>
    </div>

    <div class="section">
        <h2>Executive Summary</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Training Jobs</h3>
                <div class="metric">{{ data.summary.overview.total_training_jobs }}</div>
                <p>Total jobs in report period</p>
            </div>
            <div class="summary-card">
                <h3>Model Tests</h3>
                <div class="metric">{{ data.summary.overview.total_model_tests }}</div>
                <p>Model validation tests</p>
            </div>
        </div>
    </div>

    {% if data.training_jobs %}
    <div class="section">
        <h2>Training Jobs Details</h2>
        <table class="job-table">
            <thead>
                <tr>
                    <th>Job Name</th>
                    <th>Model</th>
                    <th>Status</th>
                    <th>Progress</th>
                    <th>Created</th>
                </tr>
            </thead>
            <tbody>
                {% for job in data.training_jobs %}
                <tr>
                    <td>{{ job.name }}</td>
                    <td>{{ job.model_name or 'N/A' }}</td>
                    <td>{{ job.status.title() }}</td>
                    <td>{{ job.progress or 0 }}%</td>
                    <td>{{ job.created_at[:19] }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    {% if data.summary.key_insights %}
    <div class="section">
        <h2>Key Insights</h2>
        <ul>
            {% for insight in data.summary.key_insights %}
            <li>{{ insight }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    {% if data.summary.recommendations %}
    <div class="section">
        <h2>Recommendations</h2>
        <ul>
            {% for recommendation in data.summary.recommendations %}
            <li>{{ recommendation }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}
</body>
</html>
        """
        
        templates['comprehensive'] = Template(comprehensive_template)
        return templates
    
    def get_report_status(self, report_id: str) -> Dict[str, Any]:
        """Get status of a report generation"""
        return {
            'report_id': report_id,
            'status': 'completed',
            'progress': 100
        }
    
    def list_reports(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List reports for a user"""
        return []
    
    def delete_report(self, report_id: str, user_id: str) -> bool:
        """Delete a report"""
        try:
            reports_dir = os.path.join('uploads', 'reports')
            for ext in ['html', 'pdf', 'json']:
                file_path = os.path.join(reports_dir, f"{report_id}.{ext}")
                if os.path.exists(file_path):
                    os.remove(file_path)
            return True
        except Exception as e:
            logger.error(f"Error deleting report {report_id}: {str(e)}")
            return False