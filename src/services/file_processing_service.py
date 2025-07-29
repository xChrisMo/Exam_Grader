"""
Enhanced File Processing Service

This service provides robust file processing with fallback mechanisms,
content validation, and quality scoring for LLM training documents.
"""

import os
import re
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from utils.logger import logger
from src.services.file_processor_chain import file_processor_chain, ProcessingResult
from src.services.extraction_method_registry import extraction_method_registry, ExtractionResult
from src.services.content_validator import content_validator, ValidationResult
from src.services.processing_error_handler import processing_error_handler, ErrorContext
from src.services.fallback_manager import fallback_manager
from src.services.retry_manager import retry_manager

class FileProcessingService:
    """Enhanced file processing service with fallback mechanisms"""
    
    def __init__(self):
        self.supported_formats = {
            '.txt': self._extract_text,
            '.pdf': self._extract_pdf,
            '.docx': self._extract_docx,
            '.doc': self._extract_doc,
            '.rtf': self._extract_rtf,
            '.html': self._extract_html,
            '.htm': self._extract_html,
            '.md': self._extract_markdown,
            '.markdown': self._extract_markdown,
            '.json': self._extract_json
        }
        
        self.fallback_methods = [
            ('primary', self._extract_primary),
            ('secondary', self._extract_secondary),
            ('fallback', self._extract_fallback)
        ]
        
        # Check availability of optional dependencies
        self.dependency_status = self._check_dependencies()
        self._log_dependency_status()
    
    def process_file_with_fallback(self, file_path: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process file with multiple fallback methods using enhanced components
        
        Args:
            file_path: Path to the file to process
            file_info: Dictionary containing file metadata
            
        Returns:
            Dictionary containing processing results and metadata
        """
        start_time = time.time()
        
        # Create processing context
        context = {
            'user_id': file_info.get('user_id'),
            'request_id': file_info.get('request_id', f'file_proc_{int(time.time())}'),
            'file_info': file_info,
            'processing_start': datetime.utcnow()
        }
        
        processing_attempts = []
        
        try:
            chain_result = file_processor_chain.process_file(file_path, context)
            
            # Record chain attempt
            processing_attempts.append({
                'method': chain_result.method_used,
                'success': chain_result.success,
                'duration_ms': int(chain_result.processing_time * 1000),
                'content_length': len(chain_result.content) if chain_result.success else 0,
                'error': chain_result.error
            })
            
            if chain_result.success:
                # Validate content using the content validator
                validation_result = content_validator.validate_content(
                    chain_result.content, 
                    file_info
                )
                
                # Enhanced quality scoring with additional metrics
                quality_metrics = self._calculate_enhanced_quality_metrics(
                    chain_result.content, validation_result.metrics
                )
                
                # Convert to enhanced format
                result = {
                    'success': True,
                    'text_content': chain_result.content,
                    'word_count': validation_result.metrics.word_count,
                    'character_count': validation_result.metrics.character_count,
                    'extraction_method': chain_result.method_used,
                    'processing_duration_ms': int(chain_result.processing_time * 1000),
                    'content_quality_score': validation_result.overall_score,
                    'validation_status': validation_result.status.value,
                    'validation_errors': validation_result.errors + validation_result.warnings,
                    'processing_attempts': processing_attempts,
                    'quality_metrics': quality_metrics,
                    'validation_suggestions': validation_result.suggestions,
                    'fallback_used': chain_result.fallback_used,
                    'retry_count': chain_result.retry_count,
                    'content_hash': self.calculate_file_hash(file_path),
                    'extraction_metadata': chain_result.metadata,
                    'quality_level': validation_result.quality.value,
                    'processing_timestamp': datetime.utcnow().isoformat()
                }
                
                logger.info(f"Successfully processed {file_path} using {chain_result.method_used} "
                           f"(quality: {validation_result.quality.value}, score: {validation_result.overall_score:.2f})")
                
            else:
                # Try extraction method registry as fallback
                logger.warning(f"File processor chain failed for {file_path}, trying extraction registry")
                
                extraction_result = extraction_method_registry.extract_with_fallback(file_path, context)
                
                # Record registry attempt
                processing_attempts.append({
                    'method': extraction_result.method_name,
                    'success': extraction_result.success,
                    'duration_ms': int(extraction_result.processing_time * 1000),
                    'content_length': len(extraction_result.content) if extraction_result.success else 0,
                    'error': extraction_result.error
                })
                
                if extraction_result.success:
                    # Validate content
                    validation_result = content_validator.validate_content(
                        extraction_result.content, 
                        file_info
                    )
                    
                    # Enhanced quality scoring
                    quality_metrics = self._calculate_enhanced_quality_metrics(
                        extraction_result.content, validation_result.metrics
                    )
                    
                    result = {
                        'success': True,
                        'text_content': extraction_result.content,
                        'word_count': validation_result.metrics.word_count,
                        'character_count': validation_result.metrics.character_count,
                        'extraction_method': extraction_result.method_name,
                        'processing_duration_ms': int(extraction_result.processing_time * 1000),
                        'content_quality_score': validation_result.overall_score,
                        'validation_status': validation_result.status.value,
                        'validation_errors': validation_result.errors + validation_result.warnings,
                        'processing_attempts': processing_attempts,
                        'quality_metrics': quality_metrics,
                        'validation_suggestions': validation_result.suggestions,
                        'fallback_used': True,
                        'retry_count': 0,
                        'content_hash': self.calculate_file_hash(file_path),
                        'extraction_metadata': extraction_result.metadata,
                        'quality_level': validation_result.quality.value,
                        'processing_timestamp': datetime.utcnow().isoformat()
                    }
                    
                    logger.info(f"Successfully processed {file_path} using extraction registry "
                               f"method {extraction_result.method_name}")
                    
                else:
                    # All methods failed - create comprehensive error result
                    result = self._create_failure_result(
                        file_path, start_time, processing_attempts, 
                        chain_result.error, extraction_result.error
                    )
                    
                    logger.error(f"All extraction methods failed for {file_path}")
        
        except Exception as e:
            # Handle unexpected errors
            error_context = ErrorContext(
                operation="file_processing_with_fallback",
                service="file_processing_service",
                timestamp=datetime.utcnow(),
                user_id=context.get('user_id'),
                request_id=context.get('request_id'),
                additional_data={
                    'file_path': file_path,
                    'error': str(e)
                }
            )
            
            processing_error_handler.handle_error(e, error_context)
            
            result = self._create_error_result(file_path, start_time, str(e), processing_attempts)
            logger.error(f"Error processing file {file_path}: {e}")
        
        return result

    def _calculate_enhanced_quality_metrics(self, content: str, base_metrics) -> Dict[str, Any]:
        """Calculate enhanced quality metrics beyond basic validation"""
        
        # Start with base metrics
        quality_metrics = {
            'word_count': base_metrics.word_count,
            'character_count': base_metrics.character_count,
            'sentence_count': base_metrics.sentence_count,
            'paragraph_count': base_metrics.paragraph_count,
            'unique_words': base_metrics.unique_words,
            'average_word_length': base_metrics.average_word_length,
            'average_sentence_length': base_metrics.average_sentence_length,
            'language_confidence': base_metrics.language_confidence,
            'structure_score': base_metrics.structure_score,
            'coherence_score': base_metrics.coherence_score,
            'diversity_score': base_metrics.diversity_score
        }
        
        # Add enhanced metrics
        try:
            # Readability metrics
            quality_metrics['readability_score'] = self._calculate_readability_score(content)
            
            # Content density metrics
            quality_metrics['content_density'] = self._calculate_content_density(content)
            
            # Format-specific quality indicators
            quality_metrics['format_quality'] = self._assess_format_quality(content)
            
            # Extraction quality indicators
            quality_metrics['extraction_quality'] = self._assess_extraction_quality(content)
            
            # Language detection confidence
            quality_metrics['language_detection'] = self._enhanced_language_detection(content)
            
        except Exception as e:
            logger.warning(f"Error calculating enhanced quality metrics: {e}")
            quality_metrics['calculation_error'] = str(e)
        
        return quality_metrics

    def _calculate_readability_score(self, content: str) -> float:
        """Calculate a simple readability score"""
        if not content or len(content.split()) < 10:
            return 0.0
        
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) == 0:
            return 0.0
        
        # Simple Flesch-like formula
        avg_sentence_length = len(words) / len(sentences)
        avg_syllables = sum(self._count_syllables(word) for word in words) / len(words)
        
        # Simplified readability score (0-100)
        score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables)
        return max(0, min(100, score)) / 100.0  # Normalize to 0-1

    def _count_syllables(self, word: str) -> int:
        """Estimate syllable count in a word"""
        word = word.lower()
        vowels = 'aeiouy'
        syllable_count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel
        
        # Handle silent e
        if word.endswith('e') and syllable_count > 1:
            syllable_count -= 1
        
        return max(1, syllable_count)

    def _calculate_content_density(self, content: str) -> float:
        """Calculate content density (meaningful content vs whitespace/formatting)"""
        if not content:
            return 0.0
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', content.strip())
        
        # Count meaningful characters (letters, numbers, basic punctuation)
        meaningful_chars = len(re.findall(r'[a-zA-Z0-9.!?,:;]', cleaned))
        total_chars = len(cleaned)
        
        if total_chars == 0:
            return 0.0
        
        return meaningful_chars / total_chars

    def _assess_format_quality(self, content: str) -> Dict[str, Any]:
        """Assess quality indicators specific to document format"""
        indicators = {
            'has_headers': bool(re.search(r'^[A-Z][A-Za-z\s]+:?\s*$', content, re.MULTILINE)),
            'has_lists': bool(re.search(r'^\s*[-*•]\s+', content, re.MULTILINE)) or 
                        bool(re.search(r'^\s*\d+\.\s+', content, re.MULTILINE)),
            'has_paragraphs': '\n\n' in content,
            'proper_capitalization': self._check_capitalization_quality(content),
            'consistent_formatting': self._check_formatting_consistency(content)
        }
        
        # Calculate overall format quality score
        score = sum(1 for v in indicators.values() if v) / len(indicators)
        indicators['overall_score'] = score
        
        return indicators

    def _check_capitalization_quality(self, content: str) -> float:
        """Check quality of capitalization"""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        properly_capitalized = sum(1 for s in sentences if s and s[0].isupper())
        return properly_capitalized / len(sentences)

    def _check_formatting_consistency(self, content: str) -> float:
        """Check consistency of formatting patterns"""
        # Simple consistency checks
        consistency_score = 0.0
        checks = 0
        
        # Check line ending consistency
        if content:
            checks += 1
            windows_endings = content.count('\r\n')
            unix_endings = content.count('\n') - windows_endings
            if windows_endings == 0 or unix_endings == 0:
                consistency_score += 1
        
        # Check spacing consistency around punctuation
        if '.' in content:
            checks += 1
            periods_with_space = len(re.findall(r'\.\s+', content))
            total_periods = content.count('.')
            if total_periods > 0 and periods_with_space / total_periods > 0.8:
                consistency_score += 1
        
        return consistency_score / max(1, checks)

    def _assess_extraction_quality(self, content: str) -> Dict[str, Any]:
        """Assess quality indicators specific to text extraction"""
        indicators = {
            'has_extraction_artifacts': self._detect_extraction_artifacts(content),
            'character_encoding_issues': self._detect_encoding_issues(content),
            'ocr_quality_indicators': self._assess_ocr_quality(content),
            'structural_integrity': self._assess_structural_integrity(content)
        }
        
        # Calculate overall extraction quality
        artifact_penalty = 0.3 if indicators['has_extraction_artifacts'] else 0
        encoding_penalty = 0.2 if indicators['character_encoding_issues'] else 0
        ocr_score = indicators['ocr_quality_indicators']['overall_score']
        structure_score = indicators['structural_integrity']
        
        overall_score = max(0, 1.0 - artifact_penalty - encoding_penalty) * ocr_score * structure_score
        indicators['overall_score'] = overall_score
        
        return indicators

    def _detect_extraction_artifacts(self, content: str) -> bool:
        """Detect common extraction artifacts"""
        artifacts = [
            r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]',  # Control characters
            r'(.)\1{5,}',  # Repeated characters
            r'\s{10,}',  # Excessive whitespace
            r'[^\w\s.!?,:;()-]{3,}',  # Strange character sequences
        ]
        
        return any(re.search(pattern, content) for pattern in artifacts)

    def _detect_encoding_issues(self, content: str) -> bool:
        """Detect character encoding issues"""
        encoding_issues = [
            r'[ÃÂ]',  # Common UTF-8 encoding issues
            r'â€™',  # Mangled apostrophes
            r'â€œ|â€',  # Mangled quotes
            r'Ã¡|Ã©|Ã­|Ã³|Ãº',  # Mangled accented characters
        ]
        
        return any(re.search(pattern, content) for pattern in encoding_issues)

    def _assess_ocr_quality(self, content: str) -> Dict[str, Any]:
        """Assess OCR quality indicators"""
        indicators = {
            'suspicious_character_substitutions': self._count_ocr_substitutions(content),
            'word_fragmentation': self._assess_word_fragmentation(content),
            'line_break_issues': self._assess_line_break_quality(content)
        }
        
        # Calculate overall OCR quality score
        substitution_penalty = min(0.5, indicators['suspicious_character_substitutions'] * 0.1)
        fragmentation_penalty = min(0.3, indicators['word_fragmentation'] * 0.1)
        line_break_penalty = min(0.2, indicators['line_break_issues'] * 0.1)
        
        overall_score = max(0, 1.0 - substitution_penalty - fragmentation_penalty - line_break_penalty)
        indicators['overall_score'] = overall_score
        
        return indicators

    def _count_ocr_substitutions(self, content: str) -> int:
        """Count suspicious OCR character substitutions"""
        substitutions = [
            r'\b[Il1]\b',  # Isolated I, l, 1 (often confused)
            r'\b[O0]\b',   # Isolated O, 0
            r'[|]',        # Vertical bars (often misread)
            r'[rn]m',      # rn -> m confusion
            r'[cl]o',      # cl -> o confusion
        ]
        
        count = 0
        for pattern in substitutions:
            count += len(re.findall(pattern, content))
        
        return count

    def _assess_word_fragmentation(self, content: str) -> float:
        """Assess word fragmentation (words broken across lines)"""
        words = content.split()
        if len(words) < 10:
            return 0.0
        
        short_words = [w for w in words if len(w) <= 2 and w.isalpha()]
        fragmentation_ratio = len(short_words) / len(words)
        
        return fragmentation_ratio

    def _assess_line_break_quality(self, content: str) -> float:
        """Assess quality of line breaks"""
        lines = content.split('\n')
        if len(lines) < 3:
            return 0.0
        
        # Count lines that end mid-word (no punctuation or capitalized next line)
        problematic_breaks = 0
        for i in range(len(lines) - 1):
            current_line = lines[i].strip()
            next_line = lines[i + 1].strip()
            
            if (current_line and next_line and 
                not current_line[-1] in '.!?:;' and 
                not next_line[0].isupper()):
                problematic_breaks += 1
        
        return problematic_breaks / max(1, len(lines) - 1)

    def _assess_structural_integrity(self, content: str) -> float:
        """Assess structural integrity of extracted content"""
        if not content:
            return 0.0
        
        score = 1.0
        
        sentences = re.split(r'[.!?]+', content)
        valid_sentences = [s for s in sentences if s.strip() and len(s.split()) >= 3]
        
        if len(sentences) > 0:
            sentence_quality = len(valid_sentences) / len(sentences)
            score *= sentence_quality
        
        words = content.split()
        if words:
            avg_word_length = sum(len(w) for w in words) / len(words)
            if avg_word_length < 2 or avg_word_length > 15:
                score *= 0.7  # Penalty for unusual word lengths
        
        return score

    def _enhanced_language_detection(self, content: str) -> Dict[str, Any]:
        """Enhanced language detection with confidence scoring"""
        # Extended English indicators
        english_patterns = [
            (r'\bthe\b', 0.15), (r'\band\b', 0.12), (r'\bof\b', 0.10),
            (r'\bto\b', 0.08), (r'\ba\b', 0.08), (r'\bin\b', 0.07),
            (r'\bis\b', 0.06), (r'\bit\b', 0.06), (r'\byou\b', 0.05),
            (r'\bthat\b', 0.05), (r'\bfor\b', 0.04), (r'\bwith\b', 0.04),
            (r'\bas\b', 0.03), (r'\bthis\b', 0.03), (r'\bhave\b', 0.03)
        ]
        
        total_score = 0.0
        matches = {}
        
        for pattern, weight in english_patterns:
            count = len(re.findall(pattern, content, re.IGNORECASE))
            matches[pattern] = count
            total_score += count * weight
        
        # Normalize by content length
        words = content.split()
        confidence = min(1.0, total_score / max(1, len(words))) if words else 0.0
        
        return {
            'language': 'english',
            'confidence': confidence,
            'pattern_matches': matches,
            'total_words': len(words)
        }

    def _create_failure_result(self, file_path: str, start_time: float, 
                             processing_attempts: List[Dict], 
                             chain_error: str, registry_error: str) -> Dict[str, Any]:
        """Create comprehensive failure result"""
        return {
            'success': False,
            'text_content': '',
            'word_count': 0,
            'character_count': 0,
            'extraction_method': None,
            'processing_duration_ms': int((time.time() - start_time) * 1000),
            'content_quality_score': 0.0,
            'validation_status': 'failed',
            'validation_errors': [
                'All extraction methods failed',
                f'Chain error: {chain_error}',
                f'Registry error: {registry_error}'
            ],
            'processing_attempts': processing_attempts,
            'quality_metrics': {
                'extraction_failure': True,
                'attempted_methods': len(processing_attempts)
            },
            'validation_suggestions': [
                'Try alternative extraction methods or check file integrity',
                'Verify file is not corrupted',
                'Check if file format is supported',
                'Consider manual content extraction'
            ],
            'fallback_used': True,
            'retry_count': 0,
            'content_hash': self.calculate_file_hash(file_path),
            'extraction_metadata': {'error': 'All methods failed'},
            'quality_level': 'invalid',
            'processing_timestamp': datetime.utcnow().isoformat()
        }

    def _create_error_result(self, file_path: str, start_time: float, 
                           error_message: str, processing_attempts: List[Dict]) -> Dict[str, Any]:
        """Create error result for unexpected exceptions"""
        return {
            'success': False,
            'text_content': '',
            'word_count': 0,
            'character_count': 0,
            'extraction_method': None,
            'processing_duration_ms': int((time.time() - start_time) * 1000),
            'content_quality_score': 0.0,
            'validation_status': 'error',
            'validation_errors': [f'Processing error: {error_message}'],
            'processing_attempts': processing_attempts,
            'quality_metrics': {
                'processing_error': True,
                'error_type': 'unexpected_exception'
            },
            'validation_suggestions': [
                'Check file integrity and try again',
                'Verify file permissions',
                'Check system resources'
            ],
            'fallback_used': False,
            'retry_count': 0,
            'content_hash': None,
            'extraction_metadata': {'error': error_message},
            'quality_level': 'invalid',
            'processing_timestamp': datetime.utcnow().isoformat()
        }
    
    def _extract_primary(self, file_path: str, file_extension: str) -> str:
        """Primary extraction method using format-specific libraries"""
        if file_extension in self.supported_formats:
            return self.supported_formats[file_extension](file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    def _extract_secondary(self, file_path: str, file_extension: str) -> str:
        """Secondary extraction method with alternative libraries"""
        if file_extension == '.pdf':
            return self._extract_pdf_alternative(file_path)
        elif file_extension in ['.docx', '.doc']:
            return self._extract_doc_alternative(file_path)
        elif file_extension == '.rtf':
            return self._extract_rtf_alternative(file_path)
        else:
            # Try reading as plain text with different encodings
            return self._extract_text_with_encoding_detection(file_path)
    
    def _extract_fallback(self, file_path: str, file_extension: str) -> str:
        """Fallback extraction method - basic text reading with error handling"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                    if content.strip():
                        if file_extension not in ['.txt', '.md', '.markdown']:
                            content = self._clean_extracted_text(content)
                        return content
            except Exception as e:
                logger.debug(f"Failed to read {file_path} with encoding {encoding}: {e}")
                continue
        
        raise ValueError("Could not read file with any encoding")
    
    def _extract_text(self, file_path: str) -> str:
        """Extract text from plain text files"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF files using PyPDF2"""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text_parts = []
                for page in pdf_reader.pages:
                    text_parts.append(page.extract_text())
                return '\n'.join(text_parts)
        except ImportError:
            raise ImportError("PyPDF2 not installed")
    
    def _extract_pdf_alternative(self, file_path: str) -> str:
        """Alternative PDF extraction using pdfplumber"""
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                return '\n'.join(text_parts)
        except ImportError:
            raise ImportError("pdfplumber not installed")
    
    def _extract_docx(self, file_path: str) -> str:
        """Extract text from DOCX files"""
        try:
            import docx
            doc = docx.Document(file_path)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        except ImportError:
            raise ImportError("python-docx not installed")
    
    def _extract_doc(self, file_path: str) -> str:
        """Extract text from legacy DOC files"""
        try:
            import subprocess
            result = subprocess.run(['antiword', file_path], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
            else:
                raise ValueError("antiword extraction failed")
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
            raise ValueError(f"DOC extraction failed: {e}")
    
    def _extract_doc_alternative(self, file_path: str) -> str:
        """Alternative DOC extraction using python-docx2txt"""
        try:
            import docx2txt
            return docx2txt.process(file_path)
        except ImportError:
            raise ImportError("docx2txt not installed")
    
    def _extract_rtf(self, file_path: str) -> str:
        """Extract text from RTF files"""
        try:
            from striprtf.striprtf import rtf_to_text
            with open(file_path, 'r', encoding='utf-8') as f:
                rtf_content = f.read()
            return rtf_to_text(rtf_content)
        except ImportError:
            raise ImportError("striprtf not installed")
    
    def _extract_rtf_alternative(self, file_path: str) -> str:
        """Alternative RTF extraction using basic regex"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Basic RTF cleanup - remove RTF control codes
        content = re.sub(r'\\[a-z]+\d*\s?', '', content)  # Remove RTF commands
        content = re.sub(r'[{}]', '', content)  # Remove braces
        content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
        return content.strip()
    
    def _extract_html(self, file_path: str) -> str:
        """Extract text from HTML files"""
        try:
            from bs4 import BeautifulSoup
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text()
        except ImportError:
            # Fallback: basic HTML tag removal
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return re.sub(r'<[^>]+>', '', html_content)
    
    def _extract_markdown(self, file_path: str) -> str:
        """Extract text from Markdown files"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Basic markdown cleanup
        content = re.sub(r'#{1,6}\s+', '', content)  # Headers
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Bold
        content = re.sub(r'\*(.*?)\*', r'\1', content)  # Italic
        content = re.sub(r'`(.*?)`', r'\1', content)  # Code
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)  # Links
        
        return content
    
    def _extract_json(self, file_path: str) -> str:
        """Extract text from JSON files"""
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        def extract_text_values(obj):
            if isinstance(obj, dict):
                texts = []
                for value in obj.values():
                    texts.extend(extract_text_values(value))
                return texts
            elif isinstance(obj, list):
                texts = []
                for item in obj:
                    texts.extend(extract_text_values(item))
                return texts
            elif isinstance(obj, str):
                return [obj]
            else:
                return [str(obj)]
        
        text_values = extract_text_values(data)
        return '\n'.join(text_values)
    
    def _extract_text_with_encoding_detection(self, file_path: str) -> str:
        """Extract text with automatic encoding detection"""
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            encoding_result = chardet.detect(raw_data)
            encoding = encoding_result['encoding']
            
            if encoding:
                return raw_data.decode(encoding, errors='ignore')
            else:
                return raw_data.decode('utf-8', errors='ignore')
        except ImportError:
            # Fallback without chardet
            return self._extract_fallback(file_path, '')
    
    def _clean_extracted_text(self, text: str) -> str:
        """Clean extracted text content"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs
        
        # Remove common binary artifacts
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)  # Control characters
        
        return text.strip()
    
    def validate_extracted_content(self, content: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted content and calculate quality score
        
        Args:
            content: Extracted text content
            file_info: File metadata
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'validation_status': 'valid',
            'validation_errors': [],
            'content_quality_score': 0.0
        }
        
        if not content or not content.strip():
            validation_result['validation_status'] = 'invalid'
            validation_result['validation_errors'].append('No content extracted')
            return validation_result
        
        # Calculate quality metrics
        word_count = len(content.split())
        char_count = len(content)
        line_count = len(content.split('\n'))
        
        # Quality scoring factors
        quality_factors = []
        
        # Factor 1: Content length (0-30 points)
        if word_count > 100:
            quality_factors.append(30)
        elif word_count > 50:
            quality_factors.append(20)
        elif word_count > 10:
            quality_factors.append(10)
        else:
            quality_factors.append(5)
            validation_result['validation_errors'].append('Very short content')
        
        # Factor 2: Text coherence (0-25 points)
        coherence_score = self._calculate_coherence_score(content)
        quality_factors.append(coherence_score)
        
        # Factor 3: Character diversity (0-20 points)
        unique_chars = len(set(content.lower()))
        char_diversity = min(20, (unique_chars / 26) * 20)  # Based on alphabet coverage
        quality_factors.append(char_diversity)
        
        # Factor 4: Structure indicators (0-15 points)
        structure_score = self._calculate_structure_score(content)
        quality_factors.append(structure_score)
        
        # Factor 5: Language detection (0-10 points)
        language_score = self._calculate_language_score(content)
        quality_factors.append(language_score)
        
        # Calculate overall quality score
        validation_result['content_quality_score'] = sum(quality_factors) / 100.0
        
        # Set validation status based on quality
        if validation_result['content_quality_score'] < 0.3:
            validation_result['validation_status'] = 'low_quality'
            validation_result['validation_errors'].append('Low content quality score')
        elif validation_result['content_quality_score'] < 0.6:
            validation_result['validation_status'] = 'medium_quality'
        else:
            validation_result['validation_status'] = 'high_quality'
        
        return validation_result
    
    def _calculate_coherence_score(self, content: str) -> float:
        """Calculate text coherence score (0-25)"""
        # Simple coherence metrics
        sentences = re.split(r'[.!?]+', content)
        if len(sentences) < 2:
            return 5.0
        
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        if 5 <= avg_sentence_length <= 30:
            coherence = 25.0
        elif 3 <= avg_sentence_length <= 50:
            coherence = 15.0
        else:
            coherence = 5.0
        
        return coherence
    
    def _calculate_structure_score(self, content: str) -> float:
        """Calculate structure score based on formatting indicators (0-15)"""
        score = 0.0
        
        if '\n\n' in content:
            score += 5.0
        
        if re.search(r'^\s*[-*•]\s+', content, re.MULTILINE):
            score += 3.0
        
        if re.search(r'^\s*\d+\.\s+', content, re.MULTILINE):
            score += 3.0
        
        if re.search(r'^[A-Z][A-Za-z\s]+:?\s*$', content, re.MULTILINE):
            score += 2.0
        
        sentences = re.split(r'[.!?]+', content)
        capitalized = sum(1 for s in sentences if s.strip() and s.strip()[0].isupper())
        if capitalized / max(len(sentences), 1) > 0.7:
            score += 2.0
        
        return min(score, 15.0)
    
    def _calculate_language_score(self, content: str) -> float:
        """Calculate language detection score (0-10)"""
        # Simple language detection based on common patterns
        english_indicators = [
            r'\bthe\b', r'\band\b', r'\bof\b', r'\bto\b', r'\ba\b',
            r'\bin\b', r'\bis\b', r'\bit\b', r'\byou\b', r'\bthat\b'
        ]
        
        matches = sum(1 for pattern in english_indicators 
                     if re.search(pattern, content, re.IGNORECASE))
        
        return min(matches * 1.0, 10.0)
    
    def retry_failed_extraction(self, file_id: str, file_path: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retry extraction for a previously failed file
        
        Args:
            file_id: Unique identifier for the file
            file_path: Path to the file
            file_info: File metadata including previous attempt info
            
        Returns:
            Updated processing results
        """
        logger.info(f"Retrying extraction for file {file_id}")
        
        # Add retry metadata
        retry_info = file_info.copy()
        retry_info['retry_attempt'] = retry_info.get('processing_retries', 0) + 1
        retry_info['retry_timestamp'] = datetime.utcnow().isoformat()
        
        # Process with enhanced logging
        result = self.process_file_with_fallback(file_path, retry_info)
        result['is_retry'] = True
        result['retry_attempt'] = retry_info['retry_attempt']
        
        return result
    
    def get_processing_status(self, file_id: str) -> Dict[str, Any]:
        """
        Get processing status for a file
        
        Args:
            file_id: Unique identifier for the file
            
        Returns:
            Processing status information
        """
        # For now, return a placeholder structure
        return {
            'file_id': file_id,
            'status': 'unknown',
            'last_processed': None,
            'processing_attempts': 0,
            'last_error': None
        }
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file for duplicate detection"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return list(self.supported_formats.keys())
    
    def is_supported_format(self, file_extension: str) -> bool:
        """Check if file format is supported"""
        return file_extension.lower() in self.supported_formats
    
    def _check_dependencies(self) -> Dict[str, Dict[str, Any]]:
        """Check availability of optional dependencies"""
        dependencies = {
            'PyPDF2': {
                'required_for': ['PDF extraction (primary)'],
                'critical': False,
                'available': False,
                'error': None
            },
            'pdfplumber': {
                'required_for': ['PDF extraction (alternative)'],
                'critical': False,
                'available': False,
                'error': None
            },
            'python-docx': {
                'required_for': ['DOCX extraction'],
                'critical': False,
                'available': False,
                'error': None
            },
            'docx2txt': {
                'required_for': ['DOCX extraction (alternative)'],
                'critical': False,
                'available': False,
                'error': None
            },
            'striprtf': {
                'required_for': ['RTF extraction'],
                'critical': False,
                'available': False,
                'error': None
            },
            'beautifulsoup4': {
                'required_for': ['HTML extraction'],
                'critical': False,
                'available': False,
                'error': None
            },
            'chardet': {
                'required_for': ['Automatic encoding detection'],
                'critical': False,
                'available': False,
                'error': None
            },
            'antiword': {
                'required_for': ['DOC extraction'],
                'critical': False,
                'available': False,
                'error': None,
                'type': 'system_command'
            }
        }
        
        # Check Python packages
        for dep_name, dep_info in dependencies.items():
            if dep_info.get('type') == 'system_command':
                # Check system commands
                try:
                    import subprocess
                    result = subprocess.run([dep_name, '--version'], 
                                          capture_output=True, timeout=5)
                    if result.returncode == 0:
                        dep_info['available'] = True
                    else:
                        dep_info['error'] = f"Command '{dep_name}' not found or failed"
                except Exception as e:
                    dep_info['error'] = str(e)
            else:
                # Check Python imports
                try:
                    if dep_name == 'python-docx':
                        import docx
                    elif dep_name == 'beautifulsoup4':
                        from bs4 import BeautifulSoup
                    else:
                        __import__(dep_name)
                    dep_info['available'] = True
                except ImportError as e:
                    dep_info['error'] = str(e)
                except Exception as e:
                    dep_info['error'] = f"Unexpected error: {str(e)}"
        
        return dependencies
    
    def _log_dependency_status(self):
        """Log the status of optional dependencies"""
        available_deps = []
        missing_deps = []
        
        for dep_name, dep_info in self.dependency_status.items():
            if dep_info['available']:
                available_deps.append(dep_name)
            else:
                missing_deps.append(f"{dep_name} ({dep_info['error']})")
        
        if available_deps:
            logger.info(f"Available optional dependencies: {', '.join(available_deps)}")
        
        if missing_deps:
            logger.warning(f"Missing optional dependencies: {', '.join(missing_deps)}")
            logger.info("Some file processing features may use fallback methods. "
                       "Install missing dependencies for optimal performance.")
    
    def get_dependency_status(self) -> Dict[str, Any]:
        """Get current dependency status information"""
        total_deps = len(self.dependency_status)
        available_deps = sum(1 for dep in self.dependency_status.values() if dep['available'])
        
        return {
            'total_dependencies': total_deps,
            'available_dependencies': available_deps,
            'missing_dependencies': total_deps - available_deps,
            'availability_percentage': (available_deps / total_deps) * 100 if total_deps > 0 else 0,
            'dependencies': dict(self.dependency_status),
            'recommendations': self._get_dependency_recommendations()
        }
    
    def _get_dependency_recommendations(self) -> List[str]:
        """Get recommendations for missing dependencies"""
        recommendations = []
        
        for dep_name, dep_info in self.dependency_status.items():
            if not dep_info['available']:
                if dep_name == 'PyPDF2':
                    recommendations.append("Install PyPDF2 for better PDF text extraction: pip install PyPDF2")
                elif dep_name == 'pdfplumber':
                    recommendations.append("Install pdfplumber for high-quality PDF extraction: pip install pdfplumber")
                elif dep_name == 'python-docx':
                    recommendations.append("Install python-docx for DOCX file support: pip install python-docx")
                elif dep_name == 'docx2txt':
                    recommendations.append("Install docx2txt as DOCX fallback: pip install docx2txt")
                elif dep_name == 'striprtf':
                    recommendations.append("Install striprtf for RTF file support: pip install striprtf")
                elif dep_name == 'beautifulsoup4':
                    recommendations.append("Install BeautifulSoup for HTML parsing: pip install beautifulsoup4")
                elif dep_name == 'chardet':
                    recommendations.append("Install chardet for encoding detection: pip install chardet")
                elif dep_name == 'antiword':
                    recommendations.append("Install antiword for DOC file support (system package)")
        
        return recommendations
    
    def refresh_dependency_status(self):
        """Refresh the dependency status check"""
        logger.info("Refreshing dependency status...")
        self.dependency_status = self._check_dependencies()
        self._log_dependency_status()
    
    def get_processing_capabilities(self) -> Dict[str, Any]:
        """Get current processing capabilities based on available dependencies"""
        capabilities = {
            'supported_formats': self.get_supported_formats(),
            'extraction_methods': {},
            'fallback_available': True,
            'quality_assessment': True
        }
        
        # Determine available extraction methods per format
        for file_format in capabilities['supported_formats']:
            methods = []
            
            if file_format == '.pdf':
                if self.dependency_status.get('PyPDF2', {}).get('available'):
                    methods.append('PyPDF2')
                if self.dependency_status.get('pdfplumber', {}).get('available'):
                    methods.append('pdfplumber')
                methods.append('fallback_text')  # Always available
                
            elif file_format == '.docx':
                if self.dependency_status.get('python-docx', {}).get('available'):
                    methods.append('python-docx')
                if self.dependency_status.get('docx2txt', {}).get('available'):
                    methods.append('docx2txt')
                methods.append('fallback_text')
                
            elif file_format == '.doc':
                if self.dependency_status.get('antiword', {}).get('available'):
                    methods.append('antiword')
                if self.dependency_status.get('docx2txt', {}).get('available'):
                    methods.append('docx2txt')
                methods.append('fallback_text')
                
            elif file_format == '.rtf':
                if self.dependency_status.get('striprtf', {}).get('available'):
                    methods.append('striprtf')
                methods.append('regex_cleanup')
                methods.append('fallback_text')
                
            elif file_format in ['.html', '.htm']:
                if self.dependency_status.get('beautifulsoup4', {}).get('available'):
                    methods.append('beautifulsoup')
                methods.append('regex_cleanup')
                methods.append('fallback_text')
                
            else:
                methods.append('direct_text')
                if self.dependency_status.get('chardet', {}).get('available'):
                    methods.append('encoding_detection')
                methods.append('fallback_text')
            
            capabilities['extraction_methods'][file_format] = methods
        
        return capabilities