"""
Security utilities for the Exam Grader application.

This module provides security-related utilities including:
- Secure key generation
- Security configuration validation
- Sensitive data sanitization
- Security audit functions
"""

import os
import re
import secrets
import string
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils.logger import logger


class SecurityUtils:
    """Utility class for security-related operations."""

    @staticmethod
    def generate_secret_key(length: int = 32) -> str:
        """Generate a cryptographically secure secret key.

        Args:
            length: Length of the key in bytes

        Returns:
            Hex-encoded secret key
        """
        return secrets.token_hex(length)

    @staticmethod
    def generate_secure_password(length: int = 16) -> str:
        """Generate a secure random password.

        Args:
            length: Length of the password

        Returns:
            Secure random password
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def validate_secret_key(secret_key: str) -> Tuple[bool, str]:
        """Validate a secret key for security requirements.

        Args:
            secret_key: Secret key to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not secret_key:
            return False, "Secret key is required"

        if len(secret_key) < 32:
            return False, "Secret key must be at least 32 characters long"

        weak_patterns = [
            "your_secret_key_here",
            "change_me",
            "default",
            "secret",
            "password",
            "123456",
            "abcdef",
        ]

        secret_lower = secret_key.lower()
        for pattern in weak_patterns:
            if pattern in secret_lower:
                return False, f"Secret key contains weak pattern: {pattern}"

        unique_chars = len(set(secret_key))
        if unique_chars < 16:
            return (
                False,
                "Secret key has insufficient entropy (too few unique characters)",
            )

        return True, "Secret key is valid"

    @staticmethod
    def sanitize_for_logging(data: str, patterns: Optional[List[str]] = None) -> str:
        """Sanitize sensitive data for safe logging.

        Args:
            data: Data to sanitize
            patterns: Additional patterns to sanitize

        Returns:
            Sanitized data safe for logging
        """
        if not data:
            return data

        # Default sensitive patterns
        default_patterns = [
            r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'\s]+)',
            r'(secret[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'\s]+)',
            r'(password["\']?\s*[:=]\s*["\']?)([^"\'\s]+)',
            r'(token["\']?\s*[:=]\s*["\']?)([^"\'\s]+)',
            r"([A-Za-z0-9+/]{40,})",  # Base64-like strings
        ]

        if patterns:
            default_patterns.extend(patterns)

        sanitized = data
        for pattern in default_patterns:
            sanitized = re.sub(
                pattern, r"\1***REDACTED***", sanitized, flags=re.IGNORECASE
            )

        return sanitized

    @staticmethod
    def audit_environment_variables() -> Dict[str, any]:
        """Audit environment variables for security issues.

        Returns:
            Dictionary containing audit results
        """
        audit_results = {
            "timestamp": logger.info.__module__,  # Use a safe timestamp
            "issues": [],
            "warnings": [],
            "recommendations": [],
        }

        sensitive_vars = [
            "SECRET_KEY",
            "HANDWRITING_OCR_API_KEY",
            "DEEPSEEK_API_KEY",
            "DATABASE_URL",
        ]

        for var in sensitive_vars:
            value = os.getenv(var, "")

            if not value:
                audit_results["warnings"].append(f"{var} is not set")
                continue

            placeholder_patterns = [
                "your_",
                "change_me",
                "default",
                "example",
                "test",
                "demo",
            ]

            value_lower = value.lower()
            for pattern in placeholder_patterns:
                if pattern in value_lower:
                    audit_results["issues"].append(
                        f"{var} appears to contain placeholder value"
                    )
                    break

            if var == "SECRET_KEY":
                is_valid, error = SecurityUtils.validate_secret_key(value)
                if not is_valid:
                    audit_results["issues"].append(
                        f"SECRET_KEY validation failed: {error}"
                    )

        debug_mode = os.getenv("DEBUG", "False").lower()
        if debug_mode == "true":
            audit_results["warnings"].append("Debug mode is enabled")

        # Generate recommendations
        if audit_results["issues"]:
            audit_results["recommendations"].append(
                "Fix all security issues before deploying to production"
            )

        if audit_results["warnings"]:
            audit_results["recommendations"].append(
                "Review and address security warnings"
            )

        return audit_results

    @staticmethod
    def scan_file_for_secrets(file_path: Path) -> List[Dict[str, any]]:
        """Scan a file for potential hardcoded secrets.

        Args:
            file_path: Path to file to scan

        Returns:
            List of potential secret findings
        """
        findings = []

        if not file_path.exists() or not file_path.is_file():
            return findings

        # Skip binary files and large files
        if file_path.suffix in [".pyc", ".so", ".dll", ".exe"]:
            return findings

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return findings

        # Patterns to look for
        secret_patterns = [
            (r'api[_-]?key\s*[:=]\s*["\']([^"\']+)["\']', "API Key"),
            (r'secret[_-]?key\s*[:=]\s*["\']([^"\']+)["\']', "Secret Key"),
            (r'password\s*[:=]\s*["\']([^"\']+)["\']', "Password"),
            (r'token\s*[:=]\s*["\']([^"\']+)["\']', "Token"),
            (r'["\']([A-Za-z0-9+/]{40,})["\']', "Base64-like String"),
        ]

        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern, secret_type in secret_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    # Skip obvious placeholders
                    value = match.group(1) if match.groups() else match.group(0)
                    if any(
                        placeholder in value.lower()
                        for placeholder in [
                            "your_",
                            "example",
                            "placeholder",
                            "change_me",
                            "xxx",
                            "set_via_environment",
                            "replace_with",
                        ]
                    ):
                        continue

                    findings.append(
                        {
                            "file": str(file_path),
                            "line": line_num,
                            "type": secret_type,
                            "context": line.strip(),
                            "value_preview": (
                                value[:10] + "..." if len(value) > 10 else value
                            ),
                        }
                    )

        return findings

    @staticmethod
    def generate_security_report() -> Dict[str, any]:
        """Generate a comprehensive security report.

        Returns:
            Dictionary containing security report
        """
        report = {
            "timestamp": "audit_timestamp",
            "environment_audit": SecurityUtils.audit_environment_variables(),
            "file_scan_summary": {"total_files_scanned": 0, "files_with_secrets": 0},
            "recommendations": [],
        }

        key_files = [
            Path(".env"),
            Path("config.py"),
            Path("settings.py"),
        ]

        files_with_secrets = 0
        total_scanned = 0

        for file_path in key_files:
            if file_path.exists():
                total_scanned += 1
                findings = SecurityUtils.scan_file_for_secrets(file_path)
                if findings:
                    files_with_secrets += 1
                    logger.warning(
                        f"Found {len(findings)} potential secrets in {file_path}"
                    )

        report["file_scan_summary"] = {
            "total_files_scanned": total_scanned,
            "files_with_secrets": files_with_secrets,
        }

        # Generate overall recommendations
        if report["environment_audit"]["issues"]:
            report["recommendations"].append(
                "Address environment variable security issues"
            )

        if files_with_secrets > 0:
            report["recommendations"].append(
                "Review and secure hardcoded secrets in files"
            )

        report["recommendations"].extend(
            [
                "Regularly rotate API keys and secrets",
                "Use environment variables for all sensitive configuration",
                "Enable security headers in production",
                "Implement proper session management",
                "Use HTTPS in production",
            ]
        )

        return report


def generate_secure_config_template() -> str:
    """Generate a secure configuration template.

    Returns:
        String containing secure configuration template
    """
    template = f"""# Exam Grader Secure Configuration Template
# Generated with secure defaults

# Security Configuration
SECRET_KEY="{SecurityUtils.generate_secret_key()}"
SESSION_TIMEOUT=3600
CSRF_ENABLED=True

# Database Configuration
DATABASE_URL=sqlite:///instance/exam_grader.db

# API Configuration (Set via environment variables)
# HANDWRITING_OCR_API_KEY=<set_via_environment>
# DEEPSEEK_API_KEY=<set_via_environment>

# Application Settings
DEBUG=False
LOG_LEVEL=INFO

# Security Headers
SECURE_HEADERS=True
FORCE_HTTPS=True

# Generated on: {logger.info.__module__}
# Remember to:
# 1. Replace placeholder API keys with real values
# 2. Keep this file secure and never commit to version control
"""

    return template
