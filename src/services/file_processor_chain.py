"""
File Processor Chain - Chain of Responsibility Pattern for File Processing

This module implements a chain of responsibility pattern for file processing,
allowing multiple extraction methods to be tried in sequence with proper
error handling and fallback mechanisms.
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone

from utils.logger import logger
from src.services.processing_error_handler import processing_error_handler, ErrorContext, ErrorCategory
from src.services.fallback_manager import fallback_manager
from src.services.retry_manager import retry_manager

@dataclass
class ProcessingResult:
    """Result of file processing operation"""
    success: bool
    content: str
    metadata: Dict[str, Any]
    processing_time: float
    method_used: str
    error: Optional[str] = None
    fallback_used: bool = False
    retry_count: int = 0

@dataclass
class ProcessorMetrics:
    """Metrics for a file processor"""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    average_processing_time: float = 0.0
    last_used: Optional[datetime] = None

class FileProcessor(ABC):
    """Abstract base class for file processors"""
    
    def __init__(self, name: str, supported_extensions: List[str], priority: int = 0):
        self.name = name
        self.supported_extensions = [ext.lower() for ext in supported_extensions]
        self.priority = priority
        self.metrics = ProcessorMetrics()
        self._next_processor: Optional['FileProcessor'] = None
    
    def set_next(self, processor: 'FileProcessor') -> 'FileProcessor':
        """Set the next processor in the chain"""
        self._next_processor = processor
        return processor
    
    def can_process(self, file_path: str) -> bool:
        """Check if this processor can handle the file"""
        extension = Path(file_path).suffix.lower()
        return extension in self.supported_extensions
    
    def process(self, file_path: str, context: Dict[str, Any]) -> ProcessingResult:
        """Process file with error handling and metrics tracking"""
        start_time = time.time()
        
        try:
            # Update metrics
            self.metrics.total_attempts += 1
            self.metrics.last_used = datetime.now(timezone.utc)
            
            if not self.can_process(file_path):
                if self._next_processor:
                    return self._next_processor.process(file_path, context)
                else:
                    return ProcessingResult(
                        success=False,
                        content="",
                        metadata={},
                        processing_time=time.time() - start_time,
                        method_used=self.name,
                        error=f"No processor available for file: {file_path}"
                    )
            
            # Attempt to process the file
            logger.info(f"Processing {file_path} with {self.name}")
            content, metadata = self._extract_content(file_path, context)
            
            processing_time = time.time() - start_time
            
            if content and content.strip():
                # Success
                self.metrics.successful_attempts += 1
                self._update_average_processing_time(processing_time)
                
                return ProcessingResult(
                    success=True,
                    content=content,
                    metadata=metadata,
                    processing_time=processing_time,
                    method_used=self.name
                )
            else:
                # No content extracted, try next processor
                self.metrics.failed_attempts += 1
                if self._next_processor:
                    return self._next_processor.process(file_path, context)
                else:
                    return ProcessingResult(
                        success=False,
                        content="",
                        metadata=metadata,
                        processing_time=processing_time,
                        method_used=self.name,
                        error="No content extracted"
                    )
                    
        except Exception as e:
            self.metrics.failed_attempts += 1
            processing_time = time.time() - start_time
            
            # Log error with context
            error_context = ErrorContext(
                operation=f"file_processing_{self.name}",
                service="file_processor_chain",
                timestamp=datetime.now(timezone.utc),
                user_id=context.get('user_id'),
                request_id=context.get('request_id', 'unknown'),
                additional_data={
                    'file_path': file_path,
                    'processor': self.name,
                    'error': str(e)
                }
            )
            
            processing_error_handler.handle_error(e, error_context)
            
            # Try next processor in chain
            if self._next_processor:
                logger.warning(f"{self.name} failed for {file_path}, trying next processor: {e}")
                return self._next_processor.process(file_path, context)
            else:
                return ProcessingResult(
                    success=False,
                    content="",
                    metadata={},
                    processing_time=processing_time,
                    method_used=self.name,
                    error=str(e)
                )
    
    def _update_average_processing_time(self, new_time: float):
        """Update average processing time"""
        if self.metrics.successful_attempts == 1:
            self.metrics.average_processing_time = new_time
        else:
            # Running average
            total_time = self.metrics.average_processing_time * (self.metrics.successful_attempts - 1)
            self.metrics.average_processing_time = (total_time + new_time) / self.metrics.successful_attempts
    
    @abstractmethod
    def _extract_content(self, file_path: str, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Extract content from file - to be implemented by subclasses"""
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processor metrics"""
        success_rate = 0.0
        if self.metrics.total_attempts > 0:
            success_rate = self.metrics.successful_attempts / self.metrics.total_attempts
        
        return {
            'name': self.name,
            'total_attempts': self.metrics.total_attempts,
            'successful_attempts': self.metrics.successful_attempts,
            'failed_attempts': self.metrics.failed_attempts,
            'success_rate': success_rate,
            'average_processing_time': self.metrics.average_processing_time,
            'last_used': self.metrics.last_used.isoformat() if self.metrics.last_used else None,
            'supported_extensions': self.supported_extensions
        }

class TextFileProcessor(FileProcessor):
    """Processor for plain text files"""
    
    def __init__(self):
        super().__init__(
            name="text_processor",
            supported_extensions=['.txt', '.md', '.markdown', '.csv', '.log'],
            priority=1
        )
    
    def _extract_content(self, file_path: str, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Extract content from text files"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                
                metadata = {
                    'encoding_used': encoding,
                    'file_size': os.path.getsize(file_path),
                    'line_count': len(content.split('\n'))
                }
                
                return content, metadata
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"Error reading {file_path} with encoding {encoding}: {e}")
                continue
        
        raise ValueError(f"Could not read text file {file_path} with any encoding")

class PDFProcessor(FileProcessor):
    """Processor for PDF files with multiple extraction methods"""
    
    def __init__(self):
        super().__init__(
            name="pdf_processor",
            supported_extensions=['.pdf'],
            priority=2
        )
    
    def _extract_content(self, file_path: str, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Extract content from PDF files using multiple methods"""
        methods = [
            ('PyPDF2', self._extract_with_pypdf2),
            ('pdfplumber', self._extract_with_pdfplumber),
            ('pdfminer', self._extract_with_pdfminer)
        ]
        
        last_error = None
        for method_name, method_func in methods:
            try:
                content, metadata = method_func(file_path)
                if content and content.strip():
                    metadata['extraction_method'] = method_name
                    return content, metadata
            except ImportError as e:
                logger.debug(f"PDF extraction method {method_name} not available: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"PDF extraction with {method_name} failed: {e}")
                last_error = e
                continue
        
        raise Exception(f"All PDF extraction methods failed. Last error: {last_error}")
    
    def _extract_with_pypdf2(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract using PyPDF2"""
        import PyPDF2
        
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text_parts = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num} from {file_path}: {e}")
                    continue
            
            content = '\n'.join(text_parts)
            metadata = {
                'page_count': len(pdf_reader.pages),
                'pages_extracted': len(text_parts),
                'file_size': os.path.getsize(file_path)
            }
            
            return content, metadata
    
    def _extract_with_pdfplumber(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract using pdfplumber"""
        import pdfplumber
        
        with pdfplumber.open(file_path) as pdf:
            text_parts = []
            
            for page_num, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num} from {file_path}: {e}")
                    continue
            
            content = '\n'.join(text_parts)
            metadata = {
                'page_count': len(pdf.pages),
                'pages_extracted': len(text_parts),
                'file_size': os.path.getsize(file_path)
            }
            
            return content, metadata
    
    def _extract_with_pdfminer(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract using pdfminer"""
        from pdfminer.high_level import extract_text
        
        content = extract_text(file_path)
        metadata = {
            'file_size': os.path.getsize(file_path),
            'extraction_method': 'pdfminer'
        }
        
        return content, metadata

class DocxProcessor(FileProcessor):
    """Processor for DOCX files"""
    
    def __init__(self):
        super().__init__(
            name="docx_processor",
            supported_extensions=['.docx'],
            priority=3
        )
    
    def _extract_content(self, file_path: str, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Extract content from DOCX files"""
        try:
            import docx
            
            doc = docx.Document(file_path)
            paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
            content = '\n'.join(paragraphs)
            
            metadata = {
                'paragraph_count': len(paragraphs),
                'file_size': os.path.getsize(file_path)
            }
            
            return content, metadata
            
        except ImportError:
            try:
                import docx2txt
                content = docx2txt.process(file_path)
                metadata = {
                    'extraction_method': 'docx2txt',
                    'file_size': os.path.getsize(file_path)
                }
                return content, metadata
            except ImportError:
                raise ImportError("Neither python-docx nor docx2txt is installed")

class HTMLProcessor(FileProcessor):
    """Processor for HTML files"""
    
    def __init__(self):
        super().__init__(
            name="html_processor",
            supported_extensions=['.html', '.htm'],
            priority=4
        )
    
    def _extract_content(self, file_path: str, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Extract content from HTML files"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            content = soup.get_text()
            
            metadata = {
                'extraction_method': 'beautifulsoup',
                'file_size': os.path.getsize(file_path)
            }
            
        except ImportError:
            # Fallback: basic HTML tag removal
            import re
            content = re.sub(r'<[^>]+>', '', html_content)
            
            metadata = {
                'extraction_method': 'regex_fallback',
                'file_size': os.path.getsize(file_path)
            }
        
        # Clean up whitespace
        content = '\n'.join(line.strip() for line in content.split('\n') if line.strip())
        
        return content, metadata

class FallbackProcessor(FileProcessor):
    """Fallback processor for unsupported file types"""
    
    def __init__(self):
        super().__init__(
            name="fallback_processor",
            supported_extensions=['*'],  # Accepts all extensions
            priority=999  # Lowest priority
        )
    
    def can_process(self, file_path: str) -> bool:
        """Fallback processor can handle any file"""
        return True
    
    def _extract_content(self, file_path: str, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Attempt basic text extraction as fallback"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                
                import re
                content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', content)
                content = re.sub(r'\s+', ' ', content)
                
                if content.strip():
                    metadata = {
                        'encoding_used': encoding,
                        'extraction_method': 'fallback_text',
                        'file_size': os.path.getsize(file_path),
                        'warning': 'Content extracted using fallback method - quality may be poor'
                    }
                    
                    return content, metadata
                    
            except Exception as e:
                logger.debug(f"Fallback extraction failed with encoding {encoding}: {e}")
                continue
        
        raise ValueError("Fallback extraction failed - could not read file as text")

class FileProcessorChain:
    """Chain of responsibility for file processing"""
    
    def __init__(self):
        self.processors: List[FileProcessor] = []
        self._chain_built = False
        self._setup_default_processors()
    
    def _setup_default_processors(self):
        """Setup default processor chain"""
        # Add processors in order of priority
        self.add_processor(TextFileProcessor())
        self.add_processor(PDFProcessor())
        self.add_processor(DocxProcessor())
        self.add_processor(HTMLProcessor())
        self.add_processor(FallbackProcessor())  # Always last
    
    def add_processor(self, processor: FileProcessor):
        """Add a processor to the chain"""
        self.processors.append(processor)
        self._chain_built = False  # Need to rebuild chain
    
    def remove_processor(self, processor_name: str) -> bool:
        """Remove a processor from the chain"""
        for i, processor in enumerate(self.processors):
            if processor.name == processor_name:
                del self.processors[i]
                self._chain_built = False
                return True
        return False
    
    def _build_chain(self):
        """Build the processor chain based on priority"""
        if self._chain_built or not self.processors:
            return
        
        # Sort processors by priority (lower number = higher priority)
        sorted_processors = sorted(self.processors, key=lambda p: p.priority)
        
        # Link processors in chain
        for i in range(len(sorted_processors) - 1):
            sorted_processors[i].set_next(sorted_processors[i + 1])
        
        self.processors = sorted_processors
        self._chain_built = True
    
    def process_file(self, file_path: str, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process file using the processor chain"""
        if context is None:
            context = {}
        
        if not os.path.exists(file_path):
            return ProcessingResult(
                success=False,
                content="",
                metadata={},
                processing_time=0.0,
                method_used="none",
                error=f"File not found: {file_path}"
            )
        
        self._build_chain()
        
        if not self.processors:
            return ProcessingResult(
                success=False,
                content="",
                metadata={},
                processing_time=0.0,
                method_used="none",
                error="No processors available"
            )
        
        # Start processing with the first processor in chain
        return self.processors[0].process(file_path, context)
    
    def get_chain_metrics(self) -> Dict[str, Any]:
        """Get metrics for all processors in the chain"""
        return {
            'processors': [processor.get_metrics() for processor in self.processors],
            'total_processors': len(self.processors),
            'chain_built': self._chain_built
        }
    
    def get_supported_extensions(self) -> List[str]:
        """Get all supported file extensions"""
        extensions = set()
        for processor in self.processors:
            if '*' not in processor.supported_extensions:
                extensions.update(processor.supported_extensions)
        return sorted(list(extensions))

# Global instance
file_processor_chain = FileProcessorChain()