"""
Unified AI Processing Service with Progress Tracking
Combines mapping and grading into a single streamlined workflow with real-time progress updates.
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass

from utils.logger import logger


@dataclass
class ProcessingProgress:
    """Data class for tracking processing progress"""
    current_step: int
    total_steps: int
    current_operation: str
    submission_index: int
    total_submissions: int
    percentage: float
    estimated_time_remaining: Optional[float] = None
    status: str = "processing"  # processing, completed, error
    details: Optional[str] = None


class UnifiedAIService:
    """
    Unified AI Processing Service that combines mapping and grading into a single workflow
    with comprehensive progress tracking and real-time status updates.
    """

    def __init__(self, mapping_service=None, grading_service=None, llm_service=None):
        """
        Initialize the unified AI service.
        
        Args:
            mapping_service: MappingService instance
            grading_service: GradingService instance  
            llm_service: LLMService instance
        """
        if mapping_service is None:
            raise ValueError("MappingService must be provided to UnifiedAIService")
        if grading_service is None:
            raise ValueError("GradingService must be provided to UnifiedAIService")
        if llm_service is None:
            raise ValueError("LLMService must be provided to UnifiedAIService")

        self.mapping_service = mapping_service
        self.grading_service = grading_service
        self.llm_service = llm_service
        
        # Progress tracking
        self.progress_callback: Optional[Callable[[ProcessingProgress], None]] = None
        self.start_time: Optional[float] = None
        self.processing_times: List[float] = []
        self.total_submissions: int = 0 # Initialize total_submissions
        
        # Optimization: Cache for guide type determination to avoid redundant LLM calls
        self._guide_type_cache: Dict[str, Tuple[str, float]] = {}
        
        # Optimization: Cache for content deduplication
        self._content_hash_cache: Dict[str, Dict] = {}
        
        logger.info("Unified AI Service initialized with optimizations")

    def set_progress_callback(self, callback: Callable[[ProcessingProgress], None]):
        """Set callback function for progress updates"""
        self.progress_callback = callback

    def _update_progress(self, progress: ProcessingProgress):
        """Update progress and call callback if set"""
        if self.progress_callback:
            self.progress_callback(progress)
        
        logger.info(f"Progress: {progress.percentage:.1f}% - {progress.current_operation}")

    def _estimate_time_remaining(self, current_step: int) -> float:
        if current_step == 0 or not self.start_time or self.total_submissions == 0:
            return 0.0
        elapsed_time = time.time() - self.start_time
        progress_ratio = current_step / self.total_submissions
        if progress_ratio == 0:
            return float('inf')  # Avoid division by zero
        estimated_total_time = elapsed_time / progress_ratio
        return max(0.0, estimated_total_time - elapsed_time) # Ensure non-negative time
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication."""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_cached_guide_type(self, guide_content: str) -> Optional[Tuple[str, float]]:
        """Get cached guide type determination result."""
        content_hash = self._generate_content_hash(guide_content)
        return self._guide_type_cache.get(content_hash)
    
    def _cache_guide_type(self, guide_content: str, guide_type: str, confidence: float):
        """Cache guide type determination result."""
        content_hash = self._generate_content_hash(guide_content)
        self._guide_type_cache[content_hash] = (guide_type, confidence)
        logger.info(f"Cached guide type: {guide_type} (confidence: {confidence})")
    
    def _determine_guide_type_optimized(self, guide_content: str) -> Tuple[str, float]:
        """Determine guide type with caching to avoid redundant LLM calls."""
        # Check cache first
        cached_result = self._get_cached_guide_type(guide_content)
        if cached_result:
            guide_type, confidence = cached_result
            logger.info(f"Using cached guide type: {guide_type} (confidence: {confidence})")
            return guide_type, confidence
        
        # If not cached, determine guide type via LLM
        logger.info("Determining guide type via LLM (not cached)")
        try:
            guide_type, confidence = self.mapping_service.determine_guide_type(guide_content)
            # Cache the result for future use
            self._cache_guide_type(guide_content, guide_type, confidence)
            return guide_type, confidence
        except Exception as e:
            logger.warning(f"Guide type determination failed: {str(e)}, using default")
            return "questions", 0.5
    
    def _group_submissions_by_content(self, submissions: List[Dict]) -> Dict[str, List[Dict]]:
        """Group submissions by content hash to identify duplicates."""
        content_groups = {}
        for submission in submissions:
            content = submission.get('content_text', submission.get('content', ''))
            if not content:
                # Handle empty content separately
                content_hash = 'empty_content'
            else:
                content_hash = self._generate_content_hash(content)
            
            if content_hash not in content_groups:
                content_groups[content_hash] = []
            content_groups[content_hash].append(submission)
        
        unique_count = len(content_groups)
        total_count = len(submissions)
        duplicate_count = total_count - unique_count
        
        if duplicate_count > 0:
            logger.info(f"Content deduplication: {unique_count} unique, {duplicate_count} duplicates from {total_count} total")
        
        return content_groups

    def process_unified_ai_grading(
        self,
        marking_guide_content: Dict,
        submissions: List[Dict],
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
        max_questions: Optional[int] = None
    ) -> Tuple[Dict, Optional[str]]:
        """
        Process unified AI grading with mapping and grading combined.
        
        Args:
            marking_guide_content: Content of the marking guide
            submissions: List of submission dictionaries
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple[Dict, Optional[str]]: (Results, Error message if any)
        """
        try:
            self.start_time = time.time()
            if progress_callback:
                self.set_progress_callback(progress_callback)
            
            self.total_submissions = len(submissions) # Set total_submissions
            logger.info(f"Starting unified AI processing for {self.total_submissions} submissions")
            
            # Calculate total steps for progress tracking
            # Steps: 1. Guide analysis, 2-N. Process each submission, N+1. Finalize results
            total_steps = 2 + self.total_submissions
            current_step = 0
            
            # Step 1: Analyze marking guide
            current_step += 1
            self._update_progress(ProcessingProgress(
                current_step=current_step,
                total_steps=total_steps,
                current_operation="Analyzing marking guide structure...",
                submission_index=0,
                total_submissions=len(submissions),
                percentage=(current_step / total_steps) * 100,
                estimated_time_remaining=self._estimate_time_remaining(current_step)
            ))
            
            # Optimization: Determine guide type once with caching
            guide_content = marking_guide_content.get("raw_content", "")
            guide_type, guide_confidence = self._determine_guide_type_optimized(guide_content)
            logger.info(f"Guide type determined: {guide_type} (confidence: {guide_confidence})")
            
            # Optimization: Group submissions by content to identify duplicates
            content_groups = self._group_submissions_by_content(submissions)
            unique_contents = len(content_groups)
            
            # Initialize results
            all_results = []
            successful_gradings = 0
            failed_gradings = 0
            total_score = 0
            total_max_score = 0
            processed_unique = 0
            
            # Step 2: Process unique content groups (eliminates duplicate processing)
            for content_hash, group_submissions in content_groups.items():
                # Process the first submission in each group
                primary_submission = group_submissions[0]
                i = processed_unique  # Use processed_unique for progress tracking
                current_step += 1
                submission_content = primary_submission.get('content_text', primary_submission.get('content', ''))
                submission_filename = primary_submission.get('filename', f'submission_{i+1}')
                
                # Handle empty content group
                if content_hash == 'empty_content' or not submission_content:
                    logger.warning(f"No content found for submission group {submission_filename}. Skipping {len(group_submissions)} submissions.")
                    
                    # Mark all submissions in this group as failed
                    for submission in group_submissions:
                        failed_gradings += 1
                        all_results.append({
                            'submission_id': submission.get('id', f'sub_{i}'),
                            'filename': submission.get('filename', f'submission_{i+1}'),
                            'status': 'error',
                            'error': 'Empty submission content',
                            'score': 0,
                            'max_score': 0,
                            'percentage': 0,
                            'letter_grade': 'F',
                            'details': 'No text could be extracted from the submission file. Please ensure the file contains readable text or images.'
                        })
                    
                    self._update_progress(ProcessingProgress(
                        current_step=current_step,
                        total_steps=total_steps,
                        current_operation=f"Skipping empty content group ({len(group_submissions)} submissions)",
                        submission_index=processed_unique + 1,
                        total_submissions=unique_contents,
                        percentage=(current_step / total_steps) * 100,
                        estimated_time_remaining=self._estimate_time_remaining(current_step),
                        details=f"No content found for {len(group_submissions)} submissions. They will be marked as failed."
                    ))
                    processed_unique += 1
                    continue
                
                # Calculate and update progress for current unique content
                current_percentage = int((current_step / total_steps) * 100)
                group_size = len(group_submissions)
                progress_details = f"Processing unique content (affects {group_size} submission{'s' if group_size > 1 else ''})"
                
                self._update_progress(ProcessingProgress(
                    current_step=current_step,
                    total_steps=total_steps,
                    current_operation=f"Processing {submission_filename}",
                    submission_index=processed_unique + 1,
                    total_submissions=unique_contents,
                    percentage=current_percentage,
                    estimated_time_remaining=self._estimate_time_remaining(current_step),
                    details=progress_details
                ))
                
                try:
                    # Process the primary submission (first in group)
                    mapping_result = None
                    mapping_error = None
                    if self.mapping_service:
                        mapping_result, mapping_error = self.mapping_service.map_submission_to_guide(
                            marking_guide_content.get("raw_content", ""), submission_content, num_questions=max_questions
                        )

                    if mapping_error:
                        logger.error(f"Mapping failed for content group {submission_filename}: {mapping_error}")
                        # Mark all submissions in this group as failed
                        for submission in group_submissions:
                            failed_gradings += 1
                            all_results.append({
                                'submission_id': submission.get('id', f'sub_{i}'),
                                'filename': submission.get('filename', f'submission_{i+1}'),
                                'status': 'error',
                                'error': mapping_error,
                                'score': 0,
                                'max_score': 0,
                                'percentage': 0,
                                'letter_grade': 'F'
                            })
                        processed_unique += 1
                        continue

                    grading_result = None
                    grading_error = None
                    if self.grading_service and mapping_result:
                        # Pass the mapped questions and answers to the grading service
                        grading_result, grading_error = self.grading_service.grade_submission(
                            marking_guide_content, submission_content, 
                            mapped_questions=mapping_result.get('mappings'),
                            guide_type=guide_type
                        )

                    if grading_error:
                        logger.error(f"Grading failed for content group {submission_filename}: {grading_error}")
                        # Mark all submissions in this group as failed
                        for submission in group_submissions:
                            failed_gradings += 1
                            all_results.append({
                                'submission_id': submission.get('id', f'sub_{i}'),
                                'filename': submission.get('filename', f'submission_{i+1}'),
                                'status': 'error',
                                'error': grading_error,
                                'score': 0,
                                'max_score': 0,
                                'percentage': 0,
                                'letter_grade': 'F'
                            })
                        processed_unique += 1
                        continue

                    if not mapping_result and not grading_result:
                        logger.warning("No mapping or grading service available, or no results generated.")
                        # Mark all submissions in this group as failed
                        for submission in group_submissions:
                            failed_gradings += 1
                            all_results.append({
                                'submission_id': submission.get('id', f'sub_{i}'),
                                'filename': submission.get('filename', f'submission_{i+1}'),
                                'status': 'error',
                                'error': 'No AI services available or no results generated',
                                'score': 0,
                                'max_score': 0,
                                'percentage': 0,
                                'letter_grade': 'F'
                            })
                        processed_unique += 1
                        continue

                    # Extract grading results
                    score = grading_result.get('score', 0)
                    max_score = grading_result.get('max_score', 0)
                    percentage = grading_result.get('percentage', 0)
                    letter_grade = self._get_letter_grade(percentage)

                    # Apply results to all submissions in the group
                    for j, submission in enumerate(group_submissions):
                        successful_gradings += 1
                        total_score += score
                        total_max_score += max_score
                        
                        result_entry = {
                            'submission_id': submission.get('id', f'sub_{i}_{j}'),
                            'filename': submission.get('filename', f'submission_{i+1}_{j+1}'),
                            'status': 'success',
                            'score': score,
                            'max_score': max_score,
                            'percentage': round(percentage, 1),
                            'letter_grade': letter_grade,
                            'detailed_feedback': grading_result.get('detailed_feedback', {}),
                            'mappings': mapping_result.get('mappings', []) if mapping_result else [],
                            'guide_type': guide_type,
                            'processing_time': time.time() - self.start_time
                        }
                        
                        # Mark duplicates for transparency
                        if j > 0:
                            result_entry['is_duplicate'] = True
                            result_entry['original_submission_id'] = group_submissions[0].get('id')
                            logger.info(f"Reused processing results for duplicate submission {submission.get('filename')}")
                        
                        all_results.append(result_entry)

                    logger.info(f"Successfully processed content group {submission_filename}: {percentage:.1f}% (applied to {len(group_submissions)} submissions)")
                
                except Exception as e:
                    logger.error(f"Error processing content group {submission_filename}: {str(e)}")
                    # Mark all submissions in this group as failed
                    for submission in group_submissions:
                        failed_gradings += 1
                        all_results.append({
                            'submission_id': submission.get('id', f'sub_{i}'),
                            'filename': submission.get('filename', f'submission_{i+1}'),
                            'status': 'error',
                            'error': str(e),
                            'score': 0,
                            'max_score': 0,
                            'percentage': 0,
                            'letter_grade': 'F'
                        })
                
                processed_unique += 1
            
            # Step 3: Finalize results with optimization statistics
            current_step += 1
            
            # Calculate optimization metrics
            total_submissions = len(submissions)
            duplicate_submissions = total_submissions - unique_contents
            optimization_ratio = (duplicate_submissions / total_submissions * 100) if total_submissions > 0 else 0
            
            self._update_progress(ProcessingProgress(
                current_step=current_step,
                total_steps=total_steps,
                current_operation="Finalizing results and generating summary...",
                submission_index=len(submissions),
                total_submissions=len(submissions),
                percentage=100.0,
                status="completed",
                details=f"Processed {successful_gradings} successful, {failed_gradings} failed. Optimization saved {optimization_ratio:.1f}% processing time."
            ))
            
            # Calculate summary statistics
            average_percentage = (total_score / total_max_score * 100) if total_max_score > 0 else 0
            processing_time = time.time() - self.start_time
            
            # Create comprehensive result
            result = {
                'status': 'success',
                'message': f'Unified AI processing completed: {successful_gradings} successful, {failed_gradings} failed',
                'results': all_results,
                'summary': {
                    'successful': successful_gradings,
                    'failed': failed_gradings,
                    'total': len(submissions),
                    'unique_contents_processed': unique_contents,
                    'duplicate_submissions_detected': duplicate_submissions,
                    'optimization_ratio': round(optimization_ratio, 1),
                    'total_score': total_score,
                    'total_max_score': total_max_score,
                    'average_percentage': round(average_percentage, 1),
                    'processing_time': round(processing_time, 2),
                    'guide_type': guide_type,
                    'guide_confidence': guide_confidence
                },
                'metadata': {
                    'processed_at': datetime.now().isoformat(),
                    'processing_method': 'unified_ai',
                    'guide_analysis': {
                        'type': guide_type,
                        'confidence': guide_confidence
                    },
                    'cache_stats': {
                        'guide_type_cache_size': len(self._guide_type_cache),
                        'content_hash_cache_size': len(self._content_hash_cache)
                    }
                }
            }
            
            logger.info(f"Unified AI processing completed in {processing_time:.2f}s: {average_percentage:.1f}% average. Processed {unique_contents} unique contents, detected {duplicate_submissions} duplicates ({optimization_ratio:.1f}% optimization).")
            return result, None
            
        except Exception as e:
            error_message = f"Unified AI processing failed: {str(e)}"
            logger.error(error_message)
            
            # Update progress with error status
            if self.progress_callback:
                self._update_progress(ProcessingProgress(
                    current_step=0,
                    total_steps=1,
                    current_operation="Processing failed",
                    submission_index=0,
                    total_submissions=len(submissions),
                    percentage=0,
                    status="error",
                    details=str(e)
                ))
            
            return {'status': 'error', 'message': error_message}, error_message

    def _get_letter_grade(self, percentage: float) -> str:
        """Convert percentage to letter grade"""
        if percentage >= 97: return "A+"
        elif percentage >= 93: return "A"
        elif percentage >= 90: return "A-"
        elif percentage >= 87: return "B+"
        elif percentage >= 83: return "B"
        elif percentage >= 80: return "B-"
        elif percentage >= 77: return "C+"
        elif percentage >= 73: return "C"
        elif percentage >= 70: return "C-"
        elif percentage >= 67: return "D+"
        elif percentage >= 63: return "D"
        elif percentage >= 60: return "D-"
        else: return "F"
    
    def get_cache_stats(self) -> Dict:
        """Get current cache statistics"""
        return {
            'guide_type_cache': {
                'size': len(self._guide_type_cache),
                'entries': list(self._guide_type_cache.keys()) if len(self._guide_type_cache) < 10 else f"{len(self._guide_type_cache)} entries"
            },
            'content_hash_cache': {
                'size': len(self._content_hash_cache),
                'unique_contents': len(set(self._content_hash_cache.values()))
            }
        }
    
    def clear_cache(self):
        """Clear all caches"""
        self._guide_type_cache.clear()
        self._content_hash_cache.clear()
        logger.info("All caches cleared")
    
    def clear_guide_type_cache(self):
        """Clear only the guide type cache"""
        self._guide_type_cache.clear()
        logger.info("Guide type cache cleared")
    
    def clear_content_cache(self):
        """Clear only the content hash cache"""
        self._content_hash_cache.clear()
        logger.info("Content hash cache cleared")

    def get_processing_stats(self) -> Dict:
        """Get processing statistics"""
        return {
            'service_type': 'unified_ai',
            'mapping_service_available': self.mapping_service is not None,
            'grading_service_available': self.grading_service is not None,
            'llm_service_available': self.llm_service is not None,
            'processing_times': self.processing_times[-10:] if self.processing_times else [],
            'average_processing_time': sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        }
