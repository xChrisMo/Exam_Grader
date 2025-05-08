"""
Storage service for grading results.

This module provides functionality to store and retrieve grading results.
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import csv

from utils.logger import logger

class GradingStorage:
    """
    Storage service for grading results.
    
    This class provides methods to:
    - Store grading results
    - Retrieve grading results
    - Export results as CSV
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the grading storage service.
        
        Args:
            storage_dir: Directory to store grading results (default: './results')
        """
        self.storage_dir = storage_dir or os.path.join(os.getcwd(), 'results')
        self.json_dir = os.path.join(self.storage_dir, 'json')
        self.csv_dir = os.path.join(self.storage_dir, 'csv')
        
        # Create directories if they don't exist
        os.makedirs(self.json_dir, exist_ok=True)
        os.makedirs(self.csv_dir, exist_ok=True)
        
        logger.info(f"Grading storage initialized at {self.storage_dir}")
    
    def _generate_key(self, guide_content: str, submission_content: str) -> str:
        """
        Generate a unique key for a guide-submission pair.
        
        Args:
            guide_content: Content of the marking guide
            submission_content: Content of the student submission
            
        Returns:
            str: Unique hash key
        """
        combined = f"{guide_content}:::{submission_content}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def _generate_filename(self, submission_id: str) -> str:
        """
        Generate a filename for a submission.
        
        Args:
            submission_id: ID or name of the submission
            
        Returns:
            str: Generated filename
        """
        # Clean the ID to make it filesystem-friendly
        clean_id = ''.join(c if c.isalnum() or c in '._- ' else '_' for c in submission_id)
        return f"grading_result_{clean_id}.json"
    
    def store_result(
        self, 
        guide_content: str, 
        submission_content: str, 
        submission_id: str,
        result: Dict[str, Any]
    ) -> bool:
        """
        Store a grading result.
        
        Args:
            guide_content: Content of the marking guide
            submission_content: Content of the student submission
            submission_id: ID or name of the submission
            result: Grading result to store
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        try:
            key = self._generate_key(guide_content, submission_content)
            filename = self._generate_filename(submission_id)
            filepath = os.path.join(self.json_dir, filename)
            
            # Add metadata to the result
            result_with_metadata = result.copy()
            result_with_metadata['metadata'] = {
                'key': key,
                'submission_id': submission_id,
                'timestamp': __import__('datetime').datetime.now().isoformat()
            }
            
            # Write result to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result_with_metadata, f, indent=2)
                
            logger.info(f"Stored grading result for {submission_id} at {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store grading result: {str(e)}")
            return False
    
    def get_result(
        self, 
        guide_content: str, 
        submission_content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a stored grading result.
        
        Args:
            guide_content: Content of the marking guide
            submission_content: Content of the student submission
            
        Returns:
            Optional[Dict]: Grading result if found, None otherwise
        """
        try:
            key = self._generate_key(guide_content, submission_content)
            
            # Search for files with matching key in metadata
            for filename in os.listdir(self.json_dir):
                if not filename.endswith('.json'):
                    continue
                    
                filepath = os.path.join(self.json_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('metadata', {}).get('key') == key:
                            logger.info(f"Found cached grading result at {filepath}")
                            return data
                except Exception as e:
                    logger.warning(f"Error reading {filepath}: {str(e)}")
                    continue
            
            logger.info(f"No cached grading result found for key {key[:8]}...")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving grading result: {str(e)}")
            return None
    
    def export_to_csv(self, session_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Export grading results to CSV.
        
        Args:
            session_id: Optional session ID to include in filename
            
        Returns:
            Tuple containing:
            - bool indicating success
            - Path to the CSV file if successful, None otherwise
        """
        try:
            # Generate filename
            timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
            session_suffix = f"_{session_id}" if session_id else ""
            csv_filename = f"grading_results{session_suffix}_{timestamp}.csv"
            csv_path = os.path.join(self.csv_dir, csv_filename)
            
            # Get all JSON files
            json_files = [f for f in os.listdir(self.json_dir) if f.endswith('.json')]
            if not json_files:
                logger.warning("No grading results found to export")
                return False, "No grading results found to export"
            
            # Extract results from JSON files
            results = []
            for filename in json_files:
                filepath = os.path.join(self.json_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # Create a flattened version for CSV
                        flat_data = {
                            'submission_id': data.get('metadata', {}).get('submission_id', 'unknown'),
                            'timestamp': data.get('metadata', {}).get('timestamp', ''),
                            'overall_score': data.get('overall_score', 0),
                            'max_possible_score': data.get('max_possible_score', 0),
                            'percent_score': data.get('percent_score', 0),
                            'assessment_confidence': data.get('assessment_confidence', 'unknown'),
                            'strengths_count': len(data.get('detailed_feedback', {}).get('strengths', [])),
                            'weaknesses_count': len(data.get('detailed_feedback', {}).get('weaknesses', [])),
                            'suggestion_count': len(data.get('detailed_feedback', {}).get('improvement_suggestions', []))
                        }
                        results.append(flat_data)
                except Exception as e:
                    logger.warning(f"Error reading {filepath}: {str(e)}")
                    continue
            
            if not results:
                logger.warning("No valid grading results found to export")
                return False, "No valid grading results found to export"
            
            # Write to CSV
            fieldnames = list(results[0].keys())
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
                
            logger.info(f"Exported {len(results)} grading results to {csv_path}")
            return True, csv_path
            
        except Exception as e:
            error_msg = f"Failed to export grading results to CSV: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_all_results(self) -> List[Dict[str, Any]]:
        """
        Get all stored grading results.
        
        Returns:
            List[Dict]: List of all grading results
        """
        try:
            results = []
            json_files = [f for f in os.listdir(self.json_dir) if f.endswith('.json')]
            
            for filename in json_files:
                filepath = os.path.join(self.json_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        results.append(data)
                except Exception as e:
                    logger.warning(f"Error reading {filepath}: {str(e)}")
                    continue
                    
            logger.info(f"Retrieved {len(results)} grading results")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving all grading results: {str(e)}")
            return []
    
    def clear_all(self) -> bool:
        """
        Clear all stored grading results.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get all JSON files
            json_files = [f for f in os.listdir(self.json_dir) if f.endswith('.json')]
            
            # Delete each file
            for filename in json_files:
                filepath = os.path.join(self.json_dir, filename)
                try:
                    os.remove(filepath)
                    logger.info(f"Deleted grading result file: {filepath}")
                except Exception as e:
                    logger.warning(f"Failed to delete file {filepath}: {str(e)}")
                    
            # Also clear CSV directory
            csv_files = [f for f in os.listdir(self.csv_dir) if f.endswith('.csv')]
            for filename in csv_files:
                filepath = os.path.join(self.csv_dir, filename)
                try:
                    os.remove(filepath)
                    logger.info(f"Deleted CSV file: {filepath}")
                except Exception as e:
                    logger.warning(f"Failed to delete CSV file {filepath}: {str(e)}")
                    
            logger.info(f"Cleared all grading results")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing grading results: {str(e)}")
            return False 