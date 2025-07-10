"""
Report Generation Service for creating detailed feedback reports.
Generates PDF and JSON reports of grading results with scores, feedback, and analysis.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas

from src.database.models import Submission, GradingResult, Mapping, MarkingGuide
from utils.logger import logger


class ReportService:
    """Service for generating detailed grading reports."""
    
    def __init__(self):
        """Initialize the report service."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for reports."""
        # Custom styles for better formatting
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leading=14
        ))
        
        self.styles.add(ParagraphStyle(
            name='FeedbackText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=8,
            leading=14,
            leftIndent=20
        ))
    
    def generate_pdf_report(self, submission_id: str, output_path: str) -> bool:
        """
        Generate a detailed PDF report for a submission.
        
        Args:
            submission_id: ID of the submission to generate report for
            output_path: Path where to save the PDF file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get submission data
            submission = Submission.query.get(submission_id)
            if not submission:
                logger.error(f"Submission {submission_id} not found")
                return False
            
            # Get grading result
            grading_result = GradingResult.query.filter_by(submission_id=submission_id).first()
            if not grading_result:
                logger.error(f"No grading result found for submission {submission_id}")
                return False
            
            # Get mappings
            mappings = Mapping.query.filter_by(submission_id=submission_id).all()
            
            # Get marking guide
            marking_guide = MarkingGuide.query.get(grading_result.marking_guide_id) if grading_result.marking_guide_id else None
            
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            story = []
            
            # Add title
            story.append(Paragraph("Grading Report", self.styles['CustomTitle']))
            story.append(Spacer(1, 20))
            
            # Add submission information
            story.append(Paragraph("Submission Information", self.styles['CustomHeading']))
            
            submission_info = [
                ["Filename:", submission.filename],
                ["Student ID:", submission.student_id or "Not provided"],
                ["Student Name:", submission.student_name or "Not provided"],
                ["Upload Date:", submission.created_at.strftime("%Y-%m-%d %H:%M:%S")],
                ["Processing Status:", submission.processing_status.title()],
            ]
            
            if marking_guide:
                submission_info.extend([
                    ["Marking Guide:", marking_guide.title],
                    ["Guide Upload Date:", marking_guide.created_at.strftime("%Y-%m-%d %H:%M:%S")],
                ])
            
            submission_table = Table(submission_info, colWidths=[2*inch, 4*inch])
            submission_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(submission_table)
            story.append(Spacer(1, 20))
            
            # Add overall results
            story.append(Paragraph("Overall Results", self.styles['CustomHeading']))
            
            results_info = [
                ["Total Score:", f"{grading_result.score:.1f}"],
                ["Maximum Score:", f"{grading_result.max_score:.1f}"],
                ["Percentage:", f"{grading_result.percentage:.1f}%"],
                ["Letter Grade:", grading_result.feedback],
                ["Grading Method:", grading_result.grading_method.upper()],
                ["Graded At:", grading_result.created_at.strftime("%Y-%m-%d %H:%M:%S")],
            ]
            
            results_table = Table(results_info, colWidths=[2*inch, 4*inch])
            results_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(results_table)
            story.append(Spacer(1, 20))
            
            # Add detailed question analysis
            if mappings:
                story.append(Paragraph("Detailed Question Analysis", self.styles['CustomHeading']))
                
                for i, mapping in enumerate(mappings, 1):
                    story.append(Paragraph(f"Question {i}", self.styles['CustomHeading']))
                    
                    # Question details
                    question_info = [
                        ["Question ID:", mapping.guide_question_id],
                        ["Question Text:", mapping.guide_question_text[:200] + "..." if len(mapping.guide_question_text) > 200 else mapping.guide_question_text],
                        ["Student Answer:", mapping.submission_answer[:200] + "..." if len(mapping.submission_answer) > 200 else mapping.submission_answer],
                        ["Maximum Score:", f"{mapping.max_score:.1f}"],
                        ["Match Score:", f"{mapping.match_score:.2f}"],
                        ["Match Reason:", mapping.match_reason or "Not provided"],
                    ]
                    
                    question_table = Table(question_info, colWidths=[2*inch, 4*inch])
                    question_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), colors.lightyellow),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
                    ]))
                    
                    story.append(question_table)
                    story.append(Spacer(1, 10))
            
            # Add detailed feedback if available
            if grading_result.detailed_feedback:
                story.append(Paragraph("Detailed Feedback", self.styles['CustomHeading']))
                
                detailed_feedback = grading_result.detailed_feedback
                if isinstance(detailed_feedback, str):
                    try:
                        detailed_feedback = json.loads(detailed_feedback)
                    except json.JSONDecodeError:
                        detailed_feedback = {"feedback": detailed_feedback}
                
                # Extract feedback from detailed_feedback
                if isinstance(detailed_feedback, dict):
                    mappings_data = detailed_feedback.get('mappings', [])
                    
                    for i, mapping_data in enumerate(mappings_data, 1):
                        story.append(Paragraph(f"Question {i} Feedback", self.styles['CustomHeading']))
                        
                        feedback_text = mapping_data.get('grade_feedback', 'No feedback provided')
                        story.append(Paragraph(feedback_text, self.styles['FeedbackText']))
                        
                        # Add strengths and weaknesses if available
                        strengths = mapping_data.get('strengths', [])
                        weaknesses = mapping_data.get('weaknesses', [])
                        
                        if strengths:
                            story.append(Paragraph("Strengths:", self.styles['CustomBody']))
                            for strength in strengths:
                                story.append(Paragraph(f"• {strength}", self.styles['FeedbackText']))
                        
                        if weaknesses:
                            story.append(Paragraph("Areas for Improvement:", self.styles['CustomBody']))
                            for weakness in weaknesses:
                                story.append(Paragraph(f"• {weakness}", self.styles['FeedbackText']))
                        
                        story.append(Spacer(1, 10))
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"PDF report generated successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {str(e)}")
            return False
    
    def generate_json_report(self, submission_id: str, output_path: str) -> bool:
        """
        Generate a detailed JSON report for a submission.
        
        Args:
            submission_id: ID of the submission to generate report for
            output_path: Path where to save the JSON file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get submission data
            submission = Submission.query.get(submission_id)
            if not submission:
                logger.error(f"Submission {submission_id} not found")
                return False
            
            # Get grading result
            grading_result = GradingResult.query.filter_by(submission_id=submission_id).first()
            if not grading_result:
                logger.error(f"No grading result found for submission {submission_id}")
                return False
            
            # Get mappings
            mappings = Mapping.query.filter_by(submission_id=submission_id).all()
            
            # Get marking guide
            marking_guide = MarkingGuide.query.get(grading_result.marking_guide_id) if grading_result.marking_guide_id else None
            
            # Build report data
            report_data = {
                "report_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "submission_id": submission_id,
                    "report_version": "1.0"
                },
                "submission_info": {
                    "filename": submission.filename,
                    "student_id": submission.student_id,
                    "student_name": submission.student_name,
                    "upload_date": submission.created_at.isoformat(),
                    "processing_status": submission.processing_status,
                    "file_size": submission.file_size,
                    "file_type": submission.file_type
                },
                "marking_guide_info": {
                    "id": marking_guide.id if marking_guide else None,
                    "title": marking_guide.title if marking_guide else None,
                    "upload_date": marking_guide.created_at.isoformat() if marking_guide else None,
                    "total_marks": marking_guide.total_marks if marking_guide else None
                },
                "grading_results": {
                    "score": grading_result.score,
                    "max_score": grading_result.max_score,
                    "percentage": grading_result.percentage,
                    "letter_grade": grading_result.feedback,
                    "grading_method": grading_result.grading_method,
                    "graded_at": grading_result.created_at.isoformat(),
                    "confidence": grading_result.confidence
                },
                "detailed_analysis": {
                    "mappings_count": len(mappings),
                    "average_match_score": sum(m.match_score for m in mappings) / len(mappings) if mappings else 0,
                    "questions_analyzed": len(mappings)
                },
                "question_analysis": []
            }
            
            # Add detailed question analysis
            for i, mapping in enumerate(mappings, 1):
                question_data = {
                    "question_number": i,
                    "question_id": mapping.guide_question_id,
                    "question_text": mapping.guide_question_text,
                    "model_answer": mapping.guide_answer,
                    "student_answer": mapping.submission_answer,
                    "max_score": mapping.max_score,
                    "match_score": mapping.match_score,
                    "match_reason": mapping.match_reason,
                    "mapping_method": mapping.mapping_method
                }
                
                # Add detailed feedback if available
                if grading_result.detailed_feedback:
                    detailed_feedback = grading_result.detailed_feedback
                    if isinstance(detailed_feedback, str):
                        try:
                            detailed_feedback = json.loads(detailed_feedback)
                        except json.JSONDecodeError:
                            detailed_feedback = {"feedback": detailed_feedback}
                    
                    if isinstance(detailed_feedback, dict):
                        mappings_data = detailed_feedback.get('mappings', [])
                        if i <= len(mappings_data):
                            mapping_detail = mappings_data[i-1]
                            question_data.update({
                                "grade_score": mapping_detail.get('grade_score'),
                                "grade_percentage": mapping_detail.get('grade_percentage'),
                                "grade_feedback": mapping_detail.get('grade_feedback'),
                                "strengths": mapping_detail.get('strengths', []),
                                "weaknesses": mapping_detail.get('weaknesses', [])
                            })
                
                report_data["question_analysis"].append(question_data)
            
            # Write JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"JSON report generated successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate JSON report: {str(e)}")
            return False
    
    def get_report_summary(self, submission_id: str) -> Dict[str, Any]:
        """
        Get a summary of grading results for a submission.
        
        Args:
            submission_id: ID of the submission
            
        Returns:
            Dict: Summary of grading results
        """
        try:
            submission = Submission.query.get(submission_id)
            if not submission:
                return {"error": "Submission not found"}
            
            grading_result = GradingResult.query.filter_by(submission_id=submission_id).first()
            if not grading_result:
                return {"error": "No grading result found"}
            
            mappings = Mapping.query.filter_by(submission_id=submission_id).all()
            
            return {
                "submission_id": submission_id,
                "filename": submission.filename,
                "score": grading_result.score,
                "max_score": grading_result.max_score,
                "percentage": grading_result.percentage,
                "letter_grade": grading_result.feedback,
                "questions_analyzed": len(mappings),
                "graded_at": grading_result.created_at.isoformat(),
                "has_detailed_feedback": bool(grading_result.detailed_feedback)
            }
            
        except Exception as e:
            logger.error(f"Failed to get report summary: {str(e)}")
            return {"error": str(e)}


# Global instance
report_service = ReportService() 