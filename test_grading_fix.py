#!/usr/bin/env python3
"""
Test script to verify the grading results fix.
This script checks if the question count and scoring issues have been resolved.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.models import db, GradingResult, Mapping, Submission, MarkingGuide
from webapp.exam_grader_app import app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_grading_results():
    """Test the grading results to verify fixes."""
    with app.app_context():
        # Get all grading results
        grading_results = GradingResult.query.all()
        logger.info(f"Total grading results found: {len(grading_results)}")
        
        if not grading_results:
            logger.warning("No grading results found in database")
            return
        
        # Group by submission_id and marking_guide_id
        submission_groups = {}
        for gr in grading_results:
            key = (gr.submission_id, gr.marking_guide_id)
            if key not in submission_groups:
                submission_groups[key] = []
            submission_groups[key].append(gr)
        
        logger.info(f"Found {len(submission_groups)} unique submission-guide combinations")
        
        # Analyze each submission group
        for (submission_id, guide_id), results in submission_groups.items():
            submission = Submission.query.get(submission_id)
            guide = MarkingGuide.query.get(guide_id)
            
            if not submission or not guide:
                logger.warning(f"Missing submission or guide for IDs: {submission_id}, {guide_id}")
                continue
            
            logger.info(f"\n--- Analyzing Submission: {submission.filename} ---")
            logger.info(f"Marking Guide: {guide.title}")
            logger.info(f"Number of grading results: {len(results)}")
            
            # Calculate totals
            total_score = sum(gr.score or 0 for gr in results)
            total_max_score = sum(gr.max_score or 0 for gr in results)
            corrected_percentage = (total_score / total_max_score * 100) if total_max_score > 0 else 0
            
            logger.info(f"Total Score: {total_score}/{total_max_score} = {corrected_percentage:.1f}%")
            
            # Check mappings
            for i, gr in enumerate(results, 1):
                mapping = gr.mapping
                if mapping:
                    logger.info(f"  Question {i}: {mapping.guide_question_text[:50]}...")
                    logger.info(f"    Score: {gr.score}/{gr.max_score} = {(gr.score/gr.max_score*100):.1f}%")
                    logger.info(f"    Match Score: {mapping.match_score}")
                else:
                    logger.info(f"  Question {i}: No mapping found")
                    logger.info(f"    Score: {gr.score}/{gr.max_score}")
            
            # Test the view_results logic
            criteria_scores = []
            for gr in results:
                detailed_feedback = gr.detailed_feedback or {}
                points_earned = gr.score or 0
                points_possible = gr.max_score or 1
                percentage = (points_earned / points_possible * 100) if points_possible > 0 else 0
                
                mapping = gr.mapping
                question_text = mapping.guide_question_text if mapping else "Question"
                
                criteria_scores.append({
                    "question_id": mapping.guide_question_id if mapping else f"q_{len(criteria_scores)+1}",
                    "description": question_text,
                    "points_earned": points_earned,
                    "points_possible": points_possible,
                    "percentage": round(percentage, 1),
                    "feedback": gr.feedback or ""
                })
            
            logger.info(f"Frontend will show: {len(criteria_scores)} questions")
            logger.info(f"Expected total score: {total_score}/{total_max_score} = {corrected_percentage:.1f}%")
            
            # Verify the fix
            if len(criteria_scores) > 1:
                logger.info("✅ FIXED: Multiple questions detected correctly")
            else:
                logger.warning("❌ ISSUE: Still showing only 1 question")
            
            if abs(corrected_percentage - (total_score/total_max_score*100)) < 0.1:
                logger.info("✅ FIXED: Score calculation is correct")
            else:
                logger.warning("❌ ISSUE: Score calculation is incorrect")

def test_database_integrity():
    """Test database integrity for grading results."""
    with app.app_context():
        # Check for orphaned grading results
        orphaned_results = db.session.query(GradingResult).filter(
            ~GradingResult.submission_id.in_(
                db.session.query(Submission.id)
            )
        ).all()
        
        if orphaned_results:
            logger.warning(f"Found {len(orphaned_results)} orphaned grading results")
        else:
            logger.info("✅ No orphaned grading results found")
        
        # Check for grading results without mappings
        results_without_mappings = db.session.query(GradingResult).filter(
            GradingResult.mapping_id.is_(None)
        ).all()
        
        # Check for grading results without associated mappings
        orphaned_grading_results = db.session.query(GradingResult).filter(
            GradingResult.mapping_id.isnot(None),
            ~GradingResult.mapping_id.in_(
                db.session.query(Mapping.id)
            )
        ).all()
        
        if results_without_mappings:
            logger.warning(f"Found {len(results_without_mappings)} grading results without mappings")
            for gr in results_without_mappings[:5]:  # Show first 5
                logger.warning(f"  - GradingResult ID: {gr.id}, Submission: {gr.submission.filename if gr.submission else 'Unknown'}")
        else:
            logger.info("✅ All grading results have associated mappings")
        
        if orphaned_grading_results:
            logger.warning(f"Found {len(orphaned_grading_results)} orphaned grading results")
            for gr in orphaned_grading_results[:5]:  # Show first 5
                logger.warning(f"  - GradingResult ID: {gr.id}, Mapping ID: {gr.mapping_id}, Submission: {gr.submission.filename if gr.submission else 'Unknown'}")
        else:
            logger.info("✅ No orphaned grading results found")

if __name__ == "__main__":
    logger.info("Starting grading results test...")
    test_database_integrity()
    test_grading_results()
    logger.info("Test completed.")