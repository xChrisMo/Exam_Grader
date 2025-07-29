"""
Analytics Service

This service provides comprehensive analytics and insights for LLM training
operations, including performance metrics, trends, and comparative analysis.
"""

import json
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from src.database.models import db, LLMTrainingJob, LLMModelTest, LLMDataset, LLMDocument
from utils.logger import logger

class AnalyticsService:
    """Service for generating training analytics and insights"""
    
    def __init__(self):
        self.metric_calculators = {
            'training_performance': self._calculate_training_performance,
            'model_accuracy_trends': self._calculate_accuracy_trends,
            'dataset_utilization': self._calculate_dataset_utilization,
            'training_efficiency': self._calculate_training_efficiency,
            'model_comparison': self._calculate_model_comparison,
            'error_analysis': self._calculate_error_analysis
        }
    
    def generate_training_analytics(self, user_id: str, time_range: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate comprehensive training analytics for a user
        
        Args:
            user_id: User ID to generate analytics for
            time_range: Optional time range filter
            
        Returns:
            Analytics data with metrics and insights
        """
        try:
            # Get training jobs within time range
            query = LLMTrainingJob.query.filter_by(user_id=user_id)
            
            if time_range:
                if time_range.get('start_date'):
                    query = query.filter(LLMTrainingJob.created_at >= time_range['start_date'])
                if time_range.get('end_date'):
                    query = query.filter(LLMTrainingJob.created_at <= time_range['end_date'])
            
            training_jobs = query.order_by(LLMTrainingJob.created_at.desc()).all()
            
            if not training_jobs:
                return {
                    'summary': {'total_jobs': 0, 'message': 'No training jobs found'},
                    'metrics': {},
                    'insights': [],
                    'recommendations': []
                }
            
            # Calculate all metrics
            analytics = {
                'summary': self._generate_summary(training_jobs),
                'metrics': {},
                'insights': [],
                'recommendations': [],
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Calculate each metric type
            for metric_name, calculator in self.metric_calculators.items():
                try:
                    analytics['metrics'][metric_name] = calculator(training_jobs, user_id)
                except Exception as e:
                    logger.error(f"Error calculating {metric_name}: {e}")
                    analytics['metrics'][metric_name] = {'error': str(e)}
            
            # Generate insights and recommendations
            analytics['insights'] = self._generate_insights(analytics['metrics'])
            analytics['recommendations'] = self._generate_recommendations(analytics['metrics'])
            
            logger.info(f"Generated analytics for user {user_id} with {len(training_jobs)} jobs")
            return analytics
            
        except Exception as e:
            logger.error(f"Error generating training analytics: {e}")
            return {
                'error': str(e),
                'summary': {'total_jobs': 0},
                'metrics': {},
                'insights': [],
                'recommendations': []
            }    

    def _generate_summary(self, training_jobs: List[LLMTrainingJob]) -> Dict[str, Any]:
        """Generate summary statistics"""
        total_jobs = len(training_jobs)
        completed_jobs = [job for job in training_jobs if job.status == 'completed']
        failed_jobs = [job for job in training_jobs if job.status == 'failed']
        running_jobs = [job for job in training_jobs if job.status in ['training', 'preparing']]
        
        # Calculate success rate
        success_rate = len(completed_jobs) / total_jobs if total_jobs > 0 else 0
        
        avg_training_time = 0
        if completed_jobs:
            training_times = []
            for job in completed_jobs:
                if job.start_time and job.end_time:
                    duration = (job.end_time - job.start_time).total_seconds() / 60  # minutes
                    training_times.append(duration)
            
            if training_times:
                avg_training_time = statistics.mean(training_times)
        
        # Calculate average accuracy
        avg_accuracy = 0
        if completed_jobs:
            accuracies = [job.accuracy for job in completed_jobs if job.accuracy is not None]
            if accuracies:
                avg_accuracy = statistics.mean(accuracies)
        
        return {
            'total_jobs': total_jobs,
            'completed_jobs': len(completed_jobs),
            'failed_jobs': len(failed_jobs),
            'running_jobs': len(running_jobs),
            'success_rate': success_rate,
            'avg_training_time_minutes': avg_training_time,
            'avg_accuracy': avg_accuracy,
            'time_range': {
                'earliest': min(job.created_at for job in training_jobs).isoformat(),
                'latest': max(job.created_at for job in training_jobs).isoformat()
            }
        }
    
    def _calculate_training_performance(self, training_jobs: List[LLMTrainingJob], user_id: str) -> Dict[str, Any]:
        """Calculate training performance metrics"""
        completed_jobs = [job for job in training_jobs if job.status == 'completed']
        
        if not completed_jobs:
            return {'message': 'No completed jobs for performance analysis'}
        
        # Accuracy distribution
        accuracies = [job.accuracy for job in completed_jobs if job.accuracy is not None]
        accuracy_stats = {}
        if accuracies:
            accuracy_stats = {
                'mean': statistics.mean(accuracies),
                'median': statistics.median(accuracies),
                'std_dev': statistics.stdev(accuracies) if len(accuracies) > 1 else 0,
                'min': min(accuracies),
                'max': max(accuracies),
                'distribution': self._create_distribution(accuracies, bins=10)
            }
        
        # Loss distribution
        losses = [job.loss for job in completed_jobs if job.loss is not None]
        loss_stats = {}
        if losses:
            loss_stats = {
                'mean': statistics.mean(losses),
                'median': statistics.median(losses),
                'std_dev': statistics.stdev(losses) if len(losses) > 1 else 0,
                'min': min(losses),
                'max': max(losses),
                'distribution': self._create_distribution(losses, bins=10)
            }
        
        # Performance over time
        performance_timeline = []
        for job in sorted(completed_jobs, key=lambda x: x.created_at):
            performance_timeline.append({
                'date': job.created_at.isoformat(),
                'job_id': job.id,
                'job_name': job.name,
                'accuracy': job.accuracy,
                'loss': job.loss,
                'training_time_minutes': self._calculate_training_duration(job)
            })
        
        return {
            'accuracy_stats': accuracy_stats,
            'loss_stats': loss_stats,
            'performance_timeline': performance_timeline,
            'total_completed_jobs': len(completed_jobs)
        }
    
    def _calculate_accuracy_trends(self, training_jobs: List[LLMTrainingJob], user_id: str) -> Dict[str, Any]:
        """Calculate accuracy trends over time"""
        completed_jobs = [job for job in training_jobs if job.status == 'completed' and job.accuracy is not None]
        
        if len(completed_jobs) < 2:
            return {'message': 'Need at least 2 completed jobs for trend analysis'}
        
        # Sort by creation date
        sorted_jobs = sorted(completed_jobs, key=lambda x: x.created_at)
        
        # Calculate trend
        accuracies = [job.accuracy for job in sorted_jobs]
        dates = [job.created_at for job in sorted_jobs]
        
        # Simple linear trend calculation
        n = len(accuracies)
        x_values = list(range(n))
        
        # Calculate slope (trend)
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(accuracies)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, accuracies))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        trend_slope = numerator / denominator if denominator != 0 else 0
        
        # Categorize trend
        if trend_slope > 0.01:
            trend_direction = 'improving'
        elif trend_slope < -0.01:
            trend_direction = 'declining'
        else:
            trend_direction = 'stable'
        
        # Calculate moving averages
        window_size = min(5, len(accuracies))
        moving_averages = []
        for i in range(len(accuracies) - window_size + 1):
            avg = statistics.mean(accuracies[i:i + window_size])
            moving_averages.append({
                'date': dates[i + window_size - 1].isoformat(),
                'moving_average': avg,
                'window_size': window_size
            })
        
        return {
            'trend_direction': trend_direction,
            'trend_slope': trend_slope,
            'accuracy_timeline': [
                {'date': date.isoformat(), 'accuracy': acc, 'job_id': job.id}
                for date, acc, job in zip(dates, accuracies, sorted_jobs)
            ],
            'moving_averages': moving_averages,
            'improvement_rate': trend_slope * 100,  # Percentage improvement per job
            'best_accuracy': max(accuracies),
            'worst_accuracy': min(accuracies),
            'accuracy_variance': statistics.variance(accuracies) if len(accuracies) > 1 else 0
        }
    
    def _calculate_dataset_utilization(self, training_jobs: List[LLMTrainingJob], user_id: str) -> Dict[str, Any]:
        """Calculate dataset utilization metrics"""
        # Get all datasets used
        dataset_usage = defaultdict(list)
        for job in training_jobs:
            if job.dataset_id:
                dataset_usage[job.dataset_id].append(job)
        
        if not dataset_usage:
            return {'message': 'No dataset usage data available'}
        
        dataset_metrics = {}
        for dataset_id, jobs in dataset_usage.items():
            dataset = db.session.get(LLMDataset, dataset_id)
            if not dataset:
                continue
            
            completed_jobs = [job for job in jobs if job.status == 'completed']
            avg_accuracy = 0
            if completed_jobs:
                accuracies = [job.accuracy for job in completed_jobs if job.accuracy is not None]
                if accuracies:
                    avg_accuracy = statistics.mean(accuracies)
            
            dataset_metrics[dataset_id] = {
                'dataset_name': dataset.name,
                'total_jobs': len(jobs),
                'completed_jobs': len(completed_jobs),
                'success_rate': len(completed_jobs) / len(jobs) if jobs else 0,
                'avg_accuracy': avg_accuracy,
                'dataset_size': {
                    'documents': dataset.document_count,
                    'words': dataset.total_words,
                    'size_mb': dataset.total_size / (1024 * 1024) if dataset.total_size else 0
                },
                'last_used': max(job.created_at for job in jobs).isoformat()
            }
        
        # Find most and least effective datasets
        effective_datasets = sorted(
            dataset_metrics.items(),
            key=lambda x: x[1]['avg_accuracy'],
            reverse=True
        )
        
        return {
            'dataset_metrics': dataset_metrics,
            'most_effective_dataset': effective_datasets[0] if effective_datasets else None,
            'least_effective_dataset': effective_datasets[-1] if len(effective_datasets) > 1 else None,
            'total_datasets_used': len(dataset_usage),
            'dataset_reuse_rate': sum(len(jobs) for jobs in dataset_usage.values()) / len(dataset_usage)
        }
    
    def _calculate_training_efficiency(self, training_jobs: List[LLMTrainingJob], user_id: str) -> Dict[str, Any]:
        """Calculate training efficiency metrics"""
        completed_jobs = [job for job in training_jobs if job.status == 'completed']
        
        if not completed_jobs:
            return {'message': 'No completed jobs for efficiency analysis'}
        
        # Calculate training durations
        training_durations = []
        for job in completed_jobs:
            duration = self._calculate_training_duration(job)
            if duration > 0:
                training_durations.append({
                    'job_id': job.id,
                    'job_name': job.name,
                    'duration_minutes': duration,
                    'epochs': job.config_epochs or job.total_epochs,
                    'accuracy': job.accuracy,
                    'efficiency_score': (job.accuracy or 0) / (duration / 60) if duration > 0 else 0  # accuracy per hour
                })
        
        if not training_durations:
            return {'message': 'No training duration data available'}
        
        # Calculate efficiency statistics
        durations = [item['duration_minutes'] for item in training_durations]
        efficiency_scores = [item['efficiency_score'] for item in training_durations]
        
        duration_stats = {
            'mean': statistics.mean(durations),
            'median': statistics.median(durations),
            'min': min(durations),
            'max': max(durations),
            'std_dev': statistics.stdev(durations) if len(durations) > 1 else 0
        }
        
        efficiency_stats = {
            'mean': statistics.mean(efficiency_scores),
            'median': statistics.median(efficiency_scores),
            'min': min(efficiency_scores),
            'max': max(efficiency_scores)
        }
        
        # Find most and least efficient jobs
        most_efficient = max(training_durations, key=lambda x: x['efficiency_score'])
        least_efficient = min(training_durations, key=lambda x: x['efficiency_score'])
        
        return {
            'duration_stats': duration_stats,
            'efficiency_stats': efficiency_stats,
            'training_durations': training_durations,
            'most_efficient_job': most_efficient,
            'least_efficient_job': least_efficient,
            'total_training_time_hours': sum(durations) / 60
        }
    
    def _calculate_model_comparison(self, training_jobs: List[LLMTrainingJob], user_id: str) -> Dict[str, Any]:
        """Compare performance across different models"""
        # Group jobs by model
        model_performance = defaultdict(list)
        for job in training_jobs:
            if job.status == 'completed' and job.model_id:
                model_performance[job.model_id].append(job)
        
        if not model_performance:
            return {'message': 'No completed jobs for model comparison'}
        
        model_metrics = {}
        for model_id, jobs in model_performance.items():
            accuracies = [job.accuracy for job in jobs if job.accuracy is not None]
            losses = [job.loss for job in jobs if job.loss is not None]
            durations = [self._calculate_training_duration(job) for job in jobs]
            durations = [d for d in durations if d > 0]
            
            model_metrics[model_id] = {
                'total_jobs': len(jobs),
                'avg_accuracy': statistics.mean(accuracies) if accuracies else 0,
                'avg_loss': statistics.mean(losses) if losses else 0,
                'avg_duration_minutes': statistics.mean(durations) if durations else 0,
                'success_rate': len(jobs) / len([j for j in training_jobs if j.model_id == model_id]),
                'accuracy_std': statistics.stdev(accuracies) if len(accuracies) > 1 else 0,
                'best_accuracy': max(accuracies) if accuracies else 0,
                'worst_accuracy': min(accuracies) if accuracies else 0
            }
        
        # Rank models by performance
        ranked_models = sorted(
            model_metrics.items(),
            key=lambda x: x[1]['avg_accuracy'],
            reverse=True
        )
        
        return {
            'model_metrics': model_metrics,
            'ranked_models': ranked_models,
            'best_performing_model': ranked_models[0] if ranked_models else None,
            'total_models_tested': len(model_performance)
        }
    
    def _calculate_error_analysis(self, training_jobs: List[LLMTrainingJob], user_id: str) -> Dict[str, Any]:
        """Analyze training errors and failure patterns"""
        failed_jobs = [job for job in training_jobs if job.status == 'failed']
        
        if not failed_jobs:
            return {'message': 'No failed jobs for error analysis', 'error_rate': 0}
        
        # Categorize errors
        error_categories = defaultdict(list)
        for job in failed_jobs:
            error_msg = job.error_message or 'Unknown error'
            category = self._categorize_error(error_msg)
            error_categories[category].append({
                'job_id': job.id,
                'job_name': job.name,
                'error_message': error_msg,
                'created_at': job.created_at.isoformat(),
                'model_id': job.model_id,
                'dataset_id': job.dataset_id
            })
        
        # Calculate error statistics
        total_jobs = len(training_jobs)
        error_rate = len(failed_jobs) / total_jobs if total_jobs > 0 else 0
        
        # Find most common errors
        most_common_errors = sorted(
            error_categories.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        # Analyze error trends over time
        error_timeline = []
        for job in sorted(failed_jobs, key=lambda x: x.created_at):
            error_timeline.append({
                'date': job.created_at.isoformat(),
                'error_category': self._categorize_error(job.error_message or ''),
                'job_id': job.id
            })
        
        return {
            'error_rate': error_rate,
            'total_failed_jobs': len(failed_jobs),
            'error_categories': dict(error_categories),
            'most_common_errors': most_common_errors,
            'error_timeline': error_timeline,
            'error_recovery_suggestions': self._get_error_recovery_suggestions(error_categories)
        }    

    def _generate_insights(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate insights based on calculated metrics"""
        insights = []
        
        # Training performance insights
        if 'training_performance' in metrics:
            perf = metrics['training_performance']
            if 'accuracy_stats' in perf and perf['accuracy_stats']:
                avg_acc = perf['accuracy_stats'].get('mean', 0)
                if avg_acc > 0.9:
                    insights.append("🎯 Excellent model performance with high accuracy scores")
                elif avg_acc > 0.7:
                    insights.append("✅ Good model performance with room for improvement")
                else:
                    insights.append("⚠️ Model performance is below optimal levels")
        
        # Accuracy trends insights
        if 'model_accuracy_trends' in metrics:
            trends = metrics['model_accuracy_trends']
            if 'trend_direction' in trends:
                if trends['trend_direction'] == 'improving':
                    insights.append("📈 Model accuracy is consistently improving over time")
                elif trends['trend_direction'] == 'declining':
                    insights.append("📉 Model accuracy is declining - review recent changes")
                else:
                    insights.append("➡️ Model accuracy is stable across training sessions")
        
        # Dataset utilization insights
        if 'dataset_utilization' in metrics:
            dataset = metrics['dataset_utilization']
            if 'total_datasets_used' in dataset:
                if dataset['total_datasets_used'] == 1:
                    insights.append("📊 Consider experimenting with different datasets for better results")
                elif dataset['total_datasets_used'] > 5:
                    insights.append("🔄 Good dataset diversity - helps identify optimal training data")
        
        # Training efficiency insights
        if 'training_efficiency' in metrics:
            efficiency = metrics['training_efficiency']
            if 'duration_stats' in efficiency:
                avg_duration = efficiency['duration_stats'].get('mean', 0)
                if avg_duration > 120:  # 2 hours
                    insights.append("⏱️ Training times are lengthy - consider optimization strategies")
                elif avg_duration < 30:  # 30 minutes
                    insights.append("⚡ Fast training times - good efficiency")
        
        # Error analysis insights
        if 'error_analysis' in metrics:
            errors = metrics['error_analysis']
            if 'error_rate' in errors:
                error_rate = errors['error_rate']
                if error_rate > 0.3:
                    insights.append("🚨 High failure rate - review training configurations")
                elif error_rate < 0.1:
                    insights.append("✨ Low failure rate indicates stable training process")
        
        return insights
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on metrics"""
        recommendations = []
        
        # Performance-based recommendations
        if 'training_performance' in metrics:
            perf = metrics['training_performance']
            if 'accuracy_stats' in perf and perf['accuracy_stats']:
                avg_acc = perf['accuracy_stats'].get('mean', 0)
                std_dev = perf['accuracy_stats'].get('std_dev', 0)
                
                if avg_acc < 0.7:
                    recommendations.append("Increase training data size or improve data quality")
                    recommendations.append("Experiment with different model architectures")
                
                if std_dev > 0.1:
                    recommendations.append("Standardize training configurations for more consistent results")
        
        # Efficiency-based recommendations
        if 'training_efficiency' in metrics:
            efficiency = metrics['training_efficiency']
            if 'duration_stats' in efficiency:
                avg_duration = efficiency['duration_stats'].get('mean', 0)
                if avg_duration > 120:
                    recommendations.append("Consider reducing batch size or model complexity to speed up training")
                    recommendations.append("Implement early stopping to avoid unnecessary training time")
        
        # Dataset recommendations
        if 'dataset_utilization' in metrics:
            dataset = metrics['dataset_utilization']
            if 'most_effective_dataset' in dataset and dataset['most_effective_dataset']:
                best_dataset = dataset['most_effective_dataset'][1]
                recommendations.append(f"Focus on datasets similar to '{best_dataset['dataset_name']}' for better results")
        
        # Error-based recommendations
        if 'error_analysis' in metrics:
            errors = metrics['error_analysis']
            if 'error_rate' in errors and errors['error_rate'] > 0.2:
                recommendations.append("Review and validate training data before starting jobs")
                recommendations.append("Implement more robust error handling and recovery mechanisms")
        
        # Model comparison recommendations
        if 'model_comparison' in metrics:
            models = metrics['model_comparison']
            if 'best_performing_model' in models and models['best_performing_model']:
                best_model = models['best_performing_model'][0]
                recommendations.append(f"Consider using '{best_model}' as your primary model for future training")
        
        return recommendations
    
    def _create_distribution(self, values: List[float], bins: int = 10) -> List[Dict[str, Any]]:
        """Create distribution data for visualization"""
        if not values:
            return []
        
        min_val = min(values)
        max_val = max(values)
        bin_width = (max_val - min_val) / bins if max_val != min_val else 1
        
        distribution = []
        for i in range(bins):
            bin_start = min_val + i * bin_width
            bin_end = bin_start + bin_width
            
            count = sum(1 for v in values if bin_start <= v < bin_end)
            if i == bins - 1:  # Include max value in last bin
                count = sum(1 for v in values if bin_start <= v <= bin_end)
            
            distribution.append({
                'bin_start': bin_start,
                'bin_end': bin_end,
                'count': count,
                'percentage': count / len(values) * 100
            })
        
        return distribution
    
    def _calculate_training_duration(self, job: LLMTrainingJob) -> float:
        """Calculate training duration in minutes"""
        if job.start_time and job.end_time:
            return (job.end_time - job.start_time).total_seconds() / 60
        return 0
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize error message into common error types"""
        error_msg = error_message.lower()
        
        if 'memory' in error_msg or 'oom' in error_msg:
            return 'memory_error'
        elif 'network' in error_msg or 'connection' in error_msg:
            return 'network_error'
        elif 'validation' in error_msg or 'invalid' in error_msg:
            return 'validation_error'
        elif 'timeout' in error_msg:
            return 'timeout_error'
        elif 'file' in error_msg or 'path' in error_msg:
            return 'file_error'
        elif 'permission' in error_msg or 'access' in error_msg:
            return 'permission_error'
        else:
            return 'unknown_error'
    
    def _get_error_recovery_suggestions(self, error_categories: Dict[str, List]) -> Dict[str, List[str]]:
        """Get recovery suggestions for each error category"""
        suggestions = {
            'memory_error': [
                'Reduce batch size in training configuration',
                'Use gradient accumulation instead of larger batches',
                'Consider training on machines with more RAM/GPU memory'
            ],
            'network_error': [
                'Check internet connection stability',
                'Implement retry mechanisms with exponential backoff',
                'Use offline training mode if available'
            ],
            'validation_error': [
                'Validate training data format and quality',
                'Check configuration parameters for valid ranges',
                'Review dataset integrity before training'
            ],
            'timeout_error': [
                'Increase timeout limits for long-running operations',
                'Break large training jobs into smaller chunks',
                'Optimize training pipeline for better performance'
            ],
            'file_error': [
                'Verify file paths and permissions',
                'Check available disk space',
                'Ensure files are not corrupted or locked'
            ],
            'permission_error': [
                'Check file and directory permissions',
                'Run with appropriate user privileges',
                'Verify access to required resources'
            ],
            'unknown_error': [
                'Review detailed error logs',
                'Contact support with error details',
                'Try with minimal configuration to isolate issue'
            ]
        }
        
        return {category: suggestions.get(category, []) 
                for category in error_categories.keys()}
    
    def generate_comparative_analysis(self, user_id: str, job_ids: List[str]) -> Dict[str, Any]:
        """Generate comparative analysis between specific training jobs"""
        try:
            jobs = LLMTrainingJob.query.filter(
                LLMTrainingJob.id.in_(job_ids),
                LLMTrainingJob.user_id == user_id
            ).all()
            
            if len(jobs) < 2:
                return {'error': 'Need at least 2 jobs for comparison'}
            
            comparison = {
                'jobs': [],
                'metrics_comparison': {},
                'recommendations': [],
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Collect job data
            for job in jobs:
                job_data = {
                    'id': job.id,
                    'name': job.name,
                    'model_id': job.model_id,
                    'status': job.status,
                    'accuracy': job.accuracy,
                    'loss': job.loss,
                    'training_duration': self._calculate_training_duration(job),
                    'config': {
                        'epochs': job.config_epochs,
                        'batch_size': job.config_batch_size,
                        'learning_rate': job.config_learning_rate
                    }
                }
                comparison['jobs'].append(job_data)
            
            # Compare metrics
            completed_jobs = [job for job in comparison['jobs'] if job['accuracy'] is not None]
            
            if completed_jobs:
                accuracies = [job['accuracy'] for job in completed_jobs]
                losses = [job['loss'] for job in completed_jobs if job['loss'] is not None]
                durations = [job['training_duration'] for job in completed_jobs]
                
                comparison['metrics_comparison'] = {
                    'accuracy': {
                        'best': max(accuracies),
                        'worst': min(accuracies),
                        'range': max(accuracies) - min(accuracies),
                        'average': statistics.mean(accuracies)
                    },
                    'training_time': {
                        'fastest': min(durations) if durations else 0,
                        'slowest': max(durations) if durations else 0,
                        'average': statistics.mean(durations) if durations else 0
                    }
                }
                
                if losses:
                    comparison['metrics_comparison']['loss'] = {
                        'best': min(losses),
                        'worst': max(losses),
                        'average': statistics.mean(losses)
                    }
            
            # Generate comparison recommendations
            if completed_jobs:
                best_job = max(completed_jobs, key=lambda x: x['accuracy'])
                comparison['recommendations'].append(
                    f"Job '{best_job['name']}' achieved the best accuracy ({best_job['accuracy']:.3f})"
                )
                
                if len(set(job['model_id'] for job in completed_jobs)) > 1:
                    comparison['recommendations'].append(
                        f"Model '{best_job['model_id']}' performed best in this comparison"
                    )
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error generating comparative analysis: {e}")
            return {'error': str(e)}