"""Optimized OCR Service with parallel processing, caching, and enhanced performance."""

import asyncio
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Redis removed - using in-memory caching
from PIL import Image, ImageEnhance, ImageFilter

from src.services.ocr_service import OCRService
from utils.logger import logger


class OptimizedOCRService(OCRService):
    """Enhanced OCR service with parallel processing, caching, and image optimization."""

    def __init__(self, api_key=None, base_url=None, allow_no_key=False):
        """Initialize optimized OCR service with in-memory caching."""
        super().__init__(api_key, base_url, allow_no_key)
        
        # Initialize in-memory cache
        self.cache = {}
        self.cache_timestamps = {}
        
        # Cache settings
        self.cache_ttl = 86400 * 7  # 7 days
        self.max_cache_size = 1000  # Maximum number of cached items
        self.max_workers = min(4, os.cpu_count() or 1)  # Limit concurrent OCR requests
        
        logger.info("In-memory cache initialized for OCR results")
        
    def _get_file_hash(self, file_path: Union[str, Path]) -> str:
        """Generate hash for file content to use as cache key."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _get_cached_result(self, file_hash: str) -> Optional[str]:
        """Retrieve cached OCR result from in-memory cache."""
        try:
            if file_hash in self.cache:
                # Check if cache entry is still valid
                timestamp = self.cache_timestamps.get(file_hash, 0)
                if time.time() - timestamp < self.cache_ttl:
                    logger.info(f"Cache hit for file hash: {file_hash[:8]}...")
                    return self.cache[file_hash]
                else:
                    # Remove expired entry
                    del self.cache[file_hash]
                    del self.cache_timestamps[file_hash]
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        
        return None
    
    def _cache_result(self, file_hash: str, result: str) -> None:
        """Cache OCR result in memory."""
        try:
            # Clean up old entries if cache is full
            if len(self.cache) >= self.max_cache_size:
                self._cleanup_cache()
            
            self.cache[file_hash] = result
            self.cache_timestamps[file_hash] = time.time()
            logger.info(f"Cached OCR result for hash: {file_hash[:8]}...")
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")
    
    def _cleanup_cache(self) -> None:
        """Remove oldest cache entries to make room for new ones."""
        try:
            # Remove oldest 20% of entries
            sorted_items = sorted(self.cache_timestamps.items(), key=lambda x: x[1])
            items_to_remove = len(sorted_items) // 5
            
            for file_hash, _ in sorted_items[:items_to_remove]:
                del self.cache[file_hash]
                del self.cache_timestamps[file_hash]
                
            logger.info(f"Cleaned up {items_to_remove} old cache entries")
        except Exception as e:
            logger.warning(f"Cache cleanup error: {e}")
    
    def _preprocess_image(self, image_path: Union[str, Path]) -> str:
        """Optimize image for better OCR accuracy and speed."""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large (max 2048px on longest side)
                max_size = 2048
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    logger.info(f"Resized image to {new_size}")
                
                # Enhance contrast and sharpness for better OCR
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.2)  # Slight contrast boost
                
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.1)  # Slight sharpness boost
                
                # Apply slight noise reduction
                img = img.filter(ImageFilter.MedianFilter(size=3))
                
                # Save optimized image
                optimized_path = str(image_path).replace('.', '_optimized.')
                img.save(optimized_path, 'JPEG', quality=95, optimize=True)
                
                logger.info(f"Image preprocessed and saved to: {optimized_path}")
                return optimized_path
                
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}, using original")
            return str(image_path)
    
    def extract_text_from_image(self, file_path: Union[str, Path]) -> str:
        """Extract text with caching and preprocessing."""
        file_path = Path(file_path)
        
        # Check cache first
        file_hash = self._get_file_hash(file_path)
        cached_result = self._get_cached_result(file_hash)
        if cached_result:
            return cached_result
        
        # Preprocess image for better OCR
        optimized_path = self._preprocess_image(file_path)
        
        try:
            # Use parent class method for actual OCR
            result = super().extract_text_from_image(optimized_path)
            
            # Cache the result
            self._cache_result(file_hash, result)
            
            return result
            
        finally:
            # Clean up optimized image if it was created
            if optimized_path != str(file_path) and os.path.exists(optimized_path):
                try:
                    os.remove(optimized_path)
                except OSError:
                    pass
    
    def extract_text_from_multiple_images_parallel(self, file_paths: List[Union[str, Path]]) -> List[Tuple[str, str, Optional[str]]]:
        """Extract text from multiple images in parallel.
        
        Returns:
            List of tuples: (file_path, extracted_text, error_message)
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(self._extract_with_error_handling, path): path 
                for path in file_paths
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_path):
                file_path = future_to_path[future]
                try:
                    text, error = future.result()
                    results.append((str(file_path), text, error))
                except Exception as e:
                    logger.error(f"Unexpected error processing {file_path}: {e}")
                    results.append((str(file_path), "", str(e)))
        
        return results
    
    def _extract_with_error_handling(self, file_path: Union[str, Path]) -> Tuple[str, Optional[str]]:
        """Extract text with error handling for parallel processing."""
        try:
            text = self.extract_text_from_image(file_path)
            return text, None
        except Exception as e:
            logger.error(f"OCR failed for {file_path}: {e}")
            return "", str(e)
    
    async def extract_text_async(self, file_path: Union[str, Path]) -> str:
        """Async wrapper for OCR extraction."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.extract_text_from_image, file_path)
    
    async def extract_text_from_multiple_images_async(self, file_paths: List[Union[str, Path]]) -> List[Tuple[str, str, Optional[str]]]:
        """Extract text from multiple images asynchronously."""
        tasks = [self.extract_text_async(path) for path in file_paths]
        results = []
        
        for i, task in enumerate(asyncio.as_completed(tasks)):
            try:
                text = await task
                results.append((str(file_paths[i]), text, None))
            except Exception as e:
                logger.error(f"Async OCR failed for {file_paths[i]}: {e}")
                results.append((str(file_paths[i]), "", str(e)))
        
        return results
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        try:
            current_time = time.time()
            valid_entries = 0
            expired_entries = 0
            
            for file_hash, timestamp in self.cache_timestamps.items():
                if current_time - timestamp < self.cache_ttl:
                    valid_entries += 1
                else:
                    expired_entries += 1
            
            # Calculate approximate memory usage
            total_size = sum(len(text.encode('utf-8')) for text in self.cache.values())
            memory_mb = total_size / (1024 * 1024)
            
            return {
                "cache_enabled": True,
                "total_entries": len(self.cache),
                "valid_entries": valid_entries,
                "expired_entries": expired_entries,
                "memory_usage_mb": round(memory_mb, 2),
                "max_cache_size": self.max_cache_size,
                "cache_ttl_hours": self.cache_ttl / 3600
            }
        except Exception as e:
            return {"cache_enabled": True, "error": str(e)}
    
    def clear_cache(self) -> int:
        """Clear all cached OCR results."""
        try:
            cleared_count = len(self.cache)
            self.cache.clear()
            self.cache_timestamps.clear()
            logger.info(f"Cleared {cleared_count} cached OCR results")
            return cleared_count
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0