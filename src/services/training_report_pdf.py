"""
PDF Generation Extension for Training Report Service

This module provides PDF generation functionality for training reports
using both WeasyPrint and ReportLab approaches.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import logger


class TrainingReportPDFGenerator:
    """PDF generation functionality for training reports"""
    
    def __init__(self, report_output_dir: Path):
        """Initialize PDF generator"""
        self.report_output_dir = report_output_dir
    
    def generate_pdf_report(self, session_data, analytics, chart_paths: Dict[str, str], 
                          output_dir: Optional[str] = None) -> str:
        """
        Generate PDF report for a training session
        
        Args:
            session_data: Session data object
            analytics: Analytics data
            chart_paths: Dictionary of chart file paths
            output_dir: Optional output directory for PDF
            
        Returns:
            Path to generated PDF file
        """
        try:
            logger.info(f"Generating PDF report for session {session_data.session.id}")
            
            # Set up output directory
            if output_dir is None:
                output_dir = self.report_output_dir / session_data.session.id
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Try weasyprint first (better HTML/CSS support)
            try:
                pdf_path = self._generate_pdf_with_weasyprint(session_data, analytics, chart_paths, output_dir)
                logger.info(f"PDF report generated with WeasyPrint: {pdf_path}")
                return pdf_path
            except ImportError:
                logger.warning("WeasyPrint not available, falling back to ReportLab")
            except Exception as e:
                logger.warning(f"WeasyPrint failed: {e}, falling back to ReportLab")
            
            # Fallback to reportlab
            try:
                pdf_path = self._generate_pdf_with_reportlab(session_data, analytics, chart_paths, output_dir)
                logger.info(f"PDF report generated with ReportLab: {pdf_path}")
                return pdf_path
            except ImportError:
                logger.error("Neither WeasyPrint nor ReportLab available for PDF generation")
                raise
            except Exception as e:
                logger.error(f"ReportLab also failed: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            raise
    
    def _generate_pdf_with_weasyprint(self, session_data, analytics, 
                                    chart_paths: Dict[str, str], output_dir: Path) -> str:
        """Generate PDF using WeasyPrint (HTML to PDF)"""
        try:
            import weasyprint
            from weasyprint import HTML, CSS
            
            # Check for Windows-specific GTK issues
            import platform
            if platform.system() == "Windows":
                try:
                    # Test basic WeasyPrint functionality
                    test_html = HTML(string="<html><body>Test</body></html>")
                    # This will fail if GTK libraries aren't available
                    test_html.render()
                except Exception as gtk_error:
                    logger.warning(f"WeasyPrint GTK libraries not available on Windows: {gtk_error}")
                    logger.info("Consider installing GTK libraries. See docs/WEASYPRINT_WINDOWS_SETUP.md")
                    raise ImportError("WeasyPrint GTK libraries not available on Windows")
            
            # Generate HTML content
            html_content = self._create_html_report(session_data, analytics, chart_paths)
            
            # Create CSS for styling
            css_content = self._create_report_css()
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_filename = f"training_report_{timestamp}.pdf"
            pdf_path = output_dir / pdf_filename
            
            # Generate PDF with error handling
            try:
                html_doc = HTML(string=html_content)
                css_doc = CSS(string=css_content)
                
                html_doc.write_pdf(str(pdf_path), stylesheets=[css_doc])
                
                return str(pdf_path)
                
            except Exception as pdf_error:
                logger.error(f"WeasyPrint PDF generation failed: {pdf_error}")
                # Clean up partial file if it exists
                if pdf_path.exists():
                    pdf_path.unlink()
                raise
            
        except ImportError:
            raise ImportError("WeasyPrint not available")
        except Exception as e:
            logger.error(f"WeasyPrint PDF generation failed: {e}")
            raise
    
    def _generate_pdf_with_reportlab(self, session_data, analytics,
                                   chart_paths: Dict[str, str], output_dir: Path) -> str:
        """Generate PDF using ReportLab (direct PDF creation)"""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
            from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_filename = f"training_report_{timestamp}.pdf"
            pdf_path = output_dir / pdf_filename
            
            # Create PDF document
            doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                                  rightMargin=72, leftMargin=72,
                                  topMargin=72, bottomMargin=18)
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Create custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#2c3e50')
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                spaceAfter=12,
                spaceBefore=20,
                textColor=colors.HexColor('#34495e')
            )
            
            # Build PDF content
            story = []
            
            # Title page
            story.extend(self._create_pdf_title_page(session_data, title_style, styles))
            story.append(PageBreak())
            
            # Executive summary
            story.extend(self._create_pdf_executive_summary(session_data, analytics, heading_style, styles))
            story.append(Spacer(1, 20))
            
            # Charts section
            if chart_paths:
                story.extend(self._create_pdf_charts_section(chart_paths, heading_style, styles))
                story.append(PageBreak())
            
            # Detailed analytics
            story.extend(self._create_pdf_analytics_section(analytics, heading_style, styles))
            
            # Build PDF
            doc.build(story)
            
            return str(pdf_path)
            
        except ImportError:
            raise ImportError("ReportLab not available")
        except Exception as e:
            logger.error(f"ReportLab PDF generation failed: {e}")
            raise
    
    def _create_html_report(self, session_data, analytics, chart_paths: Dict[str, str]) -> str:
        """Create HTML content for WeasyPrint PDF generation"""
        session = session_data.session
        
        # Start HTML document
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Training Report: {session.name}</title>
</head>
<body>
    <div class="report-container">
        <!-- Title Page -->
        <div class="title-page">
            <h1 class="main-title">Training Report</h1>
            <h2 class="session-name">{session.name}</h2>
            <div class="report-meta">
                <p><strong>Generated:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Session ID:</strong> {session.id}</p>
                <p><strong>User:</strong> {session_data.user.username if session_data.user else 'Unknown'}</p>
                <p><strong>Status:</strong> {session.status.title()}</p>
            </div>
        </div>
        
        <div class="page-break"></div>
        
        <!-- Executive Summary -->
        <section class="executive-summary">
            <h2>Executive Summary</h2>
            {self._create_html_executive_summary(session_data, analytics)}
        </section>
        
        <!-- Charts Section -->
        {self._create_html_charts_section(chart_paths) if chart_paths else ''}
        
        <!-- Detailed Analytics -->
        <section class="analytics">
            <h2>Detailed Analytics</h2>
            {self._create_html_analytics_section(analytics)}
        </section>
        
        <!-- Footer -->
        <div class="report-footer">
            <p><em>Report generated by LLM Training System v1.0</em></p>
            <p><em>Processing completed at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</em></p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _create_html_executive_summary(self, session_data, analytics) -> str:
        """Create HTML executive summary section"""
        session = session_data.session
        session_metrics = analytics.session_metrics
        
        quality = self._assess_overall_quality(analytics)
        quality_class = f"quality-{quality.lower()}"
        
        return f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">{session_metrics.get('total_guides', 0)}</div>
                <div class="metric-label">Guides Processed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{session_metrics.get('total_questions', 0)}</div>
                <div class="metric-label">Questions Extracted</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{session_metrics.get('average_confidence', 0):.2f}</div>
                <div class="metric-label">Average Confidence</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {quality_class}">{quality}</div>
                <div class="metric-label">Overall Quality</div>
            </div>
        </div>
        
        <h3>Key Insights</h3>
        <ul>
            <li>Processing completed in {session.training_duration_seconds or 0:.0f} seconds</li>
            <li>Success rate: {session_metrics.get('success_rate', 0):.1%}</li>
            <li>Average points per question: {session_metrics.get('average_points_per_question', 0):.1f}</li>
        </ul>
        """
    
    def _create_html_charts_section(self, chart_paths: Dict[str, str]) -> str:
        """Create HTML charts section"""
        if not chart_paths:
            return ""
        
        charts_html = '<section class="charts"><h2>Visual Analytics</h2>'
        
        chart_titles = {
            'confidence_distribution': 'Confidence Level Distribution',
            'score_distribution': 'Question Point Value Distribution',
            'guide_type_breakdown': 'Guide Type Breakdown',
            'question_complexity': 'Question Complexity Analysis',
            'training_progress': 'Training Session Progress',
            'performance_metrics': 'Performance Metrics Dashboard',
            'test_results': 'Model Testing Results'
        }
        
        for chart_name, chart_path in chart_paths.items():
            if os.path.exists(chart_path):
                title = chart_titles.get(chart_name, chart_name.replace('_', ' ').title())
                charts_html += f"""
                <div class="chart-container">
                    <div class="chart-title">{title}</div>
                    <img src="file://{chart_path}" alt="{title}" />
                </div>
                """
        
        charts_html += '</section>'
        return charts_html
    
    def _create_html_analytics_section(self, analytics) -> str:
        """Create HTML analytics section"""
        guide_analytics = analytics.guide_analytics
        question_analytics = analytics.question_analytics
        confidence_analytics = analytics.confidence_analytics
        
        return f"""
        <h3>Guide Analysis</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Processing Success Rate</td><td>{guide_analytics.get('processing_success_rate', 0):.1%}</td></tr>
            <tr><td>Average File Size</td><td>{guide_analytics.get('size_distribution', {}).get('average_size_mb', 0):.1f} MB</td></tr>
            <tr><td>High Quality Guides</td><td>{guide_analytics.get('quality_metrics', {}).get('high_quality_guides', 0)}</td></tr>
        </table>
        
        <h3>Question Analysis</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Questions</td><td>{question_analytics.get('total_questions', 0)}</td></tr>
            <tr><td>Total Points</td><td>{question_analytics.get('point_distribution', {}).get('total_points', 0):.1f}</td></tr>
            <tr><td>Questions with Rubric</td><td>{question_analytics.get('complexity_analysis', {}).get('with_rubric', 0)}</td></tr>
            <tr><td>Questions Requiring Review</td><td>{question_analytics.get('complexity_analysis', {}).get('requiring_review', 0)}</td></tr>
        </table>
        
        <h3>Confidence Analysis</h3>
        <table>
            <tr><th>Confidence Level</th><th>Count</th></tr>
            <tr><td>High (≥0.8)</td><td>{confidence_analytics.get('distribution', {}).get('high_confidence', 0)}</td></tr>
            <tr><td>Medium (0.6-0.8)</td><td>{confidence_analytics.get('distribution', {}).get('medium_confidence', 0)}</td></tr>
            <tr><td>Low (<0.6)</td><td>{confidence_analytics.get('distribution', {}).get('low_confidence', 0)}</td></tr>
        </table>
        """
    
    def _create_report_css(self) -> str:
        """Create CSS styling for PDF report"""
        return """
        @page {
            size: A4;
            margin: 2cm;
            @bottom-center {
                content: counter(page);
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }
        
        .report-container {
            max-width: 100%;
        }
        
        .title-page {
            text-align: center;
            padding: 2cm 0;
            page-break-after: always;
        }
        
        .main-title {
            font-size: 2.5em;
            color: #2c3e50;
            margin-bottom: 0.5em;
            font-weight: bold;
        }
        
        .session-name {
            font-size: 1.8em;
            color: #34495e;
            margin-bottom: 1em;
        }
        
        .report-meta {
            background: #f8f9fa;
            padding: 1em;
            border-radius: 8px;
            display: inline-block;
            text-align: left;
        }
        
        .page-break {
            page-break-before: always;
        }
        
        section {
            margin-bottom: 2em;
        }
        
        h1, h2, h3 {
            color: #2c3e50;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        
        h2 {
            font-size: 1.5em;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 0.2em;
        }
        
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1em;
            margin: 1em 0;
        }
        
        .metric-card {
            background: #f8f9fa;
            padding: 1em;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        
        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .chart-container {
            text-align: center;
            margin: 1.5em 0;
            page-break-inside: avoid;
        }
        
        .chart-container img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 8px;
        }
        
        .chart-title {
            font-weight: bold;
            margin-bottom: 0.5em;
            color: #34495e;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
        }
        
        th, td {
            padding: 0.75em;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .quality-excellent { color: #27ae60; }
        .quality-good { color: #f39c12; }
        .quality-fair { color: #e67e22; }
        .quality-poor { color: #e74c3c; }
        
        .report-footer {
            margin-top: 3em;
            padding-top: 1em;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }
        """
    
    def _create_pdf_title_page(self, session_data, title_style, styles):
        """Create PDF title page elements"""
        from reportlab.platypus import Paragraph, Spacer
        
        session = session_data.session
        elements = []
        
        # Main title
        elements.append(Paragraph("Training Report", title_style))
        elements.append(Spacer(1, 20))
        
        # Session name
        elements.append(Paragraph(f"<b>{session.name}</b>", styles['Heading2']))
        elements.append(Spacer(1, 30))
        
        # Metadata
        meta_data = [
            f"<b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"<b>Session ID:</b> {session.id}",
            f"<b>User:</b> {session_data.user.username if session_data.user else 'Unknown'}",
            f"<b>Status:</b> {session.status.title()}"
        ]
        
        for meta in meta_data:
            elements.append(Paragraph(meta, styles['Normal']))
            elements.append(Spacer(1, 10))
        
        return elements
    
    def _create_pdf_executive_summary(self, session_data, analytics, heading_style, styles):
        """Create PDF executive summary elements"""
        from reportlab.platypus import Paragraph, Spacer
        
        elements = []
        session_metrics = analytics.session_metrics
        
        elements.append(Paragraph("Executive Summary", heading_style))
        elements.append(Spacer(1, 15))
        
        # Key metrics
        metrics = [
            f"<b>Total Guides Processed:</b> {session_metrics.get('total_guides', 0)}",
            f"<b>Questions Extracted:</b> {session_metrics.get('total_questions', 0)}",
            f"<b>Average Confidence:</b> {session_metrics.get('average_confidence', 0):.2f}",
            f"<b>Processing Success Rate:</b> {session_metrics.get('success_rate', 0):.1%}",
            f"<b>Overall Quality:</b> {self._assess_overall_quality(analytics)}"
        ]
        
        for metric in metrics:
            elements.append(Paragraph(metric, styles['Normal']))
            elements.append(Spacer(1, 8))
        
        return elements
    
    def _create_pdf_charts_section(self, chart_paths, heading_style, styles):
        """Create PDF charts section elements"""
        from reportlab.platypus import Paragraph, Spacer, Image
        
        elements = []
        elements.append(Paragraph("Visual Analytics", heading_style))
        elements.append(Spacer(1, 15))
        
        chart_titles = {
            'confidence_distribution': 'Confidence Level Distribution',
            'score_distribution': 'Question Point Value Distribution',
            'guide_type_breakdown': 'Guide Type Breakdown',
            'question_complexity': 'Question Complexity Analysis',
            'training_progress': 'Training Session Progress',
            'performance_metrics': 'Performance Metrics Dashboard'
        }
        
        for chart_name, chart_path in chart_paths.items():
            if os.path.exists(chart_path):
                title = chart_titles.get(chart_name, chart_name.replace('_', ' ').title())
                elements.append(Paragraph(f"<b>{title}</b>", styles['Heading3']))
                elements.append(Spacer(1, 10))
                
                # Add image
                try:
                    img = Image(chart_path, width=400, height=300)
                    elements.append(img)
                    elements.append(Spacer(1, 20))
                except Exception as e:
                    logger.warning(f"Could not add chart {chart_name}: {e}")
        
        return elements
    
    def _create_pdf_analytics_section(self, analytics, heading_style, styles):
        """Create PDF analytics section elements"""
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        
        elements = []
        elements.append(Paragraph("Detailed Analytics", heading_style))
        elements.append(Spacer(1, 15))
        
        # Guide analytics table
        guide_analytics = analytics.guide_analytics
        guide_data = [
            ['Metric', 'Value'],
            ['Processing Success Rate', f"{guide_analytics.get('processing_success_rate', 0):.1%}"],
            ['Average File Size', f"{guide_analytics.get('size_distribution', {}).get('average_size_mb', 0):.1f} MB"],
            ['High Quality Guides', str(guide_analytics.get('quality_metrics', {}).get('high_quality_guides', 0))]
        ]
        
        guide_table = Table(guide_data)
        guide_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(Paragraph("Guide Analysis", styles['Heading3']))
        elements.append(guide_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _assess_overall_quality(self, analytics) -> str:
        """Assess overall quality of the training session"""
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