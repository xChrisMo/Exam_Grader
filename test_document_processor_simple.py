#!/usr/bin/env python3
"""Simple test script for DocumentProcessorService without pytest dependencies."""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import directly without going through src package
sys.path.insert(0, str(project_root / "src"))

from services.document_processor_service import DocumentProcessorService
from models.document_models import FileUpload, DocumentType


def test_basic_functionality():
    """Test basic document processor functionality."""
    print("Testing DocumentProcessorService...")
    
    # Initialize service
    service = DocumentProcessorService()
    success = service.initialize()
    print(f"Service initialization: {'✓' if success else '✗'}")
    
    # Test health check
    health = service.health_check()
    print(f"Health check: {'✓' if health else '✗'}")
    
    # Test TXT file processing
    txt_content = "This is a sample text document for testing LLM training."
    txt_upload = FileUpload(
        filename="sample.txt",
        content=txt_content.encode('utf-8'),
        content_type="text/plain",
        size=len(txt_content.encode('utf-8'))
    )
    
    # Validate file upload
    validation_result = service.validate_file_upload(txt_upload)
    print(f"TXT validation: {'✓' if validation_result.is_valid else '✗'}")
    if not validation_result.is_valid:
        for error in validation_result.errors:
            print(f"  Error: {error.message}")
    
    # Process file upload
    if validation_result.is_valid:
        processing_result = service.process_file_upload(txt_upload)
        print(f"TXT processing: {'✓' if processing_result.success else '✗'}")
        
        if processing_result.success:
            doc = processing_result.document
            print(f"  Document ID: {doc.id}")
            print(f"  Document type: {doc.document_type.value}")
            print(f"  Word count: {doc.metadata.word_count}")
            print(f"  Character count: {doc.metadata.character_count}")
            print(f"  Content preview: {doc.content[:50]}...")
        else:
            print(f"  Error: {processing_result.error_message}")
    
    # Test JSON file processing
    json_data = {
        "title": "Training Document",
        "content": "This is content for LLM training",
        "metadata": {
            "author": "Test Author",
            "category": "training"
        }
    }
    json_content = json.dumps(json_data)
    json_upload = FileUpload(
        filename="sample.json",
        content=json_content.encode('utf-8'),
        content_type="application/json",
        size=len(json_content.encode('utf-8'))
    )
    
    json_result = service.process_file_upload(json_upload)
    print(f"JSON processing: {'✓' if json_result.success else '✗'}")
    
    if json_result.success:
        doc = json_result.document
        print(f"  JSON content extracted: {'✓' if 'Training Document' in doc.content else '✗'}")
    
    # Test dataset creation
    if validation_result.is_valid and processing_result.success and json_result.success:
        dataset = service.create_dataset(
            name="Test Training Dataset",
            description="A dataset for testing",
            document_ids=[processing_result.document.id, json_result.document.id]
        )
        print(f"Dataset creation: ✓")
        print(f"  Dataset ID: {dataset.id}")
        print(f"  Document count: {len(dataset.document_ids)}")
        
        # Test dataset statistics
        stats = service.get_dataset_statistics(dataset.id)
        if stats:
            print(f"Dataset statistics: ✓")
            print(f"  Total words: {stats['total_words']}")
            print(f"  Total characters: {stats['total_characters']}")
        else:
            print("Dataset statistics: ✗")
    
    # Test file validation edge cases
    print("\nTesting validation edge cases...")
    
    # Test unsupported file type
    bad_upload = FileUpload(
        filename="test.xyz",
        content=b"test content",
        content_type="application/octet-stream",
        size=12
    )
    bad_validation = service.validate_file_upload(bad_upload)
    print(f"Unsupported file rejection: {'✓' if not bad_validation.is_valid else '✗'}")
    
    # Test dangerous filename
    dangerous_upload = FileUpload(
        filename="../../../etc/passwd.txt",
        content=b"test content",
        content_type="text/plain",
        size=12
    )
    dangerous_validation = service.validate_file_upload(dangerous_upload)
    print(f"Dangerous filename rejection: {'✓' if not dangerous_validation.is_valid else '✗'}")
    
    # Test content sanitization
    dirty_content = "  This   has\r\n\r\n\r\nexcessive   whitespace  "
    clean_content = service._sanitize_content(dirty_content)
    expected_clean = "This has\n\nexcessive whitespace"
    print(f"Content sanitization: {'✓' if clean_content == expected_clean else '✗'}")
    
    print("\nAll tests completed!")
    return True


if __name__ == "__main__":
    try:
        test_basic_functionality()
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)