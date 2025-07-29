"""
Tests for enhanced file processing components

This module tests the FileProcessorChain, ExtractionMethodRegistry, 
and ContentValidator components.
"""

import os
import tempfile
import pytest
from pathlib import Path

from src.services.file_processor_chain import file_processor_chain, FileProcessorChain
from src.services.extraction_method_registry import extraction_method_registry, ExtractionMethodRegistry
from src.services.content_validator import content_validator, ContentValidator, ContentQuality, ValidationStatus

class TestFileProcessorChain:
    """Test the FileProcessorChain functionality"""
    
    def test_chain_initialization(self):
        """Test that the chain initializes with default processors"""
        chain = FileProcessorChain()
        assert len(chain.processors) > 0
        
        # Check that we have expected processors
        processor_names = [p.name for p in chain.processors]
        assert 'text_processor' in processor_names
        assert 'pdf_processor' in processor_names
        assert 'docx_processor' in processor_names
        assert 'fallback_processor' in processor_names
    
    def test_text_file_processing(self):
        """Test processing a simple text file"""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_content = "This is a test document with multiple sentences. It contains various words and punctuation."
            f.write(test_content)
            temp_path = f.name
        
        try:
            # Process the file
            result = file_processor_chain.process_file(temp_path)
            
            assert result.success
            assert result.content == test_content
            assert result.method_used == 'text_processor'
            assert result.processing_time > 0
            
        finally:
            os.unlink(temp_path)
    
    def test_unsupported_file_fallback(self):
        """Test that unsupported files fall back to the fallback processor"""
        # Create a temporary file with unusual extension
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
            test_content = "This is content in an unsupported format."
            f.write(test_content)
            temp_path = f.name
        
        try:
            # Process the file
            result = file_processor_chain.process_file(temp_path)
            
            # Should succeed using fallback processor
            assert result.success
            assert result.method_used == 'fallback_processor'
            assert test_content in result.content
            
        finally:
            os.unlink(temp_path)
    
    def test_nonexistent_file(self):
        """Test handling of nonexistent files"""
        result = file_processor_chain.process_file('/nonexistent/file.txt')
        
        assert not result.success
        assert 'File not found' in result.error
    
    def test_chain_metrics(self):
        """Test that chain metrics are collected"""
        metrics = file_processor_chain.get_chain_metrics()
        
        assert 'processors' in metrics
        assert 'total_processors' in metrics
        assert metrics['total_processors'] > 0
        
        # Check processor metrics structure
        for processor_metrics in metrics['processors']:
            assert 'name' in processor_metrics
            assert 'total_attempts' in processor_metrics
            assert 'success_rate' in processor_metrics

class TestExtractionMethodRegistry:
    """Test the ExtractionMethodRegistry functionality"""
    
    def test_registry_initialization(self):
        """Test that the registry initializes with default methods"""
        registry = ExtractionMethodRegistry()
        info = registry.get_all_methods_info()
        
        assert info['total_methods'] > 0
        assert 'methods' in info
        assert 'file_type_mappings' in info
        
        assert '.pdf' in info['file_type_mappings']
        assert '.txt' in info['file_type_mappings']
        assert '.docx' in info['file_type_mappings']
    
    def test_get_methods_for_file_type(self):
        """Test getting methods for specific file types"""
        registry = ExtractionMethodRegistry()
        
        # Test PDF methods
        pdf_methods = registry.get_methods('.pdf')
        assert len(pdf_methods) > 0
        
        # Test text methods
        txt_methods = registry.get_methods('.txt')
        assert len(txt_methods) > 0
        
        # Test unsupported type falls back to wildcard methods
        unknown_methods = registry.get_methods('.unknown')
        assert len(unknown_methods) > 0  # Should have fallback methods
    
    def test_text_extraction(self):
        """Test text extraction using the registry"""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_content = "This is a test document for extraction."
            f.write(test_content)
            temp_path = f.name
        
        try:
            # Extract using registry
            result = extraction_method_registry.extract_with_fallback(temp_path)
            
            assert result.success
            assert result.content == test_content
            assert result.processing_time > 0
            
        finally:
            os.unlink(temp_path)
    
    def test_method_info(self):
        """Test getting information about specific methods"""
        registry = ExtractionMethodRegistry()
        
        method_info = registry.get_method_info('utf8_text_extractor')
        assert method_info is not None
        assert method_info['name'] == 'utf8_text_extractor'
        assert '.txt' in method_info['file_types']
        assert 'dependencies' in method_info
        assert 'is_available' in method_info

class TestContentValidator:
    """Test the ContentValidator functionality"""
    
    def test_validator_initialization(self):
        """Test that the validator initializes correctly"""
        validator = ContentValidator()
        assert validator.min_word_count > 0
        assert validator.min_character_count > 0
        assert len(validator.english_indicators) > 0
    
    def test_valid_content_validation(self):
        """Test validation of good quality content"""
        content = """
        This is a well-structured document with multiple paragraphs.
        It contains proper sentences with good grammar and punctuation.
        
        The document has several paragraphs that demonstrate good structure.
        Each paragraph contains multiple sentences with varied vocabulary.
        
        This content should receive a good quality score because it has:
        - Proper paragraph breaks
        - Good sentence structure
        - Varied vocabulary
        - Appropriate length
        """
        
        result = content_validator.validate_content(content)
        
        assert result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
        assert result.quality in [ContentQuality.GOOD, ContentQuality.EXCELLENT, ContentQuality.FAIR]
        assert result.overall_score > 0.3
        assert result.metrics.word_count > 0
        assert result.metrics.sentence_count > 0
        assert result.metrics.paragraph_count > 0
    
    def test_poor_content_validation(self):
        """Test validation of poor quality content"""
        content = "short"
        
        result = content_validator.validate_content(content)
        
        assert result.status == ValidationStatus.WARNING
        assert result.quality in [ContentQuality.POOR, ContentQuality.INVALID]
        assert result.overall_score < 0.5
        assert len(result.warnings) > 0
    
    def test_empty_content_validation(self):
        """Test validation of empty content"""
        result = content_validator.validate_content("")
        
        assert result.status == ValidationStatus.FAILED
        assert result.quality == ContentQuality.INVALID
        assert result.overall_score == 0.0
        assert len(result.errors) > 0
    
    def test_content_metrics_calculation(self):
        """Test that content metrics are calculated correctly"""
        content = "This is a test. It has two sentences."
        
        result = content_validator.validate_content(content)
        
        assert result.metrics.word_count == 9
        assert result.metrics.sentence_count == 2
        assert result.metrics.character_count == len(content)
        assert result.metrics.unique_words > 0
        assert result.metrics.average_word_length > 0
    
    def test_batch_validation(self):
        """Test batch validation of multiple content items"""
        contents = [
            ("Good quality content with proper structure and length.", {}),
            ("Short", {}),
            ("", {})
        ]
        
        results = content_validator.validate_batch(contents)
        
        assert len(results) == 3
        assert results[0].quality != ContentQuality.INVALID
        assert results[1].quality in [ContentQuality.POOR, ContentQuality.INVALID]
        assert results[2].quality == ContentQuality.INVALID
    
    def test_quality_summary(self):
        """Test quality summary generation"""
        contents = [
            ("Good quality content with proper structure and length.", {}),
            ("Another good quality document with multiple sentences and paragraphs.", {}),
            ("Short", {})
        ]
        
        results = content_validator.validate_batch(contents)
        summary = content_validator.get_quality_summary(results)
        
        assert summary['total_items'] == 3
        assert 'average_score' in summary
        assert 'quality_distribution' in summary
        assert 'status_distribution' in summary

class TestIntegration:
    """Test integration between components"""
    
    def test_full_processing_pipeline(self):
        """Test the complete processing pipeline"""
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_content = """
            This is a comprehensive test document for the file processing system.
            It contains multiple paragraphs with varied content and structure.
            
            The document includes:
            - Multiple sentences per paragraph
            - Proper punctuation and capitalization
            - Varied vocabulary and sentence lengths
            - Good overall structure
            
            This should result in a high-quality assessment from the content validator.
            The file processor chain should handle this text file efficiently.
            """
            f.write(test_content)
            temp_path = f.name
        
        try:
            # Process through the chain
            chain_result = file_processor_chain.process_file(temp_path)
            assert chain_result.success
            
            # Validate the content
            validation_result = content_validator.validate_content(chain_result.content)
            assert validation_result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
            assert validation_result.quality in [ContentQuality.GOOD, ContentQuality.EXCELLENT, ContentQuality.FAIR]
            
            # Test extraction registry as alternative
            extraction_result = extraction_method_registry.extract_with_fallback(temp_path)
            assert extraction_result.success
            assert extraction_result.content == chain_result.content
            
        finally:
            os.unlink(temp_path)

if __name__ == '__main__':
    # Run basic tests
    import logging
    logging.info("Testing FileProcessorChain...")
    chain_test = TestFileProcessorChain()
    chain_test.test_chain_initialization()
    logging.info("✓ Chain initialization test passed")
    
    logging.info("Testing ExtractionMethodRegistry...")
    registry_test = TestExtractionMethodRegistry()
    registry_test.test_registry_initialization()
    logging.info("✓ Registry initialization test passed")
    
    logging.info("Testing ContentValidator...")
    validator_test = TestContentValidator()
    validator_test.test_validator_initialization()
    logging.info("✓ Validator initialization test passed")
    
    logging.info("Testing Integration...")
    integration_test = TestIntegration()
    integration_test.test_full_processing_pipeline()
    logging.info("✓ Integration test passed")
    
    logging.info("All enhanced file processing tests passed! ✅")