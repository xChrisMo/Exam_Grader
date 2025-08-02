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
        
        # Mock data collection - in real implementation, this would query the database
        training_jobs = [
            {
                'id': '1',
                'name': 'Sample Training Job',
                'status': 'completed',
                'progress': 100,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'model_name': 'GPT-3.5'
            }
        ]
        
        model_tests = [
            {
                'id': '1',
                'name': 'Sample Model Test',
                'status': 'completed',
                'results': {'accuracy': 0.85},
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        ]
        
        analytics = {
            'total_jobs': len(training_jobs),
            'success_rate': 0.85,
            'average_accuracy': 0.82
        }
        
        return {
            'metadata': {
                'report_id': str(uuid.uuid4()),
                'title': config.title,
                'description': config.description,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'user_id': user_id
            },
            'training_jobs': training_jobs,
            'model_tests': model_tests,
            'analytics': analytics,
            'summary': self._generate_summary(training_jobs, model_tests, analytics)
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