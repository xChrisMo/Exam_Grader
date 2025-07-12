"""
Unified Configuration Management System for Exam Grader Application.

This module consolidates all configuration settings from config.py and config_manager.py
into a single, centralized system with environment-specific settings and validation.
"""

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Import logger with fallback
try:
    from utils.logger import Logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

logger = Logger().get_logger()

# Load environment variables
load_dotenv()


@dataclass
class SecurityConfig:
    """Security-related configuration settings."""

    secret_key: str = ""
    session_timeout: int = 3600  # 1 hour
    csrf_enabled: bool = True
    rate_limit_enabled: bool = False  # Disabled rate limiting
    max_requests_per_hour: int = 0  # No limit
    secure_cookies: bool = True
    session_cookie_httponly: bool = True
    session_cookie_secure: bool = False # Changed to False for local HTTP development
    session_cookie_samesite: str = "Lax"
    session_cookie_domain: str = None # Set to None to avoid domain issues with CSRF tokens

    def __post_init__(self):
        """Validate security configuration."""
        if self.secret_key and len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    database_url: str = "sqlite:///exam_grader.db"
    database_pool_size: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600
    database_echo: bool = False

    def __post_init__(self):
        """Validate database configuration."""
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")


@dataclass
class FileConfig:
    """File processing configuration settings."""

    max_file_size_mb: int = 20
    max_content_length: int = field(init=False)
    supported_formats: List[str] = field(
        default_factory=lambda: [
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
            ".gif",
        ]
    )
    temp_dir: Path = field(default_factory=lambda: Path("temp"))
    output_dir: Path = field(default_factory=lambda: Path("output"))
    upload_dir: Path = field(default_factory=lambda: Path("uploads"))
    storage_max_size_mb: int = 1000
    storage_expiration_days: int = 30
    cleanup_interval_hours: int = 24

    def __post_init__(self):
        """Validate and setup file configuration."""
        self.max_content_length = self.max_file_size_mb * 1024 * 1024

        # Create directories if they don't exist
        for directory in [self.temp_dir, self.output_dir, self.upload_dir]:
            directory.mkdir(exist_ok=True)

        if self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")


@dataclass
class APIConfig:
    """External API configuration settings."""

    handwriting_ocr_api_key: str = ""
    deepseek_api_key: str = ""
    handwriting_ocr_api_url: str = field(default_factory=lambda: os.getenv("HANDWRITING_OCR_API_URL", ""))
    handwriting_ocr_delete_after: int = 3600
    deepseek_api_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_URL", ""))
    deepseek_model: str = field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner"))
    api_timeout: int = 30
    api_retry_attempts: int = 3
    api_retry_delay: float = 2.0

    # LLM Response Handling Configuration
    llm_require_json_response: bool = True  # Enforce JSON response format
    llm_strict_mode: bool = False  # When True, fails completely if LLM fails
    llm_retry_attempts: int = 3  # Total attempts including initial try
    llm_retry_delay: float = 2.0  # Base delay between attempts in seconds
    llm_json_timeout: float = 10.0  # Additional time allowance for JSON parsing
    llm_retry_on_json_error: int = 2  # Retries specifically for JSON parse failures
    llm_json_schema: Optional[Dict] = None  # Optional JSON schema validation
    llm_fallback_to_plaintext: bool = True  # Attempt plaintext parsing if JSON fails

    def __post_init__(self):
        """Validate API configuration."""
        if not self.handwriting_ocr_api_key:
            logger.warning(
                "HandwritingOCR API key not configured - OCR features will be limited"
            )
        if not self.deepseek_api_key:
            logger.warning(
                "DeepSeek API key not configured - LLM features will be limited"
            )


@dataclass
class CacheConfig:
    """Caching configuration settings."""

    cache_type: str = "simple"
    cache_default_timeout: int = 3600
    cache_threshold: int = 500

    def __post_init__(self):
        """Validate cache configuration."""
        valid_types = ["simple", "memory"]
        if self.cache_type not in valid_types:
            raise ValueError(f"cache_type must be one of {valid_types}")


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    log_level: str = "INFO"
    log_file: Optional[str] = None
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def __post_init__(self):
        """Validate logging configuration."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")


@dataclass
class ServerConfig:
    """Server configuration settings."""

    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = False
    testing: bool = False
    threaded: bool = True

    def __post_init__(self):
        """Validate server configuration."""
        if not (1 <= self.port <= 65535):
            raise ValueError("port must be between 1 and 65535")


class UnifiedConfig:
    """
    Unified configuration manager that consolidates all application settings.

    This class provides a single point of configuration management with
    environment-specific settings and proper validation.
    """

    def __init__(self, environment: str = None):
        """
        Initialize unified configuration.

        Args:
            environment: Environment name (development, testing, production)
        """
        self.environment = environment or os.getenv("FLASK_ENV", "development")
        self._load_configuration()

    def _load_configuration(self):
        """Load configuration based on environment."""
        # Security configuration
        self.security = SecurityConfig(
            secret_key=self._get_secret_key(),
            session_timeout=int(os.getenv("SESSION_TIMEOUT", "3600")),
            csrf_enabled=os.getenv("CSRF_ENABLED", "True").lower() == "true",
            rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "True").lower()
            == "true",
            max_requests_per_hour=int(os.getenv("MAX_REQUESTS_PER_HOUR", "1000")),
            secure_cookies=self.environment == "production",
            session_cookie_secure=False,  # Explicitly disabled for development
            session_cookie_domain=None,  # Ensure cookies work on localhost
        )

        # Database configuration
        self.database = DatabaseConfig(
            database_url=os.getenv("DATABASE_URL", "sqlite:///exam_grader.db"),
            database_echo=os.getenv("DATABASE_ECHO", "False").lower() == "true",
        )

        # File configuration
        supported_formats_env = os.getenv("SUPPORTED_FORMATS", "")
        supported_formats = []
        if supported_formats_env:
            # Ensure each format starts with a dot
            for fmt in supported_formats_env.split(","):
                fmt = fmt.strip()
                if fmt:
                    if not fmt.startswith("."):
                        fmt = "." + fmt
                    supported_formats.append(fmt)
        
        # Use default formats if none were provided
        if not supported_formats:
            supported_formats = [
                ".pdf",
                ".docx",
                ".doc",
                ".txt",
                ".jpg",
                ".jpeg",
                ".png",
                ".bmp",
                ".tiff",
                ".gif",
            ]
        
        self.files = FileConfig(
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "20")),
            temp_dir=Path(os.getenv("TEMP_DIR", "temp")),
            output_dir=Path(os.getenv("OUTPUT_DIR", "output")),
            upload_dir=Path(os.getenv("UPLOAD_DIR", "uploads")),
            supported_formats=supported_formats
        )

        # API configuration
        self.api = APIConfig(
            handwriting_ocr_api_key=os.getenv("HANDWRITING_OCR_API_KEY", ""),
            handwriting_ocr_api_url=os.getenv(
                "HANDWRITING_OCR_API_URL", "https://www.handwritingocr.com/api/v3"
            ),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        deepseek_api_url=os.getenv(
            "DEEPSEEK_API_URL", ""
        ),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner"),
            # LLM-Only Mode Configuration
            llm_require_json_response=os.getenv("LLM_REQUIRE_JSON", "True").lower() == "true",
            llm_strict_mode=os.getenv("LLM_STRICT_MODE", "False").lower() == "true",
            llm_retry_attempts=int(os.getenv("LLM_RETRY_ATTEMPTS", "3")),
            llm_retry_delay=float(os.getenv("LLM_RETRY_DELAY", "2.0")),
            llm_json_timeout=float(os.getenv("LLM_JSON_TIMEOUT", "10.0")),
            llm_retry_on_json_error=int(os.getenv("LLM_RETRY_ON_JSON_ERROR", "2")),
            llm_fallback_to_plaintext=os.getenv("LLM_FALLBACK_TO_PLAINTEXT", "True").lower() == "true",
        )

        # Cache configuration
        self.cache = CacheConfig(
            cache_type=os.getenv("CACHE_TYPE", "simple"),
        )

        # Logging configuration
        self.logging = LoggingConfig(
            log_level="DEBUG" if self.environment == "development" else os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE"),
        )

        # Server configuration
        self.server: ServerConfig = ServerConfig(
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "5000")),
            debug=self.environment == "development",
            testing=self.environment == "testing",
        )

        # Adjust secure cookie setting based on environment
        if self.environment in ["development", "testing"] or self.server.debug:
            self.security.session_cookie_secure = False
            logger.info("Session cookies set to non-secure for development/testing environment.")

    def _get_secret_key(self) -> str:
        """Get or generate a secure secret key."""
        logger.debug("Attempting to retrieve SECRET_KEY.")
        secret_key = os.getenv("SECRET_KEY")
        if not secret_key:
            if self.environment == "production":
                raise ValueError("SECRET_KEY must be set in production environment")
            # Generate a secure key for development
            secret_key = secrets.token_hex(32)
            logger.warning(
                "Using generated SECRET_KEY for development. Set SECRET_KEY environment variable for production."
            )
            logger.debug(f"Using SECRET_KEY (first 5 chars): {secret_key[:5]}...")
        return secret_key

    def get_flask_config(self) -> Dict[str, Any]:
        """
        Get Flask-compatible configuration dictionary.

        Returns:
            Dictionary of Flask configuration settings
        """
        return {
            "SECRET_KEY": self.security.secret_key,
            "DEBUG": self.server.debug,
            "TESTING": self.server.testing,
            "MAX_CONTENT_LENGTH": self.files.max_content_length,
            "PERMANENT_SESSION_LIFETIME": self.security.session_timeout,
            "SESSION_COOKIE_HTTPONLY": self.security.session_cookie_httponly,
            "SESSION_COOKIE_SECURE": self.security.session_cookie_secure,
            "SESSION_COOKIE_SAMESITE": self.security.session_cookie_samesite,
            "SESSION_COOKIE_DOMAIN": self.security.session_cookie_domain,
            "WTF_CSRF_ENABLED": self.security.csrf_enabled,
            "WTF_CSRF_TIME_LIMIT": 86400,  # Extend CSRF token validity to 24 hours
            "SQLALCHEMY_DATABASE_URI": self.database.database_url,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "pool_size": self.database.database_pool_size,
                "pool_timeout": self.database.database_pool_timeout,
                "pool_recycle": self.database.database_pool_recycle,
                "echo": self.database.database_echo,
            },
        }

    def validate(self) -> bool:
        """
        Validate all configuration settings.

        Returns:
            True if all settings are valid

        Raises:
            ValueError: If any configuration is invalid
        """
        try:
            # All validation is done in __post_init__ methods
            logger.info(
                f"Configuration validated successfully for environment: {self.environment}"
            )
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            raise


# Global configuration instance
config = UnifiedConfig()
