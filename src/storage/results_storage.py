"""
Storage module for mapping and grading results.
"""

import os
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class ResultsStorage:
    """Storage for mapping and grading results."""

    def __init__(self, base_dir=None):
        """Initialize the storage with a base directory."""
        if base_dir is None:
            # Default to a 'results' directory in the project root
            base_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'temp',
                'results'
            )
        
        self.base_dir = base_dir
        self.mapping_dir = os.path.join(base_dir, 'mappings')
        self.grading_dir = os.path.join(base_dir, 'gradings')
        self.batch_dir = os.path.join(base_dir, 'batches')
        
        # Create directories if they don't exist
        os.makedirs(self.mapping_dir, exist_ok=True)
        os.makedirs(self.grading_dir, exist_ok=True)
        os.makedirs(self.batch_dir, exist_ok=True)
        
        logger.info(f"Results storage initialized at {base_dir}")

    def store_mapping_result(self, mapping_result):
        """
        Store a mapping result and return a reference ID.
        
        Args:
            mapping_result: The mapping result dictionary
            
        Returns:
            str: A unique ID for the stored result
        """
        # Generate a unique ID
        result_id = str(uuid.uuid4())
        
        # Add metadata
        if 'metadata' not in mapping_result:
            mapping_result['metadata'] = {}
        
        mapping_result['metadata']['stored_at'] = datetime.now().isoformat()
        mapping_result['metadata']['result_id'] = result_id
        
        # Save to file
        file_path = os.path.join(self.mapping_dir, f"{result_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(mapping_result, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Stored mapping result with ID {result_id}")
        return result_id

    def get_mapping_result(self, result_id):
        """
        Retrieve a mapping result by its ID.
        
        Args:
            result_id: The unique ID of the result
            
        Returns:
            dict: The mapping result, or None if not found
        """
        file_path = os.path.join(self.mapping_dir, f"{result_id}.json")
        if not os.path.exists(file_path):
            logger.warning(f"Mapping result with ID {result_id} not found")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
            return result
        except Exception as e:
            logger.error(f"Error loading mapping result {result_id}: {str(e)}")
            return None

    def store_grading_result(self, grading_result):
        """
        Store a grading result and return a reference ID.
        
        Args:
            grading_result: The grading result dictionary
            
        Returns:
            str: A unique ID for the stored result
        """
        # Generate a unique ID
        result_id = str(uuid.uuid4())
        
        # Add metadata
        if 'metadata' not in grading_result:
            grading_result['metadata'] = {}
        
        grading_result['metadata']['stored_at'] = datetime.now().isoformat()
        grading_result['metadata']['result_id'] = result_id
        
        # Save to file
        file_path = os.path.join(self.grading_dir, f"{result_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(grading_result, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Stored grading result with ID {result_id}")
        return result_id

    def get_grading_result(self, result_id):
        """
        Retrieve a grading result by its ID.
        
        Args:
            result_id: The unique ID of the result
            
        Returns:
            dict: The grading result, or None if not found
        """
        file_path = os.path.join(self.grading_dir, f"{result_id}.json")
        if not os.path.exists(file_path):
            logger.warning(f"Grading result with ID {result_id} not found")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
            return result
        except Exception as e:
            logger.error(f"Error loading grading result {result_id}: {str(e)}")
            return None

    def store_batch_results(self, batch_type, results):
        """
        Store a batch of results and return a reference ID.
        
        Args:
            batch_type: Type of batch ('mapping' or 'grading')
            results: List of result dictionaries
            
        Returns:
            str: A unique ID for the stored batch
        """
        # Generate a unique ID
        batch_id = str(uuid.uuid4())
        
        # Create a batch metadata object
        batch_data = {
            'batch_id': batch_id,
            'batch_type': batch_type,
            'created_at': datetime.now().isoformat(),
            'count': len(results),
            'results': results
        }
        
        # Save to file
        file_path = os.path.join(self.batch_dir, f"{batch_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(batch_data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Stored batch {batch_type} results with ID {batch_id}")
        return batch_id

    def get_batch_results(self, batch_id):
        """
        Retrieve a batch of results by its ID.
        
        Args:
            batch_id: The unique ID of the batch
            
        Returns:
            dict: The batch data, or None if not found
        """
        file_path = os.path.join(self.batch_dir, f"{batch_id}.json")
        if not os.path.exists(file_path):
            logger.warning(f"Batch results with ID {batch_id} not found")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            return batch_data
        except Exception as e:
            logger.error(f"Error loading batch results {batch_id}: {str(e)}")
            return None

    def clear(self):
        """Clear all stored results."""
        for directory in [self.mapping_dir, self.grading_dir, self.batch_dir]:
            try:
                for file_name in os.listdir(directory):
                    if file_name.endswith('.json'):
                        file_path = os.path.join(directory, file_name)
                        os.unlink(file_path)
                        logger.debug(f"Removed result file: {file_path}")
            except Exception as e:
                logger.error(f"Error clearing directory {directory}: {str(e)}")
        
        logger.info("Cleared all stored results")
