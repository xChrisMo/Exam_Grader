"""
Training Visualization Service for LLM Training Page

This service generates charts and visualizations for training reports.
"""

import base64
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import matplotlib with non-interactive backend
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from src.services.base_service import BaseService, ServiceStatus
from utils.logger import logger


class TrainingVisualizationService(BaseService):
    """Service for generating charts and visualizations for training reports"""
    
    def __init__(self):
        """Initialize the visualization service"""
        super().__init__("training_visualization_service")
        
        # Chart configuration
        self.chart_config = {
            'figure_size': (10, 6),
            'dpi': 100,
            'colors': {
                'primary': '#3498db',
                'secondary': '#2ecc71',
                'warning': '#f39c12',
                'danger': '#e74c3c',
                'success': '#27ae60'
            }
        }
        
        # Output directory for charts
        self.charts_dir = Path("output/training_charts")
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("TrainingVisualizationService initialized successfully")
    
    async def initialize(self) -> bool:
        """Initialize the service"""
        try:
            self.status = ServiceStatus.HEALTHY
            return True
        except Exception as e:
            logger.error(f"Failed to initialize TrainingVisualizationService: {e}")
            self.status = ServiceStatus.UNHEALTHY
            return False
    
    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            # Test matplotlib functionality
            fig, ax = plt.subplots(figsize=(2, 2))
            ax.plot([1, 2, 3], [1, 2, 3])
            plt.close(fig)
            return True
        except Exception as e:
            logger.error(f"TrainingVisualizationService health check failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            plt.close('all')
            logger.info("TrainingVisualizationService cleanup completed")
        except Exception as e:
            logger.error(f"Error during TrainingVisualizationService cleanup: {e}")
    
    def generate_all_charts(self, session_id: str, analytics_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate all charts for a training session
        
        Args:
            session_id: ID of the training session
            analytics_data: Analytics data from TrainingReportService
            
        Returns:
            Dictionary mapping chart names to base64 encoded images
        """
        try:
            logger.info(f"Generating charts for session {session_id}")
            
            charts = {}
            
            # Score distribution chart
            if 'question_analytics' in analytics_data:
                charts['score_distribution'] = self.create_score_distribution_chart(
                    analytics_data['question_analytics']
                )
            
            # Confidence level visualization
            if 'confidence_analytics' in analytics_data:
                charts['confidence_levels'] = self.create_confidence_level_chart(
                    analytics_data['confidence_analytics']
                )
            
            # Question type breakdown
            if 'guide_analytics' in analytics_data:
                charts['question_types'] = self.create_question_type_breakdown_chart(
                    analytics_data['guide_analytics']
                )
            
            # Training progress visualization
            if 'session_metrics' in analytics_data:
                charts['training_progress'] = self.create_training_progress_chart(
                    analytics_data['session_metrics']
                )
            
            logger.info(f"Generated {len(charts)} charts for session {session_id}")
            return charts
            
        except Exception as e:
            logger.error(f"Failed to generate charts for session {session_id}: {e}")
            return {}
    
    def create_score_distribution_chart(self, question_analytics: Dict[str, Any]) -> str:
        """Create score distribution chart"""
        try:
            point_distribution = question_analytics.get('point_distribution', {})
            
            if not point_distribution:
                return self._create_no_data_chart("Score Distribution")
            
            # Extract data
            categories = []
            values = []
            
            for category, count in point_distribution.items():
                if isinstance(count, (int, float)) and category not in ['average_points', 'total_points']:
                    categories.append(category)
                    values.append(count)
            
            if not values:
                return self._create_no_data_chart("Score Distribution")
            
            # Create chart
            fig, ax = plt.subplots(figsize=self.chart_config['figure_size'])
            
            bars = ax.bar(categories, values, color=self.chart_config['colors']['primary'], alpha=0.7)
            ax.set_title('Question Score Distribution', fontsize=14, fontweight='bold')
            ax.set_xlabel('Point Categories')
            ax.set_ylabel('Number of Questions')
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{int(height)}', ha='center', va='bottom')
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            return self._save_chart_as_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create score distribution chart: {e}")
            return self._create_error_chart("Score Distribution", str(e))
    
    def create_confidence_level_chart(self, confidence_analytics: Dict[str, Any]) -> str:
        """Create confidence level visualization"""
        try:
            if confidence_analytics.get('no_confidence_data'):
                return self._create_no_data_chart("Confidence Levels")
            
            distribution = confidence_analytics.get('distribution', {})
            
            if not distribution:
                return self._create_no_data_chart("Confidence Levels")
            
            # Create pie chart
            fig, ax = plt.subplots(figsize=self.chart_config['figure_size'])
            
            labels = list(distribution.keys())
            sizes = list(distribution.values())
            colors = [self.chart_config['colors']['success'], 
                     self.chart_config['colors']['warning'], 
                     self.chart_config['colors']['danger']]
            
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors[:len(labels)], 
                                              autopct='%1.1f%%', startangle=90)
            ax.set_title('Confidence Level Distribution', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            return self._save_chart_as_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create confidence level chart: {e}")
            return self._create_error_chart("Confidence Levels", str(e))
    
    def create_question_type_breakdown_chart(self, guide_analytics: Dict[str, Any]) -> str:
        """Create question type breakdown chart"""
        try:
            type_distribution = guide_analytics.get('type_distribution', {})
            
            if not type_distribution:
                return self._create_no_data_chart("Question Types")
            
            # Create pie chart
            fig, ax = plt.subplots(figsize=self.chart_config['figure_size'])
            
            labels = list(type_distribution.keys())
            sizes = list(type_distribution.values())
            colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
            
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, 
                                              autopct='%1.1f%%', startangle=90)
            ax.set_title('Guide Type Distribution', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            return self._save_chart_as_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create question type breakdown chart: {e}")
            return self._create_error_chart("Question Types", str(e))
    
    def create_training_progress_chart(self, session_metrics: Dict[str, Any]) -> str:
        """Create training progress visualization"""
        try:
            # Create metrics overview chart
            fig, ((ax1, ax2)) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Chart 1: Guide and question counts
            total_guides = session_metrics.get('total_guides', 0)
            total_questions = session_metrics.get('total_questions', 0)
            successful_guides = session_metrics.get('successful_guides', 0)
            failed_guides = session_metrics.get('failed_guides', 0)
            
            categories = ['Total Guides', 'Successful', 'Failed', 'Total Questions']
            values = [total_guides, successful_guides, failed_guides, total_questions]
            colors = [self.chart_config['colors']['primary'], 
                     self.chart_config['colors']['success'],
                     self.chart_config['colors']['danger'],
                     self.chart_config['colors']['secondary']]
            
            bars = ax1.bar(categories, values, color=colors, alpha=0.7)
            ax1.set_title('Training Session Overview', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Count')
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{int(height)}', ha='center', va='bottom')
            
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Chart 2: Success rate and confidence
            success_rate = session_metrics.get('success_rate', 0) * 100
            avg_confidence = session_metrics.get('average_confidence', 0) * 100
            
            metrics = ['Success Rate (%)', 'Avg Confidence (%)']
            metric_values = [success_rate, avg_confidence]
            
            bars = ax2.bar(metrics, metric_values, color=self.chart_config['colors']['success'], alpha=0.7)
            ax2.set_title('Quality Metrics', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Percentage')
            ax2.set_ylim(0, 100)
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'{height:.1f}%', ha='center', va='bottom')
            
            plt.tight_layout()
            return self._save_chart_as_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create training progress chart: {e}")
            return self._create_error_chart("Training Progress", str(e))
    
    def _save_chart_as_base64(self, fig) -> str:
        """Save matplotlib figure as base64 encoded string"""
        try:
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=self.chart_config['dpi'], 
                       bbox_inches='tight', facecolor='white')
            buffer.seek(0)
            
            # Encode as base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Clean up
            buffer.close()
            plt.close(fig)
            
            return image_base64
            
        except Exception as e:
            logger.error(f"Failed to save chart as base64: {e}")
            plt.close(fig)
            return ""
    
    def _create_no_data_chart(self, title: str) -> str:
        """Create a chart indicating no data is available"""
        try:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=14, color='gray')
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.axis('off')
            
            return self._save_chart_as_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create no data chart: {e}")
            return ""
    
    def _create_error_chart(self, title: str, error_message: str) -> str:
        """Create a chart indicating an error occurred"""
        try:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            ax.text(0.5, 0.5, f'Error: {error_message}', 
                   ha='center', va='center', transform=ax.transAxes, 
                   fontsize=12, color='red')
            ax.set_title(f'{title} - Error', fontsize=14, fontweight='bold', color='red')
            ax.axis('off')
            
            return self._save_chart_as_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to create error chart: {e}")
            return ""