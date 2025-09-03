"""Enhanced Input Validation System for Exam Grader Application.

This module provides comprehensive input validation and sanitization
for all user inputs, including forms, files, and API requests.
"""

import hashlib
import html
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from utils.logger import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

try:
    pass
except ImportError:
    # Fallback error classes
    class ValidationError(Exception):
        pass

    class SecurityError(Exception):
        pass


class FileValidator:
    """Enhanced file validation with security checks."""

    # Allowed file extensions and their MIME types
    ALLOWED_EXTENSIONS = {
        ".pdf": ["application/pdf"],
        ".docx": [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ],
        ".doc": ["application/msword"],
        ".txt": ["text/plain"],
        ".jpg": ["image/jpeg"],
        ".jpeg": ["image/jpeg"],
        ".png": ["image/png"],
        ".gif": ["image/gif"],
        ".bmp": ["image/bmp"],
        ".tiff": ["image/tiff"],
        ".tif": ["image/tiff"],
    }

    # Maximum file sizes by category (in bytes)
    MAX_FILE_SIZES = {
        "document": 50 * 1024 * 1024,  # 50MB for documents
        "image": 20 * 1024 * 1024,  # 20MB for images
        "default": 25 * 1024 * 1024,  # 25MB default
    }

    # Dangerous file signatures (magic bytes)
    DANGEROUS_SIGNATURES = {
        b"\x4d\x5a": "PE executable",
        b"\x7f\x45\x4c\x46": "ELF executable",
        b"\xca\xfe\xba\xbe": "Java class file",
        b"\xfe\xed\xfa": "Mach-O executable",
        b"\x50\x4b\x03\x04": "ZIP archive (potential)",
        b"\x1f\x8b\x08": "GZIP archive",
        b"\x42\x5a\x68": "BZIP2 archive",
    }

    @classmethod
    def validate_file(
        cls, file_obj, filename: str
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Comprehensive file validation.

        Args:
            file_obj: File object to validate
            filename: Original filename

        Returns:
            Tuple of (is_valid, error_message, file_info)
        """
        try:
            file_info = {
                "original_filename": filename,
                "size": 0,
                "extension": "",
                "mime_type": "",
                "hash": "",
                "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Validate filename
            is_valid, error = cls._validate_filename(filename)
            if not is_valid:
                return False, error, file_info

            # Get file extension
            file_path = Path(filename)
            extension = file_path.suffix.lower()
            file_info["extension"] = extension

            if extension not in cls.ALLOWED_EXTENSIONS:
                return False, f"File type '{extension}' is not allowed", file_info

            file_obj.seek(0)
            file_content = file_obj.read()
            file_obj.seek(0)  # Reset for later use

            file_info["size"] = len(file_content)

            # Validate file size
            is_valid, error = cls._validate_file_size(file_content, extension)
            if not is_valid:
                return False, error, file_info

            # Validate file signature
            is_valid, error = cls._validate_file_signature(file_content, extension)
            if not is_valid:
                return False, error, file_info

            # Validate MIME type
            is_valid, error, mime_type = cls._validate_mime_type(file_content, filename)
            if not is_valid:
                return False, error, file_info

            file_info["mime_type"] = mime_type

            # Generate file hash
            file_info["hash"] = cls._generate_file_hash(file_content)

            # Additional content validation
            is_valid, error = cls._validate_file_content(file_content, extension)
            if not is_valid:
                return False, error, file_info

            return True, None, file_info

        except Exception as e:
            logger.error(f"Error validating file {filename}: {str(e)}")
            return False, f"File validation failed: {str(e)}", file_info

    @classmethod
    def _validate_filename(cls, filename: str) -> Tuple[bool, Optional[str]]:
        """Validate filename for security."""
        if not filename or len(filename.strip()) == 0:
            return False, "Filename cannot be empty"

        if len(filename) > 255:
            return False, "Filename too long (max 255 characters)"

        dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "\x00"]
        for char in dangerous_chars:
            if char in filename:
                return False, f"Filename contains invalid character: {char}"

        if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
            return False, "Filename contains path traversal patterns"

        reserved_names = [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        ]

        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            return False, f"Filename uses reserved name: {name_without_ext}"

        return True, None

    @classmethod
    def _validate_file_size(
        cls, file_content: bytes, extension: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate file size based on type."""
        file_size = len(file_content)

        # Determine file category
        if extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif"]:
            category = "image"
        elif extension in [".pdf", ".docx", ".doc", ".txt"]:
            category = "document"
        else:
            category = "default"

        max_size = cls.MAX_FILE_SIZES.get(category, cls.MAX_FILE_SIZES["default"])

        if file_size > max_size:
            max_mb = max_size / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            return False, f"File too large: {actual_mb:.1f}MB (max: {max_mb:.1f}MB)"

        if file_size == 0:
            return False, "File is empty"

        return True, None

    @classmethod
    def _validate_file_signature(
        cls, file_content: bytes, extension: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate file signature (magic bytes)."""
        if len(file_content) < 4:
            return False, "File too small to validate signature"

        for signature, description in cls.DANGEROUS_SIGNATURES.items():
            if file_content.startswith(signature):
                return False, f"Dangerous file type detected: {description}"

        # Validate specific file type signatures
        signature_checks = {
            ".pdf": [b"%PDF-"],
            ".jpg": [b"\xff\xd8\xff"],
            ".jpeg": [b"\xff\xd8\xff"],
            ".png": [b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"],
            ".gif": [b"GIF87a", b"GIF89a"],
            ".bmp": [b"BM"],
            ".tiff": [b"II*\x00", b"MM\x00*"],
            ".tif": [b"II*\x00", b"MM\x00*"],
        }

        if extension in signature_checks:
            valid_signatures = signature_checks[extension]
            if not any(file_content.startswith(sig) for sig in valid_signatures):
                return False, f"Invalid file signature for {extension} file"

        return True, None

    @classmethod
    def _validate_mime_type(
        cls, file_content: bytes, filename: str
    ) -> Tuple[bool, Optional[str], str]:
        """Validate MIME type."""
        mime_type, _ = mimetypes.guess_type(filename)

        if not mime_type:
            return False, "Could not determine MIME type", ""

        # Get file extension
        extension = Path(filename).suffix.lower()

        if extension in cls.ALLOWED_EXTENSIONS:
            allowed_mimes = cls.ALLOWED_EXTENSIONS[extension]
            if mime_type not in allowed_mimes:
                return (
                    False,
                    f"MIME type '{mime_type}' not allowed for {extension} files",
                    mime_type,
                )

        return True, None, mime_type

    @classmethod
    def _validate_file_content(
        cls, file_content: bytes, extension: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate file content for malicious patterns."""
        try:
            content_str = file_content.decode("utf-8", errors="ignore")
        except:
            content_str = str(file_content)

        if extension in [".txt"]:
            script_patterns = [
                r"<script[^>]*>",
                r"javascript:",
                r"vbscript:",
                r"data:text/html",
                r"eval\s*\(",
                r"document\.write",
            ]

            for pattern in script_patterns:
                if re.search(pattern, content_str, re.IGNORECASE):
                    return False, "Potentially malicious script content detected"

        executable_patterns = [
            b"\x4d\x5a",  # PE header
            b"\x7f\x45\x4c\x46",  # ELF header
            b"\xca\xfe\xba\xbe",  # Java class
        ]

        for pattern in executable_patterns:
            if pattern in file_content:
                return False, "Embedded executable content detected"

        return True, None

    @classmethod
    def _generate_file_hash(cls, file_content: bytes) -> str:
        """Generate SHA-256 hash of file content."""
        return hashlib.sha256(file_content).hexdigest()


class FormValidator:
    """Enhanced form input validation."""

    # Common validation patterns
    PATTERNS = {
        "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "username": r"^[a-zA-Z0-9_]{3,30}$",
        "password": r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$",
        "phone": r"^[\+]?[1-9]?[0-9]{7,15}$",
        "url": r"^https?:\/\/(?:[-\w.])+(?:\:[0-9]+)?(?:\/(?:[\w\/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$",
    }

    # Dangerous patterns to detect
    DANGEROUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"data:text/html",
        r"(?i)(union|select|insert|update|delete|drop|create|alter)\s+",
        r"(?i)(exec|execute|sp_|xp_)\s*\(",
        r"\.\.[\\/]",
        r"%2e%2e[\\/]",
        r"(?i)(cmd|powershell|bash|sh)\s+",
    ]

    @classmethod
    def validate_form_data(
        cls, form_data: Dict[str, Any], validation_rules: Dict[str, Dict[str, Any]]
    ) -> Tuple[bool, Dict[str, List[str]], Dict[str, Any]]:
        """Validate form data against rules.

        Args:
            form_data: Form data to validate
            validation_rules: Validation rules for each field

        Returns:
            Tuple of (is_valid, errors, sanitized_data)
        """
        errors = {}
        sanitized_data = {}

        try:
            for field_name, rules in validation_rules.items():
                field_errors = []
                value = form_data.get(field_name)

                if rules.get("required", False) and (
                    value is None or str(value).strip() == ""
                ):
                    field_errors.append(f"{field_name} is required")
                    continue

                if value is None or str(value).strip() == "":
                    sanitized_data[field_name] = ""
                    continue

                str_value = str(value).strip()

                # Length validation
                min_length = rules.get("min_length")
                max_length = rules.get("max_length")

                if min_length and len(str_value) < min_length:
                    field_errors.append(
                        f"{field_name} must be at least {min_length} characters"
                    )

                if max_length and len(str_value) > max_length:
                    field_errors.append(
                        f"{field_name} must be no more than {max_length} characters"
                    )

                # Pattern validation
                pattern = rules.get("pattern")
                if pattern:
                    if pattern in cls.PATTERNS:
                        pattern = cls.PATTERNS[pattern]

                    if not re.match(pattern, str_value):
                        field_errors.append(f"{field_name} format is invalid")

                # Custom validation function
                custom_validator = rules.get("validator")
                if custom_validator and callable(custom_validator):
                    try:
                        is_valid, error_msg = custom_validator(str_value)
                        if not is_valid:
                            field_errors.append(error_msg or f"{field_name} is invalid")
                    except Exception as e:
                        logger.error(
                            f"Custom validator error for {field_name}: {str(e)}"
                        )
                        field_errors.append(f"{field_name} validation failed")

                # Security validation
                if cls._contains_dangerous_pattern(str_value):
                    field_errors.append(
                        f"{field_name} contains potentially dangerous content"
                    )

                # Sanitize the value
                sanitized_value = cls._sanitize_input(
                    str_value, rules.get("sanitize_html", True)
                )
                sanitized_data[field_name] = sanitized_value

                if field_errors:
                    errors[field_name] = field_errors

            is_valid = len(errors) == 0
            return is_valid, errors, sanitized_data

        except Exception as e:
            logger.error(f"Error validating form data: {str(e)}")
            return False, {"general": ["Form validation failed"]}, {}

    @classmethod
    def _contains_dangerous_pattern(cls, text: str) -> bool:
        """Check if text contains dangerous patterns."""
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def _sanitize_input(cls, text: str, sanitize_html: bool = True) -> str:
        """Sanitize input text."""
        if sanitize_html:
            # HTML escape
            text = html.escape(text)

        # Remove null bytes
        text = text.replace("\x00", "")

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text


class APIValidator:
    """API request validation."""

    @classmethod
    def validate_json_request(
        cls, request_data: Any, schema: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Any]:
        """Validate JSON request against schema.

        Args:
            request_data: JSON request data
            schema: Validation schema

        Returns:
            Tuple of (is_valid, error_message, validated_data)
        """
        try:
            # Basic type checking
            if not isinstance(request_data, dict):
                return False, "Request data must be a JSON object", None

            validated_data = {}

            # Check required fields
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in request_data:
                    return False, f"Required field '{field}' is missing", None

            # Validate each field
            properties = schema.get("properties", {})
            for field_name, field_schema in properties.items():
                if field_name in request_data:
                    value = request_data[field_name]

                    # Type validation
                    expected_type = field_schema.get("type")
                    if expected_type and not cls._validate_type(value, expected_type):
                        return (
                            False,
                            f"Field '{field_name}' must be of type {expected_type}",
                            None,
                        )

                    # Additional validations
                    if expected_type == "string":
                        max_length = field_schema.get("maxLength")
                        if max_length and len(str(value)) > max_length:
                            return (
                                False,
                                f"Field '{field_name}' exceeds maximum length of {max_length}",
                                None,
                            )

                        if FormValidator._contains_dangerous_pattern(str(value)):
                            return (
                                False,
                                f"Field '{field_name}' contains potentially dangerous content",
                                None,
                            )

                    validated_data[field_name] = value

            return True, None, validated_data

        except Exception as e:
            logger.error(f"Error validating JSON request: {str(e)}")
            return False, "JSON validation failed", None

    @classmethod
    def _validate_type(cls, value: Any, expected_type: str) -> bool:
        """Validate value type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        expected_python_type = type_map.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)

        return True


# Global validator instances
file_validator = FileValidator()
form_validator = FormValidator()
api_validator = APIValidator()


def validate_file_upload(
    file_obj, filename: str
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Convenience function for file validation.

    Args:
        file_obj: File object to validate
        filename: Original filename

    Returns:
        Tuple of (is_valid, error_message, file_info)
    """
    return file_validator.validate_file(file_obj, filename)


def validate_form_input(
    form_data: Dict[str, Any], validation_rules: Dict[str, Dict[str, Any]]
) -> Tuple[bool, Dict[str, List[str]], Dict[str, Any]]:
    """Convenience function for form validation.

    Args:
        form_data: Form data to validate
        validation_rules: Validation rules

    Returns:
        Tuple of (is_valid, errors, sanitized_data)
    """
    return form_validator.validate_form_data(form_data, validation_rules)


def validate_api_request(
    request_data: Any, schema: Dict[str, Any]
) -> Tuple[bool, Optional[str], Any]:
    """Convenience function for API validation.

    Args:
        request_data: API request data
        schema: Validation schema

    Returns:
        Tuple of (is_valid, error_message, validated_data)
    """
    return api_validator.validate_json_request(request_data, schema)
