"""Document models for LLM training system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import hashlib


class DocumentType(Enum):
    """Supported document types."""
    PDF = "pdf"
    TXT = "txt"
    DOCX = "docx"
    JSON = "json"


class DocumentStatus(Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass
class DocumentMetadata:
    """Document metadata information."""
    word_count: int = 0
    character_count: int = 0
    language: Optional[str] = None
    encoding: Optional[str] = None
    page_count: Optional[int] = None
    file_size: int = 0
    checksum: Optional[str] = None
    upload_date: datetime = field(default_factory=datetime.utcnow)
    processed_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "word_count": self.word_count,
            "character_count": self.character_count,
            "language": self.language,
            "encoding": self.encoding,
            "page_count": self.page_count,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "upload_date": self.upload_date.isoformat(),
            "processed_date": self.processed_date.isoformat() if self.processed_date else None
        }


@dataclass
class ProcessedDocument:
    """Processed document with extracted content."""
    id: str
    name: str
    original_name: str
    document_type: DocumentType
    content: str
    status: DocumentStatus
    metadata: DocumentMetadata
    datasets: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "original_name": self.original_name,
            "document_type": self.document_type.value,
            "content": self.content,
            "status": self.status.value,
            "metadata": self.metadata.to_dict(),
            "datasets": self.datasets,
            "error_message": self.error_message
        }
    
    @classmethod
    def create_from_file(cls, file_id: str, filename: str, content: str, 
                        document_type: DocumentType, file_size: int) -> 'ProcessedDocument':
        """Create a processed document from file data."""
        # Calculate content statistics
        word_count = len(content.split()) if content else 0
        character_count = len(content) if content else 0
        
        # Generate checksum
        checksum = hashlib.md5(content.encode('utf-8')).hexdigest() if content else None
        
        metadata = DocumentMetadata(
            word_count=word_count,
            character_count=character_count,
            file_size=file_size,
            checksum=checksum
        )
        
        return cls(
            id=file_id,
            name=filename,
            original_name=filename,
            document_type=document_type,
            content=content,
            status=DocumentStatus.PROCESSED,
            metadata=metadata
        )


@dataclass
class Dataset:
    """Document dataset for training organization."""
    id: str
    name: str
    description: Optional[str] = None
    document_ids: List[str] = field(default_factory=list)
    created_date: datetime = field(default_factory=datetime.utcnow)
    updated_date: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dataset to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "document_ids": self.document_ids,
            "document_count": len(self.document_ids),
            "created_date": self.created_date.isoformat(),
            "updated_date": self.updated_date.isoformat()
        }
    
    def add_document(self, document_id: str) -> None:
        """Add a document to the dataset."""
        if document_id not in self.document_ids:
            self.document_ids.append(document_id)
            self.updated_date = datetime.utcnow()
    
    def remove_document(self, document_id: str) -> None:
        """Remove a document from the dataset."""
        if document_id in self.document_ids:
            self.document_ids.remove(document_id)
            self.updated_date = datetime.utcnow()


@dataclass
class DocumentProcessingResult:
    """Result of document processing operation."""
    success: bool
    document: Optional[ProcessedDocument] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "document": self.document.to_dict() if self.document else None,
            "error_message": self.error_message,
            "warnings": self.warnings
        }
    
    @classmethod
    def success_result(cls, document: ProcessedDocument, warnings: List[str] = None) -> 'DocumentProcessingResult':
        """Create a successful processing result."""
        return cls(
            success=True,
            document=document,
            warnings=warnings or []
        )
    
    @classmethod
    def error_result(cls, error_message: str, warnings: List[str] = None) -> 'DocumentProcessingResult':
        """Create an error processing result."""
        return cls(
            success=False,
            error_message=error_message,
            warnings=warnings or []
        )


@dataclass
class FileUpload:
    """File upload information."""
    filename: str
    content: bytes
    content_type: str
    size: int
    
    def get_file_extension(self) -> str:
        """Get file extension."""
        return self.filename.lower().split('.')[-1] if '.' in self.filename else ''
    
    def get_document_type(self) -> Optional[DocumentType]:
        """Get document type from file extension."""
        extension = self.get_file_extension()
        type_mapping = {
            'pdf': DocumentType.PDF,
            'txt': DocumentType.TXT,
            'docx': DocumentType.DOCX,
            'json': DocumentType.JSON
        }
        return type_mapping.get(extension)