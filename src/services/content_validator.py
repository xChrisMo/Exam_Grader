"""
Content Validator

This module provides comprehensive content validation and quality assessment
for extracted text content, including quality scoring, language detection,
and content structure analysis.
"""

import re
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple

from utils.logger import logger

class ContentQuality(Enum):
    """Content quality levels"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    INVALID = "invalid"

class ValidationStatus(Enum):
    """Validation status levels"""

    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    FAILED = "failed"

@dataclass
class QualityMetrics:
    """Quality metrics for content assessment"""

    word_count: int = 0
    character_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    unique_words: int = 0
    average_word_length: float = 0.0
    average_sentence_length: float = 0.0
    readability_score: float = 0.0
    language_confidence: float = 0.0
    structure_score: float = 0.0
    coherence_score: float = 0.0
    diversity_score: float = 0.0

@dataclass
class ValidationResult:
    """Result of content validation"""

    status: ValidationStatus
    quality: ContentQuality
    overall_score: float
    metrics: QualityMetrics
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ContentValidator:
    """Validates and assesses quality of extracted content"""

    def __init__(self):
        self.min_word_count = 5
        self.min_character_count = 20
        self.max_repetition_ratio = 0.7
        self.min_language_confidence = 0.3

        self.english_indicators = [
            r"\bthe\b",
            r"\band\b",
            r"\bof\b",
            r"\bto\b",
            r"\ba\b",
            r"\bin\b",
            r"\bis\b",
            r"\bit\b",
            r"\byou\b",
            r"\bthat\b",
            r"\bfor\b",
            r"\bwith\b",
            r"\bas\b",
            r"\bthis\b",
            r"\bhave\b",
            r"\bfrom\b",
            r"\bor\b",
            r"\bone\b",
            r"\bhad\b",
            r"\bby\b",
            r"\bword\b",
            r"\bbut\b",
            r"\bnot\b",
            r"\bwhat\b",
            r"\ball\b",
        ]

        self.structure_patterns = {
            "headers": r"^[A-Z][A-Za-z\s]+:?\s*$",
            "bullet_points": r"^\s*[-*•]\s+",
            "numbered_lists": r"^\s*\d+\.\s+",
            "paragraphs": r"\n\s*\n",
            "sentences": r"[.!?]+\s+",
            "capitalized_sentences": r"[.!?]+\s+[A-Z]",
        }

    def validate_content(
        self, content: str, file_info: Dict[str, Any] = None
    ) -> ValidationResult:
        """
        Validate content and assess its quality

        Args:
            content: Text content to validate
            file_info: Optional file metadata

        Returns:
            ValidationResult with quality assessment
        """
        if file_info is None:
            file_info = {}

        result = ValidationResult(
            status=ValidationStatus.VALID,
            quality=ContentQuality.GOOD,
            overall_score=0.0,
            metrics=QualityMetrics(),
        )

        # Basic validation checks
        if not self._basic_validation(content, result):
            return result

        # Calculate quality metrics
        result.metrics = self._calculate_metrics(content)

        # Perform quality assessments
        self._assess_content_length(result)
        self._assess_language_quality(content, result)
        self._assess_structure_quality(content, result)
        self._assess_coherence_quality(content, result)
        self._assess_diversity_quality(content, result)
        self._detect_common_issues(content, result)

        # Calculate overall score and quality level
        result.overall_score = self._calculate_overall_score(result.metrics)
        result.quality = self._determine_quality_level(result.overall_score)

        # Add metadata
        result.metadata.update(
            {
                "validation_timestamp": datetime.now(timezone.utc).isoformat(),
                "file_info": file_info,
                "validator_version": "1.0",
            }
        )

        # Generate suggestions
        self._generate_suggestions(result)

        logger.debug(
            f"Content validation completed: {result.quality.value} "
            f"(score: {result.overall_score:.2f})"
        )

        return result

    def _basic_validation(self, content: str, result: ValidationResult) -> bool:
        """Perform basic validation checks"""
        if not content:
            result.status = ValidationStatus.FAILED
            result.quality = ContentQuality.INVALID
            result.errors.append("Content is empty")
            return False

        if not content.strip():
            result.status = ValidationStatus.FAILED
            result.quality = ContentQuality.INVALID
            result.errors.append("Content contains only whitespace")
            return False

        # Check minimum length requirements
        word_count = len(content.split())
        char_count = len(content.strip())

        if word_count < self.min_word_count:
            result.status = ValidationStatus.WARNING
            result.warnings.append(
                f"Content has only {word_count} words (minimum: {self.min_word_count})"
            )

        if char_count < self.min_character_count:
            result.status = ValidationStatus.WARNING
            result.warnings.append(
                f"Content has only {char_count} characters (minimum: {self.min_character_count})"
            )

        return True

    def _calculate_metrics(self, content: str) -> QualityMetrics:
        """Calculate basic content metrics"""
        metrics = QualityMetrics()

        # Basic counts
        metrics.character_count = len(content)
        words = content.split()
        metrics.word_count = len(words)

        if metrics.word_count > 0:
            metrics.unique_words = len(set(word.lower() for word in words))
            metrics.average_word_length = sum(len(word) for word in words) / len(words)

        # Sentence analysis
        sentences = re.split(r"[.!?]+", content)
        sentences = [s.strip() for s in sentences if s.strip()]
        metrics.sentence_count = len(sentences)

        if metrics.sentence_count > 0:
            total_words_in_sentences = sum(
                len(sentence.split()) for sentence in sentences
            )
            metrics.average_sentence_length = (
                total_words_in_sentences / metrics.sentence_count
            )

        # Paragraph analysis
        paragraphs = re.split(r"\n\s*\n", content)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        metrics.paragraph_count = len(paragraphs)

        return metrics

    def _assess_content_length(self, result: ValidationResult):
        """Assess content based on length"""
        metrics = result.metrics

        # Word count assessment
        if metrics.word_count < 10:
            result.warnings.append(
                "Very short content - may not be sufficient for analysis"
            )
        elif metrics.word_count < 50:
            result.warnings.append("Short content - consider if more content is needed")

        # Character count assessment
        if metrics.character_count > 100000:  # 100KB
            result.warnings.append("Very long content - processing may be slow")

    def _assess_language_quality(self, content: str, result: ValidationResult):
        """Assess language quality and detect language"""
        # Simple English language detection
        english_matches = 0
        total_indicators = len(self.english_indicators)

        for pattern in self.english_indicators:
            if re.search(pattern, content, re.IGNORECASE):
                english_matches += 1

        language_confidence = english_matches / total_indicators
        result.metrics.language_confidence = language_confidence

        if language_confidence < self.min_language_confidence:
            result.warnings.append(
                f"Low English language confidence ({language_confidence:.2f})"
            )

        words = content.lower().split()
        if len(words) > 10:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1

            most_common_count = max(word_counts.values())
            repetition_ratio = most_common_count / len(words)

            if repetition_ratio > self.max_repetition_ratio:
                result.warnings.append(
                    f"High word repetition detected ({repetition_ratio:.2f})"
                )

    def _assess_structure_quality(self, content: str, result: ValidationResult):
        """Assess content structure quality"""
        structure_score = 0.0
        max_score = 100.0

        if re.search(self.structure_patterns["paragraphs"], content):
            structure_score += 20
        else:
            result.suggestions.append(
                "Consider adding paragraph breaks for better readability"
            )

        if re.search(self.structure_patterns["headers"], content, re.MULTILINE):
            structure_score += 15

        has_bullets = bool(
            re.search(self.structure_patterns["bullet_points"], content, re.MULTILINE)
        )
        has_numbers = bool(
            re.search(self.structure_patterns["numbered_lists"], content, re.MULTILINE)
        )

        if has_bullets or has_numbers:
            structure_score += 15

        # Check sentence structure (25 points)
        sentences = re.split(r"[.!?]+", content)
        valid_sentences = [s for s in sentences if s.strip() and len(s.split()) >= 3]

        if len(valid_sentences) > 0:
            sentence_score = min(
                25, (len(valid_sentences) / max(1, result.metrics.sentence_count)) * 25
            )
            structure_score += sentence_score

        # Check capitalization (25 points)
        capitalized_sentences = len(
            re.findall(self.structure_patterns["capitalized_sentences"], content)
        )
        if result.metrics.sentence_count > 0:
            capitalization_ratio = capitalized_sentences / result.metrics.sentence_count
            structure_score += min(25, capitalization_ratio * 25)

        result.metrics.structure_score = structure_score / max_score

        if result.metrics.structure_score < 0.3:
            result.warnings.append("Poor content structure detected")

    def _assess_coherence_quality(self, content: str, result: ValidationResult):
        """Assess content coherence"""
        coherence_score = 0.0

        # Check average sentence length (reasonable range: 10-25 words)
        avg_sentence_length = result.metrics.average_sentence_length
        if 10 <= avg_sentence_length <= 25:
            coherence_score += 0.4
        elif 5 <= avg_sentence_length <= 35:
            coherence_score += 0.2
        else:
            result.suggestions.append(
                "Consider adjusting sentence length for better readability"
            )

        # Check average word length (reasonable range: 4-7 characters)
        avg_word_length = result.metrics.average_word_length
        if 4 <= avg_word_length <= 7:
            coherence_score += 0.3
        elif 3 <= avg_word_length <= 9:
            coherence_score += 0.15

        # Check paragraph distribution
        if result.metrics.paragraph_count > 0 and result.metrics.word_count > 0:
            words_per_paragraph = (
                result.metrics.word_count / result.metrics.paragraph_count
            )
            if 50 <= words_per_paragraph <= 200:
                coherence_score += 0.3
            elif 20 <= words_per_paragraph <= 300:
                coherence_score += 0.15

        result.metrics.coherence_score = coherence_score

        if coherence_score < 0.3:
            result.warnings.append("Content coherence could be improved")

    def _assess_diversity_quality(self, content: str, result: ValidationResult):
        """Assess content diversity"""
        if result.metrics.word_count == 0:
            result.metrics.diversity_score = 0.0
            return

        # Vocabulary diversity (unique words / total words)
        vocabulary_diversity = result.metrics.unique_words / result.metrics.word_count

        # Character diversity (unique characters / total characters)
        unique_chars = len(set(content.lower()))
        char_diversity = unique_chars / max(1, result.metrics.character_count)

        # Combined diversity score
        diversity_score = (vocabulary_diversity * 0.7) + (char_diversity * 0.3)
        result.metrics.diversity_score = diversity_score

        if diversity_score < 0.3:
            result.warnings.append(
                "Low content diversity - consider varying vocabulary"
            )
        elif diversity_score > 0.8:
            result.suggestions.append("Good vocabulary diversity detected")

    def _detect_common_issues(self, content: str, result: ValidationResult):
        """Detect common content issues"""

        if re.search(r"\s{5,}", content):
            result.warnings.append("Excessive whitespace detected")

        if re.search(r"(.)\1{4,}", content):
            result.warnings.append(
                "Repeated characters detected - may indicate extraction errors"
            )

        if re.search(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", content):
            result.warnings.append("Binary artifacts detected in text")

        incomplete_sentences = re.findall(r"[a-z]\s*$", content, re.MULTILINE)
        if len(incomplete_sentences) > result.metrics.sentence_count * 0.3:
            result.warnings.append("Many incomplete sentences detected")

        words_without_punctuation = len(re.findall(r"\b\w+\b", content))
        punctuation_marks = len(re.findall(r"[.!?;,:]", content))

        if (
            words_without_punctuation > 20
            and punctuation_marks < words_without_punctuation * 0.1
        ):
            result.warnings.append(
                "Low punctuation density - may indicate extraction issues"
            )

    def _calculate_overall_score(self, metrics: QualityMetrics) -> float:
        """Calculate overall quality score (0-1)"""
        scores = []

        # Length score (0-0.2)
        if metrics.word_count >= 100:
            length_score = 0.2
        elif metrics.word_count >= 50:
            length_score = 0.15
        elif metrics.word_count >= 20:
            length_score = 0.1
        else:
            length_score = 0.05
        scores.append(length_score)

        # Language score (0-0.25)
        language_score = min(0.25, metrics.language_confidence * 0.25)
        scores.append(language_score)

        # Structure score (0-0.2)
        structure_score = metrics.structure_score * 0.2
        scores.append(structure_score)

        # Coherence score (0-0.2)
        coherence_score = metrics.coherence_score * 0.2
        scores.append(coherence_score)

        # Diversity score (0-0.15)
        diversity_score = metrics.diversity_score * 0.15
        scores.append(diversity_score)

        return sum(scores)

    def _determine_quality_level(self, overall_score: float) -> ContentQuality:
        """Determine quality level based on overall score"""
        if overall_score >= 0.8:
            return ContentQuality.EXCELLENT
        elif overall_score >= 0.6:
            return ContentQuality.GOOD
        elif overall_score >= 0.4:
            return ContentQuality.FAIR
        elif overall_score >= 0.2:
            return ContentQuality.POOR
        else:
            return ContentQuality.INVALID

    def _generate_suggestions(self, result: ValidationResult):
        """Generate improvement suggestions based on validation results"""
        metrics = result.metrics

        if metrics.word_count < 50:
            result.suggestions.append(
                "Consider extracting more content or checking extraction method"
            )

        if metrics.average_sentence_length < 5:
            result.suggestions.append(
                "Sentences appear very short - check for extraction fragmentation"
            )
        elif metrics.average_sentence_length > 30:
            result.suggestions.append(
                "Sentences appear very long - may need better sentence segmentation"
            )

        if metrics.paragraph_count == 0:
            result.suggestions.append(
                "No paragraph breaks detected - consider improving text structure"
            )

        if metrics.language_confidence < 0.5:
            result.suggestions.append(
                "Low English language confidence - verify content language or extraction quality"
            )

        if metrics.diversity_score < 0.3:
            result.suggestions.append(
                "Low vocabulary diversity - may indicate repetitive or poor quality content"
            )

        if result.quality == ContentQuality.POOR:
            result.suggestions.append(
                "Consider trying alternative extraction methods for better quality"
            )

    def validate_batch(
        self, contents: List[Tuple[str, Dict[str, Any]]]
    ) -> List[ValidationResult]:
        """Validate multiple content items"""
        results = []

        for content, file_info in contents:
            try:
                result = self.validate_content(content, file_info)
                results.append(result)
            except Exception as e:
                logger.error(f"Error validating content: {e}")
                error_result = ValidationResult(
                    status=ValidationStatus.ERROR,
                    quality=ContentQuality.INVALID,
                    overall_score=0.0,
                    metrics=QualityMetrics(),
                    errors=[f"Validation error: {str(e)}"],
                )
                results.append(error_result)

        return results

    def get_quality_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Get summary statistics for a batch of validation results"""
        if not results:
            return {}

        quality_counts = {}
        status_counts = {}
        total_score = 0.0

        for result in results:
            quality_counts[result.quality.value] = (
                quality_counts.get(result.quality.value, 0) + 1
            )
            status_counts[result.status.value] = (
                status_counts.get(result.status.value, 0) + 1
            )
            total_score += result.overall_score

        return {
            "total_items": len(results),
            "average_score": total_score / len(results),
            "quality_distribution": quality_counts,
            "status_distribution": status_counts,
            "excellent_count": quality_counts.get("excellent", 0),
            "good_count": quality_counts.get("good", 0),
            "fair_count": quality_counts.get("fair", 0),
            "poor_count": quality_counts.get("poor", 0),
            "invalid_count": quality_counts.get("invalid", 0),
        }

# Global instance
content_validator = ContentValidator()
