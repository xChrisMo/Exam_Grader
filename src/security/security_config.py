"""Comprehensive Security Configuration System for Exam Grader Application.

This module provides centralized security configuration management,
integrating all security components and providing unified security policies.
"""

import json
import os
from pathlib import Path
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Union

try:
    from utils.logger import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

try:
    from src.database.models import UserRole
except ImportError:

    class UserRole:
        STUDENT = "student"
        INSTRUCTOR = "instructor"
        ADMIN = "admin"
        SUPER_ADMIN = "super_admin"

    class Permission:
        pass

@dataclass
class SecurityHeaders:
    """Security headers configuration."""

    content_security_policy: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    strict_transport_security: str = "max-age=31536000; includeSubDomains; preload"
    x_content_type_options: str = "nosniff"
    x_frame_options: str = "DENY"
    x_xss_protection: str = "1; mode=block"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = (
        "geolocation=(), microphone=(), camera=(), "
        "payment=(), usb=(), magnetometer=(), gyroscope=(), "
        "accelerometer=(), ambient-light-sensor=()"
    )
    cross_origin_embedder_policy: str = "require-corp"
    cross_origin_opener_policy: str = "same-origin"
    cross_origin_resource_policy: str = "same-origin"

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for Flask response headers."""
        return {
            "Content-Security-Policy": self.content_security_policy,
            "Strict-Transport-Security": self.strict_transport_security,
            "X-Content-Type-Options": self.x_content_type_options,
            "X-Frame-Options": self.x_frame_options,
            "X-XSS-Protection": self.x_xss_protection,
            "Referrer-Policy": self.referrer_policy,
            "Permissions-Policy": self.permissions_policy,
            "Cross-Origin-Embedder-Policy": self.cross_origin_embedder_policy,
            "Cross-Origin-Opener-Policy": self.cross_origin_opener_policy,
            "Cross-Origin-Resource-Policy": self.cross_origin_resource_policy,
        }

@dataclass
class FileUploadSecurity:
    """File upload security configuration."""

    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: List[str] = field(
        default_factory=lambda: [
            ".pdf",
            ".doc",
            ".docx",
            ".txt",
            ".rtf",
            ".odt",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".tiff",
            ".zip",
            ".rar",
            ".7z",
            ".tar",
            ".gz",
        ]
    )
    blocked_extensions: List[str] = field(
        default_factory=lambda: [
            ".exe",
            ".bat",
            ".cmd",
            ".com",
            ".scr",
            ".pif",
            ".vbs",
            ".js",
            ".jar",
            ".ps1",
            ".sh",
            ".php",
            ".asp",
            ".aspx",
            ".jsp",
            ".py",
            ".rb",
            ".pl",
        ]
    )
    scan_for_malware: bool = True
    quarantine_suspicious: bool = True
    max_filename_length: int = 255
    allowed_mime_types: List[str] = field(
        default_factory=lambda: [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/rtf",
            "application/vnd.oasis.opendocument.text",
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/bmp",
            "image/tiff",
            "application/zip",
            "application/x-rar-compressed",
            "application/x-7z-compressed",
            "application/x-tar",
            "application/gzip",
        ]
    )
    virus_scan_timeout: int = 30  # seconds
    content_validation: bool = True

@dataclass
class SessionSecurity:
    """Session security configuration."""

    session_timeout_minutes: int = 30
    max_concurrent_sessions: int = 3
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "Strict"
    regenerate_session_on_login: bool = True
    track_session_ip: bool = True
    track_user_agent: bool = True
    detect_session_hijacking: bool = True
    session_encryption: bool = True
    idle_timeout_minutes: int = 15
    absolute_timeout_hours: int = 8

@dataclass
class AuthenticationSecurity:
    """Authentication security configuration."""

    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 15
    password_min_length: int = 8
    password_max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special_chars: bool = True
    password_history_count: int = 5
    password_expiry_days: int = 90
    force_password_change_on_first_login: bool = True
    two_factor_authentication: bool = False
    remember_me_duration_days: int = 30
    brute_force_protection: bool = True
    captcha_after_failed_attempts: int = 3

@dataclass
class RateLimiting:
    """Rate limiting configuration."""

    enabled: bool = True
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10
    whitelist_ips: List[str] = field(default_factory=list)
    blacklist_ips: List[str] = field(default_factory=list)
    rate_limit_by_ip: bool = True
    rate_limit_by_user: bool = True
    rate_limit_storage: str = "memory"  # 'memory' or 'redis'

    # Endpoint-specific rate limits
    login_attempts_per_minute: int = 5
    upload_attempts_per_minute: int = 10
    api_calls_per_minute: int = 100

@dataclass
class InputValidation:
    """Input validation configuration."""

    max_input_length: int = 10000
    sanitize_html: bool = True
    block_script_tags: bool = True
    block_sql_injection: bool = True
    block_path_traversal: bool = True
    block_command_injection: bool = True
    validate_json_schema: bool = True
    max_json_depth: int = 10
    max_array_length: int = 1000
    unicode_normalization: bool = True
    trim_whitespace: bool = True

@dataclass
class AuditLogging:
    """Audit logging configuration."""

    enabled: bool = True
    log_authentication: bool = True
    log_authorization: bool = True
    log_file_operations: bool = True
    log_admin_actions: bool = True
    log_security_events: bool = True
    log_failed_requests: bool = True
    log_sensitive_data: bool = False
    retention_days: int = 90
    log_format: str = "json"
    log_level: str = "INFO"
    separate_security_log: bool = True

@dataclass
class EncryptionSettings:
    """Encryption settings configuration."""

    algorithm: str = "AES-256-GCM"
    key_derivation: str = "PBKDF2"
    key_iterations: int = 100000
    salt_length: int = 32
    iv_length: int = 16
    encrypt_session_data: bool = True
    encrypt_file_storage: bool = False
    encrypt_database_fields: List[str] = field(
        default_factory=lambda: ["password_hash", "email", "personal_info"]
    )
    key_rotation_days: int = 365

@dataclass
class SecurityMonitoring:
    """Security monitoring configuration."""

    enabled: bool = True
    monitor_failed_logins: bool = True
    monitor_privilege_escalation: bool = True
    monitor_file_access: bool = True
    monitor_suspicious_patterns: bool = True
    alert_threshold_failed_logins: int = 10
    alert_threshold_time_window_minutes: int = 5
    email_alerts: bool = True
    webhook_alerts: bool = False
    alert_recipients: List[str] = field(default_factory=list)
    real_time_monitoring: bool = True

@dataclass
class ComplianceSettings:
    """Compliance and regulatory settings."""

    gdpr_compliance: bool = True
    data_retention_days: int = 2555  # 7 years
    right_to_erasure: bool = True
    data_portability: bool = True
    consent_tracking: bool = True
    privacy_by_design: bool = True
    data_minimization: bool = True
    purpose_limitation: bool = True
    audit_trail_required: bool = True

@dataclass
class SecurityConfiguration:
    """Main security configuration class."""

    headers: SecurityHeaders = field(default_factory=SecurityHeaders)
    file_upload: FileUploadSecurity = field(default_factory=FileUploadSecurity)
    session: SessionSecurity = field(default_factory=SessionSecurity)
    authentication: AuthenticationSecurity = field(
        default_factory=AuthenticationSecurity
    )
    rate_limiting: RateLimiting = field(default_factory=RateLimiting)
    input_validation: InputValidation = field(default_factory=InputValidation)
    audit_logging: AuditLogging = field(default_factory=AuditLogging)
    encryption: EncryptionSettings = field(default_factory=EncryptionSettings)
    monitoring: SecurityMonitoring = field(default_factory=SecurityMonitoring)
    compliance: ComplianceSettings = field(default_factory=ComplianceSettings)

    # Environment-specific settings
    environment: str = "production"  # 'development', 'testing', 'production'
    debug_mode: bool = False
    security_level: str = "high"  # 'low', 'medium', 'high', 'maximum'

    def __post_init__(self):
        """Apply environment-specific adjustments."""
        if self.environment == "development":
            self._apply_development_settings()
        elif self.environment == "testing":
            self._apply_testing_settings()
        elif self.environment == "production":
            self._apply_production_settings()

    def _apply_development_settings(self):
        """Apply development environment settings."""
        self.debug_mode = True
        self.session.session_cookie_secure = False
        self.headers.strict_transport_security = ""
        self.rate_limiting.requests_per_minute = 1000
        self.authentication.max_failed_attempts = 10
        self.audit_logging.log_level = "DEBUG"

        logger.info("Applied development security settings")

    def _apply_testing_settings(self):
        """Apply testing environment settings."""
        self.session.session_timeout_minutes = 5
        self.authentication.lockout_duration_minutes = 1
        self.rate_limiting.requests_per_minute = 10000
        self.audit_logging.enabled = False

        logger.info("Applied testing security settings")

    def _apply_production_settings(self):
        """Apply production environment settings."""
        self.debug_mode = False
        self.session.session_cookie_secure = True
        self.authentication.two_factor_authentication = True
        self.monitoring.enabled = True
        self.compliance.audit_trail_required = True

        logger.info("Applied production security settings")

    def validate_configuration(self) -> List[str]:
        """Validate security configuration.

        Returns:
            List of validation errors
        """
        errors = []

        # Session validation
        if self.session.session_timeout_minutes < 5:
            errors.append("Session timeout too short (minimum 5 minutes)")

        if self.session.session_timeout_minutes > 480:  # 8 hours
            errors.append("Session timeout too long (maximum 8 hours)")

        # Authentication validation
        if self.authentication.password_min_length < 8:
            errors.append("Password minimum length too short (minimum 8 characters)")

        if self.authentication.max_failed_attempts < 3:
            errors.append("Max failed attempts too low (minimum 3)")

        # File upload validation
        if self.file_upload.max_file_size > 500 * 1024 * 1024:  # 500MB
            errors.append("Max file size too large (maximum 500MB)")

        # Rate limiting validation
        if self.rate_limiting.requests_per_minute > 10000:
            errors.append("Rate limit too high (maximum 10000 requests per minute)")

        # Production-specific validation
        if self.environment == "production":
            if not self.session.session_cookie_secure:
                errors.append("Session cookies must be secure in production")

            if not self.headers.strict_transport_security:
                errors.append("HSTS header required in production")

            if self.debug_mode:
                errors.append("Debug mode must be disabled in production")
        elif self.environment == "development":
            # In development, these are warnings, not errors
            if not self.session.session_cookie_secure:
                logger.debug(
                    "Development mode: Session cookies are not secure (this is normal)"
                )

            if not self.headers.strict_transport_security:
                logger.debug(
                    "Development mode: HSTS header not required (this is normal)"
                )

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Configuration dictionary
        """
        return asdict(self)

    def save_to_file(self, file_path: Union[str, Path]):
        """Save configuration to JSON file.

        Args:
            file_path: Path to save configuration
        """
        try:
            config_dict = self.to_dict()

            with open(file_path, "w") as f:
                json.dump(config_dict, f, indent=2, default=str)

            logger.info(f"Security configuration saved to {file_path}")

        except Exception as e:
            logger.error(f"Error saving security configuration: {str(e)}")
            raise

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> "SecurityConfiguration":
        """Load configuration from JSON file.

        Args:
            file_path: Path to configuration file

        Returns:
            SecurityConfiguration instance
        """
        try:
            with open(file_path, "r") as f:
                config_dict = json.load(f)

            # Reconstruct nested dataclasses
            config = cls()

            for key, value in config_dict.items():
                if hasattr(config, key) and isinstance(value, dict):
                    # Handle nested dataclass
                    nested_class = type(getattr(config, key))
                    setattr(config, key, nested_class(**value))
                else:
                    setattr(config, key, value)

            logger.info(f"Security configuration loaded from {file_path}")
            return config

        except Exception as e:
            logger.error(f"Error loading security configuration: {str(e)}")
            raise

    @classmethod
    def create_default_config(
        cls, environment: str = "production"
    ) -> "SecurityConfiguration":
        """Create default security configuration.

        Args:
            environment: Target environment

        Returns:
            SecurityConfiguration instance
        """
        config = cls(environment=environment)

        # Apply security level adjustments
        if config.security_level == "maximum":
            config._apply_maximum_security()

        return config

    def _apply_maximum_security(self):
        """Apply maximum security settings."""
        # Stricter session settings
        self.session.session_timeout_minutes = 15
        self.session.idle_timeout_minutes = 5
        self.session.max_concurrent_sessions = 1

        # Stricter authentication
        self.authentication.max_failed_attempts = 3
        self.authentication.lockout_duration_minutes = 30
        self.authentication.two_factor_authentication = True
        self.authentication.password_min_length = 12

        # Stricter rate limiting
        self.rate_limiting.requests_per_minute = 30
        self.rate_limiting.login_attempts_per_minute = 3

        # Enhanced monitoring
        self.monitoring.alert_threshold_failed_logins = 3
        self.monitoring.real_time_monitoring = True

        # Stricter file upload
        self.file_upload.max_file_size = 10 * 1024 * 1024  # 10MB
        self.file_upload.scan_for_malware = True
        self.file_upload.quarantine_suspicious = True

        logger.info("Applied maximum security settings")

class SecurityConfigManager:
    """Manage security configuration lifecycle."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize security config manager.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or "config/security.json"
        self._config: Optional[SecurityConfiguration] = None

        logger.info(f"Security config manager initialized (config: {self.config_path})")

    def load_config(self, environment: str = None) -> SecurityConfiguration:
        """Load security configuration.

        Args:
            environment: Target environment

        Returns:
            SecurityConfiguration instance
        """
        try:
            if os.path.exists(self.config_path):
                self._config = SecurityConfiguration.load_from_file(self.config_path)
            else:
                # Create default configuration
                env = environment or os.getenv("FLASK_ENV", "production")
                self._config = SecurityConfiguration.create_default_config(env)

                # Save default configuration
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                self._config.save_to_file(self.config_path)

            # Validate configuration
            errors = self._config.validate_configuration()
            if errors:
                logger.warning(f"Security configuration validation errors: {errors}")

            return self._config

        except Exception as e:
            logger.error(f"Error loading security configuration: {str(e)}")
            # Fallback to default configuration
            self._config = SecurityConfiguration.create_default_config("production")
            return self._config

    def get_config(self) -> SecurityConfiguration:
        """Get current security configuration.

        Returns:
            SecurityConfiguration instance
        """
        if self._config is None:
            self._config = self.load_config()

        return self._config

    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update security configuration.

        Args:
            updates: Configuration updates

        Returns:
            True if update successful
        """
        try:
            config = self.get_config()

            # Apply updates
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)

            # Validate updated configuration
            errors = config.validate_configuration()
            if errors:
                logger.error(f"Configuration update validation failed: {errors}")
                return False

            # Save updated configuration
            config.save_to_file(self.config_path)

            logger.info("Security configuration updated successfully")
            return True

        except Exception as e:
            logger.error(f"Error updating security configuration: {str(e)}")
            return False

    def reset_to_defaults(self, environment: str = "production") -> bool:
        """Reset configuration to defaults.

        Args:
            environment: Target environment

        Returns:
            True if reset successful
        """
        try:
            self._config = SecurityConfiguration.create_default_config(environment)
            self._config.save_to_file(self.config_path)

            logger.info(f"Security configuration reset to defaults ({environment})")
            return True

        except Exception as e:
            logger.error(f"Error resetting security configuration: {str(e)}")
            return False

# Global security config manager
security_config_manager = None

def init_security_config(
    config_path: str = None, environment: str = None
) -> SecurityConfiguration:
    """Initialize global security configuration.

    Args:
        config_path: Path to configuration file
        environment: Target environment

    Returns:
        SecurityConfiguration instance
    """
    global security_config_manager
    security_config_manager = SecurityConfigManager(config_path)
    return security_config_manager.load_config(environment)

def get_security_config() -> SecurityConfiguration:
    """Get global security configuration.

    Returns:
        SecurityConfiguration instance
    """
    if security_config_manager is None:
        init_security_config()

    return security_config_manager.get_config()
