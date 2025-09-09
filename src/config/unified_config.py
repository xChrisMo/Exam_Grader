"""
Unified Configuration Management System for Exam Grader Application.

This module consolidates all configuration settings into a single, centralized system
with environment-specific settings, validation, and migration utilities.
"""

import os
from pathlib import Path
import secrets
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Import logger with fallback
try:
    from utils.logger import Logger

    logger = Logger().get_logger()
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

def load_environment_variables():
    """Load environment variables from multiple .env files with priority."""
    instance_env = Path("instance/.env")
    if instance_env.exists():
        load_dotenv(instance_env, override=True)

    root_env = Path(".env")
    if root_env.exists():
        load_dotenv(root_env, override=False)  # Don't override instance settings

load_environment_variables()

@dataclass
class SecurityConfig:
    """Security-related configuration settings."""

    secret_key: str = ""
    session_timeout: int = None  # No session timeout
    csrf_enabled: bool = True
    rate_limit_enabled: bool = False  # Disabled rate limiting
    max_requests_per_hour: int = None  # No limit
    secure_cookies: bool = True
    session_cookie_httponly: bool = True
    session_cookie_secure: bool = True  # Secure cookies for production
    session_cookie_samesite: str = "Lax"
    session_cookie_domain: str = (
        None  # Set to None to avoid domain issues with CSRF tokens
    )

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

    max_file_size_mb: int = None  # No file size limit
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
            ".zip",
            ".rar",
            ".7z",
            ".tar",
            ".gz",
            ".mp4",
            ".avi",
            ".mov",
            ".mp3",
            ".wav",
            ".flac"
        ]
    )
    temp_dir: Path = field(default_factory=lambda: Path("temp"))
    output_dir: Path = field(default_factory=lambda: Path("output"))
    upload_dir: Path = field(default_factory=lambda: Path("uploads"))
    storage_max_size_mb: int = None  # No storage limit
    storage_expiration_days: int = 30
    cleanup_interval_hours: int = 24

    def __post_init__(self):
        """Validate and setup file configuration."""
        # Set unlimited content length if no file size limit
        if self.max_file_size_mb is None:
            self.max_content_length = None  # No limit
        else:
            self.max_content_length = self.max_file_size_mb * 1024 * 1024

        for directory in [self.temp_dir, self.output_dir, self.upload_dir]:
            directory.mkdir(exist_ok=True)

        # Skip validation if no limit is set
        if self.max_file_size_mb is not None and self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")

@dataclass
class APIConfig:
    """External API configuration settings."""

    handwriting_ocr_api_key: str = ""
    deepseek_api_key: str = ""
    handwriting_ocr_api_url: str = field(
        default_factory=lambda: os.getenv("HANDWRITING_OCR_API_URL", "")
    )
    handwriting_ocr_delete_after: int = 3600
    deepseek_api_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_URL", "")
    )
    deepseek_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "deepseek-chat")
    )
    api_timeout: int = 60
    api_retry_attempts: int = 3
    api_retry_delay: float = 2.0

    # LLM Response Handling Configuration
    llm_require_json_response: bool = True  # Enforce JSON response format
    llm_strict_mode: bool = False  # When True, fails completely if LLM fails
    llm_retry_attempts: int = 3  # Total attempts including initial try
    llm_retry_delay: float = 2.0  # Base delay between attempts in seconds
    llm_json_timeout: float = 30.0  # Additional time allowance for JSON parsing
    llm_retry_on_json_error: int = 2  # Retries specifically for JSON parse failures
    llm_json_schema: Optional[Dict] = None  # Optional JSON schema validation
    llm_fallback_to_plaintext: bool = True  # Attempt plaintext parsing if JSON fails

    # Guide Processing Configuration
    enable_direct_llm_guide_processing: bool = False  # Disabled - using existing services
    default_guide_processing_method: str = "traditional_ocr"  # Default processing method
    allow_guide_processing_method_selection: bool = True  # Allow users to choose method
    llm_vision_max_file_size: str = "20MB"  # Maximum file size for LLM vision processing
    llm_vision_supported_formats: List[str] = field(
        default_factory=lambda: ["pdf", "docx", "jpg", "png", "tiff"]
    )
    enable_processing_fallback: bool = True  # Enable fallback to traditional OCR
    fallback_timeout_seconds: int = 30  # Timeout for fallback processing
    max_fallback_attempts: int = 2  # Maximum fallback attempts

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
    log_max_bytes: int = None  # No log size limit
    log_backup_count: int = None  # No backup limit
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def __post_init__(self):
        """Validate logging configuration."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")

@dataclass
class ServerConfig:
    """Server configuration settings."""

    host: str = field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8501")))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "False").lower() == "true")
    testing: bool = field(default_factory=lambda: os.getenv("TESTING", "False").lower() == "true")
    threaded: bool = field(default_factory=lambda: os.getenv("THREADED", "True").lower() == "true")
    max_batch_processing_workers: int = field(default_factory=lambda: int(os.getenv("MAX_BATCH_WORKERS", "5")))
    batch_processing_size: int = field(default_factory=lambda: int(os.getenv("BATCH_PROCESSING_SIZE", "5")))

    def __post_init__(self):
        """Validate server configuration."""
        if not (1 <= self.port <= 65535):
            raise ValueError("port must be between 1 and 65535")

class ConfigurationMigrator:
    """Handles migration of deprecated environment variables to new names."""

    # Mapping of old variable names to new ones
    VARIABLE_MIGRATIONS = {
        "DATABASE_URI": "DATABASE_URL",
        "DEEPSEEK_SEED": "DEEPSEEK_RANDOM_SEED",
        "DEEPSEEK_TOKEN_LIMIT": "DEEPSEEK_MAX_TOKENS",
        "NOTIFICATION_LEVEL": "LOG_LEVEL",
    }

    @classmethod
    def migrate_environment_variables(cls):
        """Migrate deprecated environment variables to new names."""
        migrated = []

        for old_var, new_var in cls.VARIABLE_MIGRATIONS.items():
            old_value = os.getenv(old_var)
            new_value = os.getenv(new_var)

            if old_value and not new_value:
                # Migrate the old variable to the new one
                os.environ[new_var] = old_value
                migrated.append(f"{old_var} -> {new_var}")
                logger.warning(
                    f"Migrated deprecated environment variable: {old_var} -> {new_var}"
                )

        if migrated:
            logger.info(f"Migrated {len(migrated)} deprecated environment variables")

        return migrated

class ConfigurationValidator:
    """Validates configuration settings and provides helpful error messages."""

    @staticmethod
    def validate_api_keys(api_config: "APIConfig") -> List[str]:
        """Validate API key configuration and return warnings."""
        warnings = []

        if not api_config.handwriting_ocr_api_key:
            warnings.append(
                "HandwritingOCR API key not configured - OCR features will be limited"
            )

        if not api_config.deepseek_api_key:
            warnings.append(
                "DeepSeek API key not configured - LLM features will be limited"
            )

        if not api_config.handwriting_ocr_api_key and not api_config.deepseek_api_key:
            warnings.append(
                "No API keys configured - application will run in limited mode"
            )

        return warnings

    @staticmethod
    def validate_directories(file_config: "FileConfig") -> List[str]:
        """Validate directory configuration and return warnings."""
        warnings = []

        for dir_name, directory in [
            ("temp", file_config.temp_dir),
            ("output", file_config.output_dir),
            ("upload", file_config.upload_dir),
        ]:
            if not directory.exists():
                try:
                    directory.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created {dir_name} directory: {directory}")
                except Exception as e:
                    warnings.append(
                        f"Failed to create {dir_name} directory {directory}: {e}"
                    )
            elif not os.access(directory, os.W_OK):
                warnings.append(
                    f"{dir_name.title()} directory is not writable: {directory}"
                )

        return warnings

    @staticmethod
    def validate_database_url(database_url: str) -> List[str]:
        """Validate database URL and return warnings."""
        warnings = []

        if database_url.startswith("sqlite:///"):
            db_path = database_url.replace("sqlite:///", "")
            db_dir = Path(db_path).parent

            if not db_dir.exists():
                try:
                    db_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created database directory: {db_dir}")
                except Exception as e:
                    warnings.append(
                        f"Failed to create database directory {db_dir}: {e}"
                    )

        return warnings

class UnifiedConfig:
    """
    Unified configuration manager that consolidates all application settings.

    This class provides a single point of configuration management with
    environment-specific settings, validation, and migration utilities.
    """

    def __init__(self, environment: str = None):
        """
        Initialize unified configuration.

        Args:
            environment: Environment name (development, testing, production)
        """
        self.environment = environment or os.getenv("FLASK_ENV", "production")

        # Migrate deprecated environment variables
        ConfigurationMigrator.migrate_environment_variables()

        # Load configuration
        self._load_configuration()

        # Validate configuration
        self._validate_configuration()

    def _load_configuration(self):
        """Load configuration based on environment."""
        # Security configuration
        self.security = SecurityConfig(
            secret_key=self._get_secret_key(),
            session_timeout=None,  # No session timeout
            csrf_enabled=os.getenv("CSRF_ENABLED", "True").lower() == "true",
            rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "True").lower()
            == "true",
            max_requests_per_hour=None,  # No request limit
            secure_cookies=self.environment == "production",
            session_cookie_secure=self.environment == "production",
            session_cookie_domain=None,  # Ensure cookies work on localhost
        )

        # Database configuration with path resolution
        raw_db_url = os.getenv("DATABASE_URL", "sqlite:///exam_grader.db")
        resolved_db_url = self._resolve_database_url(raw_db_url)

        self.database = DatabaseConfig(
            database_url=resolved_db_url,
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
            max_file_size_mb=None,  # No file size limit
            temp_dir=Path(os.getenv("TEMP_DIR", "temp")),
            output_dir=Path(os.getenv("OUTPUT_DIR", "output")),
            upload_dir=Path(os.getenv("UPLOAD_DIR", "uploads")),
            supported_formats=supported_formats,
        )

        # API configuration
        self.api = APIConfig(
            handwriting_ocr_api_key=os.getenv("HANDWRITING_OCR_API_KEY", ""),
            handwriting_ocr_api_url=os.getenv(
                "HANDWRITING_OCR_API_URL", "https://www.handwritingocr.com/api/v3"
            ),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            deepseek_api_url=os.getenv("DEEPSEEK_API_URL", ""),
            deepseek_model=os.getenv("LLM_MODEL", "deepseek-chat"),
            # LLM-Only Mode Configuration
            llm_require_json_response=os.getenv("LLM_REQUIRE_JSON", "True").lower()
            == "true",
            llm_strict_mode=os.getenv("LLM_STRICT_MODE", "False").lower() == "true",
            llm_retry_attempts=int(os.getenv("LLM_RETRY_ATTEMPTS", "3")),
            llm_retry_delay=float(os.getenv("LLM_RETRY_DELAY", "2.0")),
            llm_json_timeout=float(os.getenv("LLM_JSON_TIMEOUT", "10.0")),
            llm_retry_on_json_error=int(os.getenv("LLM_RETRY_ON_JSON_ERROR", "2")),
            llm_fallback_to_plaintext=os.getenv(
                "LLM_FALLBACK_TO_PLAINTEXT", "True"
            ).lower()
            == "true",
            # Guide Processing Configuration (using existing services)
            enable_direct_llm_guide_processing=os.getenv("ENABLE_DIRECT_LLM_GUIDE_PROCESSING", "False").lower() == "true",
            default_guide_processing_method=os.getenv("DEFAULT_GUIDE_PROCESSING_METHOD", "traditional_ocr"),
            allow_guide_processing_method_selection=os.getenv("ALLOW_GUIDE_PROCESSING_METHOD_SELECTION", "True").lower() == "true",
            llm_vision_max_file_size=os.getenv("LLM_VISION_MAX_FILE_SIZE", "20MB"),
            llm_vision_supported_formats=os.getenv("LLM_VISION_SUPPORTED_FORMATS", "pdf,docx,jpg,png,tiff").split(","),
            enable_processing_fallback=os.getenv("ENABLE_PROCESSING_FALLBACK", "True").lower() == "true",
            fallback_timeout_seconds=int(os.getenv("FALLBACK_TIMEOUT_SECONDS", "30")),
            max_fallback_attempts=int(os.getenv("MAX_FALLBACK_ATTEMPTS", "2")),
        )

        # Cache configuration
        self.cache = CacheConfig(
            cache_type=os.getenv("CACHE_TYPE", "simple"),
        )

        # Logging configuration
        self.logging = LoggingConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE"),
        )

        # Server configuration
        self.server: ServerConfig = ServerConfig(
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "5000")),
            debug=False,
            testing=self.environment == "testing",
        )

        # Adjust secure cookie setting based on environment
        if self.environment in ["development", "testing"] or self.server.debug:
            self.security.session_cookie_secure = False
            logger.info(
                "Session cookies set to non-secure for development/testing environment."
            )

    def _get_secret_key(self) -> str:
        """Get or generate a secure secret key."""

        secret_key = os.getenv("SECRET_KEY")
        if not secret_key:
            if self.environment == "production":
                raise ValueError("SECRET_KEY must be set in production environment")
            secret_key = secrets.token_hex(32)
            logger.warning(
                "Using generated SECRET_KEY for development. Set SECRET_KEY environment variable for production."
            )

        return secret_key

    def _resolve_database_url(self, database_url: str) -> str:
        """Resolve database URL with proper path resolution for SQLite databases."""
        if database_url.startswith("sqlite:///"):
            # Extract the path part after sqlite:///
            db_path = database_url[10:]  # Remove "sqlite:///"

            # If it's a relative path, resolve it relative to the project root
            if not os.path.isabs(db_path):
                # Get the project root (parent of src directory)
                project_root = Path(__file__).parent.parent.parent
                resolved_path = os.path.join(project_root, db_path)
                resolved_path = os.path.abspath(resolved_path)

                # Ensure the directory exists
                db_dir = os.path.dirname(resolved_path)
                os.makedirs(db_dir, exist_ok=True)

                # Return the resolved URL
                return f"sqlite:///{resolved_path}"
            else:
                # Already absolute path
                return database_url
        else:
            # Not a SQLite database, return as-is
            return database_url

    def get_flask_config(self) -> Dict[str, Any]:
        """
        Get Flask-compatible configuration dictionary.

        Returns:
            Dictionary of Flask configuration settings
        """
        from datetime import timedelta

        return {
            "SECRET_KEY": self.security.secret_key,
            "DEBUG": self.server.debug,
            "TESTING": self.server.testing,
            "MAX_CONTENT_LENGTH": None,  # No file size limit
            "PERMANENT_SESSION_LIFETIME": timedelta(days=365),  # Very long session (1 year)
            "SESSION_COOKIE_HTTPONLY": self.security.session_cookie_httponly,
            "SESSION_COOKIE_SECURE": self.security.session_cookie_secure,
            "SESSION_COOKIE_SAMESITE": self.security.session_cookie_samesite,
            "SESSION_COOKIE_DOMAIN": self.security.session_cookie_domain,
            "WTF_CSRF_ENABLED": self.security.csrf_enabled,
            "WTF_CSRF_TIME_LIMIT": None,  # No CSRF time limit
            "SQLALCHEMY_DATABASE_URI": self.database.database_url,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "pool_size": self.database.database_pool_size,
                "pool_timeout": self.database.database_pool_timeout,
                "pool_recycle": self.database.database_pool_recycle,
                "echo": self.database.database_echo,
                # SQLite-specific optimizations to reduce locking
                "connect_args": (
                    {
                        "check_same_thread": False,
                        "timeout": 30,  # 30 second timeout for database operations
                    }
                    if self.database.database_url.startswith("sqlite")
                    else {}
                ),
                "poolclass": (
                    None if self.database.database_url.startswith("sqlite") else None
                ),
            },
        }

    def _validate_configuration(self):
        """Validate all configuration settings and log warnings."""
        validation_warnings = []

        # Validate API keys
        api_warnings = ConfigurationValidator.validate_api_keys(self.api)
        validation_warnings.extend(api_warnings)

        # Validate directories
        dir_warnings = ConfigurationValidator.validate_directories(self.files)
        validation_warnings.extend(dir_warnings)

        # Validate database
        db_warnings = ConfigurationValidator.validate_database_url(
            self.database.database_url
        )
        validation_warnings.extend(db_warnings)

        # Log all warnings
        for warning in validation_warnings:
            logger.warning(warning)

        if validation_warnings:
            logger.info(
                f"Configuration loaded with {len(validation_warnings)} warnings"
            )
        else:
            logger.info("Configuration loaded successfully with no warnings")

    def validate(self) -> bool:
        """
        Validate all configuration settings.

        Returns:
            True if all settings are valid

        Raises:
            ValueError: If any configuration is invalid
        """
        try:
            # Validation is done during initialization
            logger.info(
                f"Configuration validated successfully for environment: {self.environment}"
            )
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            raise

    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current configuration settings.

        Returns:
            Dictionary containing configuration summary
        """
        return {
            "environment": self.environment,
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "debug": self.server.debug,
                "testing": self.server.testing,
            },
            "database": {
                "type": (
                    "sqlite"
                    if self.database.database_url.startswith("sqlite")
                    else "other"
                ),
                "echo": self.database.database_echo,
            },
            "files": {
                "max_size_mb": self.files.max_file_size_mb,
                "supported_formats": len(self.files.supported_formats),
                "temp_dir": str(self.files.temp_dir),
                "output_dir": str(self.files.output_dir),
                "upload_dir": str(self.files.upload_dir),
            },
            "api": {
                "ocr_configured": bool(self.api.handwriting_ocr_api_key),
                "llm_configured": bool(self.api.deepseek_api_key),
                "deepseek_model": self.api.deepseek_model,
            },
            "security": {
                "csrf_enabled": self.security.csrf_enabled,
                "secure_cookies": self.security.session_cookie_secure,
                "session_timeout": self.security.session_timeout,
            },
            "logging": {
                "level": self.logging.log_level,
                "file": self.logging.log_file,
            },
        }

    def reload(self):
        """Reload configuration from environment variables."""
        logger.info("Reloading configuration from environment variables")

        # Reload environment variables
        load_environment_variables()

        # Migrate any new deprecated variables
        ConfigurationMigrator.migrate_environment_variables()

        # Reload configuration
        self._load_configuration()

        # Re-validate configuration
        self._validate_configuration()

        logger.info("Configuration reloaded successfully")

    def export_environment_template(self, include_values: bool = False) -> str:
        """
        Export environment variable template.

        Args:
            include_values: Whether to include current values (for backup)

        Returns:
            String containing environment variable template
        """
        template_lines = [
            "# Exam Grader Application Configuration",
            "# Generated environment variable template",
            "",
            "# Security Settings",
            f"SECRET_KEY={'=' + self.security.secret_key if include_values else '=<generate_secure_random_key>'}",
            f"SESSION_TIMEOUT={'=' + str(self.security.session_timeout) if include_values else '=3600'}",
            f"CSRF_ENABLED={'=' + str(self.security.csrf_enabled) if include_values else '=True'}",
            "",
            "# Database Settings",
            f"DATABASE_URL={'=' + self.database.database_url if include_values else '=sqlite:///exam_grader.db'}",
            f"DATABASE_ECHO={'=' + str(self.database.database_echo) if include_values else '=False'}",
            "",
            "# File Processing Settings",
            f"MAX_FILE_SIZE_MB={'=' + str(self.files.max_file_size_mb) if include_values else '=None'}",
            f"SUPPORTED_FORMATS={'=' + ','.join(self.files.supported_formats) if include_values else '=.pdf,.docx,.jpg,.png'}",
            f"TEMP_DIR={'=' + str(self.files.temp_dir) if include_values else '=temp'}",
            f"OUTPUT_DIR={'=' + str(self.files.output_dir) if include_values else '=output'}",
            f"UPLOAD_DIR={'=' + str(self.files.upload_dir) if include_values else '=uploads'}",
            "",
            "# API Settings",
            f"HANDWRITING_OCR_API_KEY={'=' + self.api.handwriting_ocr_api_key if include_values else '=your_ocr_api_key'}",
            f"HANDWRITING_OCR_API_URL={'=' + self.api.handwriting_ocr_api_url if include_values else '=https://www.handwritingocr.com/api/v3'}",
            f"DEEPSEEK_API_KEY={'=' + self.api.deepseek_api_key if include_values else '=your_deepseek_api_key'}",
            f"DEEPSEEK_MODEL={'=' + self.api.deepseek_model if include_values else '=deepseek-chat'}",
            "",
            "# Server Settings",
            f"HOST={'=' + self.server.host if include_values else '=127.0.0.1'}",
            f"PORT={'=' + str(self.server.port) if include_values else '=5000'}",
            f"DEBUG={'=' + str(self.server.debug) if include_values else '=False'}",
            "",
            "# Logging Settings",
            f"LOG_LEVEL={'=' + self.logging.log_level if include_values else '=INFO'}",
            f"LOG_FILE={'=' + (self.logging.log_file or '') if include_values else '='}",
            "",
            "# Cache Settings",
            f"CACHE_TYPE={'=' + self.cache.cache_type if include_values else '=simple'}",
        ]

        return "\n".join(template_lines)

    @property
    def ocr(self):
        """Get OCR configuration object with enabled property."""
        class OCRConfig:
            def __init__(self, api_config):
                self.api_key = api_config.handwriting_ocr_api_key
                self.api_url = api_config.handwriting_ocr_api_url
                self.delete_after = api_config.handwriting_ocr_delete_after
            
            @property
            def enabled(self):
                """Check if OCR is enabled (has API key)."""
                return bool(self.api_key and self.api_key.strip())
        
        return OCRConfig(self.api)

# Global configuration instance
config = UnifiedConfig()
