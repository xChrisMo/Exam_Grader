"""
Extraction Method Registry

This module provides a registry for managing multiple extraction methods
for different file types, allowing dynamic registration and selection of
the best extraction method based on file characteristics and success rates.
"""

import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils.logger import logger

class ExtractionPriority(Enum):
    """Priority levels for extraction methods"""

    HIGHEST = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    LOWEST = 5

@dataclass
class ExtractionMethodInfo:
    """Information about an extraction method"""

    name: str
    func: Callable
    file_types: List[str]
    priority: ExtractionPriority
    dependencies: List[str] = field(default_factory=list)
    description: str = ""

    # Performance metrics
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    average_processing_time: float = 0.0
    last_used: Optional[datetime] = None

    # Availability status
    is_available: bool = True
    last_availability_check: Optional[datetime] = None
    availability_error: Optional[str] = None

@dataclass
class ExtractionResult:
    """Result of an extraction attempt"""

    success: bool
    content: str
    metadata: Dict[str, Any]
    method_name: str
    processing_time: float
    error: Optional[str] = None

class ExtractionMethodRegistry:
    """Registry for managing file extraction methods"""

    def __init__(self):
        self._methods: Dict[str, ExtractionMethodInfo] = {}
        self._file_type_methods: Dict[str, List[str]] = {}
        self._setup_default_methods()

    def _setup_default_methods(self):
        """Setup default extraction methods"""

        # PDF extraction methods
        self.register_method(
            name="pypdf2_extractor",
            func=self._extract_pdf_pypdf2,
            file_types=[".pdf"],
            priority=ExtractionPriority.HIGH,
            dependencies=["PyPDF2"],
            description="Extract text from PDF using PyPDF2",
        )

        self.register_method(
            name="pdfplumber_extractor",
            func=self._extract_pdf_pdfplumber,
            file_types=[".pdf"],
            priority=ExtractionPriority.HIGHEST,
            dependencies=["pdfplumber"],
            description="Extract text from PDF using pdfplumber (best quality)",
        )

        self.register_method(
            name="pdfminer_extractor",
            func=self._extract_pdf_pdfminer,
            file_types=[".pdf"],
            priority=ExtractionPriority.MEDIUM,
            dependencies=["pdfminer.six"],
            description="Extract text from PDF using pdfminer",
        )

        # DOCX extraction methods
        self.register_method(
            name="python_docx_extractor",
            func=self._extract_docx_python_docx,
            file_types=[".docx"],
            priority=ExtractionPriority.HIGHEST,
            dependencies=["python-docx"],
            description="Extract text from DOCX using python-docx",
        )

        self.register_method(
            name="docx2txt_extractor",
            func=self._extract_docx_docx2txt,
            file_types=[".docx"],
            priority=ExtractionPriority.HIGH,
            dependencies=["docx2txt"],
            description="Extract text from DOCX using docx2txt",
        )

        # DOC extraction methods
        self.register_method(
            name="antiword_extractor",
            func=self._extract_doc_antiword,
            file_types=[".doc"],
            priority=ExtractionPriority.HIGHEST,
            dependencies=["antiword"],
            description="Extract text from DOC using antiword",
        )

        # RTF extraction methods
        self.register_method(
            name="striprtf_extractor",
            func=self._extract_rtf_striprtf,
            file_types=[".rtf"],
            priority=ExtractionPriority.HIGHEST,
            dependencies=["striprtf"],
            description="Extract text from RTF using striprtf",
        )

        self.register_method(
            name="rtf_regex_extractor",
            func=self._extract_rtf_regex,
            file_types=[".rtf"],
            priority=ExtractionPriority.LOW,
            dependencies=[],
            description="Extract text from RTF using regex (fallback)",
        )

        # HTML extraction methods
        self.register_method(
            name="beautifulsoup_extractor",
            func=self._extract_html_beautifulsoup,
            file_types=[".html", ".htm"],
            priority=ExtractionPriority.HIGHEST,
            dependencies=["beautifulsoup4"],
            description="Extract text from HTML using BeautifulSoup",
        )

        self.register_method(
            name="html_regex_extractor",
            func=self._extract_html_regex,
            file_types=[".html", ".htm"],
            priority=ExtractionPriority.LOW,
            dependencies=[],
            description="Extract text from HTML using regex (fallback)",
        )

        # Text extraction methods
        self.register_method(
            name="utf8_text_extractor",
            func=self._extract_text_utf8,
            file_types=[".txt", ".md", ".markdown", ".csv", ".log"],
            priority=ExtractionPriority.HIGHEST,
            dependencies=[],
            description="Extract text using UTF-8 encoding",
        )

        self.register_method(
            name="chardet_text_extractor",
            func=self._extract_text_chardet,
            file_types=[".txt", ".md", ".markdown", ".csv", ".log"],
            priority=ExtractionPriority.HIGH,
            dependencies=["chardet"],
            description="Extract text with automatic encoding detection",
        )

        self.register_method(
            name="fallback_text_extractor",
            func=self._extract_text_fallback,
            file_types=["*"],  # Supports all file types as fallback
            priority=ExtractionPriority.LOWEST,
            dependencies=[],
            description="Fallback text extraction for any file type",
        )

        # Check availability of all methods
        self._check_all_method_availability()

    def register_method(
        self,
        name: str,
        func: Callable,
        file_types: List[str],
        priority: ExtractionPriority,
        dependencies: List[str] = None,
        description: str = "",
    ) -> bool:
        """Register a new extraction method"""
        if dependencies is None:
            dependencies = []

        method_info = ExtractionMethodInfo(
            name=name,
            func=func,
            file_types=[ft.lower() for ft in file_types],
            priority=priority,
            dependencies=dependencies,
            description=description,
        )

        method_info.is_available = self._check_method_availability(method_info)

        self._methods[name] = method_info

        # Update file type mappings
        for file_type in method_info.file_types:
            if file_type not in self._file_type_methods:
                self._file_type_methods[file_type] = []
            if name not in self._file_type_methods[file_type]:
                self._file_type_methods[file_type].append(name)

        logger.info(
            f"Registered extraction method: {name} for {file_types} "
            f"(available: {method_info.is_available})"
        )

        return method_info.is_available

    def unregister_method(self, name: str) -> bool:
        """Unregister an extraction method"""
        if name not in self._methods:
            return False

        method_info = self._methods[name]

        for file_type in method_info.file_types:
            if file_type in self._file_type_methods:
                if name in self._file_type_methods[file_type]:
                    self._file_type_methods[file_type].remove(name)
                if not self._file_type_methods[file_type]:
                    del self._file_type_methods[file_type]

        del self._methods[name]
        logger.info(f"Unregistered extraction method: {name}")
        return True

    def get_methods(self, file_type: str) -> List[str]:
        """Get available extraction methods for a file type"""
        file_type = file_type.lower()
        methods = []

        if file_type in self._file_type_methods:
            methods.extend(self._file_type_methods[file_type])

        # Add wildcard methods (fallback methods)
        if "*" in self._file_type_methods:
            methods.extend(self._file_type_methods["*"])

        # Filter to only available methods and sort by priority
        available_methods = []
        for method_name in methods:
            if method_name in self._methods:
                method_info = self._methods[method_name]
                if method_info.is_available:
                    available_methods.append((method_name, method_info.priority.value))

        # Sort by priority (lower number = higher priority)
        available_methods.sort(key=lambda x: x[1])

        return [method_name for method_name, _ in available_methods]

    def extract_with_method(
        self, method_name: str, file_path: str, context: Dict[str, Any] = None
    ) -> ExtractionResult:
        """Extract content using a specific method"""
        if context is None:
            context = {}

        if method_name not in self._methods:
            return ExtractionResult(
                success=False,
                content="",
                metadata={},
                method_name=method_name,
                processing_time=0.0,
                error=f"Method {method_name} not found",
            )

        method_info = self._methods[method_name]

        if not method_info.is_available:
            return ExtractionResult(
                success=False,
                content="",
                metadata={},
                method_name=method_name,
                processing_time=0.0,
                error=f"Method {method_name} not available: {method_info.availability_error}",
            )

        start_time = time.time()

        try:
            # Update metrics
            method_info.total_attempts += 1
            method_info.last_used = datetime.now(timezone.utc)

            # Call the extraction method
            content, metadata = method_info.func(file_path, context)
            processing_time = time.time() - start_time

            if content and content.strip():
                # Success
                method_info.successful_attempts += 1
                self._update_average_processing_time(method_info, processing_time)

                return ExtractionResult(
                    success=True,
                    content=content,
                    metadata=metadata,
                    method_name=method_name,
                    processing_time=processing_time,
                )
            else:
                # No content extracted
                method_info.failed_attempts += 1
                return ExtractionResult(
                    success=False,
                    content="",
                    metadata=metadata,
                    method_name=method_name,
                    processing_time=processing_time,
                    error="No content extracted",
                )

        except Exception as e:
            method_info.failed_attempts += 1
            processing_time = time.time() - start_time

            logger.warning(
                f"Extraction method {method_name} failed for {file_path}: {e}"
            )

            return ExtractionResult(
                success=False,
                content="",
                metadata={},
                method_name=method_name,
                processing_time=processing_time,
                error=str(e),
            )

    def extract_with_fallback(
        self, file_path: str, context: Dict[str, Any] = None
    ) -> ExtractionResult:
        """Extract content trying methods in priority order"""
        if context is None:
            context = {}

        file_extension = Path(file_path).suffix.lower()
        methods = self.get_methods(file_extension)

        if not methods:
            return ExtractionResult(
                success=False,
                content="",
                metadata={},
                method_name="none",
                processing_time=0.0,
                error=f"No extraction methods available for {file_extension}",
            )

        last_error = None
        for method_name in methods:
            result = self.extract_with_method(method_name, file_path, context)
            if result.success:
                return result
            last_error = result.error

        return ExtractionResult(
            success=False,
            content="",
            metadata={},
            method_name="fallback_failed",
            processing_time=0.0,
            error=f"All extraction methods failed. Last error: {last_error}",
        )

    def _check_method_availability(self, method_info: ExtractionMethodInfo) -> bool:
        """Check if a method's dependencies are available"""
        method_info.last_availability_check = datetime.now(timezone.utc)

        for dependency in method_info.dependencies:
            if dependency == "antiword":
                # Special handling for antiword system command
                try:
                    result = subprocess.run(
                        ["which", "antiword"], capture_output=True, timeout=5
                    )
                    if result.returncode != 0:
                        method_info.availability_error = f"Missing system command: {dependency}"
                        logger.debug(f"Method {method_info.name} unavailable: antiword not found in PATH")
                        return False
                except Exception as e:
                    method_info.availability_error = f"Error checking {dependency}: {str(e)}"
                    logger.debug(f"Method {method_info.name} unavailable: {e}")
                    return False
            else:
                # Check Python imports
                try:
                    __import__(dependency)
                except ImportError as e:
                    method_info.availability_error = f"Missing dependency: {dependency}"
                    logger.debug(f"Method {method_info.name} unavailable: {e}")
                    return False

        method_info.availability_error = None
        return True

    def _check_all_method_availability(self):
        """Check availability of all registered methods"""
        for method_info in self._methods.values():
            method_info.is_available = self._check_method_availability(method_info)

    def _update_average_processing_time(
        self, method_info: ExtractionMethodInfo, new_time: float
    ):
        """Update average processing time for a method"""
        if method_info.successful_attempts == 1:
            method_info.average_processing_time = new_time
        else:
            # Running average
            total_time = method_info.average_processing_time * (
                method_info.successful_attempts - 1
            )
            method_info.average_processing_time = (
                total_time + new_time
            ) / method_info.successful_attempts

    def get_method_info(self, method_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific method"""
        if method_name not in self._methods:
            return None

        method_info = self._methods[method_name]
        success_rate = 0.0
        if method_info.total_attempts > 0:
            success_rate = method_info.successful_attempts / method_info.total_attempts

        return {
            "name": method_info.name,
            "file_types": method_info.file_types,
            "priority": method_info.priority.name,
            "dependencies": method_info.dependencies,
            "description": method_info.description,
            "is_available": method_info.is_available,
            "availability_error": method_info.availability_error,
            "total_attempts": method_info.total_attempts,
            "successful_attempts": method_info.successful_attempts,
            "failed_attempts": method_info.failed_attempts,
            "success_rate": success_rate,
            "average_processing_time": method_info.average_processing_time,
            "last_used": (
                method_info.last_used.isoformat() if method_info.last_used else None
            ),
            "last_availability_check": (
                method_info.last_availability_check.isoformat()
                if method_info.last_availability_check
                else None
            ),
        }

    def get_all_methods_info(self) -> Dict[str, Any]:
        """Get information about all registered methods"""
        return {
            "methods": {
                name: self.get_method_info(name) for name in self._methods.keys()
            },
            "file_type_mappings": dict(self._file_type_methods),
            "total_methods": len(self._methods),
            "available_methods": sum(
                1 for m in self._methods.values() if m.is_available
            ),
        }

    # Default extraction method implementations

    def _extract_pdf_pypdf2(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract PDF using PyPDF2"""
        import PyPDF2

        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text_parts = []

            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            content = "\n".join(text_parts)
            metadata = {
                "page_count": len(pdf_reader.pages),
                "pages_extracted": len(text_parts),
                "extraction_library": "PyPDF2",
            }

            return content, metadata

    def _extract_pdf_pdfplumber(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract PDF using pdfplumber"""
        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            text_parts = []

            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            content = "\n".join(text_parts)
            metadata = {
                "page_count": len(pdf.pages),
                "pages_extracted": len(text_parts),
                "extraction_library": "pdfplumber",
            }

            return content, metadata

    def _extract_pdf_pdfminer(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract PDF using pdfminer"""
        from pdfminer.high_level import extract_text

        content = extract_text(file_path)
        metadata = {"extraction_library": "pdfminer"}

        return content, metadata

    def _extract_docx_python_docx(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract DOCX using python-docx"""
        import docx

        doc = docx.Document(file_path)
        paragraphs = [
            paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()
        ]
        content = "\n".join(paragraphs)

        metadata = {
            "paragraph_count": len(paragraphs),
            "extraction_library": "python-docx",
        }

        return content, metadata

    def _extract_docx_docx2txt(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract DOCX using docx2txt"""
        import docx2txt

        content = docx2txt.process(file_path)
        metadata = {"extraction_library": "docx2txt"}

        return content, metadata

    def _extract_doc_antiword(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract DOC using antiword"""
        import subprocess

        try:
            result = subprocess.run(
                ["antiword", file_path], capture_output=True, text=True, timeout=int(os.getenv("TIMEOUT_ANTIWORD", "30"))
            )

            if result.returncode != 0:
                raise ValueError(f"antiword failed with return code {result.returncode}: {result.stderr}")

            content = result.stdout
            metadata = {"extraction_library": "antiword"}

            return content, metadata
        except FileNotFoundError:
            raise ValueError("antiword command not found - please install antiword for DOC file processing")
        except subprocess.TimeoutExpired:
            raise ValueError("antiword processing timed out")
        except Exception as e:
            raise ValueError(f"antiword extraction failed: {str(e)}")

    def _extract_rtf_striprtf(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract RTF using striprtf"""
        from striprtf.striprtf import rtf_to_text

        with open(file_path, "r", encoding="utf-8") as f:
            rtf_content = f.read()

        content = rtf_to_text(rtf_content)
        metadata = {"extraction_library": "striprtf"}

        return content, metadata

    def _extract_rtf_regex(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract RTF using regex (fallback)"""
        import re

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Basic RTF cleanup
        content = re.sub(r"\\[a-z]+\d*\s?", "", content)  # Remove RTF commands
        content = re.sub(r"[{}]", "", content)  # Remove braces
        content = re.sub(r"\s+", " ", content)  # Normalize whitespace

        metadata = {"extraction_library": "regex_fallback"}

        return content.strip(), metadata

    def _extract_html_beautifulsoup(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract HTML using BeautifulSoup"""
        from bs4 import BeautifulSoup

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        content = soup.get_text()

        # Clean up whitespace
        content = "\n".join(
            line.strip() for line in content.split("\n") if line.strip()
        )

        metadata = {"extraction_library": "beautifulsoup4"}

        return content, metadata

    def _extract_html_regex(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract HTML using regex (fallback)"""

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()

        # Remove HTML tags
        content = re.sub(r"<[^>]+>", "", html_content)

        # Clean up whitespace
        content = "\n".join(
            line.strip() for line in content.split("\n") if line.strip()
        )

        metadata = {"extraction_library": "regex_fallback"}

        return content, metadata

    def _extract_text_utf8(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract text using UTF-8 encoding"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        metadata = {"encoding": "utf-8", "extraction_library": "builtin"}

        return content, metadata

    def _extract_text_chardet(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract text with automatic encoding detection"""
        import chardet

        with open(file_path, "rb") as f:
            raw_data = f.read()

        encoding_result = chardet.detect(raw_data)
        encoding = encoding_result["encoding"] or "utf-8"

        content = raw_data.decode(encoding, errors="ignore")

        metadata = {
            "encoding": encoding,
            "encoding_confidence": encoding_result["confidence"],
            "extraction_library": "chardet",
        }

        return content, metadata

    def _extract_text_fallback(
        self, file_path: str, context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Fallback text extraction for any file type"""

        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                    content = f.read()

                content = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", content)
                content = re.sub(r"\s+", " ", content)

                if content.strip():
                    metadata = {
                        "encoding": encoding,
                        "extraction_library": "fallback",
                        "warning": "Fallback extraction used - quality may be poor",
                    }

                    return content, metadata

            except Exception:
                continue

        raise ValueError("Could not extract text using any encoding")

# Global instance
extraction_method_registry = ExtractionMethodRegistry()
