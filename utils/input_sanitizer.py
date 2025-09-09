"""
Enhanced input sanitization utilities for the Exam Grader application.
"""

import re
import urllib.parse
import base64
import html
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import setup_logger

logger = setup_logger(__name__)

class InputSanitizer:
    """Comprehensive input sanitization for security and data integrity."""

    # Dangerous patterns to detect and remove
    SCRIPT_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"onfocus\s*=",
        r"onblur\s*=",
        r"onchange\s*=",
        r"onsubmit\s*=",
    ]

    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r'(\b(OR|AND)\s+[\'"][^\'"]*[\'"])',
        r"(--|#|/\*|\*/)",
        r"(\bxp_cmdshell\b)",
        r"(\bsp_executesql\b)",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./+",
        r"\.\.\\+",
        r"%2e%2e%2f",
        r"%2e%2e\\",
        r"\.\.%2f",
        r"\.\.%5c",
    ]

    # Command injection patterns
    COMMAND_PATTERNS = [
        r"[;&|`$(){}[\]<>]",
        r"\b(cat|ls|dir|type|copy|move|del|rm|chmod|chown|sudo|su)\b",
        r"(\||&&|\|\||;)",
    ]

    @staticmethod
    def sanitize_string(
        value: str,
        max_length: Optional[int] = None,
        allow_html: bool = False,
        strict: bool = False,
    ) -> str:
        """
        Sanitize string input with various security checks.

        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML tags
            strict: Whether to apply strict sanitization

        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value) if value is not None else ""

        # Normalize unicode characters
        value = unicodedata.normalize("NFKC", value)

        # Remove null bytes and control characters
        value = "".join(char for char in value if ord(char) >= 32 or char in "\t\n\r")

        # Remove dangerous script patterns
        for pattern in InputSanitizer.SCRIPT_PATTERNS:
            value = re.sub(pattern, "", value, flags=re.IGNORECASE | re.DOTALL)

        for pattern in InputSanitizer.SQL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {pattern}")
                if strict:
                    raise ValueError(
                        "Input contains potentially dangerous SQL patterns"
                    )
                value = re.sub(pattern, "", value, flags=re.IGNORECASE)

        for pattern in InputSanitizer.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Path traversal attempt detected: {pattern}")
                if strict:
                    raise ValueError("Input contains path traversal patterns")
                value = re.sub(pattern, "", value, flags=re.IGNORECASE)

        if strict:
            for pattern in InputSanitizer.COMMAND_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"Command injection attempt detected: {pattern}")
                    raise ValueError(
                        "Input contains potentially dangerous command patterns"
                    )

        # HTML sanitization
        if not allow_html:
            value = html.escape(value)
        else:
            # Allow only safe HTML tags
            safe_tags = ["b", "i", "u", "em", "strong", "p", "br", "span"]
            # This is a simplified approach - in production, use a library like bleach
            value = re.sub(
                r"<(?!/?(?:" + "|".join(safe_tags) + r")\b)[^>]*>", "", value
            )

        # Apply length limit
        if max_length and len(value) > max_length:
            value = value[:max_length]
            logger.debug(f"String truncated to {max_length} characters")

        return value.strip()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for safe storage.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        if not filename:
            return "unnamed_file"

        # Remove path components
        filename = filename.split("/")[-1].split("\\")[-1]

        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)

        # Remove leading/trailing dots and spaces
        filename = filename.strip(". ")

        # Ensure filename is not empty
        if not filename:
            filename = "unnamed_file"

        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            max_name_length = 255 - len(ext) - 1 if ext else 255
            filename = name[:max_name_length] + ("." + ext if ext else "")

        return filename

    @staticmethod
    def sanitize_json(data: Any, max_depth: int = 10, max_items: int = 1000) -> Any:
        """
        Sanitize JSON data recursively.

        Args:
            data: JSON data to sanitize
            max_depth: Maximum nesting depth
            max_items: Maximum number of items in collections

        Returns:
            Sanitized JSON data
        """

        def _sanitize_recursive(obj, depth=0):
            if depth > max_depth:
                logger.warning(f"JSON depth limit exceeded: {depth}")
                return None

            if isinstance(obj, str):
                return InputSanitizer.sanitize_string(obj, max_length=10000)
            elif isinstance(obj, (int, float, bool)) or obj is None:
                return obj
            elif isinstance(obj, list):
                if len(obj) > max_items:
                    logger.warning(f"JSON list size limit exceeded: {len(obj)}")
                    obj = obj[:max_items]
                return [_sanitize_recursive(item, depth + 1) for item in obj]
            elif isinstance(obj, dict):
                if len(obj) > max_items:
                    logger.warning(f"JSON dict size limit exceeded: {len(obj)}")
                    # Keep first max_items items
                    obj = dict(list(obj.items())[:max_items])
                return {
                    InputSanitizer.sanitize_string(
                        str(k), max_length=100
                    ): _sanitize_recursive(v, depth + 1)
                    for k, v in obj.items()
                }
            else:
                # Convert unknown types to string and sanitize
                return InputSanitizer.sanitize_string(str(obj), max_length=1000)

        return _sanitize_recursive(data)

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email address format.

        Args:
            email: Email address to validate

        Returns:
            True if valid email format
        """
        if not email or len(email) > 254:
            return False

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_url(url: str, allowed_schemes: List[str] = None) -> bool:
        """
        Validate URL format and scheme.

        Args:
            url: URL to validate
            allowed_schemes: List of allowed URL schemes

        Returns:
            True if valid URL
        """
        if not url:
            return False

        if allowed_schemes is None:
            allowed_schemes = ["http", "https"]

        try:
            parsed = urllib.parse.urlparse(url)
            return (
                parsed.scheme in allowed_schemes and parsed.netloc and len(url) <= 2048
            )
        except Exception:
            return False

    @staticmethod
    def sanitize_base64(data: str) -> Optional[bytes]:
        """
        Safely decode base64 data.

        Args:
            data: Base64 encoded string

        Returns:
            Decoded bytes or None if invalid
        """
        try:
            # Remove whitespace and validate base64 format
            data = re.sub(r"\s+", "", data)
            if not re.match(r"^[A-Za-z0-9+/]*={0,2}$", data):
                return None

            # Decode and validate size
            decoded = base64.b64decode(data)
            if len(decoded) > 50 * 1024 * 1024:  # 50MB limit
                logger.warning("Base64 data exceeds size limit")
                return None

            return decoded
        except Exception as e:
            logger.warning(f"Invalid base64 data: {str(e)}")
            return None

    @staticmethod
    def detect_encoding_attacks(data: str) -> List[str]:
        """
        Detect various encoding-based attacks.

        Args:
            data: Input data to check

        Returns:
            List of detected attack types
        """
        attacks = []

        if "%" in data:
            try:
                decoded = urllib.parse.unquote(data)
                if decoded != data:
                    for pattern in InputSanitizer.SCRIPT_PATTERNS:
                        if re.search(pattern, decoded, re.IGNORECASE):
                            attacks.append("url_encoded_script")
                            break
            except Exception:
                pass

        if "&" in data and ";" in data:
            decoded = html.unescape(data)
            if decoded != data:
                for pattern in InputSanitizer.SCRIPT_PATTERNS:
                    if re.search(pattern, decoded, re.IGNORECASE):
                        attacks.append("html_entity_encoded_script")
                        break

        normalized = unicodedata.normalize("NFKC", data)
        if normalized != data:
            for pattern in InputSanitizer.SCRIPT_PATTERNS:
                if re.search(pattern, normalized, re.IGNORECASE):
                    attacks.append("unicode_normalization_attack")
                    break

        return attacks

def sanitize_form_data(
    form_data: Dict[str, Any], field_rules: Optional[Dict[str, Dict]] = None
) -> Dict[str, Any]:
    """
    Sanitize form data with field-specific rules.

    Args:
        form_data: Form data to sanitize
        field_rules: Dictionary of field-specific sanitization rules

    Returns:
        Sanitized form data
    """
    if field_rules is None:
        field_rules = {}

    sanitized = {}

    for field, value in form_data.items():
        rules = field_rules.get(field, {})

        if isinstance(value, str):
            sanitized[field] = InputSanitizer.sanitize_string(
                value,
                max_length=rules.get("max_length"),
                allow_html=rules.get("allow_html", False),
                strict=rules.get("strict", False),
            )
        elif isinstance(value, list):
            sanitized[field] = [
                (
                    InputSanitizer.sanitize_string(str(item))
                    if isinstance(item, str)
                    else item
                )
                for item in value[: rules.get("max_items", 100)]
            ]
        else:
            sanitized[field] = value

    return sanitized

def validate_file_upload(
    file_data: bytes, filename: str, allowed_types: List[str] = None
) -> Tuple[bool, str]:
    """
    Validate uploaded file for security.

    Args:
        file_data: File content as bytes
        filename: Original filename
        allowed_types: List of allowed file extensions

    Returns:
        Tuple of (is_valid, error_message)
    """
    if allowed_types is None:
        allowed_types = [".txt", ".pdf", ".docx", ".jpg", ".png"]

    # Check filename
    if not filename:
        return False, "No filename provided"

    # Sanitize filename
    safe_filename = InputSanitizer.sanitize_filename(filename)
    if safe_filename != filename:
        logger.warning(f"Filename sanitized: {filename} -> {safe_filename}")

    # Check file extension
    ext = "." + filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    if ext not in allowed_types:
        return False, f"File type {ext} not allowed"

    # Check file size
    if len(file_data) > 50 * 1024 * 1024:  # 50MB
        return False, "File too large"

    if ext in [".txt", ".csv", ".json"]:
        try:
            content = file_data.decode("utf-8", errors="ignore")
            attacks = InputSanitizer.detect_encoding_attacks(content)
            if attacks:
                return (
                    False,
                    f"Potential security threats detected: {', '.join(attacks)}",
                )
        except Exception:
            pass

    file_signatures = {
        ".pdf": [b"%PDF"],
        ".jpg": [b"\xff\xd8\xff"],
        ".png": [b"\x89PNG\r\n\x1a\n"],
        ".docx": [b"PK\x03\x04"],  # ZIP-based format
    }

    if ext in file_signatures:
        valid_signature = any(file_data.startswith(sig) for sig in file_signatures[ext])
        if not valid_signature:
            return False, f"Invalid file signature for {ext} file"

    return True, "File validation passed"
