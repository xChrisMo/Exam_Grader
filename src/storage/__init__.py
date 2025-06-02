"""
Storage modules for the Exam Grader application.

This package provides storage services for:
- Student submissions
- Marking guides  
- Mapping results
- Grading results
- General results storage
"""

from .base_storage import BaseStorage
from .submission_storage import SubmissionStorage
from .guide_storage import GuideStorage
from .mapping_storage import MappingStorage
from .grading_storage import GradingStorage
from .results_storage import ResultsStorage

__all__ = [
    'BaseStorage',
    'SubmissionStorage', 
    'GuideStorage',
    'MappingStorage',
    'GradingStorage',
    'ResultsStorage'
]
