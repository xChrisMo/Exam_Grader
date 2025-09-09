"""
Training Report Service for LLM Training Page

This service generates comprehensive training reports including markdown reports,
statistical analysis, and detailed insights about training sessions.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import joinedload

from src.database.models import (
    db, TrainingSession, TrainingGuide, TrainingQuestion,
    TrainingResult, TestSubmission, User
)
from src.services.base_service import BaseService, ServiceStatus
from src.services.training_report_pdf import TrainingReportPDFGenerator
from utils.logger import logger

@dataclass
class ReportSection:
    """Represents a section in the training report"""
    title: str
    content: str
    level: int = 2  # Markdown header level
    subsections: List['ReportSection'] = None

    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []

@dataclass
class AnalyticsData:
    """Container for analytics data used in reports"""
    session_metrics: Dict[str, Any]
    guide_analytics: Dict[str, Any]
    question_analytics: Dict[str, Any]
    confidence_analytics: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    test_results: Dict[str, Any]

@dataclass
class SessionData:
    """Container for session data used in report generation"""
    session: TrainingSession
    guides: List[TrainingGuide]
    questions: List[TrainingQuestion]
    results: List[TrainingResult]
    test_submissions: List[TestSubmission]
    user: Optional[User] = None

class TrainingReportService(BaseService):
    """Service for generating comprehensive training reports and analytics"""

    def __init__(self):
        """Initialize the training report service"""
        super().__init__("training_report_service")

        # Report configuration
        self.report_templates_dir = Path("templates/reports")
        self.report_output_dir = Path("output/training_reports")
        self.report_output_dir.mkdir(parents=True, exist_ok=True)

        # Analytics configuration
        self.confidence_thresholds = {
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }

        logger.info("TrainingReportService initialized successfully")

    async def initialize(self) -> bool:
        """Initialize the service"""
        try:
            self.status = ServiceStatus.HEALTHY
            logger.info("TrainingReportService initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize TrainingReportService: {e}")
            self.status = ServiceStatus.UNHEALTHY
            return False

    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            # Check database connectivity
            db.session.execute(db.text("SELECT 1"))

            # Check output directory is writable
            test_file = self.report_output_dir / "health_check.tmp"
            test_file.write_text("test")
            test_file.unlink()

            return True

        except Exception as e:
            logger.error(f"TrainingReportService health check failed: {e}")
            return False

    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            logger.info("TrainingReportService cleanup completed")
        except Exception as e:
            logger.error(f"Error during TrainingReportService cleanup: {e}")

    def generate_markdown_report(self, session_id: str) -> str:
        """
        Generate comprehensive markdown report for a training session

        Args:
            session_id: ID of the training session

        Returns:
            Markdown report content as string
        """
        try:
            with self.track_request("generate_markdown_report"):
                logger.info(f"Generating markdown report for session {session_id}")

                # Get session data
                session_data = self._get_session_data(session_id)

                # Generate analytics
                analytics = self._generate_analytics(session_data)

                # Create report sections
                report_sections = self._create_report_sections(session_data, analytics)

                # Generate markdown content
                markdown_content = self._render_markdown_report(report_sections, session_data)

                # Save report to file
                report_path = self._save_markdown_report(session_id, markdown_content)

                logger.info(f"Markdown report generated successfully: {report_path}")
                return markdown_content

        except Exception as e:
            logger.error(f"Failed to generate markdown report for session {session_id}: {e}")
            raise

    def generate_report_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Generate a summary of the training report for quick overview

        Args:
            session_id: ID of the training session

        Returns:
            Dictionary with report summary
        """
        try:
            with self.track_request("generate_report_summary"):
                logger.info(f"Generating report summary for session {session_id}")

                # Get session data
                session_data = self._get_session_data(session_id)

                # Generate analytics
                analytics = self._generate_analytics(session_data)

                # Create summary
                summary = {
                    "session_info": {
                        "session_id": session_id,
                        "name": session_data.session.name,
                        "status": session_data.session.status,
                        "created_at": session_data.session.created_at.isoformat(),
                        "duration_seconds": session_data.session.training_duration_seconds
                    },
                    "key_metrics": {
                        "total_guides": analytics.session_metrics.get("total_guides", 0),
                        "total_questions": analytics.session_metrics.get("total_questions", 0),
                        "average_confidence": analytics.session_metrics.get("average_confidence", 0),
                        "high_confidence_questions": analytics.confidence_analytics.get("high_confidence_count", 0),
                        "questions_requiring_review": analytics.confidence_analytics.get("review_required_count", 0)
                    },
                    "quality_assessment": {
                        "overall_quality": self._assess_overall_quality(analytics),
                        "confidence_distribution": analytics.confidence_analytics.get("distribution", {}),
                        "guide_type_distribution": analytics.guide_analytics.get("type_distribution", {})
                    },
                    "recommendations": self._generate_summary_recommendations(analytics)
                }

                return summary

        except Exception as e:
            logger.error(f"Failed to generate report summary for session {session_id}: {e}")
            raise

    def _get_session_data(self, session_id: str) -> SessionData:
        """
        Get comprehensive session data for report generation

        Args:
            session_id: ID of the training session

        Returns:
            SessionData object with all related data
        """
        try:
            # Get session with all related data
            session = db.session.query(TrainingSession).options(
                joinedload(TrainingSession.training_guides).joinedload(TrainingGuide.training_questions),
                joinedload(TrainingSession.training_results),
                joinedload(TrainingSession.test_submissions),
                joinedload(TrainingSession.user)
            ).filter_by(id=session_id).first()

            if not session:
                raise ValueError(f"Training session {session_id} not found")

            return SessionData(
                session=session,
                guides=session.training_guides,
                questions=[q for guide in session.training_guides for q in guide.training_questions],
                results=session.training_results,
                test_submissions=session.test_submissions,
                user=session.user
            )

        except Exception as e:
            logger.error(f"Failed to get session data for {session_id}: {e}")
            raise

    def _generate_analytics(self, session_data: SessionData) -> AnalyticsData:
        """
        Generate comprehensive analytics from session data

        Args:
            session_data: Session data object

        Returns:
            AnalyticsData with computed analytics
        """
        try:
            # Session-level metrics
            session_metrics = self._calculate_session_metrics(session_data)

            # Guide analytics
            guide_analytics = self._analyze_guides(session_data.guides)

            # Question analytics
            question_analytics = self._analyze_questions(session_data.questions)

            # Confidence analytics
            confidence_analytics = self._analyze_confidence_levels(session_data.questions, session_data.session.confidence_threshold)

            # Performance metrics
            performance_metrics = self._calculate_performance_metrics(session_data)

            # Test results analytics
            test_results = self._analyze_test_results(session_data.test_submissions)

            return AnalyticsData(
                session_metrics=session_metrics,
                guide_analytics=guide_analytics,
                question_analytics=question_analytics,
                confidence_analytics=confidence_analytics,
                performance_metrics=performance_metrics,
                test_results=test_results
            )

        except Exception as e:
            logger.error(f"Failed to generate analytics: {e}")
            raise

    def _calculate_session_metrics(self, session_data: SessionData) -> Dict[str, Any]:
        """
        Calculate session-level metrics

        Args:
            session_data: Session data object

        Returns:
            Dictionary with session metrics
        """
        try:
            session = session_data.session

            # Basic counts
            total_guides = len(session_data.guides)
            total_questions = len(session_data.questions)

            # Confidence calculations
            confidence_scores = [q.extraction_confidence for q in session_data.questions if q.extraction_confidence is not None]
            average_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

            # Processing statistics
            successful_guides = sum(1 for guide in session_data.guides if guide.processing_status == "completed")
            failed_guides = sum(1 for guide in session_data.guides if guide.processing_status == "failed")

            # Point calculations
            total_points = sum(q.point_value for q in session_data.questions)
            average_points_per_question = total_points / total_questions if total_questions > 0 else 0

            return {
                "total_guides": total_guides,
                "total_questions": total_questions,
                "successful_guides": successful_guides,
                "failed_guides": failed_guides,
                "success_rate": successful_guides / total_guides if total_guides > 0 else 0,
                "average_confidence": average_confidence,
                "total_points": total_points,
                "average_points_per_question": average_points_per_question,
                "training_duration": session.training_duration_seconds,
                "questions_per_guide": total_questions / successful_guides if successful_guides > 0 else 0
            }

        except Exception as e:
            logger.error(f"Failed to calculate session metrics: {e}")
            return {}

    def _analyze_guides(self, guides: List[TrainingGuide]) -> Dict[str, Any]:
        """
        Analyze training guides for patterns and insights

        Args:
            guides: List of training guides

        Returns:
            Dictionary with guide analytics
        """
        try:
            if not guides:
                return {"type_distribution": {}, "size_distribution": {}, "format_distribution": {}}

            # Type distribution
            type_counts = {}
            for guide in guides:
                guide_type = guide.guide_type
                type_counts[guide_type] = type_counts.get(guide_type, 0) + 1

            # Size distribution
            sizes = [guide.file_size for guide in guides]
            size_distribution = {
                "small (<1MB)": sum(1 for s in sizes if s < 1024*1024),
                "medium (1-5MB)": sum(1 for s in sizes if 1024*1024 <= s < 5*1024*1024),
                "large (>5MB)": sum(1 for s in sizes if s >= 5*1024*1024),
                "average_size_mb": sum(sizes) / len(sizes) / (1024*1024) if sizes else 0
            }

            # Format distribution
            format_counts = {}
            for guide in guides:
                file_ext = Path(guide.filename).suffix.lower()
                format_counts[file_ext] = format_counts.get(file_ext, 0) + 1

            # Quality metrics
            confidence_scores = [guide.confidence_score for guide in guides if guide.confidence_score is not None]
            quality_metrics = {
                "average_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                "high_quality_guides": sum(1 for score in confidence_scores if score > 0.8),
                "low_quality_guides": sum(1 for score in confidence_scores if score < 0.5)
            }

            return {
                "type_distribution": type_counts,
                "size_distribution": size_distribution,
                "format_distribution": format_counts,
                "quality_metrics": quality_metrics,
                "processing_success_rate": sum(1 for g in guides if g.processing_status == "completed") / len(guides)
            }

        except Exception as e:
            logger.error(f"Failed to analyze guides: {e}")
            return {}

    def _analyze_questions(self, questions: List[TrainingQuestion]) -> Dict[str, Any]:
        """
        Analyze training questions for patterns and insights

        Args:
            questions: List of training questions

        Returns:
            Dictionary with question analytics
        """
        try:
            if not questions:
                return {"point_distribution": {}, "question_types": {}, "complexity_analysis": {}}

            # Point value distribution
            point_values = [q.point_value for q in questions]
            point_distribution = {
                "total_points": sum(point_values),
                "average_points": sum(point_values) / len(point_values) if point_values else 0,
                "min_points": min(point_values) if point_values else 0,
                "max_points": max(point_values) if point_values else 0,
                "point_ranges": {
                    "1-5 points": sum(1 for p in point_values if 1 <= p <= 5),
                    "6-10 points": sum(1 for p in point_values if 6 <= p <= 10),
                    "11-20 points": sum(1 for p in point_values if 11 <= p <= 20),
                    "20+ points": sum(1 for p in point_values if p > 20)
                }
            }

            # Question complexity analysis
            complexity_analysis = {
                "with_rubric": sum(1 for q in questions if q.rubric_details),
                "with_visual_elements": sum(1 for q in questions if q.visual_elements),
                "with_context": sum(1 for q in questions if q.context),
                "requiring_review": sum(1 for q in questions if q.manual_review_required)
            }

            # Question number patterns
            question_numbers = [q.question_number for q in questions]
            question_types = {
                "numeric_questions": sum(1 for qn in question_numbers if qn.isdigit()),
                "lettered_questions": sum(1 for qn in question_numbers if qn.isalpha()),
                "mixed_format": sum(1 for qn in question_numbers if not qn.isdigit() and not qn.isalpha())
            }

            return {
                "point_distribution": point_distribution,
                "question_types": question_types,
                "complexity_analysis": complexity_analysis,
                "total_questions": len(questions)
            }

        except Exception as e:
            logger.error(f"Failed to analyze questions: {e}")
            return {}

    def _analyze_confidence_levels(self, questions: List[TrainingQuestion], threshold: float) -> Dict[str, Any]:
        """
        Analyze confidence levels across questions

        Args:
            questions: List of training questions
            threshold: Confidence threshold for flagging

        Returns:
            Dictionary with confidence analytics
        """
        try:
            if not questions:
                return {"distribution": {}, "flagged_items": [], "trends": {}}

            # Get confidence scores
            confidence_scores = [q.extraction_confidence for q in questions if q.extraction_confidence is not None]

            if not confidence_scores:
                return {"distribution": {}, "flagged_items": [], "trends": {}}

            # Confidence distribution
            distribution = {
                "high_confidence": sum(1 for score in confidence_scores if score >= self.confidence_thresholds['high']),
                "medium_confidence": sum(1 for score in confidence_scores if self.confidence_thresholds['medium'] <= score < self.confidence_thresholds['high']),
                "low_confidence": sum(1 for score in confidence_scores if score < self.confidence_thresholds['medium']),
                "average_confidence": sum(confidence_scores) / len(confidence_scores),
                "min_confidence": min(confidence_scores),
                "max_confidence": max(confidence_scores)
            }

            # Flagged items (below threshold)
            flagged_items = [
                {
                    "question_id": q.id,
                    "question_number": q.question_number,
                    "confidence": q.extraction_confidence,
                    "guide_id": q.guide_id
                }
                for q in questions
                if q.extraction_confidence is not None and q.extraction_confidence < threshold
            ]

            # Confidence trends
            trends = {
                "below_threshold_count": len(flagged_items),
                "review_required_count": sum(1 for q in questions if q.manual_review_required),
                "confidence_variance": self._calculate_variance(confidence_scores)
            }

            return {
                "distribution": distribution,
                "flagged_items": flagged_items,
                "trends": trends,
                "high_confidence_count": distribution["high_confidence"],
                "review_required_count": trends["review_required_count"]
            }

        except Exception as e:
            logger.error(f"Failed to analyze confidence levels: {e}")
            return {}

    def _calculate_performance_metrics(self, session_data: SessionData) -> Dict[str, Any]:
        """
        Calculate performance metrics for the training session

        Args:
            session_data: Session data object

        Returns:
            Dictionary with performance metrics
        """
        try:
            session = session_data.session

            # Processing efficiency
            total_files = len(session_data.guides)
            processing_time = session.training_duration_seconds or 0

            efficiency_metrics = {
                "files_per_minute": (total_files / (processing_time / 60)) if processing_time > 0 else 0,
                "average_processing_time_per_file": processing_time / total_files if total_files > 0 else 0,
                "total_processing_time": processing_time
            }

            # Quality metrics
            successful_extractions = sum(1 for guide in session_data.guides if guide.processing_status == "completed")
            quality_metrics = {
                "extraction_success_rate": successful_extractions / total_files if total_files > 0 else 0,
                "average_questions_per_guide": len(session_data.questions) / successful_extractions if successful_extractions > 0 else 0
            }

            # Resource utilization
            total_file_size = sum(guide.file_size for guide in session_data.guides)
            resource_metrics = {
                "total_data_processed_mb": total_file_size / (1024 * 1024),
                "mb_per_second": (total_file_size / (1024 * 1024)) / processing_time if processing_time > 0 else 0
            }

            return {
                "efficiency": efficiency_metrics,
                "quality": quality_metrics,
                "resources": resource_metrics
            }

        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {e}")
            return {}

    def _analyze_test_results(self, test_submissions: List[TestSubmission]) -> Dict[str, Any]:
        """
        Analyze test submission results

        Args:
            test_submissions: List of test submissions

        Returns:
            Dictionary with test results analytics
        """
        try:
            if not test_submissions:
                return {"summary": {}, "accuracy_metrics": {}, "issues": []}

            # Basic summary
            total_tests = len(test_submissions)
            successful_tests = sum(1 for test in test_submissions if test.processing_status == "completed")

            # Accuracy metrics
            predicted_scores = [test.predicted_score for test in test_submissions if test.predicted_score is not None]
            confidence_scores = [test.confidence_score for test in test_submissions if test.confidence_score is not None]

            accuracy_metrics = {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
                "average_predicted_score": sum(predicted_scores) / len(predicted_scores) if predicted_scores else 0,
                "average_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            }

            # Issues and misalignments
            issues = []
            for test in test_submissions:
                if test.misalignments:
                    issues.append({
                        "test_id": test.id,
                        "filename": test.filename,
                        "misalignments": test.misalignments,
                        "confidence": test.confidence_score
                    })

            return {
                "summary": {
                    "total_submissions": total_tests,
                    "processed_successfully": successful_tests,
                    "processing_errors": total_tests - successful_tests
                },
                "accuracy_metrics": accuracy_metrics,
                "issues": issues
            }

        except Exception as e:
            logger.error(f"Failed to analyze test results: {e}")
            return {}

    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values"""
        if not values:
            return 0.0

        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)

    def _assess_overall_quality(self, analytics: AnalyticsData) -> str:
        """
        Assess overall quality of the training session

        Args:
            analytics: Analytics data

        Returns:
            Quality assessment string
        """
        try:
            # Get key metrics
            avg_confidence = analytics.session_metrics.get("average_confidence", 0)
            success_rate = analytics.session_metrics.get("success_rate", 0)
            high_confidence_ratio = analytics.confidence_analytics.get("high_confidence_count", 0) / max(analytics.session_metrics.get("total_questions", 1), 1)

            # Quality scoring
            quality_score = (avg_confidence * 0.4) + (success_rate * 0.3) + (high_confidence_ratio * 0.3)

            if quality_score >= 0.8:
                return "Excellent"
            elif quality_score >= 0.6:
                return "Good"
            elif quality_score >= 0.4:
                return "Fair"
            else:
                return "Poor"

        except Exception as e:
            logger.error(f"Failed to assess overall quality: {e}")
            return "Unknown"

    def _generate_summary_recommendations(self, analytics: AnalyticsData) -> List[str]:
        """
        Generate recommendations based on analytics

        Args:
            analytics: Analytics data

        Returns:
            List of recommendation strings
        """
        try:
            recommendations = []

            # Confidence-based recommendations
            avg_confidence = analytics.session_metrics.get("average_confidence", 0)
            if avg_confidence < 0.6:
                recommendations.append("Consider reviewing and improving marking guide quality for better extraction confidence")

            # Success rate recommendations
            success_rate = analytics.session_metrics.get("success_rate", 0)
            if success_rate < 0.8:
                recommendations.append("Some guides failed processing - check file formats and quality")

            # Question complexity recommendations
            review_required = analytics.confidence_analytics.get("review_required_count", 0)
            if review_required > 0:
                recommendations.append(f"{review_required} questions require manual review - consider simplifying complex questions")

            # Test results recommendations
            if analytics.test_results.get("issues"):
                recommendations.append("Test submissions show alignment issues - consider retraining with clearer examples")

            if not recommendations:
                recommendations.append("Training session completed successfully with good quality metrics")

            return recommendations

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return ["Unable to generate recommendations due to analysis error"]
 # ===== CHART AND VISUALIZATION GENERATION =====

    def generate_charts(self, session_id: str, output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Generate all charts and visualizations for a training session

        Args:
            session_id: ID of the training session
            output_dir: Optional output directory for charts

        Returns:
            Dictionary mapping chart names to file paths
        """
        try:
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            import matplotlib.pyplot as plt
            import seaborn as sns

            with self.track_request("generate_charts"):
                logger.info(f"Generating charts for session {session_id}")

                # Set up output directory
                if output_dir is None:
                    output_dir = self.report_output_dir / session_id / "charts"
                else:
                    output_dir = Path(output_dir)

                output_dir.mkdir(parents=True, exist_ok=True)

                # Get session data and analytics
                session_data = self._get_session_data(session_id)
                analytics = self._generate_analytics(session_data)

                # Configure matplotlib style
                plt.style.use('default')
                sns.set_palette("husl")

                chart_paths = {}

                # Generate individual charts
                chart_paths.update(self._create_confidence_distribution_chart(analytics, output_dir))
                chart_paths.update(self._create_score_distribution_chart(analytics, output_dir))
                chart_paths.update(self._create_guide_type_breakdown_chart(analytics, output_dir))
                chart_paths.update(self._create_question_complexity_chart(analytics, output_dir))
                chart_paths.update(self._create_training_progress_chart(session_data, output_dir))
                chart_paths.update(self._create_performance_metrics_chart(analytics, output_dir))

                # Generate test results charts if available
                if analytics.test_results.get("summary", {}).get("total_submissions", 0) > 0:
                    chart_paths.update(self._create_test_results_chart(analytics, output_dir))

                logger.info(f"Generated {len(chart_paths)} charts for session {session_id}")
                return chart_paths

        except ImportError as e:
            logger.error(f"Visualization libraries not available: {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to generate charts for session {session_id}: {e}")
            return {}

    def _create_confidence_distribution_chart(self, analytics: AnalyticsData, output_dir: Path) -> Dict[str, str]:
        """Create confidence level distribution chart"""
        try:

            confidence_data = analytics.confidence_analytics.get("distribution", {})
            if not confidence_data:
                return {}

            # Prepare data
            categories = ["High\n(â‰¥0.8)", "Medium\n(0.6-0.8)", "Low\n(<0.6)"]
            values = [
                confidence_data.get("high_confidence", 0),
                confidence_data.get("medium_confidence", 0),
                confidence_data.get("low_confidence", 0)
            ]

            # Create chart
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(categories, values, color=['#2ecc71', '#f39c12', '#e74c3c'])

            # Customize chart
            ax.set_title('Confidence Level Distribution', fontsize=16, fontweight='bold', pad=20)
            ax.set_ylabel('Number of Questions', fontsize=12)
            ax.set_xlabel('Confidence Level', fontsize=12)

            # Add value labels on bars
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{int(value)}', ha='center', va='bottom', fontweight='bold')

            # Add grid for better readability
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)

            # Adjust layout and save
            plt.tight_layout()
            chart_path = output_dir / "confidence_distribution.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            return {"confidence_distribution": str(chart_path)}

        except Exception as e:
            logger.error(f"Failed to create confidence distribution chart: {e}")
            return {}

    def _create_score_distribution_chart(self, analytics: AnalyticsData, output_dir: Path) -> Dict[str, str]:
        """Create score distribution histogram"""
        try:

            point_data = analytics.question_analytics.get("point_distribution", {})
            if not point_data or not point_data.get("point_ranges"):
                return {}

            # Prepare data
            ranges = point_data["point_ranges"]
            categories = list(ranges.keys())
            values = list(ranges.values())

            # Create chart
            fig, ax = plt.subplots(figsize=(12, 6))
            bars = ax.bar(categories, values, color='#3498db', alpha=0.8)

            # Customize chart
            ax.set_title('Question Point Value Distribution', fontsize=16, fontweight='bold', pad=20)
            ax.set_ylabel('Number of Questions', fontsize=12)
            ax.set_xlabel('Point Range', fontsize=12)

            # Add value labels on bars
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{int(value)}', ha='center', va='bottom', fontweight='bold')

            # Add statistics text
            stats_text = f"Total Points: {point_data.get('total_points', 0):.1f}\n"
            stats_text += f"Average: {point_data.get('average_points', 0):.1f} pts/question"
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

            # Add grid
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)

            plt.tight_layout()
            chart_path = output_dir / "score_distribution.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            return {"score_distribution": str(chart_path)}

        except Exception as e:
            logger.error(f"Failed to create score distribution chart: {e}")
            return {}

    def _create_guide_type_breakdown_chart(self, analytics: AnalyticsData, output_dir: Path) -> Dict[str, str]:
        """Create guide type breakdown pie chart"""
        try:

            guide_data = analytics.guide_analytics.get("type_distribution", {})
            if not guide_data:
                return {}

            # Prepare data
            labels = []
            sizes = []
            for guide_type, count in guide_data.items():
                if count > 0:
                    # Format labels for better readability
                    formatted_label = guide_type.replace('_', ' ').title()
                    labels.append(f"{formatted_label}\n({count})")
                    sizes.append(count)

            if not sizes:
                return {}

            # Create pie chart
            fig, ax = plt.subplots(figsize=(10, 8))
            colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                            colors=colors[:len(sizes)], startangle=90)

            # Customize chart
            ax.set_title('Guide Type Distribution', fontsize=16, fontweight='bold', pad=20)

            # Improve text readability
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')

            plt.tight_layout()
            chart_path = output_dir / "guide_type_breakdown.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            return {"guide_type_breakdown": str(chart_path)}

        except Exception as e:
            logger.error(f"Failed to create guide type breakdown chart: {e}")
            return {}

    def _create_question_complexity_chart(self, analytics: AnalyticsData, output_dir: Path) -> Dict[str, str]:
        """Create question complexity analysis chart"""
        try:

            complexity_data = analytics.question_analytics.get("complexity_analysis", {})
            if not complexity_data:
                return {}

            # Prepare data
            categories = []
            values = []

            complexity_mapping = {
                "with_rubric": "Has Rubric",
                "with_visual_elements": "Visual Elements",
                "with_context": "Has Context",
                "requiring_review": "Needs Review"
            }

            for key, label in complexity_mapping.items():
                if key in complexity_data:
                    categories.append(label)
                    values.append(complexity_data[key])

            if not values:
                return {}

            # Create horizontal bar chart
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(categories, values, color=['#3498db', '#e74c3c', '#2ecc71', '#f39c12'])

            # Customize chart
            ax.set_title('Question Complexity Analysis', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Number of Questions', fontsize=12)

            # Add value labels on bars
            for bar, value in zip(bars, values):
                width = bar.get_width()
                ax.text(width + 0.1, bar.get_y() + bar.get_height()/2.,
                       f'{int(value)}', ha='left', va='center', fontweight='bold')

            # Add grid
            ax.grid(axis='x', alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)

            plt.tight_layout()
            chart_path = output_dir / "question_complexity.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            return {"question_complexity": str(chart_path)}

        except Exception as e:
            logger.error(f"Failed to create question complexity chart: {e}")
            return {}

    def _create_training_progress_chart(self, session_data: SessionData, output_dir: Path) -> Dict[str, str]:
        """Create training progress visualization"""
        try:

            session = session_data.session

            # Create progress stages
            stages = [
                "Session Created",
                "Guides Uploaded",
                "Processing Started",
                "Questions Extracted",
                "Training Completed"
            ]

            # Determine completion status
            progress_values = [1, 1, 1, 1, 1 if session.status == "completed" else 0.5]

            # Create timeline chart
            fig, ax = plt.subplots(figsize=(12, 6))

            # Create progress line
            x_positions = range(len(stages))
            ax.plot(x_positions, progress_values, 'o-', linewidth=3, markersize=10, color='#2ecc71')

            # Customize chart
            ax.set_title('Training Session Progress', fontsize=16, fontweight='bold', pad=20)
            ax.set_xticks(x_positions)
            ax.set_xticklabels(stages, rotation=45, ha='right')
            ax.set_ylabel('Completion Status', fontsize=12)
            ax.set_ylim(-0.1, 1.1)

            # Add completion indicators
            for i, (stage, value) in enumerate(zip(stages, progress_values)):
                color = '#2ecc71' if value == 1 else '#f39c12'
                ax.scatter(i, value, s=200, c=color, zorder=5)

                # Add status text
                status_text = "âœ“" if value == 1 else "â³"
                ax.text(i, value + 0.1, status_text, ha='center', va='bottom', fontsize=16)

            # Add session info
            info_text = f"Duration: {session.training_duration_seconds or 0:.0f}s\n"
            info_text += f"Status: {session.status.title()}"
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

            plt.tight_layout()
            chart_path = output_dir / "training_progress.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            return {"training_progress": str(chart_path)}

        except Exception as e:
            logger.error(f"Failed to create training progress chart: {e}")
            return {}

    def _create_performance_metrics_chart(self, analytics: AnalyticsData, output_dir: Path) -> Dict[str, str]:
        """Create performance metrics dashboard"""
        try:

            performance_data = analytics.performance_metrics
            if not performance_data:
                return {}

            # Create subplot layout
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Training Performance Metrics', fontsize=16, fontweight='bold')

            # Efficiency metrics
            efficiency = performance_data.get("efficiency", {})
            if efficiency:
                metrics = ["Files/Min", "Avg Time/File", "Total Time"]
                values = [
                    efficiency.get("files_per_minute", 0),
                    efficiency.get("average_processing_time_per_file", 0),
                    efficiency.get("total_processing_time", 0) / 60  # Convert to minutes
                ]
                ax1.bar(metrics, values, color='#3498db')
                ax1.set_title('Processing Efficiency')
                ax1.set_ylabel('Time (minutes)')

                # Add value labels
                for i, v in enumerate(values):
                    ax1.text(i, v + max(values) * 0.01, f'{v:.1f}', ha='center', va='bottom')

            # Quality metrics
            quality = performance_data.get("quality", {})
            session_metrics = analytics.session_metrics
            if quality and session_metrics:
                metrics = ["Success Rate", "Avg Confidence", "Questions/Guide"]
                values = [
                    quality.get("extraction_success_rate", 0) * 100,
                    session_metrics.get("average_confidence", 0) * 100,
                    quality.get("average_questions_per_guide", 0)
                ]
                ax2.bar(metrics, values, color='#2ecc71')
                ax2.set_title('Quality Metrics')
                ax2.set_ylabel('Percentage / Count')

                # Add value labels
                for i, v in enumerate(values):
                    ax2.text(i, v + max(values) * 0.01, f'{v:.1f}', ha='center', va='bottom')

            # Resource utilization
            resources = performance_data.get("resources", {})
            if resources:
                ax3.pie([resources.get("total_data_processed_mb", 0)],
                       labels=[f"Data Processed\n{resources.get('total_data_processed_mb', 0):.1f} MB"],
                       autopct='%1.1f%%', colors=['#f39c12'])
                ax3.set_title('Data Processing')

            # Processing rate
            if resources:
                rate = resources.get("mb_per_second", 0)
                ax4.bar(["Processing Rate"], [rate], color='#9b59b6')
                ax4.set_title('Processing Rate')
                ax4.set_ylabel('MB/second')
                ax4.text(0, rate + rate * 0.01, f'{rate:.2f}', ha='center', va='bottom')

            plt.tight_layout()
            chart_path = output_dir / "performance_metrics.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            return {"performance_metrics": str(chart_path)}

        except Exception as e:
            logger.error(f"Failed to create performance metrics chart: {e}")
            return {}

    def _create_test_results_chart(self, analytics: AnalyticsData, output_dir: Path) -> Dict[str, str]:
        """Create test results analysis chart"""
        try:

            test_data = analytics.test_results
            if not test_data or not test_data.get("accuracy_metrics"):
                return {}

            accuracy_metrics = test_data["accuracy_metrics"]

            # Create chart
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            fig.suptitle('Model Testing Results', fontsize=16, fontweight='bold')

            # Test success rate
            success_rate = accuracy_metrics.get("success_rate", 0) * 100
            failure_rate = 100 - success_rate

            ax1.pie([success_rate, failure_rate],
                   labels=[f"Successful\n({success_rate:.1f}%)", f"Failed\n({failure_rate:.1f}%)"],
                   autopct='%1.1f%%', colors=['#2ecc71', '#e74c3c'])
            ax1.set_title('Test Processing Success Rate')

            # Accuracy metrics bar chart
            metrics = ["Avg Score", "Avg Confidence"]
            values = [
                accuracy_metrics.get("average_predicted_score", 0),
                accuracy_metrics.get("average_confidence", 0) * 100
            ]

            bars = ax2.bar(metrics, values, color=['#3498db', '#f39c12'])
            ax2.set_title('Test Accuracy Metrics')
            ax2.set_ylabel('Score / Percentage')

            # Add value labels
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + max(values) * 0.01,
                        f'{value:.1f}', ha='center', va='bottom', fontweight='bold')

            plt.tight_layout()
            chart_path = output_dir / "test_results.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            return {"test_results": str(chart_path)}

        except Exception as e:
            logger.error(f"Failed to create test results chart: {e}")
            return {}

    # ===== REPORT GENERATION METHODS =====

    def _create_report_sections(self, session_data: SessionData, analytics: AnalyticsData) -> List[ReportSection]:
        """
        Create structured report sections

        Args:
            session_data: Session data object
            analytics: Analytics data

        Returns:
            List of report sections
        """
        try:
            sections = []

            # Executive Summary
            sections.append(self._create_executive_summary_section(session_data, analytics))

            # Session Overview
            sections.append(self._create_session_overview_section(session_data, analytics))

            # Guide Analysis
            sections.append(self._create_guide_analysis_section(analytics))

            # Question Analysis
            sections.append(self._create_question_analysis_section(analytics))

            # Confidence Analysis
            sections.append(self._create_confidence_analysis_section(analytics))

            # Performance Metrics
            sections.append(self._create_performance_section(analytics))

            # Test Results (if available)
            if analytics.test_results.get("summary", {}).get("total_submissions", 0) > 0:
                sections.append(self._create_test_results_section(analytics))

            # Recommendations
            sections.append(self._create_recommendations_section(analytics))

            return sections

        except Exception as e:
            logger.error(f"Failed to create report sections: {e}")
            return []

    def _create_executive_summary_section(self, session_data: SessionData, analytics: AnalyticsData) -> ReportSection:
        """Create executive summary section"""
        session = session_data.session
        session_metrics = analytics.session_metrics

        content = f"""
**Training Session:** {session.name}
**Status:** {session.status.title()}
**Created:** {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {session.training_duration_seconds or 0:.0f} seconds

### Key Metrics
- **Total Guides Processed:** {session_metrics.get('total_guides', 0)}
- **Questions Extracted:** {session_metrics.get('total_questions', 0)}
- **Average Confidence:** {session_metrics.get('average_confidence', 0):.2f}
- **Processing Success Rate:** {session_metrics.get('success_rate', 0):.1%}
- **Overall Quality:** {self._assess_overall_quality(analytics)}

### Quick Insights
{chr(10).join(f"- {rec}" for rec in self._generate_summary_recommendations(analytics)[:3])}
"""

        return ReportSection("Executive Summary", content.strip(), level=2)

    def _create_session_overview_section(self, session_data: SessionData, analytics: AnalyticsData) -> ReportSection:
        """Create session overview section"""
        session = session_data.session
        session_metrics = analytics.session_metrics

        content = f"""
### Configuration
- **Max Questions to Answer:** {session.max_questions_to_answer or 'Not specified'}
- **Use in Main App:** {'Yes' if session.use_in_main_app else 'No'}
- **Confidence Threshold:** {session.confidence_threshold}

### Processing Statistics
- **Total Guides:** {session_metrics.get('total_guides', 0)}
- **Successful Processing:** {session_metrics.get('successful_guides', 0)}
- **Failed Processing:** {session_metrics.get('failed_guides', 0)}
- **Questions per Guide:** {session_metrics.get('questions_per_guide', 0):.1f}
- **Total Points Available:** {session_metrics.get('total_points', 0):.1f}
- **Average Points per Question:** {session_metrics.get('average_points_per_question', 0):.1f}
"""

        return ReportSection("Session Overview", content.strip(), level=2)

    def _create_guide_analysis_section(self, analytics: AnalyticsData) -> ReportSection:
        """Create guide analysis section"""
        guide_analytics = analytics.guide_analytics

        # Type distribution
        type_dist = guide_analytics.get("type_distribution", {})
        type_content = "\n".join([f"- **{k.replace('_', ' ').title()}:** {v}" for k, v in type_dist.items()])

        # Size distribution
        size_dist = guide_analytics.get("size_distribution", {})

        content = f"""
### Guide Types
{type_content}

### File Size Analysis
- **Small files (<1MB):** {size_dist.get('small (<1MB)', 0)}
- **Medium files (1-5MB):** {size_dist.get('medium (1-5MB)', 0)}
- **Large files (>5MB):** {size_dist.get('large (>5MB)', 0)}
- **Average file size:** {size_dist.get('average_size_mb', 0):.1f} MB

### Quality Metrics
- **Average confidence:** {guide_analytics.get('quality_metrics', {}).get('average_confidence', 0):.2f}
- **High quality guides:** {guide_analytics.get('quality_metrics', {}).get('high_quality_guides', 0)}
- **Low quality guides:** {guide_analytics.get('quality_metrics', {}).get('low_quality_guides', 0)}
- **Processing success rate:** {guide_analytics.get('processing_success_rate', 0):.1%}
"""

        return ReportSection("Guide Analysis", content.strip(), level=2)

    def _create_question_analysis_section(self, analytics: AnalyticsData) -> ReportSection:
        """Create question analysis section"""
        question_analytics = analytics.question_analytics
        point_dist = question_analytics.get("point_distribution", {})
        complexity = question_analytics.get("complexity_analysis", {})

        # Point ranges
        ranges = point_dist.get("point_ranges", {})
        range_content = "\n".join([f"- **{k}:** {v} questions" for k, v in ranges.items()])

        content = f"""
### Point Distribution
{range_content}

**Statistics:**
- **Total points:** {point_dist.get('total_points', 0):.1f}
- **Average points per question:** {point_dist.get('average_points', 0):.1f}
- **Point range:** {point_dist.get('min_points', 0):.1f} - {point_dist.get('max_points', 0):.1f}

### Question Complexity
- **Questions with rubric details:** {complexity.get('with_rubric', 0)}
- **Questions with visual elements:** {complexity.get('with_visual_elements', 0)}
- **Questions with context:** {complexity.get('with_context', 0)}
- **Questions requiring manual review:** {complexity.get('requiring_review', 0)}

### Total Questions Analyzed
**{question_analytics.get('total_questions', 0)}** questions extracted and processed.
"""

        return ReportSection("Question Analysis", content.strip(), level=2)

    def _create_confidence_analysis_section(self, analytics: AnalyticsData) -> ReportSection:
        """Create confidence analysis section"""
        confidence_analytics = analytics.confidence_analytics
        distribution = confidence_analytics.get("distribution", {})
        trends = confidence_analytics.get("trends", {})

        content = f"""
### Confidence Distribution
- **High confidence (â‰¥0.8):** {distribution.get('high_confidence', 0)} questions
- **Medium confidence (0.6-0.8):** {distribution.get('medium_confidence', 0)} questions
- **Low confidence (<0.6):** {distribution.get('low_confidence', 0)} questions

### Statistical Summary
- **Average confidence:** {distribution.get('average_confidence', 0):.3f}
- **Confidence range:** {distribution.get('min_confidence', 0):.3f} - {distribution.get('max_confidence', 0):.3f}
- **Confidence variance:** {trends.get('confidence_variance', 0):.3f}

### Quality Flags
- **Questions below threshold:** {trends.get('below_threshold_count', 0)}
- **Questions requiring review:** {trends.get('review_required_count', 0)}

### Flagged Items
"""

        # Add flagged items if any
        flagged_items = confidence_analytics.get("flagged_items", [])
        if flagged_items:
            content += "\n**Items requiring attention:**\n"
            for item in flagged_items[:10]:  # Limit to first 10
                content += f"- Question {item['question_number']}: {item['confidence']:.3f}\n"

            if len(flagged_items) > 10:
                content += f"- ... and {len(flagged_items) - 10} more items\n"
        else:
            content += "\nNo items flagged for review.\n"

        return ReportSection("Confidence Analysis", content.strip(), level=2)

    def _create_performance_section(self, analytics: AnalyticsData) -> ReportSection:
        """Create performance metrics section"""
        performance = analytics.performance_metrics
        efficiency = performance.get("efficiency", {})
        quality = performance.get("quality", {})
        resources = performance.get("resources", {})

        content = f"""
### Processing Efficiency
- **Files processed per minute:** {efficiency.get('files_per_minute', 0):.1f}
- **Average processing time per file:** {efficiency.get('average_processing_time_per_file', 0):.1f} seconds
- **Total processing time:** {efficiency.get('total_processing_time', 0):.1f} seconds

### Quality Metrics
- **Extraction success rate:** {quality.get('extraction_success_rate', 0):.1%}
- **Average questions per guide:** {quality.get('average_questions_per_guide', 0):.1f}

### Resource Utilization
- **Total data processed:** {resources.get('total_data_processed_mb', 0):.1f} MB
- **Processing rate:** {resources.get('mb_per_second', 0):.2f} MB/second
"""

        return ReportSection("Performance Metrics", content.strip(), level=2)

    def _create_test_results_section(self, analytics: AnalyticsData) -> ReportSection:
        """Create test results section"""
        test_results = analytics.test_results
        summary = test_results.get("summary", {})
        accuracy = test_results.get("accuracy_metrics", {})
        issues = test_results.get("issues", [])

        content = f"""
### Test Summary
- **Total test submissions:** {summary.get('total_submissions', 0)}
- **Successfully processed:** {summary.get('processed_successfully', 0)}
- **Processing errors:** {summary.get('processing_errors', 0)}
- **Success rate:** {accuracy.get('success_rate', 0):.1%}

### Accuracy Metrics
- **Average predicted score:** {accuracy.get('average_predicted_score', 0):.2f}
- **Average confidence:** {accuracy.get('average_confidence', 0):.2f}

### Issues and Misalignments
"""

        if issues:
            content += f"\n**{len(issues)} issues detected:**\n"
            for issue in issues[:5]:  # Limit to first 5
                content += f"- {issue['filename']}: Confidence {issue.get('confidence', 0):.2f}\n"

            if len(issues) > 5:
                content += f"- ... and {len(issues) - 5} more issues\n"
        else:
            content += "\nNo significant issues detected in test submissions.\n"

        return ReportSection("Model Testing Results", content.strip(), level=2)

    def _create_recommendations_section(self, analytics: AnalyticsData) -> ReportSection:
        """Create recommendations section"""
        recommendations = self._generate_summary_recommendations(analytics)

        content = "Based on the analysis of your training session, here are our recommendations:\n\n"
        content += "\n".join([f"{i+1}. {rec}" for i, rec in enumerate(recommendations)])

        return ReportSection("Recommendations", content.strip(), level=2)

    def _render_markdown_report(self, sections: List[ReportSection], session_data: SessionData) -> str:
        """
        Render report sections into markdown format

        Args:
            sections: List of report sections
            session_data: Session data object

        Returns:
            Complete markdown report
        """
        try:
            # Report header
            session = session_data.session
            markdown_content = f"""# Training Report: {session.name}

**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
**Session ID:** {session.id}
**User:** {session_data.user.username if session_data.user else 'Unknown'}

---

"""

            # Add sections
            for section in sections:
                markdown_content += f"{'#' * section.level} {section.title}\n\n"
                markdown_content += section.content + "\n\n"

                # Add subsections if any
                for subsection in section.subsections:
                    markdown_content += f"{'#' * subsection.level} {subsection.title}\n\n"
                    markdown_content += subsection.content + "\n\n"

            # Footer
            markdown_content += f"""---

*Report generated by LLM Training System v1.0*
*Processing completed at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""

            return markdown_content

        except Exception as e:
            logger.error(f"Failed to render markdown report: {e}")
            return f"# Error Generating Report\n\nAn error occurred while generating the report: {e}"

    def _save_markdown_report(self, session_id: str, content: str) -> str:
        """
        Save markdown report to file

        Args:
            session_id: Session ID
            content: Markdown content

        Returns:
            Path to saved report file
        """
        try:
            # Create session-specific directory
            session_dir = self.report_output_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"training_report_{timestamp}.md"
            report_path = session_dir / filename

            # Save report
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Markdown report saved to: {report_path}")
            return str(report_path)

        except Exception as e:
            logger.error(f"Failed to save markdown report: {e}")
            raise

    # ===== PDF GENERATION METHODS =====

    def generate_pdf_report(self, session_id: str, output_dir: Optional[str] = None) -> str:
        """
        Generate PDF report for a training session

        Args:
            session_id: ID of the training session
            output_dir: Optional output directory for PDF

        Returns:
            Path to generated PDF file
        """
        try:
            with self.track_request("generate_pdf_report"):
                logger.info(f"Generating PDF report for session {session_id}")

                # Get session data and analytics
                session_data = self._get_session_data(session_id)
                analytics = self._generate_analytics(session_data)

                # Generate charts first
                chart_paths = self.generate_charts(session_id, output_dir)

                # Initialize PDF generator
                pdf_generator = TrainingReportPDFGenerator(self.report_output_dir)

                # Generate PDF
                pdf_path = pdf_generator.generate_pdf_report(session_data, analytics, chart_paths, output_dir)

                logger.info(f"PDF report generated successfully: {pdf_path}")
                return pdf_path

        except Exception as e:
            logger.error(f"Failed to generate PDF report for session {session_id}: {e}")
            raise

# Global instance for easy access
training_report_service = TrainingReportService()