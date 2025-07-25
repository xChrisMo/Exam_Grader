"""
Report Service - Generates training reports and analytics.

This service creates comprehensive reports based on training results,
model performance, and dataset analysis.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import seaborn as sns
import pandas as pd
from io import BytesIO
import base64

from src.services.base_service import BaseService, ServiceStatus
from src.services.training_service import training_service, TrainingJob, TrainingStatus
from src.services.model_manager_service import model_manager_service
from utils.logger import logger


@dataclass
class ReportConfig:
    """Report generation configuration"""
    include_charts: bool = True
    include_logs: bool = True
    include_metrics: bool = True
    chart_format: str = 'png'
    chart_dpi: int = 300


class ReportService(BaseService):
    """Service for generating training reports and analytics"""

    def __init__(self):
        super().__init__("report_service")
        self.output_dir = "output/reports"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Configure matplotlib style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")

    async def initialize(self) -> bool:
        """Initialize the report service"""
        try:
            self.status = ServiceStatus.HEALTHY
            logger.info("Report service initialized successfully")
            return True
        except Exception as e:
            self.status = ServiceStatus.UNHEALTHY
            logger.error(f"Failed to initialize report service: {str(e)}")
            return False

    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            return os.path.exists(self.output_dir)
        except Exception as e:
            logger.error(f"Report service health check failed: {str(e)}")
            return False

    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            # Close any open matplotlib figures
            plt.close('all')
            logger.info("Report service cleanup completed")
        except Exception as e:
            logger.error(f"Error during report service cleanup: {str(e)}")

    def generate_report(
        self,
        job_ids: List[str],
        config: Optional[ReportConfig] = None
    ) -> str:
        """Generate report for one or more training jobs"""
        try:
            with self.track_request("generate_report"):
                if not job_ids:
                    raise ValueError("No job IDs provided")
                
                if len(job_ids) == 1:
                    # Single job report
                    report = self.generate_training_report(job_ids[0], config)
                    return job_ids[0]  # Return job_id as report_id
                else:
                    # Comparison report for multiple jobs
                    report = self.generate_comparison_report(job_ids, config)
                    return f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise

    def generate_training_report(
        self,
        job_id: str,
        config: Optional[ReportConfig] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive training report for a job"""
        try:
            with self.track_request("generate_training_report"):
                if config is None:
                    config = ReportConfig()
                
                job = training_service.get_training_job(job_id)
                if not job:
                    raise ValueError(f"Training job {job_id} not found")
                
                # Generate report sections
                report = {
                    'job_id': job_id,
                    'generated_at': datetime.now().isoformat(),
                    'job_info': self._generate_job_info_section(job),
                    'model_info': self._generate_model_info_section(job),
                    'training_summary': self._generate_training_summary(job),
                    'performance_metrics': self._generate_performance_metrics(job),
                }
                
                if config.include_charts:
                    report['charts'] = self._generate_training_charts(job, config)
                
                if config.include_logs:
                    report['logs'] = job.logs
                
                if config.include_metrics:
                    report['detailed_metrics'] = job.metrics
                
                # Save report to file
                report_path = self._save_report(job_id, report)
                report['report_path'] = report_path
                
                logger.info(f"Generated training report for job {job_id}")
                return report
                
        except Exception as e:
            logger.error(f"Error generating training report for job {job_id}: {str(e)}")
            raise

    def generate_comparison_report(
        self,
        job_ids: List[str],
        config: Optional[ReportConfig] = None
    ) -> Dict[str, Any]:
        """Generate comparison report for multiple training jobs"""
        try:
            with self.track_request("generate_comparison_report"):
                if config is None:
                    config = ReportConfig()
                
                jobs = []
                for job_id in job_ids:
                    job = training_service.get_training_job(job_id)
                    if job:
                        jobs.append(job)
                
                if not jobs:
                    raise ValueError("No valid training jobs found")
                
                report = {
                    'job_ids': job_ids,
                    'generated_at': datetime.now().isoformat(),
                    'comparison_summary': self._generate_comparison_summary(jobs),
                    'performance_comparison': self._generate_performance_comparison(jobs),
                }
                
                if config.include_charts:
                    report['comparison_charts'] = self._generate_comparison_charts(jobs, config)
                
                # Save report
                report_id = f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                report_path = self._save_report(report_id, report)
                report['report_path'] = report_path
                
                logger.info(f"Generated comparison report for {len(jobs)} jobs")
                return report
                
        except Exception as e:
            logger.error(f"Error generating comparison report: {str(e)}")
            raise

    def generate_dataset_analysis(self, dataset_id: str) -> Dict[str, Any]:
        """Generate dataset analysis report"""
        try:
            with self.track_request("generate_dataset_analysis"):
                # TODO: Implement actual dataset analysis
                # For now, return mock analysis
                
                analysis = {
                    'dataset_id': dataset_id,
                    'generated_at': datetime.now().isoformat(),
                    'statistics': {
                        'total_documents': 10,
                        'total_words': 50000,
                        'average_document_length': 5000,
                        'vocabulary_size': 8000,
                        'unique_tokens': 7500
                    },
                    'quality_metrics': {
                        'readability_score': 0.75,
                        'diversity_score': 0.82,
                        'completeness_score': 0.90
                    },
                    'recommendations': [
                        "Dataset has good diversity for training",
                        "Consider adding more technical documents",
                        "Text quality is suitable for fine-tuning"
                    ]
                }
                
                logger.info(f"Generated dataset analysis for {dataset_id}")
                return analysis
                
        except Exception as e:
            logger.error(f"Error generating dataset analysis: {str(e)}")
            raise

    def _generate_job_info_section(self, job: TrainingJob) -> Dict[str, Any]:
        """Generate job information section"""
        duration = None
        if job.start_time and job.end_time:
            duration = (job.end_time - job.start_time).total_seconds()
        elif job.start_time:
            duration = (datetime.now() - job.start_time).total_seconds()
        
        return {
            'name': job.name,
            'status': job.status.value,
            'progress': job.progress,
            'start_time': job.start_time.isoformat() if job.start_time else None,
            'end_time': job.end_time.isoformat() if job.end_time else None,
            'duration_seconds': duration,
            'duration_formatted': self._format_duration(duration) if duration else None,
            'error_message': job.error_message
        }

    def _generate_model_info_section(self, job: TrainingJob) -> Dict[str, Any]:
        """Generate model information section"""
        model = model_manager_service.get_model_by_id(job.model_id)
        
        return {
            'model_id': job.model_id,
            'model_name': model.name if model else 'Unknown',
            'provider': model.provider.value if model else 'Unknown',
            'configuration': job.config.to_dict(),
            'capabilities': model.capabilities if model else []
        }

    def _generate_training_summary(self, job: TrainingJob) -> Dict[str, Any]:
        """Generate comprehensive training summary"""
        summary = {
            'total_epochs': job.total_epochs,
            'completed_epochs': job.current_epoch,
            'final_loss': job.loss,
            'final_accuracy': job.accuracy,
            'final_validation_loss': job.validation_loss,
            'final_validation_accuracy': job.validation_accuracy
        }
        
        # Add improvement metrics if we have epoch data
        if job.metrics and len(job.metrics) > 1:
            epoch_keys = [k for k in job.metrics.keys() if k.startswith('epoch_')]
            if epoch_keys:
                epoch_keys.sort(key=lambda x: int(x.split('_')[1]))  # Sort by epoch number
                first_epoch = job.metrics[epoch_keys[0]]
                last_epoch = job.metrics[epoch_keys[-1]]
                
                summary['loss_improvement'] = first_epoch['loss'] - last_epoch['loss']
                summary['accuracy_improvement'] = last_epoch['accuracy'] - first_epoch['accuracy']
                summary['val_loss_improvement'] = first_epoch['val_loss'] - last_epoch['val_loss']
                summary['val_accuracy_improvement'] = last_epoch['val_accuracy'] - first_epoch['val_accuracy']
                
                # Calculate best metrics across all epochs
                all_losses = [job.metrics[k]['loss'] for k in epoch_keys]
                all_accuracies = [job.metrics[k]['accuracy'] for k in epoch_keys]
                all_val_losses = [job.metrics[k]['val_loss'] for k in epoch_keys]
                all_val_accuracies = [job.metrics[k]['val_accuracy'] for k in epoch_keys]
                
                summary['best_training_loss'] = min(all_losses)
                summary['best_training_accuracy'] = max(all_accuracies)
                summary['best_validation_loss'] = min(all_val_losses)
                summary['best_validation_accuracy'] = max(all_val_accuracies)
                
                # Find epochs where best metrics occurred
                summary['best_loss_epoch'] = all_losses.index(min(all_losses)) + 1
                summary['best_accuracy_epoch'] = all_accuracies.index(max(all_accuracies)) + 1
                summary['best_val_loss_epoch'] = all_val_losses.index(min(all_val_losses)) + 1
                summary['best_val_accuracy_epoch'] = all_val_accuracies.index(max(all_val_accuracies)) + 1
                
                # Calculate convergence metrics
                summary['loss_convergence_rate'] = self._calculate_convergence_rate(all_losses)
                summary['accuracy_convergence_rate'] = self._calculate_convergence_rate(all_accuracies)
        
        return summary

    def _generate_performance_metrics(self, job: TrainingJob) -> Dict[str, Any]:
        """Generate performance metrics section"""
        metrics = {
            'training_metrics': {},
            'validation_metrics': {},
            'final_evaluation': {}
        }
        
        # Extract training metrics from job metrics
        if job.metrics:
            epoch_data = []
            for key, value in job.metrics.items():
                if key.startswith('epoch_'):
                    epoch_num = int(key.split('_')[1])
                    epoch_data.append({
                        'epoch': epoch_num,
                        'loss': value['loss'],
                        'accuracy': value['accuracy'],
                        'val_loss': value['val_loss'],
                        'val_accuracy': value['val_accuracy']
                    })
            
            if epoch_data:
                metrics['training_metrics'] = {
                    'epochs': epoch_data,
                    'best_accuracy': max(d['accuracy'] for d in epoch_data),
                    'best_val_accuracy': max(d['val_accuracy'] for d in epoch_data),
                    'lowest_loss': min(d['loss'] for d in epoch_data),
                    'lowest_val_loss': min(d['val_loss'] for d in epoch_data)
                }
            
            if 'final_evaluation' in job.metrics:
                metrics['final_evaluation'] = job.metrics['final_evaluation']
        
        return metrics

    def _generate_comparison_summary(self, jobs: List[TrainingJob]) -> Dict[str, Any]:
        """Generate comparison summary for multiple jobs"""
        completed_jobs = [j for j in jobs if j.status == TrainingStatus.COMPLETED]
        
        summary = {
            'total_jobs': len(jobs),
            'completed_jobs': len(completed_jobs),
            'failed_jobs': len([j for j in jobs if j.status == TrainingStatus.FAILED]),
            'average_duration': None,
            'best_performing_job': None,
            'models_compared': list(set(j.model_id for j in jobs))
        }
        
        if completed_jobs:
            # Calculate average duration
            durations = []
            for job in completed_jobs:
                if job.start_time and job.end_time:
                    duration = (job.end_time - job.start_time).total_seconds()
                    durations.append(duration)
            
            if durations:
                summary['average_duration'] = sum(durations) / len(durations)
            
            # Find best performing job (highest accuracy)
            best_job = max(completed_jobs, key=lambda j: j.accuracy or 0)
            summary['best_performing_job'] = {
                'job_id': best_job.id,
                'name': best_job.name,
                'accuracy': best_job.accuracy,
                'model_id': best_job.model_id
            }
        
        return summary

    def _generate_performance_comparison(self, jobs: List[TrainingJob]) -> Dict[str, Any]:
        """Generate performance comparison data"""
        comparison_data = []
        
        for job in jobs:
            if job.status == TrainingStatus.COMPLETED:
                job_data = {
                    'job_id': job.id,
                    'name': job.name,
                    'model_id': job.model_id,
                    'accuracy': job.accuracy,
                    'loss': job.loss,
                    'val_accuracy': job.validation_accuracy,
                    'val_loss': job.validation_loss,
                    'epochs': job.current_epoch,
                    'learning_rate': job.config.learning_rate,
                    'batch_size': job.config.batch_size
                }
                
                # Add final evaluation metrics if available
                if job.metrics and 'final_evaluation' in job.metrics:
                    final_eval = job.metrics['final_evaluation']
                    job_data.update({
                        'test_accuracy': final_eval.get('test_accuracy'),
                        'precision': final_eval.get('precision'),
                        'recall': final_eval.get('recall'),
                        'f1_score': final_eval.get('f1_score')
                    })
                
                comparison_data.append(job_data)
        
        return {
            'jobs': comparison_data,
            'rankings': {
                'by_accuracy': sorted(comparison_data, key=lambda x: x['accuracy'] or 0, reverse=True),
                'by_val_accuracy': sorted(comparison_data, key=lambda x: x['val_accuracy'] or 0, reverse=True),
                'by_loss': sorted(comparison_data, key=lambda x: x['loss'] or float('inf'))
            }
        }

    def _generate_training_charts(self, job: TrainingJob, config: ReportConfig) -> Dict[str, str]:
        """Generate training charts"""
        charts = {}
        
        if not job.metrics:
            return charts
        
        try:
            # Extract epoch data
            epoch_data = []
            for key, value in job.metrics.items():
                if key.startswith('epoch_'):
                    epoch_num = int(key.split('_')[1])
                    epoch_data.append({
                        'epoch': epoch_num,
                        'loss': value['loss'],
                        'accuracy': value['accuracy'],
                        'val_loss': value['val_loss'],
                        'val_accuracy': value['val_accuracy']
                    })
            
            if not epoch_data:
                return charts
            
            df = pd.DataFrame(epoch_data)
            
            # Training Loss Chart
            plt.figure(figsize=(10, 6))
            plt.plot(df['epoch'], df['loss'], label='Training Loss', marker='o')
            plt.plot(df['epoch'], df['val_loss'], label='Validation Loss', marker='s')
            plt.xlabel('Epoch')
            plt.ylabel('Loss')
            plt.title(f'Training Loss - {job.name}')
            plt.legend()
            plt.grid(True, alpha=0.3)
            charts['loss_chart'] = self._plot_to_base64(config)
            
            # Training Accuracy Chart
            plt.figure(figsize=(10, 6))
            plt.plot(df['epoch'], df['accuracy'], label='Training Accuracy', marker='o')
            plt.plot(df['epoch'], df['val_accuracy'], label='Validation Accuracy', marker='s')
            plt.xlabel('Epoch')
            plt.ylabel('Accuracy')
            plt.title(f'Training Accuracy - {job.name}')
            plt.legend()
            plt.grid(True, alpha=0.3)
            charts['accuracy_chart'] = self._plot_to_base64(config)
            
            # Combined Metrics Chart
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Loss subplot
            ax1.plot(df['epoch'], df['loss'], label='Training', marker='o')
            ax1.plot(df['epoch'], df['val_loss'], label='Validation', marker='s')
            ax1.set_xlabel('Epoch')
            ax1.set_ylabel('Loss')
            ax1.set_title('Loss')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Accuracy subplot
            ax2.plot(df['epoch'], df['accuracy'], label='Training', marker='o')
            ax2.plot(df['epoch'], df['val_accuracy'], label='Validation', marker='s')
            ax2.set_xlabel('Epoch')
            ax2.set_ylabel('Accuracy')
            ax2.set_title('Accuracy')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            plt.suptitle(f'Training Metrics - {job.name}')
            plt.tight_layout()
            charts['combined_chart'] = self._plot_to_base64(config)
            
        except Exception as e:
            logger.error(f"Error generating training charts: {str(e)}")
        
        return charts

    def _generate_comparison_charts(self, jobs: List[TrainingJob], config: ReportConfig) -> Dict[str, str]:
        """Generate comparison charts for multiple jobs"""
        charts = {}
        completed_jobs = [j for j in jobs if j.status == TrainingStatus.COMPLETED]
        
        if not completed_jobs:
            return charts
        
        try:
            # Accuracy Comparison Bar Chart
            job_names = [j.name for j in completed_jobs]
            accuracies = [j.accuracy or 0 for j in completed_jobs]
            val_accuracies = [j.validation_accuracy or 0 for j in completed_jobs]
            
            x = range(len(job_names))
            width = 0.35
            
            plt.figure(figsize=(12, 6))
            plt.bar([i - width/2 for i in x], accuracies, width, label='Training Accuracy')
            plt.bar([i + width/2 for i in x], val_accuracies, width, label='Validation Accuracy')
            plt.xlabel('Training Jobs')
            plt.ylabel('Accuracy')
            plt.title('Accuracy Comparison')
            plt.xticks(x, job_names, rotation=45, ha='right')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            charts['accuracy_comparison'] = self._plot_to_base64(config)
            
            # Loss Comparison Bar Chart
            losses = [j.loss or 0 for j in completed_jobs]
            val_losses = [j.validation_loss or 0 for j in completed_jobs]
            
            plt.figure(figsize=(12, 6))
            plt.bar([i - width/2 for i in x], losses, width, label='Training Loss')
            plt.bar([i + width/2 for i in x], val_losses, width, label='Validation Loss')
            plt.xlabel('Training Jobs')
            plt.ylabel('Loss')
            plt.title('Loss Comparison')
            plt.xticks(x, job_names, rotation=45, ha='right')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            charts['loss_comparison'] = self._plot_to_base64(config)
            
        except Exception as e:
            logger.error(f"Error generating comparison charts: {str(e)}")
        
        return charts

    def _plot_to_base64(self, config: ReportConfig) -> str:
        """Convert current matplotlib plot to base64 string"""
        buffer = BytesIO()
        plt.savefig(buffer, format=config.chart_format, dpi=config.chart_dpi, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        buffer.close()
        plt.close()
        return f"data:image/{config.chart_format};base64,{image_base64}"

    def _save_report(self, report_id: str, report: Dict[str, Any]) -> str:
        """Save report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"training_report_{report_id}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Remove base64 charts from saved report to reduce file size
        report_copy = report.copy()
        if 'charts' in report_copy:
            report_copy['charts'] = {k: f"<base64_chart_{k}>" for k in report_copy['charts'].keys()}
        if 'comparison_charts' in report_copy:
            report_copy['comparison_charts'] = {k: f"<base64_chart_{k}>" for k in report_copy['comparison_charts'].keys()}
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_copy, f, indent=2, ensure_ascii=False)
        
        return filepath

    def _calculate_convergence_rate(self, values: List[float]) -> float:
        """Calculate convergence rate for a series of values"""
        if len(values) < 2:
            return 0.0
        
        # Calculate the rate of change between consecutive values
        changes = []
        for i in range(1, len(values)):
            change = abs(values[i] - values[i-1])
            changes.append(change)
        
        # Return average rate of change (lower is better for convergence)
        return sum(changes) / len(changes) if changes else 0.0

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"

    def get_available_reports(self) -> List[Dict[str, Any]]:
        """Get list of available reports"""
        try:
            reports = []
            if os.path.exists(self.output_dir):
                for filename in os.listdir(self.output_dir):
                    if filename.endswith('.json') and filename.startswith('training_report_'):
                        filepath = os.path.join(self.output_dir, filename)
                        stat = os.stat(filepath)
                        
                        # Extract report ID from filename: training_report_{report_id}_{timestamp}.json
                        try:
                            # Remove prefix and suffix, then split by underscore
                            name_without_prefix = filename[len('training_report_'):]
                            name_without_suffix = name_without_prefix[:-5]  # Remove .json
                            parts = name_without_suffix.split('_')
                            # Report ID is everything except the last 2 parts (date and time)
                            if len(parts) >= 3:
                                report_id = '_'.join(parts[:-2])
                            else:
                                report_id = parts[0] if parts else filename
                        except Exception:
                            # Fallback to filename if parsing fails
                            report_id = filename
                        
                        reports.append({
                            'id': report_id,
                            'filename': filename,
                            'filepath': filepath,
                            'size': stat.st_size,
                            'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
            
            # Sort by creation time (newest first)
            reports.sort(key=lambda x: x['created_at'], reverse=True)
            return reports
            
        except Exception as e:
            logger.error(f"Error getting available reports: {str(e)}")
            return []

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get report by ID"""
        try:
            # Look for existing report file first
            if os.path.exists(self.output_dir):
                for filename in os.listdir(self.output_dir):
                    if filename.endswith('.json') and filename.startswith('training_report_'):
                        # Extract report ID from filename
                        try:
                            name_without_prefix = filename[len('training_report_'):]
                            name_without_suffix = name_without_prefix[:-5]  # Remove .json
                            parts = name_without_suffix.split('_')
                            # Report ID is everything except the last 2 parts (date and time)
                            if len(parts) >= 3:
                                file_report_id = '_'.join(parts[:-2])
                            else:
                                file_report_id = parts[0] if parts else filename
                            
                            if file_report_id == report_id:
                                filepath = os.path.join(self.output_dir, filename)
                                with open(filepath, 'r', encoding='utf-8') as f:
                                    report_data = json.load(f)
                                
                                # Add content field for viewing
                                report_data['content'] = self._generate_html_content(report_data)
                                return report_data
                        except Exception:
                            continue
            
            # If no existing report found, try to generate one for the job
            job = training_service.get_training_job(report_id)
            if job:
                report = self.generate_training_report(report_id)
                report['content'] = self._generate_html_content(report)
                return report
            
            return None
                
        except Exception as e:
            logger.error(f"Error getting report {report_id}: {str(e)}")
            return None

    def _generate_html_content(self, report: Dict[str, Any]) -> str:
        """Generate HTML content for report viewing"""
        try:
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Training Report - {report.get('job_id', 'Unknown')}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                    .section {{ margin-bottom: 30px; }}
                    .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e9ecef; border-radius: 3px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .chart {{ text-align: center; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Training Report</h1>
                    <p><strong>Job ID:</strong> {report.get('job_id', 'Unknown')}</p>
                    <p><strong>Generated:</strong> {report.get('generated_at', 'Unknown')}</p>
                </div>
            """
            
            # Job Info Section
            if 'job_info' in report:
                job_info = report['job_info']
                html += f"""
                <div class="section">
                    <h2>Job Information</h2>
                    <div class="metric"><strong>Name:</strong> {job_info.get('name', 'Unknown')}</div>
                    <div class="metric"><strong>Status:</strong> {job_info.get('status', 'Unknown')}</div>
                    <div class="metric"><strong>Progress:</strong> {job_info.get('progress', 0)}%</div>
                    <div class="metric"><strong>Duration:</strong> {job_info.get('duration_formatted', 'Unknown')}</div>
                </div>
                """
            
            # Training Summary Section
            if 'training_summary' in report:
                summary = report['training_summary']
                html += f"""
                <div class="section">
                    <h2>Training Summary</h2>
                    <div class="metric"><strong>Epochs:</strong> {summary.get('completed_epochs', 0)}/{summary.get('total_epochs', 0)}</div>
                    <div class="metric"><strong>Final Loss:</strong> {summary.get('final_loss', 'N/A')}</div>
                    <div class="metric"><strong>Final Accuracy:</strong> {summary.get('final_accuracy', 'N/A')}</div>
                    <div class="metric"><strong>Validation Loss:</strong> {summary.get('final_validation_loss', 'N/A')}</div>
                    <div class="metric"><strong>Validation Accuracy:</strong> {summary.get('final_validation_accuracy', 'N/A')}</div>
                </div>
                """
            
            # Charts Section
            if 'charts' in report:
                html += '<div class="section"><h2>Training Charts</h2>'
                for chart_name, chart_data in report['charts'].items():
                    if chart_data.startswith('data:image'):
                        html += f'<div class="chart"><h3>{chart_name.replace("_", " ").title()}</h3><img src="{chart_data}" alt="{chart_name}" style="max-width: 100%;"></div>'
                html += '</div>'
            
            html += """
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            logger.error(f"Error generating HTML content: {str(e)}")
            return f"<html><body><h1>Error generating report content</h1><p>{str(e)}</p></body></html>"

# Global instance
report_service = ReportService()