"""
Integration tests for the complete processing pipeline

Tests the integration between all processing system components
including error handling, fallback mechanisms, caching, and monitoring.
"""

import pytest
import tempfile
import os
import time
from unittest.mock import Mock, patch
from pathlib import Path

from src.services.core_service import core_service
from src.services.consolidated_llm_service import ConsolidatedLLMService
from src.services.file_processing_service import FileProcessingService
from src.services.processing_error_handler import processing_error_handler, ErrorContext
from src.services.fallback_manager import fallback_manager
from src.services.retry_manager import retry_manager
from src.services.cache_manager import cache_manager
from src.services.performance_monitor import performance_monitor
from src.database.models import db, MarkingGuide, Submission, GradingResult

class TestProcessingPipelineIntegration:
    """Integration tests for the complete processing pipeline"""
    
    @pytest.fixture
    def temp_files(self):
        """Create temporary files for testing"""
        files = {}
        
        # Create a test marking guide file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            guide_content = """
            Question 1: What is the capital of France? (10 points)
            Answer: Paris
            
            Question 2: Explain photosynthesis. (15 points)
            Answer: Photosynthesis is the process by which plants convert sunlight into energy...
            
            Question 3: Calculate 2 + 2. (5 points)
            Answer: 4
            """
            f.write(guide_content)
            files['guide'] = f.name
        
        # Create a test submission file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            submission_content = """
            Student Name: John Doe
            
            Answer 1: The capital of France is Paris.
            
            Answer 2: Photosynthesis is when plants use sunlight to make food. 
            They take in carbon dioxide and water and produce glucose and oxygen.
            
            Answer 3: 2 + 2 = 4
            """
            f.write(submission_content)
            files['submission'] = f.name
        
        yield files
        
        # Cleanup
        for file_path in files.values():
            try:
                os.unlink(file_path)
            except OSError:
                pass
    
    def test_file_processing_pipeline(self, temp_files):
        """Test the complete file processing pipeline"""
        file_service = FileProcessingService()
        
        # Process the guide file
        guide_info = {
            'name': 'test_guide.txt',
            'size': os.path.getsize(temp_files['guide']),
            'type': 'txt',
            'user_id': 'test_user'
        }
        
        guide_result = file_service.process_file_with_fallback(
            temp_files['guide'], guide_info
        )
        
        assert guide_result['success'] is True
        assert guide_result['word_count'] > 0
        assert guide_result['content_quality_score'] > 0
        assert 'Question 1' in guide_result['text_content']
        assert 'Question 2' in guide_result['text_content']
        
        # Process the submission file
        submission_info = {
            'name': 'test_submission.txt',
            'size': os.path.getsize(temp_files['submission']),
            'type': 'txt',
            'user_id': 'test_user'
        }
        
        submission_result = file_service.process_file_with_fallback(
            temp_files['submission'], submission_info
        )
        
        assert submission_result['success'] is True
        assert submission_result['word_count'] > 0
        assert 'John Doe' in submission_result['text_content']
        assert 'Answer 1' in submission_result['text_content']
    
    def test_error_handling_in_pipeline(self, temp_files):
        """Test error handling throughout the processing pipeline"""
        file_service = FileProcessingService()
        
        # Test with non-existent file
        file_info = {'name': 'nonexistent.txt', 'size': 0, 'type': 'txt'}
        result = file_service.process_file_with_fallback('/nonexistent/file.txt', file_info)
        
        assert result['success'] is False
        assert len(result['validation_errors']) > 0
        assert result['fallback_used'] is True
        
        # Test with corrupted file (empty file)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            empty_file = f.name
        
        try:
            empty_info = {'name': 'empty.txt', 'size': 0, 'type': 'txt'}
            empty_result = file_service.process_file_with_fallback(empty_file, empty_info)
            
            assert empty_result['success'] is False
            assert empty_result['validation_status'] in ['failed', 'invalid']
        finally:
            os.unlink(empty_file)
    
    def test_caching_in_pipeline(self, temp_files):
        """Test caching behavior in the processing pipeline"""
        file_service = FileProcessingService()
        
        file_info = {
            'name': 'cached_test.txt',
            'size': os.path.getsize(temp_files['guide']),
            'type': 'txt'
        }
        
        # First processing - should cache result
        start_time = time.time()
        result1 = file_service.process_file_with_fallback(temp_files['guide'], file_info)
        first_duration = time.time() - start_time
        
        assert result1['success'] is True
        
        # Second processing - should be faster due to caching
        start_time = time.time()
        result2 = file_service.process_file_with_fallback(temp_files['guide'], file_info)
        second_duration = time.time() - start_time
        
        assert result2['success'] is True
        assert result1['text_content'] == result2['text_content']
        
        # Check cache statistics
        cache_stats = cache_manager.get_stats()
        assert cache_stats['total_hits'] > 0 or cache_stats['total_entries'] > 0
    
    def test_performance_monitoring_integration(self, temp_files):
        """Test performance monitoring throughout the pipeline"""
        file_service = FileProcessingService()
        
        # Clear previous metrics
        performance_monitor.clear_metrics()
        
        file_info = {
            'name': 'perf_test.txt',
            'size': os.path.getsize(temp_files['guide']),
            'type': 'txt'
        }
        
        result = file_service.process_file_with_fallback(temp_files['guide'], file_info)
        
        assert result['success'] is True
        
        # Check that performance metrics were collected
        summary = performance_monitor.get_performance_summary()
        assert summary['total_operations'] > 0
        
        all_stats = performance_monitor.get_all_operation_stats()
        assert len(all_stats) > 0
    
    @patch('src.services.consolidated_llm_service.ConsolidatedLLMService')
    def test_llm_service_integration(self, mock_llm_service, temp_files):
        """Test LLM service integration with error handling"""
        # Mock LLM service responses
        mock_instance = Mock()
        mock_instance.is_available.return_value = True
        mock_instance.compare_answers.return_value = {
            "overall_grade": {"score": 85, "feedback": "Good answer"},
            "criteria_scores": {"accuracy": 90, "completeness": 80, "understanding": 85, "clarity": 85},
            "strengths": ["Correct answer", "Clear explanation"],
            "areas_for_improvement": ["Could provide more detail"]
        }
        mock_llm_service.return_value = mock_instance
        
        # Test LLM processing with fallback
        llm_service = ConsolidatedLLMService()
        
        result = llm_service.compare_answers(
            "What is the capital of France?",
            "Paris",
            "The capital of France is Paris."
        )
        
        assert result['overall_grade']['score'] == 85
        assert 'strengths' in result
        assert 'areas_for_improvement' in result
    
    def test_fallback_mechanisms_integration(self, temp_files):
        """Test fallback mechanisms across the pipeline"""
        file_service = FileProcessingService()
        
        # Test with unsupported file type
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
            f.write("Content in unsupported format")
            unsupported_file = f.name
        
        try:
            file_info = {
                'name': 'unsupported.xyz',
                'size': os.path.getsize(unsupported_file),
                'type': 'xyz'
            }
            
            result = file_service.process_file_with_fallback(unsupported_file, file_info)
            
            # Should succeed using fallback processor
            assert result['success'] is True
            assert result['fallback_used'] is True
            assert result['extraction_method'] in ['fallback_processor', 'fallback']
            assert 'Content in unsupported format' in result['text_content']
            
        finally:
            os.unlink(unsupported_file)
    
    def test_retry_mechanisms_integration(self):
        """Test retry mechanisms in the pipeline"""
        # Test retry manager with simulated failures
        attempt_count = 0
        
        def unreliable_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError(f"Attempt {attempt_count} failed")
            return f"Success on attempt {attempt_count}"
        
        error_context = ErrorContext(
            operation="test_retry",
            service="test_service",
            timestamp=time.time(),
            request_id="test_request"
        )
        
        result = retry_manager.execute_with_retry(
            unreliable_function, "test_retry", processing_error_handler, error_context
        )
        
        assert result == "Success on attempt 3"
        assert attempt_count == 3
        
        # Check retry statistics
        retry_stats = retry_manager.get_retry_stats()
        assert "test_retry" in retry_stats
        assert retry_stats["test_retry"]["success_rate"] == 100.0
    
    def test_comprehensive_error_scenarios(self, temp_files):
        """Test comprehensive error scenarios across the pipeline"""
        file_service = FileProcessingService()
        
        # Scenario 1: File processing with multiple fallbacks
        with patch.object(file_service, '_extract_primary', side_effect=ImportError("Library not found")):
            with patch.object(file_service, '_extract_secondary', side_effect=TimeoutError("Processing timeout")):
                
                file_info = {'name': 'error_test.txt', 'size': 100, 'type': 'txt'}
                result = file_service.process_file_with_fallback(temp_files['guide'], file_info)
                
                # Should succeed with fallback method
                assert result['success'] is True
                assert result['fallback_used'] is True
                assert len(result['processing_attempts']) >= 3
        
        # Scenario 2: Complete processing failure
        with patch.object(file_service, '_extract_primary', side_effect=Exception("Primary failed")):
            with patch.object(file_service, '_extract_secondary', side_effect=Exception("Secondary failed")):
                with patch.object(file_service, '_extract_fallback', side_effect=Exception("Fallback failed")):
                    
                    file_info = {'name': 'total_failure.txt', 'size': 100, 'type': 'txt'}
                    result = file_service.process_file_with_fallback(temp_files['guide'], file_info)
                    
                    assert result['success'] is False
                    assert len(result['validation_errors']) > 0
                    assert result['fallback_used'] is True
    
    def test_quality_assessment_pipeline(self, temp_files):
        """Test quality assessment throughout the pipeline"""
        file_service = FileProcessingService()
        
        # Test with high-quality content
        high_quality_content = """
        This is a well-structured document with multiple paragraphs.
        It contains proper sentences with good grammar and punctuation.
        
        The document demonstrates excellent organization with clear sections.
        Each paragraph flows logically to the next, maintaining coherence.
        
        The vocabulary is diverse and appropriate for the subject matter.
        Technical terms are used correctly and consistently throughout.
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(high_quality_content)
            high_quality_file = f.name
        
        try:
            file_info = {
                'name': 'high_quality.txt',
                'size': len(high_quality_content),
                'type': 'txt'
            }
            
            result = file_service.process_file_with_fallback(high_quality_file, file_info)
            
            assert result['success'] is True
            assert result['content_quality_score'] > 0.6
            assert result['quality_level'] in ['good', 'excellent']
            assert result['validation_status'] in ['valid', 'high_quality']
            
            # Check quality metrics
            quality_metrics = result['quality_metrics']
            assert quality_metrics['word_count'] > 50
            assert quality_metrics['sentence_count'] > 5
            assert quality_metrics['paragraph_count'] > 2
            assert quality_metrics['language_confidence'] > 0.5
            
        finally:
            os.unlink(high_quality_file)
    
    def test_concurrent_processing(self, temp_files):
        """Test concurrent processing scenarios"""
        import threading
        import concurrent.futures
        
        file_service = FileProcessingService()
        results = []
        
        def process_file(file_path, file_info):
            return file_service.process_file_with_fallback(file_path, file_info)
        
        # Process multiple files concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            
            for i in range(5):
                file_info = {
                    'name': f'concurrent_test_{i}.txt',
                    'size': os.path.getsize(temp_files['guide']),
                    'type': 'txt',
                    'thread_id': i
                }
                
                future = executor.submit(process_file, temp_files['guide'], file_info)
                futures.append(future)
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
        
        # Verify all processing succeeded
        assert len(results) == 5
        for result in results:
            assert result['success'] is True
            assert result['word_count'] > 0
        
        # Check that performance monitoring handled concurrent operations
        summary = performance_monitor.get_performance_summary()
        assert summary['total_operations'] > 0

class TestEndToEndProcessing:
    """End-to-end processing tests"""
    
    def test_complete_grading_workflow(self, temp_files):
        """Test complete grading workflow from file to result"""
        # This would typically involve database operations
        # For now, test the processing components
        
        file_service = FileProcessingService()
        
        # Process marking guide
        guide_info = {
            'name': 'marking_guide.txt',
            'size': os.path.getsize(temp_files['guide']),
            'type': 'txt',
            'user_id': 'test_user'
        }
        
        guide_result = file_service.process_file_with_fallback(
            temp_files['guide'], guide_info
        )
        
        # Process student submission
        submission_info = {
            'name': 'student_submission.txt',
            'size': os.path.getsize(temp_files['submission']),
            'type': 'txt',
            'user_id': 'test_user'
        }
        
        submission_result = file_service.process_file_with_fallback(
            temp_files['submission'], submission_info
        )
        
        # Verify both processed successfully
        assert guide_result['success'] is True
        assert submission_result['success'] is True
        
        # Verify content quality
        assert guide_result['content_quality_score'] > 0.3
        assert submission_result['content_quality_score'] > 0.3
        
        # Verify extracted content contains expected elements
        assert 'Question 1' in guide_result['text_content']
        assert 'Answer 1' in submission_result['text_content']
    
    def test_system_resilience(self, temp_files):
        """Test system resilience under various failure conditions"""
        file_service = FileProcessingService()
        
        # Test with various problematic files
        test_cases = [
            ("empty_file", ""),
            ("single_char", "x"),
            ("only_whitespace", "   \n\n   \t\t   "),
            ("binary_artifacts", "Hello\x00\x01\x02World"),
            ("excessive_repetition", "a " * 1000),
        ]
        
        for test_name, content in test_cases:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                test_file = f.name
            
            try:
                file_info = {
                    'name': f'{test_name}.txt',
                    'size': len(content),
                    'type': 'txt'
                }
                
                result = file_service.process_file_with_fallback(test_file, file_info)
                
                # System should handle all cases gracefully
                assert 'success' in result
                assert 'validation_status' in result
                assert 'content_quality_score' in result
                
                # Empty or problematic content should be detected
                if not content.strip():
                    assert result['success'] is False
                    assert result['validation_status'] in ['failed', 'invalid']
                
            finally:
                os.unlink(test_file)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])