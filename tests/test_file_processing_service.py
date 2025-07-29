"""
Unit tests for FileProcessingService

Tests the enhanced file processing functionality including
fallback mechanisms, content validation, and quality scoring.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from src.services.file_processing_service import FileProcessingService

class TestFileProcessingService:
    """Test cases for FileProcessingService"""
    
    @pytest.fixture
    def service(self):
        """Create FileProcessingService instance for testing"""
        return FileProcessingService()
    
    @pytest.fixture
    def temp_file(self):
        """Create temporary file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is test content for file processing.\nIt has multiple lines.\nAnd some structure.")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except OSError:
            pass
    
    def test_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert hasattr(service, 'supported_formats')
        assert hasattr(service, 'fallback_methods')
        assert '.txt' in service.supported_formats
        assert '.pdf' in service.supported_formats
        assert '.docx' in service.supported_formats
    
    def test_process_file_with_fallback_success(self, service, temp_file):
        """Test successful file processing with primary method"""
        file_info = {
            'name': 'test.txt',
            'size': 1024,
            'type': 'txt'
        }
        
        result = service.process_file_with_fallback(temp_file, file_info)
        
        assert result['success'] is True
        assert result['text_content'] != ''
        assert result['word_count'] > 0
        assert result['character_count'] > 0
        assert result['extraction_method'] == 'primary'
        assert result['processing_duration_ms'] > 0
        assert result['content_quality_score'] > 0
        assert result['validation_status'] in ['valid', 'high_quality', 'medium_quality']
    
    def test_process_file_with_fallback_empty_file(self, service):
        """Test processing of empty file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            file_info = {'name': 'empty.txt', 'size': 0, 'type': 'txt'}
            result = service.process_file_with_fallback(temp_path, file_info)
            
            assert result['success'] is False
            assert result['validation_status'] == 'invalid'
            assert 'No content extracted' in result['validation_errors']
        finally:
            os.unlink(temp_path)
    
    def test_extract_text_plain_text(self, service, temp_file):
        """Test plain text extraction"""
        result = service._extract_text(temp_file)
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert 'test content' in result.lower()
    
    @patch('src.services.file_processing_service.PyPDF2')
    def test_extract_pdf_success(self, mock_pypdf2, service):
        """Test successful PDF extraction"""
        # Mock PDF reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "PDF content here"
        
        mock_reader = Mock()
        mock_reader.pages = [mock_page]
        
        mock_pypdf2.PdfReader.return_value = mock_reader
        
        with patch('builtins.open', mock_open(read_data=b'fake pdf data')):
            result = service._extract_pdf('test.pdf')
            
            assert result == "PDF content here"
    
    @patch('src.services.file_processing_service.PyPDF2', side_effect=ImportError)
    def test_extract_pdf_import_error(self, mock_pypdf2, service):
        """Test PDF extraction with missing library"""
        with pytest.raises(ImportError, match="PyPDF2 not installed"):
            service._extract_pdf('test.pdf')
    
    @patch('src.services.file_processing_service.docx')
    def test_extract_docx_success(self, mock_docx, service):
        """Test successful DOCX extraction"""
        # Mock document
        mock_paragraph1 = Mock()
        mock_paragraph1.text = "First paragraph"
        mock_paragraph2 = Mock()
        mock_paragraph2.text = "Second paragraph"
        
        mock_doc = Mock()
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
        
        mock_docx.Document.return_value = mock_doc
        
        result = service._extract_docx('test.docx')
        
        assert result == "First paragraph\nSecond paragraph"
    
    def test_extract_markdown(self, service):
        """Test markdown extraction and cleanup"""
        markdown_content = """# Header 1
        
        This is **bold** text and *italic* text.
        
        Here's some `code` and a [link](http://example.com).
        
        ## Header 2
        
        More content here."""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(markdown_content)
            temp_path = f.name
        
        try:
            result = service._extract_markdown(temp_path)
            
            # Check that markdown syntax is cleaned up
            assert '**' not in result
            assert '*' not in result  # Should be cleaned from formatting
            assert '`' not in result
            assert '[link]' in result  # Link text should remain
            assert 'http://example.com' not in result  # URL should be removed
        finally:
            os.unlink(temp_path)
    
    def test_extract_json(self, service):
        """Test JSON text extraction"""
        json_content = {
            "title": "Test Document",
            "content": "This is the main content",
            "metadata": {
                "author": "Test Author",
                "tags": ["test", "example"]
            },
            "sections": [
                {"name": "Introduction", "text": "Intro text"},
                {"name": "Conclusion", "text": "Conclusion text"}
            ]
        }
        
        import json
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f)
            temp_path = f.name
        
        try:
            result = service._extract_json(temp_path)
            
            # Check that text values are extracted
            assert 'Test Document' in result
            assert 'This is the main content' in result
            assert 'Test Author' in result
            assert 'Intro text' in result
            assert 'Conclusion text' in result
        finally:
            os.unlink(temp_path)
    
    def test_clean_extracted_text(self, service):
        """Test text cleaning functionality"""
        dirty_text = """
        
        This    has     excessive    whitespace.

        And multiple newlines.
        
        \x00\x01Some control characters\x7f here.
        """
        
        cleaned = service._clean_extracted_text(dirty_text)
        
        # Check whitespace normalization
        assert '    ' not in cleaned  # Multiple spaces should be reduced
        assert '\n\n\n' not in cleaned  # Multiple newlines should be reduced
        
        # Check control character removal
        assert '\x00' not in cleaned
        assert '\x01' not in cleaned
        assert '\x7f' not in cleaned
    
    def test_validate_extracted_content_good_quality(self, service):
        """Test content validation with good quality content"""
        content = """
        This is a well-structured document with multiple sentences. 
        It contains proper punctuation and formatting. The content is 
        substantial and provides meaningful information. There are 
        multiple paragraphs with good sentence structure.
        
        This second paragraph continues the theme. It maintains good
        quality throughout the document. The vocabulary is diverse
        and the content is coherent.
        """
        
        file_info = {'name': 'test.txt', 'size': len(content)}
        result = service.validate_extracted_content(content, file_info)
        
        assert result['validation_status'] in ['valid', 'high_quality', 'medium_quality']
        assert result['content_quality_score'] > 0.5
        assert len(result['validation_errors']) == 0
    
    def test_validate_extracted_content_poor_quality(self, service):
        """Test content validation with poor quality content"""
        content = "a a a a a"  # Very short, repetitive content
        
        file_info = {'name': 'test.txt', 'size': len(content)}
        result = service.validate_extracted_content(content, file_info)
        
        assert result['validation_status'] == 'low_quality'
        assert result['content_quality_score'] < 0.5
        assert len(result['validation_errors']) > 0
    
    def test_validate_extracted_content_empty(self, service):
        """Test content validation with empty content"""
        content = ""
        
        file_info = {'name': 'test.txt', 'size': 0}
        result = service.validate_extracted_content(content, file_info)
        
        assert result['validation_status'] == 'invalid'
        assert result['content_quality_score'] == 0.0
        assert 'No content extracted' in result['validation_errors']
    
    def test_calculate_coherence_score(self, service):
        """Test coherence score calculation"""
        # Good coherence
        good_content = "This is a sentence. This is another sentence. Here is a third sentence."
        good_score = service._calculate_coherence_score(good_content)
        assert good_score > 15
        
        # Poor coherence (very long sentences)
        poor_content = "This is an extremely long sentence that goes on and on and on and never seems to end and just keeps adding more and more words without any real structure or meaning."
        poor_score = service._calculate_coherence_score(poor_content)
        assert poor_score < good_score
        
        # No sentences
        no_sentences = "just words without punctuation"
        no_score = service._calculate_coherence_score(no_sentences)
        assert no_score == 5.0
    
    def test_calculate_structure_score(self, service):
        """Test structure score calculation"""
        # Well-structured content
        structured_content = """
        Title: Document Title
        
        This is the first paragraph with proper structure.
        
        • First bullet point
        • Second bullet point
        • Third bullet point
        
        1. First numbered item
        2. Second numbered item
        
        This is another paragraph. It has proper capitalization.
        """
        
        score = service._calculate_structure_score(structured_content)
        assert score > 10  # Should get points for various structural elements
        
        # Unstructured content
        unstructured_content = "just plain text without any structure or formatting"
        unstructured_score = service._calculate_structure_score(unstructured_content)
        assert unstructured_score < score
    
    def test_calculate_language_score(self, service):
        """Test language detection score calculation"""
        # English content
        english_content = "The quick brown fox jumps over the lazy dog. This is a test of the English language."
        english_score = service._calculate_language_score(english_content)
        assert english_score > 5
        
        # Non-English or gibberish
        gibberish_content = "xyz abc def ghi jkl mno pqr stu vwx"
        gibberish_score = service._calculate_language_score(gibberish_content)
        assert gibberish_score < english_score
    
    def test_retry_failed_extraction(self, service, temp_file):
        """Test retry mechanism for failed extractions"""
        file_info = {
            'name': 'test.txt',
            'size': 1024,
            'type': 'txt',
            'processing_retries': 1
        }
        
        result = service.retry_failed_extraction('file-id', temp_file, file_info)
        
        assert result['is_retry'] is True
        assert result['retry_attempt'] == 2
        assert 'retry_attempt' in result
    
    def test_calculate_file_hash(self, service, temp_file):
        """Test file hash calculation"""
        hash1 = service.calculate_file_hash(temp_file)
        hash2 = service.calculate_file_hash(temp_file)
        
        # Same file should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64-character hex string
    
    def test_get_supported_formats(self, service):
        """Test getting supported formats"""
        formats = service.get_supported_formats()
        
        assert isinstance(formats, list)
        assert '.txt' in formats
        assert '.pdf' in formats
        assert '.docx' in formats
        assert len(formats) > 5
    
    def test_is_supported_format(self, service):
        """Test format support checking"""
        assert service.is_supported_format('.txt') is True
        assert service.is_supported_format('.pdf') is True
        assert service.is_supported_format('.xyz') is False
        assert service.is_supported_format('.TXT') is True  # Case insensitive
    
    def test_fallback_methods_order(self, service):
        """Test that fallback methods are tried in correct order"""
        # Mock all methods to fail except fallback
        with patch.object(service, '_extract_primary', side_effect=Exception("Primary failed")):
            with patch.object(service, '_extract_secondary', side_effect=Exception("Secondary failed")):
                with patch.object(service, '_extract_fallback', return_value="Fallback success"):
                    
                    result = service.process_file_with_fallback('test.txt', {'name': 'test.txt'})
                    
                    assert result['success'] is True
                    assert result['extraction_method'] == 'fallback'
                    assert result['text_content'] == "Fallback success"
                    assert len(result['processing_attempts']) == 3
    
    def test_processing_attempts_logging(self, service, temp_file):
        """Test that processing attempts are properly logged"""
        file_info = {'name': 'test.txt', 'size': 1024, 'type': 'txt'}
        
        result = service.process_file_with_fallback(temp_file, file_info)
        
        assert 'processing_attempts' in result
        assert len(result['processing_attempts']) >= 1
        
        attempt = result['processing_attempts'][0]
        assert 'method' in attempt
        assert 'success' in attempt
        assert 'duration_ms' in attempt
        assert 'content_length' in attempt

class TestFileProcessingServiceIntegration:
    """Integration tests for FileProcessingService"""
    
    @pytest.fixture
    def service(self):
        """Create FileProcessingService instance for integration testing"""
        return FileProcessingService()
    
    def test_multiple_file_formats(self, service):
        """Test processing multiple file formats"""
        # Create test files of different formats
        test_files = []
        
        # Text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a text file content.")
            test_files.append((f.name, '.txt'))
        
        # Markdown file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Markdown Title\n\nThis is **markdown** content.")
            test_files.append((f.name, '.md'))
        
        try:
            for file_path, ext in test_files:
                file_info = {'name': f'test{ext}', 'size': os.path.getsize(file_path), 'type': ext[1:]}
                result = service.process_file_with_fallback(file_path, file_info)
                
                assert result['success'] is True
                assert result['text_content'] != ''
                assert result['word_count'] > 0
        finally:
            # Cleanup
            for file_path, _ in test_files:
                try:
                    os.unlink(file_path)
                except OSError:
                    pass

if __name__ == '__main__':
    pytest.main([__file__])