"""Unit tests for DocumentProcessorService."""

import pytest
import json
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock

from src.services.document_processor_service import DocumentProcessorService
from src.models.document_models import (
    DocumentType, DocumentStatus, FileUpload, ProcessedDocument, Dataset
)


class TestDocumentProcessorService:
    """Test cases for DocumentProcessorService."""
    
    @pytest.fixture
    def service(self):
        """Create a DocumentProcessorService instance for testing."""
        service = DocumentProcessorService()
        service.initialize()
        return service
    
    @pytest.fixture
    def sample_txt_upload(self):
        """Create a sample TXT file upload."""
        content = "This is a sample text document for testing."
        return FileUpload(
            filename="test.txt",
            content=content.encode('utf-8'),
            content_type="text/plain",
            size=len(content.encode('utf-8'))
        )
    
    @pytest.fixture
    def sample_json_upload(self):
        """Create a sample JSON file upload."""
        data = {
            "title": "Test Document",
            "content": "This is test content",
            "metadata": {
                "author": "Test Author",
                "tags": ["test", "sample"]
            }
        }
        content = json.dumps(data)
        return FileUpload(
            filename="test.json",
            content=content.encode('utf-8'),
            content_type="application/json",
            size=len(content.encode('utf-8'))
        )
    
    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.service_name == "document_processor"
        assert service.is_initialized()
    
    def test_health_check(self, service):
        """Test service health check."""
        assert service.health_check() is True
    
    def test_validate_file_upload_valid_txt(self, service, sample_txt_upload):
        """Test validation of valid TXT file upload."""
        result = service.validate_file_upload(sample_txt_upload)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_file_upload_valid_json(self, service, sample_json_upload):
        """Test validation of valid JSON file upload."""
        result = service.validate_file_upload(sample_json_upload)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_file_upload_too_large(self, service):
        """Test validation of file that's too large."""
        large_content = "x" * (DocumentProcessorService.MAX_FILE_SIZE + 1)
        upload = FileUpload(
            filename="large.txt",
            content=large_content.encode('utf-8'),
            content_type="text/plain",
            size=len(large_content.encode('utf-8'))
        )
        
        result = service.validate_file_upload(upload)
        assert result.is_valid is False
        assert any("exceeds maximum allowed size" in error.message for error in result.errors)
    
    def test_validate_file_upload_unsupported_extension(self, service):
        """Test validation of unsupported file extension."""
        upload = FileUpload(
            filename="test.xyz",
            content=b"test content",
            content_type="application/octet-stream",
            size=12
        )
        
        result = service.validate_file_upload(upload)
        assert result.is_valid is False
        assert any("not supported" in error.message for error in result.errors)
    
    def test_validate_file_upload_dangerous_filename(self, service):
        """Test validation of dangerous filename."""
        upload = FileUpload(
            filename="../../../etc/passwd.txt",
            content=b"test content",
            content_type="text/plain",
            size=12
        )
        
        result = service.validate_file_upload(upload)
        assert result.is_valid is False
        assert any("dangerous characters" in error.message for error in result.errors)
    
    def test_validate_file_upload_empty_filename(self, service):
        """Test validation of empty filename."""
        upload = FileUpload(
            filename="",
            content=b"test content",
            content_type="text/plain",
            size=12
        )
        
        result = service.validate_file_upload(upload)
        assert result.is_valid is False
        assert any("required" in error.message for error in result.errors)
    
    def test_process_txt_file_upload_success(self, service, sample_txt_upload):
        """Test successful processing of TXT file upload."""
        result = service.process_file_upload(sample_txt_upload)
        
        assert result.success is True
        assert result.document is not None
        assert result.document.document_type == DocumentType.TXT
        assert result.document.status == DocumentStatus.PROCESSED
        assert "sample text document" in result.document.content
        assert result.document.metadata.word_count > 0
        assert result.document.metadata.character_count > 0
    
    def test_process_json_file_upload_success(self, service, sample_json_upload):
        """Test successful processing of JSON file upload."""
        result = service.process_file_upload(sample_json_upload)
        
        assert result.success is True
        assert result.document is not None
        assert result.document.document_type == DocumentType.JSON
        assert result.document.status == DocumentStatus.PROCESSED
        assert "Test Document" in result.document.content
        assert "Test Author" in result.document.content
        assert result.document.metadata.word_count > 0
    
    @patch('src.services.document_processor_service.fitz')
    def test_process_pdf_file_upload_success(self, mock_fitz, service):
        """Test successful processing of PDF file upload."""
        # Mock PDF document
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.get_text.return_value = "This is PDF content"
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.open.return_value = mock_doc
        
        upload = FileUpload(
            filename="test.pdf",
            content=b"fake pdf content",
            content_type="application/pdf",
            size=100
        )
        
        result = service.process_file_upload(upload)
        
        assert result.success is True
        assert result.document is not None
        assert result.document.document_type == DocumentType.PDF
        assert "PDF content" in result.document.content
    
    @patch('src.services.document_processor_service.DocxDocument')
    def test_process_docx_file_upload_success(self, mock_docx, service):
        """Test successful processing of DOCX file upload."""
        # Mock DOCX document
        mock_doc = MagicMock()
        mock_paragraph = MagicMock()
        mock_paragraph.text = "This is DOCX content"
        mock_doc.paragraphs = [mock_paragraph]
        mock_docx.return_value = mock_doc
        
        upload = FileUpload(
            filename="test.docx",
            content=b"fake docx content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size=100
        )
        
        result = service.process_file_upload(upload)
        
        assert result.success is True
        assert result.document is not None
        assert result.document.document_type == DocumentType.DOCX
        assert "DOCX content" in result.document.content
    
    def test_process_file_upload_validation_failure(self, service):
        """Test processing with validation failure."""
        upload = FileUpload(
            filename="test.xyz",  # Unsupported extension
            content=b"test content",
            content_type="application/octet-stream",
            size=12
        )
        
        result = service.process_file_upload(upload)
        
        assert result.success is False
        assert result.error_message is not None
        assert "not supported" in result.error_message
    
    def test_process_file_upload_content_too_large(self, service):
        """Test processing with content that's too large after extraction."""
        large_content = "x" * (DocumentProcessorService.MAX_CONTENT_LENGTH + 1)
        upload = FileUpload(
            filename="large.txt",
            content=large_content.encode('utf-8'),
            content_type="text/plain",
            size=len(large_content.encode('utf-8'))
        )
        
        result = service.process_file_upload(upload)
        
        assert result.success is False
        assert "too large" in result.error_message
    
    def test_sanitize_content(self, service):
        """Test content sanitization."""
        dirty_content = "  This   has\r\n\r\n\r\nexcessive   whitespace  \x00\x01  "
        clean_content = service._sanitize_content(dirty_content)
        
        assert clean_content == "This has\n\nexcessive whitespace"
    
    def test_is_dangerous_filename(self, service):
        """Test dangerous filename detection."""
        assert service._is_dangerous_filename("../../../etc/passwd") is True
        assert service._is_dangerous_filename("file<script>") is True
        assert service._is_dangerous_filename("CON.txt") is True
        assert service._is_dangerous_filename("normal_file.txt") is False
    
    def test_document_management(self, service, sample_txt_upload):
        """Test document management operations."""
        # Process a document
        result = service.process_file_upload(sample_txt_upload)
        assert result.success is True
        
        doc_id = result.document.id
        
        # Test get document
        retrieved_doc = service.get_document(doc_id)
        assert retrieved_doc is not None
        assert retrieved_doc.id == doc_id
        
        # Test list documents
        all_docs = service.list_documents()
        assert len(all_docs) == 1
        assert all_docs[0].id == doc_id
        
        # Test delete document
        deleted = service.delete_document(doc_id)
        assert deleted is True
        
        # Verify deletion
        assert service.get_document(doc_id) is None
        assert len(service.list_documents()) == 0
    
    def test_dataset_management(self, service, sample_txt_upload, sample_json_upload):
        """Test dataset management operations."""
        # Process documents
        result1 = service.process_file_upload(sample_txt_upload)
        result2 = service.process_file_upload(sample_json_upload)
        
        doc_id1 = result1.document.id
        doc_id2 = result2.document.id
        
        # Create dataset
        dataset = service.create_dataset(
            name="Test Dataset",
            description="A test dataset",
            document_ids=[doc_id1, doc_id2]
        )
        
        assert dataset.name == "Test Dataset"
        assert len(dataset.document_ids) == 2
        assert doc_id1 in dataset.document_ids
        assert doc_id2 in dataset.document_ids
        
        # Test get dataset
        retrieved_dataset = service.get_dataset(dataset.id)
        assert retrieved_dataset is not None
        assert retrieved_dataset.name == "Test Dataset"
        
        # Test list datasets
        all_datasets = service.list_datasets()
        assert len(all_datasets) == 1
        assert all_datasets[0].id == dataset.id
        
        # Test add document to dataset
        # First create another document
        another_upload = FileUpload(
            filename="another.txt",
            content=b"Another test document",
            content_type="text/plain",
            size=21
        )
        result3 = service.process_file_upload(another_upload)
        doc_id3 = result3.document.id
        
        added = service.add_document_to_dataset(dataset.id, doc_id3)
        assert added is True
        
        updated_dataset = service.get_dataset(dataset.id)
        assert len(updated_dataset.document_ids) == 3
        assert doc_id3 in updated_dataset.document_ids
        
        # Test remove document from dataset
        removed = service.remove_document_from_dataset(dataset.id, doc_id3)
        assert removed is True
        
        updated_dataset = service.get_dataset(dataset.id)
        assert len(updated_dataset.document_ids) == 2
        assert doc_id3 not in updated_dataset.document_ids
        
        # Test dataset statistics
        stats = service.get_dataset_statistics(dataset.id)
        assert stats is not None
        assert stats["document_count"] == 2
        assert stats["total_words"] > 0
        assert stats["total_characters"] > 0
        
        # Test delete dataset
        deleted = service.delete_dataset(dataset.id)
        assert deleted is True
        
        # Verify deletion
        assert service.get_dataset(dataset.id) is None
        assert len(service.list_datasets()) == 0
    
    def test_extract_text_from_dict(self, service):
        """Test text extraction from dictionary."""
        data = {
            "title": "Test Title",
            "content": "Test content",
            "nested": {
                "author": "Test Author",
                "tags": ["tag1", "tag2"]
            }
        }
        
        text = service._extract_text_from_dict(data)
        
        assert "title: Test Title" in text
        assert "content: Test content" in text
        assert "nested.author: Test Author" in text
        assert "nested.tags[0]: tag1" in text
    
    def test_extract_text_from_list(self, service):
        """Test text extraction from list."""
        data = [
            "First item",
            {"key": "value"},
            ["nested", "list"]
        ]
        
        text = service._extract_text_from_list(data)
        
        assert "item_0: First item" in text
        assert "item_1.key: value" in text
        assert "item_2[0]: nested" in text
    
    def test_file_upload_get_document_type(self):
        """Test FileUpload.get_document_type method."""
        upload_txt = FileUpload("test.txt", b"content", "text/plain", 7)
        assert upload_txt.get_document_type() == DocumentType.TXT
        
        upload_pdf = FileUpload("test.pdf", b"content", "application/pdf", 7)
        assert upload_pdf.get_document_type() == DocumentType.PDF
        
        upload_docx = FileUpload("test.docx", b"content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 7)
        assert upload_docx.get_document_type() == DocumentType.DOCX
        
        upload_json = FileUpload("test.json", b"content", "application/json", 7)
        assert upload_json.get_document_type() == DocumentType.JSON
        
        upload_unknown = FileUpload("test.xyz", b"content", "application/octet-stream", 7)
        assert upload_unknown.get_document_type() is None
    
    def test_file_upload_get_file_extension(self):
        """Test FileUpload.get_file_extension method."""
        upload = FileUpload("test.TXT", b"content", "text/plain", 7)
        assert upload.get_file_extension() == "txt"
        
        upload_no_ext = FileUpload("test", b"content", "text/plain", 7)
        assert upload_no_ext.get_file_extension() == ""
    
    def test_processed_document_to_dict(self, service, sample_txt_upload):
        """Test ProcessedDocument.to_dict method."""
        result = service.process_file_upload(sample_txt_upload)
        doc = result.document
        
        doc_dict = doc.to_dict()
        
        assert doc_dict["id"] == doc.id
        assert doc_dict["name"] == doc.name
        assert doc_dict["document_type"] == doc.document_type.value
        assert doc_dict["status"] == doc.status.value
        assert "metadata" in doc_dict
        assert isinstance(doc_dict["metadata"], dict)
    
    def test_dataset_to_dict(self, service):
        """Test Dataset.to_dict method."""
        dataset = service.create_dataset("Test Dataset", "Description")
        dataset_dict = dataset.to_dict()
        
        assert dataset_dict["id"] == dataset.id
        assert dataset_dict["name"] == dataset.name
        assert dataset_dict["description"] == dataset.description
        assert dataset_dict["document_count"] == len(dataset.document_ids)
        assert "created_date" in dataset_dict
        assert "updated_date" in dataset_dict
    
    def test_cleanup(self, service, sample_txt_upload):
        """Test service cleanup."""
        # Add some data
        service.process_file_upload(sample_txt_upload)
        service.create_dataset("Test Dataset")
        
        assert len(service.list_documents()) > 0
        assert len(service.list_datasets()) > 0
        
        # Cleanup
        service.cleanup()
        
        assert len(service.list_documents()) == 0
        assert len(service.list_datasets()) == 0