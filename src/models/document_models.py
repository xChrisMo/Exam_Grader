"""
Document models for the application.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DocumentType(Enum):
    """Document type enumeration."""
    MARKING_GUIDE = "marking_guide"
    SUBMISSION = "submission"
    GENERAL = "general"


class DocumentStatus(Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DocumentMetadata:
    """Document metadata structure."""
    filename: str
    size: int
    mime_type: str
    upload_time: datetime
    user_id: str
    document_type: DocumentType = DocumentType.GENERAL


@dataclass
class ProcessedDocument:
    """Processed document structure."""
    id: str
    metadata: DocumentMetadata
    content: str
    status: DocumentStatus
    processing_time: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class DocumentProcessingResult:
    """Result of document processing."""
    success: bool
    document: Optional[ProcessedDocument] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None


@dataclass
class FileUpload:
    """File upload structure."""
    filename: str
    content: bytes
    mime_type: str
    size: int


@dataclass
class Dataset:
    """Dataset structure."""
    id: str
    name: str
    description: str
    documents: List[ProcessedDocument]
    created_at: datetime
    user_id: str
    metadata: Dict[str, Any]