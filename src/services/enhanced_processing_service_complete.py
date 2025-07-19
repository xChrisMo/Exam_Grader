    def _calculate_final_score(self, grading_results: List[Dict], guide: MarkingGuide) -> Dict:
        """Calculate final score from selected grading results."""
        if not grading_results:
            return {
                "total_score": 0,
                "max_possible_score": guide.total_marks or 0,
                "percentage": 0,
                "grade_level": "F",
                "selected_questions": 0,
                "detailed_results": []
            }
        
        total_score = sum(result.get('score', 0) for result in grading_results)
        max_possible = sum(result.get('max_score', 0) for result in grading_results)
        percentage = (total_score / max_possible * 100) if max_possible > 0 else 0
        
        # Determine grade level
        if percentage >= 90:
            grade_level = "A+"
        elif percentage >= 85:
            grade_level = "A"
        elif percentage >= 80:
            grade_level = "A-"
        elif percentage >= 75:
            grade_level = "B+"
        elif percentage >= 70:
            grade_level = "B"
        elif percentage >= 65:
            grade_level = "B-"
        elif percentage >= 60:
            grade_level = "C+"
        elif percentage >= 55:
            grade_level = "C"
        elif percentage >= 50:
            grade_level = "C-"
        else:
            grade_level = "F"
        
        return {
            "total_score": total_score,
            "max_possible_score": max_possible,
            "percentage": percentage,
            "grade_level": grade_level,
            "selected_questions": len(grading_results),
            "detailed_results": grading_results
        }
    
    def _save_grading_results_with_retry(self, submission_id: str, marking_guide_id: str, results: List[Dict], session_id: str):
        """Save grading results to database with retry logic for database locks."""
        import time
        import random
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Clear existing results for this session
                GradingResult.query.filter_by(
                    submission_id=submission_id,
                    grading_session_id=session_id
                ).delete()
                
                # Save new results
                for result in results:
                    grading_result = GradingResult(
                        submission_id=submission_id,
                        marking_guide_id=marking_guide_id,
                        grading_session_id=session_id,
                        mapping_id=result.get('mapping_id'),
                        score=result.get('score', 0),
                        max_score=result.get('max_score', 0),
                        percentage=result.get('percentage', 0),
                        feedback=result.get('feedback', ''),
                        confidence=result.get('confidence', 0.0)
                    )
                    db.session.add(grading_result)
                
                # Commit immediately
                db.session.commit()
                logger.info(f"Successfully saved {len(results)} grading results")
                return
                
            except Exception as e:
                db.session.rollback()
                if attempt < max_retries - 1:
                    # Wait with exponential backoff and jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Database lock saving results on attempt {attempt + 1}, retrying in {wait_time:.2f}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to save grading results after {max_retries} attempts: {str(e)}")
                    raise
    
    def _update_grading_session_with_retry(self, grading_session: GradingSession, questions_graded: int):
        """Update grading session with retry logic for database locks."""
        import time
        import random
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Refresh the session object to avoid stale data
                db.session.refresh(grading_session)
                
                # Update session
                grading_session.status = "completed"
                grading_session.total_questions_graded = questions_graded
                grading_session.processing_end_time = datetime.utcnow()
                
                # Commit immediately
                db.session.commit()
                logger.info(f"Successfully updated grading session {grading_session.id}")
                return
                
            except Exception as e:
                db.session.rollback()
                if attempt < max_retries - 1:
                    # Wait with exponential backoff and jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Database lock updating session on attempt {attempt + 1}, retrying in {wait_time:.2f}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to update grading session after {max_retries} attempts: {str(e)}")
                    raise

    def _commit_with_retry(self, operation_name: str):
        """Commit database changes with retry logic for database locks."""
        import time
        import random
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                db.session.commit()
                logger.info(f"Successfully committed {operation_name}")
                return
                
            except Exception as e:
                db.session.rollback()
                if attempt < max_retries - 1:
                    # Wait with exponential backoff and jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Database lock during {operation_name} on attempt {attempt + 1}, retrying in {wait_time:.2f}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to commit {operation_name} after {max_retries} attempts: {str(e)}")
                    raise