"""Optimized Unified AI Service with redundancy elimination and enhanced caching."""

import json
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime

from utils.logger import logger
from utils.cache import cache_get, cache_set


@dataclass
class ProcessingProgress:
    """Progress tracking for AI processing."""
    progress_id: str
    total_submissions: int
    current_submission: int = 0
    current_stage: str = "initializing"
    progress_percentage: float = 0.0
    start_time: float = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = time.time()
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class OptimizedUnifiedAIService:
    """Optimized unified AI service with redundancy elimination and caching."""
    
    def __init__(self, mapping_service=None, grading_service=None, llm_service=None):
        """Initialize optimized unified AI service."""
        self.mapping_service = mapping_service
        self.grading_service = grading_service
        self.llm_service = llm_service
        self.progress_callback = None
        
        # Cache for guide type determination (avoid repeated LLM calls)
        self._guide_type_cache = {}
        
        # Cache for mapping results (avoid reprocessing same content)
        self._mapping_cache = {}
        
        # Cache for grading results
        self._grading_cache = {}
        
    def set_progress_callback(self, callback: Callable):
        """Set progress callback function."""
        self.progress_callback = callback
        
    def _update_progress(self, stage: str, percentage: float, message: str = ""):
        """Update progress if callback is set."""
        if self.progress_callback:
            self.progress_callback({
                'stage': stage,
                'percentage': percentage,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
            
    def _generate_cache_key(self, content: str, context: str = "") -> str:
        """Generate cache key for content."""
        import hashlib
        key_content = f"{context}:{content}"
        return hashlib.md5(key_content.encode()).hexdigest()
        
    def _get_cached_guide_type(self, guide_content: str) -> Optional[Dict]:
        """Get cached guide type determination."""
        cache_key = f"guide_type:{self._generate_cache_key(guide_content)}"
        return cache_get(cache_key)
        
    def _cache_guide_type(self, guide_content: str, result: Dict):
        """Cache guide type determination result."""
        cache_key = f"guide_type:{self._generate_cache_key(guide_content)}"
        cache_set(cache_key, result, ttl=7200)  # Cache for 2 hours
        
    def _get_cached_mapping(self, guide_content: str, submission_content: str, guide_type: str) -> Optional[Dict]:
        """Get cached mapping result."""
        cache_key = f"mapping:{self._generate_cache_key(guide_content + submission_content + guide_type)}"
        return cache_get(cache_key)
        
    def _cache_mapping(self, guide_content: str, submission_content: str, guide_type: str, result: Dict):
        """Cache mapping result."""
        cache_key = f"mapping:{self._generate_cache_key(guide_content + submission_content + guide_type)}"
        cache_set(cache_key, result, ttl=3600)  # Cache for 1 hour
        
    def _get_cached_grading(self, guide_content: str, submission_content: str, mapping_data: Dict) -> Optional[Dict]:
        """Get cached grading result."""
        mapping_str = json.dumps(mapping_data, sort_keys=True)
        cache_key = f"grading:{self._generate_cache_key(guide_content + submission_content + mapping_str)}"
        return cache_get(cache_key)
        
    def _cache_grading(self, guide_content: str, submission_content: str, mapping_data: Dict, result: Dict):
        """Cache grading result."""
        mapping_str = json.dumps(mapping_data, sort_keys=True)
        cache_key = f"grading:{self._generate_cache_key(guide_content + submission_content + mapping_str)}"
        cache_set(cache_key, result, ttl=3600)  # Cache for 1 hour
        
    def determine_guide_type_optimized(self, guide_content: str) -> Dict:
        """Determine guide type with caching to avoid redundant LLM calls."""
        # Check cache first
        cached_result = self._get_cached_guide_type(guide_content)
        if cached_result:
            logger.info("Using cached guide type determination")
            return cached_result
            
        # If not cached, determine guide type
        logger.info("Determining guide type via LLM")
        result = self.mapping_service.determine_guide_type(guide_content)
        
        # Cache the result
        self._cache_guide_type(guide_content, result)
        
        return result
        
    def process_submission_optimized(self, guide_data: Dict, submission: Dict, guide_type: str) -> Dict:
        """Process single submission with optimized caching and redundancy elimination."""
        guide_content = guide_data.get('content', '')
        submission_content = submission.get('content', '')
        submission_id = submission.get('id')
        
        logger.info(f"Processing submission {submission_id} with optimizations")
        
        # Step 1: Check for cached mapping result
        mapping_result = self._get_cached_mapping(guide_content, submission_content, guide_type)
        if not mapping_result:
            logger.info(f"Performing mapping for submission {submission_id}")
            mapping_result = self.mapping_service.map_submission_to_guide_optimized(
                submission, guide_data, guide_type
            )
            # Cache the mapping result
            self._cache_mapping(guide_content, submission_content, guide_type, mapping_result)
        else:
            logger.info(f"Using cached mapping for submission {submission_id}")
            
        # Step 2: Check for cached grading result
        grading_result = self._get_cached_grading(guide_content, submission_content, mapping_result)
        if not grading_result:
            logger.info(f"Performing grading for submission {submission_id}")
            grading_result = self.grading_service.grade_submission_optimized(
                submission, guide_data, mapping_result
            )
            # Cache the grading result
            self._cache_grading(guide_content, submission_content, mapping_result, grading_result)
        else:
            logger.info(f"Using cached grading for submission {submission_id}")
            
        return {
            'submission_id': submission_id,
            'mapping': mapping_result,
            'grading': grading_result,
            'processed_at': datetime.now().isoformat()
        }
        
    def process_batch_optimized(self, guide_data: Dict, submissions: List[Dict], 
                               progress_id: str = None) -> Dict:
        """Process multiple submissions with batch optimizations and caching."""
        start_time = time.time()
        total_submissions = len(submissions)
        
        logger.info(f"Starting optimized batch processing for {total_submissions} submissions")
        
        # Initialize progress tracking
        progress = ProcessingProgress(
            progress_id=progress_id or f"batch_{int(time.time())}",
            total_submissions=total_submissions
        )
        
        self._update_progress("initializing", 0, "Starting batch processing")
        
        # Step 1: Determine guide type once (cached)
        progress.current_stage = "determining_guide_type"
        self._update_progress("determining_guide_type", 5, "Determining guide type")
        
        guide_type_result = self.determine_guide_type_optimized(guide_data.get('content', ''))
        guide_type = guide_type_result.get('guide_type', 'qa')
        
        # Step 2: Group submissions by content hash to identify duplicates
        content_groups = {}
        for submission in submissions:
            content_hash = self._generate_cache_key(submission.get('content', ''))
            if content_hash not in content_groups:
                content_groups[content_hash] = []
            content_groups[content_hash].append(submission)
            
        unique_contents = len(content_groups)
        logger.info(f"Found {unique_contents} unique content groups from {total_submissions} submissions")
        
        # Step 3: Process unique contents and reuse results for duplicates
        results = []
        processed_unique = 0
        
        for content_hash, group_submissions in content_groups.items():
            # Process the first submission in the group
            primary_submission = group_submissions[0]
            
            progress.current_submission = processed_unique + 1
            progress.current_stage = "processing"
            percentage = 10 + (processed_unique / unique_contents) * 80
            self._update_progress("processing", percentage, 
                                f"Processing submission {primary_submission.get('id')}")
            
            # Process the primary submission
            primary_result = self.process_submission_optimized(
                guide_data, primary_submission, guide_type
            )
            results.append(primary_result)
            
            # Reuse results for duplicate submissions
            for duplicate_submission in group_submissions[1:]:
                duplicate_result = primary_result.copy()
                duplicate_result['submission_id'] = duplicate_submission.get('id')
                duplicate_result['is_duplicate'] = True
                duplicate_result['original_submission_id'] = primary_submission.get('id')
                results.append(duplicate_result)
                
                logger.info(f"Reused processing results for duplicate submission {duplicate_submission.get('id')}")
            
            processed_unique += 1
            
        # Step 4: Finalize results
        progress.current_stage = "finalizing"
        self._update_progress("finalizing", 95, "Finalizing results")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        batch_result = {
            'progress_id': progress.progress_id,
            'total_submissions': total_submissions,
            'unique_contents': unique_contents,
            'duplicates_found': total_submissions - unique_contents,
            'results': results,
            'guide_type': guide_type,
            'processing_time_seconds': round(processing_time, 2),
            'processed_at': datetime.now().isoformat(),
            'optimizations_applied': {
                'guide_type_cached': True,
                'content_deduplication': True,
                'mapping_caching': True,
                'grading_caching': True
            }
        }
        
        self._update_progress("completed", 100, "Batch processing completed")
        
        logger.info(f"Optimized batch processing completed in {processing_time:.2f}s")
        logger.info(f"Processed {unique_contents} unique contents, reused {total_submissions - unique_contents} duplicates")
        
        return batch_result
        
    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring."""
        from utils.cache import cache_stats
        return cache_stats()
        
    def clear_cache(self) -> None:
        """Clear all caches."""
        from utils.cache import cache_clear
        cache_clear()
        logger.info("All caches cleared")