"""
Batch Processing Service for handling multiple file uploads efficiently.
Supports parallel and sequential processing with progress tracking.
"""

import asyncio
import concurrent.futures
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from werkzeug.datastructures import FileStorage

from utils.logger import logger


class BatchProcessingService:
    """Service for batch processing multiple submissions with OCR support."""

    def __init__(self, parse_function=None, ocr_service=None, max_workers=3, **kwargs):
        """
        Initialize batch processing service.

        Args:
            parse_function: Function to parse individual submissions
            ocr_service: OCR service for image processing
            max_workers: Maximum number of parallel workers
            **kwargs: Additional arguments for backward compatibility
        """
        self.parse_function = parse_function
        self.ocr_service = ocr_service
        self.max_workers = max_workers
        
        # Handle additional arguments for backward compatibility
        for key, value in kwargs.items():
            setattr(self, key, value)

    def process_files_batch(
        self,
        files: List[FileStorage],
        temp_dir: str,
        parallel: bool = True,
        batch_size: int = 5,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process multiple files in batches.
        
        Args:
            files: List of uploaded files
            temp_dir: Temporary directory for file storage
            parallel: Whether to process files in parallel
            batch_size: Number of files to process simultaneously
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Starting batch processing of {len(files)} files")
        logger.info(f"Mode: {'Parallel' if parallel else 'Sequential'}, Batch size: {batch_size}")
        logger.info(f"Parse function available: {self.parse_function is not None}")

        results = {
            'successful': [],
            'failed': [],
            'total_files': len(files),
            'processed_count': 0,
            'start_time': datetime.now(),
            'end_time': None
        }

        try:
            if parallel:
                results = self._process_parallel(files, temp_dir, batch_size, progress_callback, results)
            else:
                results = self._process_sequential(files, temp_dir, progress_callback, results)

        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            results['error'] = str(e)
        finally:
            results['end_time'] = datetime.now()
            duration = (results['end_time'] - results['start_time']).total_seconds()
            logger.info(f"Batch processing completed in {duration:.2f} seconds")
            logger.info(f"Results: {len(results['successful'])} successful, {len(results['failed'])} failed")

        return results

    def _process_parallel(
        self,
        files: List[FileStorage],
        temp_dir: str,
        batch_size: int,
        progress_callback: Optional[callable],
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process files in parallel batches."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Process files in batches
            for i in range(0, len(files), batch_size):
                batch = files[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}: files {i+1}-{min(i+batch_size, len(files))}")

                # Submit batch to thread pool
                future_to_file = {
                    executor.submit(self._process_single_file, file, temp_dir, i + j): (file, i + j)
                    for j, file in enumerate(batch)
                }

                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_file):
                    file, index = future_to_file[future]
                    try:
                        result = future.result()
                        if result['success']:
                            results['successful'].append(result)
                        else:
                            results['failed'].append(result)
                    except Exception as e:
                        logger.error(f"Error processing file {file.filename}: {str(e)}")
                        results['failed'].append({
                            'filename': file.filename,
                            'index': index,
                            'success': False,
                            'error': str(e)
                        })

                    results['processed_count'] += 1

                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(results['processed_count'], len(files), file.filename)

        return results

    def _process_sequential(
        self,
        files: List[FileStorage],
        temp_dir: str,
        progress_callback: Optional[callable],
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process files sequentially."""
        for i, file in enumerate(files):
            logger.info(f"Processing file {i+1}/{len(files)}: {file.filename}")

            try:
                result = self._process_single_file(file, temp_dir, i)
                if result['success']:
                    results['successful'].append(result)
                else:
                    results['failed'].append(result)
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                results['failed'].append({
                    'filename': file.filename,
                    'index': i,
                    'success': False,
                    'error': str(e)
                })

            results['processed_count'] += 1

            # Call progress callback if provided
            if progress_callback:
                progress_callback(results['processed_count'], len(files), file.filename)

        return results

    def _process_single_file(self, file: FileStorage, temp_dir: str, index: int) -> Dict[str, Any]:
        """
        Process a single file.
        
        Args:
            file: The uploaded file
            temp_dir: Temporary directory
            index: File index in batch
            
        Returns:
            Processing result dictionary
        """
        result = {
            'filename': file.filename,
            'index': index,
            'success': False,
            'submission_id': None,
            'answers': {},
            'raw_text': '',
            'error': None,
            'processing_time': None
        }

        start_time = datetime.now()

        try:
            # Generate unique filename
            filename = f"submission_{uuid.uuid4().hex}_{file.filename}"
            file_path = os.path.join(temp_dir, filename)

            # Save file
            file.save(file_path)
            logger.info(f"Saved file: {file_path}")

            # Determine if file needs OCR processing
            file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            is_image = file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp']

            # Process file with OCR if needed
            if is_image and self.ocr_service:
                logger.info(f"Processing image file with OCR: {file.filename}")
                try:
                    # Use OCR service to extract text from image
                    raw_text = self.ocr_service.extract_text_from_image(file_path)
                    logger.info(f"OCR extracted {len(raw_text)} characters from {file.filename}")

                    result.update({
                        'success': True,
                        'answers': {'raw_content': raw_text},
                        'raw_text': raw_text,
                        'error': None,
                        'submission_id': f"sub_{uuid.uuid4().hex[:8]}",
                        'file_path': file_path,
                        'processing_method': 'ocr'
                    })
                    logger.info(f"Successfully processed image {file.filename} with OCR")

                except Exception as ocr_error:
                    logger.error(f"OCR processing failed for {file.filename}: {str(ocr_error)}")
                    result.update({
                        'success': False,
                        'error': f"OCR processing failed: {str(ocr_error)}",
                        'processing_method': 'ocr_failed'
                    })

            # Process file with parse function if available
            elif self.parse_function:
                logger.debug(f"Calling parse function: {self.parse_function.__name__}")
                try:
                    answers, raw_text, error = self.parse_function(file_path)
                    logger.debug(f"Parse results: {len(answers) if answers else 0} answers, {len(raw_text) if raw_text else 0} chars")
                except Exception as parse_error:
                    logger.error(f"Parse function failed: {str(parse_error)}")
                    answers, raw_text, error = {}, '', str(parse_error)

                result.update({
                    'success': error is None,
                    'answers': answers or {},
                    'raw_text': raw_text or '',
                    'error': error,
                    'submission_id': f"sub_{uuid.uuid4().hex[:8]}",
                    'file_path': file_path,
                    'processing_method': 'parse_function'
                })

                if error:
                    logger.warning(f"Processing error for {file.filename}: {error}")
                else:
                    logger.info(f"Successfully processed {file.filename}")
            else:
                # No processing available, just save the file
                logger.warning("No processing method available - file saved only")
                result.update({
                    'success': True,
                    'submission_id': f"sub_{uuid.uuid4().hex[:8]}",
                    'file_path': file_path,
                    'processing_method': 'file_only'
                })
                logger.info(f"File saved successfully: {file.filename}")

        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")
            result['error'] = str(e)

        finally:
            end_time = datetime.now()
            result['processing_time'] = (end_time - start_time).total_seconds()
            logger.debug(f"File processing completed in {result['processing_time']:.2f} seconds")

        return result

    def cleanup_temp_files(self, results: Dict[str, Any]) -> None:
        """Clean up temporary files after processing."""
        logger.info("Cleaning up temporary files...")
        
        cleanup_count = 0
        for result_list in [results.get('successful', []), results.get('failed', [])]:
            for result in result_list:
                file_path = result.get('file_path')
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        cleanup_count += 1
                    except OSError as e:
                        logger.warning(f"Could not remove temporary file {file_path}: {str(e)}")

        logger.info(f"Cleaned up {cleanup_count} temporary files")

    def get_processing_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of processing results."""
        successful_count = len(results.get('successful', []))
        failed_count = len(results.get('failed', []))
        total_count = results.get('total_files', 0)
        
        duration = 0
        if results.get('start_time') and results.get('end_time'):
            duration = (results['end_time'] - results['start_time']).total_seconds()

        return {
            'total_files': total_count,
            'successful': successful_count,
            'failed': failed_count,
            'success_rate': (successful_count / total_count * 100) if total_count > 0 else 0,
            'processing_time': duration,
            'average_time_per_file': duration / total_count if total_count > 0 else 0,
            'failed_files': [r.get('filename') for r in results.get('failed', [])],
            'errors': [r.get('error') for r in results.get('failed', []) if r.get('error')]
        }
