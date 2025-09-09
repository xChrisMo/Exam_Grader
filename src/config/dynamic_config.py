"""
Dynamic Configuration System

This module provides a centralized configuration system that replaces all hardcoded values
with environment-configurable options. It ensures consistency across the application
and makes deployment easier.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path

from utils.logger import logger


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


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///exam_grader.db"))
    pool_size: int = field(default_factory=lambda: int(os.getenv("DB_POOL_SIZE", "10")))
    pool_timeout: int = field(default_factory=lambda: int(os.getenv("DB_POOL_TIMEOUT", "30")))
    pool_recycle: int = field(default_factory=lambda: int(os.getenv("DB_POOL_RECYCLE", "3600")))
    busy_timeout: int = field(default_factory=lambda: int(os.getenv("DB_BUSY_TIMEOUT", "30000")))
    cache_size: int = field(default_factory=lambda: int(os.getenv("DB_CACHE_SIZE", "64000")))


@dataclass
class APIConfig:
    """API configuration settings."""
    timeout: int = field(default_factory=lambda: int(os.getenv("API_TIMEOUT", "60")))
    retry_attempts: int = field(default_factory=lambda: int(os.getenv("API_RETRY_ATTEMPTS", "3")))
    retry_delay: float = field(default_factory=lambda: float(os.getenv("API_RETRY_DELAY", "2.0")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("API_MAX_RETRIES", "10")))
    max_backoff_delay: float = field(default_factory=lambda: float(os.getenv("API_MAX_BACKOFF_DELAY", "60.0")))


@dataclass
class LLMConfig:
    """LLM service configuration settings."""
    base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "deepseek-chat"))
    api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    connection_pool_size: int = field(default_factory=lambda: int(os.getenv("LLM_CONNECTION_POOL_SIZE", "3")))
    retry_attempts: int = field(default_factory=lambda: int(os.getenv("LLM_RETRY_ATTEMPTS", "3")))
    retry_delay: float = field(default_factory=lambda: float(os.getenv("LLM_RETRY_DELAY", "2.0")))
    json_timeout: float = field(default_factory=lambda: float(os.getenv("LLM_JSON_TIMEOUT", "30.0")))
    retry_on_json_error: int = field(default_factory=lambda: int(os.getenv("LLM_RETRY_ON_JSON_ERROR", "2")))
    vision_max_file_size: str = field(default_factory=lambda: os.getenv("LLM_VISION_MAX_FILE_SIZE", "20MB"))


@dataclass
class OCRConfig:
    """OCR service configuration settings."""
    api_key: str = field(default_factory=lambda: os.getenv("HANDWRITING_OCR_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("OCR_BASE_URL", "https://www.handwritingocr.com/api/v3"))
    request_timeout: int = field(default_factory=lambda: int(os.getenv("OCR_REQUEST_TIMEOUT", "30")))
    retry_delay: int = field(default_factory=lambda: int(os.getenv("OCR_RETRY_DELAY", "5")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("OCR_MAX_RETRIES", "3")))


@dataclass
class FileConfig:
    """File processing configuration settings."""
    max_file_size_mb: int = field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE_MB", "20")))
    max_storage_size_mb: int = field(default_factory=lambda: int(os.getenv("MAX_STORAGE_SIZE_MB", "1000")))
    upload_dir: str = field(default_factory=lambda: os.getenv("UPLOAD_DIR", "uploads"))
    temp_dir: str = field(default_factory=lambda: os.getenv("TEMP_DIR", "temp"))
    output_dir: str = field(default_factory=lambda: os.getenv("OUTPUT_DIR", "output"))
    logs_dir: str = field(default_factory=lambda: os.getenv("LOGS_DIR", "logs"))
    instance_dir: str = field(default_factory=lambda: os.getenv("INSTANCE_DIR", "instance"))
    cleanup_interval_hours: int = field(default_factory=lambda: int(os.getenv("CLEANUP_INTERVAL_HOURS", "24")))
    storage_expiration_days: int = field(default_factory=lambda: int(os.getenv("STORAGE_EXPIRATION_DAYS", "30")))


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    default_size: int = field(default_factory=lambda: int(os.getenv("CACHE_DEFAULT_SIZE", "10000")))
    default_ttl: int = field(default_factory=lambda: int(os.getenv("CACHE_DEFAULT_TTL", "86400")))
    l1_memory_size: int = field(default_factory=lambda: int(os.getenv("CACHE_L1_SIZE", "5000")))
    l2_memory_size: int = field(default_factory=lambda: int(os.getenv("CACHE_L2_SIZE", "50000")))
    timeout: int = field(default_factory=lambda: int(os.getenv("CACHE_TIMEOUT", "3600")))


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", ""))
    session_timeout: int = field(default_factory=lambda: int(os.getenv("SESSION_TIMEOUT", "3600")))
    max_concurrent_sessions: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_SESSIONS", "3")))
    max_failed_attempts: int = field(default_factory=lambda: int(os.getenv("MAX_FAILED_ATTEMPTS", "5")))
    lockout_duration: int = field(default_factory=lambda: int(os.getenv("LOCKOUT_DURATION", "15")))
    password_max_length: int = field(default_factory=lambda: int(os.getenv("PASSWORD_MAX_LENGTH", "128")))
    min_secret_key_length: int = field(default_factory=lambda: int(os.getenv("MIN_SECRET_KEY_LENGTH", "32")))


@dataclass
class RateLimitConfig:
    """Rate limiting configuration settings."""
    requests_per_minute: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")))
    requests_per_hour: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_HOUR", "3600")))
    login_attempts_per_minute: int = field(default_factory=lambda: int(os.getenv("LOGIN_ATTEMPTS_PER_MINUTE", "5")))
    burst_limit: int = field(default_factory=lambda: int(os.getenv("BURST_LIMIT", "10")))
    window_seconds: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_WINDOW", "3600")))


@dataclass
class ProcessingConfig:
    """Processing configuration settings."""
    max_attempts: int = field(default_factory=lambda: int(os.getenv("PROCESSING_MAX_ATTEMPTS", "3")))
    base_delay: float = field(default_factory=lambda: float(os.getenv("PROCESSING_BASE_DELAY", "1.0")))
    max_delay: float = field(default_factory=lambda: float(os.getenv("PROCESSING_MAX_DELAY", "30.0")))
    exponential_base: float = field(default_factory=lambda: float(os.getenv("PROCESSING_EXPONENTIAL_BASE", "2.0")))
    jitter: bool = field(default_factory=lambda: os.getenv("PROCESSING_JITTER", "True").lower() == "true")
    backoff_multiplier: float = field(default_factory=lambda: float(os.getenv("PROCESSING_BACKOFF_MULTIPLIER", "1.5")))
    fallback_timeout: int = field(default_factory=lambda: int(os.getenv("FALLBACK_TIMEOUT_SECONDS", "30")))
    max_fallback_attempts: int = field(default_factory=lambda: int(os.getenv("MAX_FALLBACK_ATTEMPTS", "2")))


@dataclass
class TimeoutConfig:
    """Timeout configuration settings."""
    ocr_processing: int = field(default_factory=lambda: int(os.getenv("TIMEOUT_OCR_PROCESSING", "180")))
    llm_processing: int = field(default_factory=lambda: int(os.getenv("TIMEOUT_LLM_PROCESSING", "600")))
    file_processing: int = field(default_factory=lambda: int(os.getenv("TIMEOUT_FILE_PROCESSING", "90")))
    mapping_service: int = field(default_factory=lambda: int(os.getenv("TIMEOUT_MAPPING_SERVICE", "180")))
    grading_service: int = field(default_factory=lambda: int(os.getenv("TIMEOUT_GRADING_SERVICE", "600")))
    health_check: int = field(default_factory=lambda: int(os.getenv("TIMEOUT_HEALTH_CHECK", "30")))
    service_initialization: int = field(default_factory=lambda: int(os.getenv("TIMEOUT_SERVICE_INIT", "60")))
    default: int = field(default_factory=lambda: int(os.getenv("TIMEOUT_DEFAULT", "60")))
    standard_request: int = field(default_factory=lambda: int(os.getenv("TIMEOUT_STANDARD_REQUEST", "30")))
    antiword: int = field(default_factory=lambda: int(os.getenv("TIMEOUT_ANTIWORD", "30")))
    tesseract: int = field(default_factory=lambda: int(os.getenv("TIMEOUT_TESSERACT", "5")))


@dataclass
class PerformanceConfig:
    """Performance configuration settings."""
    max_memory_mb: int = field(default_factory=lambda: int(os.getenv("MAX_MEMORY_MB", "1024")))
    max_cpu_percent: int = field(default_factory=lambda: int(os.getenv("MAX_CPU_PERCENT", "80")))
    max_concurrent_operations: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_OPERATIONS", "10")))
    max_concurrent_processes: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_PROCESSES", "4")))
    memory_limit_gb: int = field(default_factory=lambda: int(os.getenv("MEMORY_LIMIT_GB", "4")))
    connection_limit: int = field(default_factory=lambda: int(os.getenv("CONNECTION_LIMIT", "200")))
    max_request_body_size: int = field(default_factory=lambda: int(os.getenv("MAX_REQUEST_BODY_SIZE", "104857600")))  # 100MB


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    max_bytes: int = field(default_factory=lambda: int(os.getenv("LOG_MAX_BYTES", "10485760")))  # 10MB
    backup_count: int = field(default_factory=lambda: int(os.getenv("LOG_BACKUP_COUNT", "5")))
    encoding: str = field(default_factory=lambda: os.getenv("LOG_ENCODING", "utf-8"))


@dataclass
class MonitoringConfig:
    """Monitoring configuration settings."""
    enabled: bool = field(default_factory=lambda: os.getenv("MONITORING_ENABLED", "True").lower() == "true")
    check_interval: int = field(default_factory=lambda: int(os.getenv("MONITORING_CHECK_INTERVAL", "30")))
    response_time_warning_ms: int = field(default_factory=lambda: int(os.getenv("RESPONSE_TIME_WARNING_MS", "5000")))
    response_time_critical_ms: int = field(default_factory=lambda: int(os.getenv("RESPONSE_TIME_CRITICAL_MS", "10000")))
    error_rate_warning: float = field(default_factory=lambda: float(os.getenv("ERROR_RATE_WARNING", "0.05")))
    error_rate_critical: float = field(default_factory=lambda: float(os.getenv("ERROR_RATE_CRITICAL", "0.1")))
    cpu_warning: int = field(default_factory=lambda: int(os.getenv("CPU_WARNING", "80")))
    cpu_critical: int = field(default_factory=lambda: int(os.getenv("CPU_CRITICAL", "95")))
    memory_warning: int = field(default_factory=lambda: int(os.getenv("MEMORY_WARNING", "85")))
    memory_critical: int = field(default_factory=lambda: int(os.getenv("MEMORY_CRITICAL", "95")))
    disk_warning: int = field(default_factory=lambda: int(os.getenv("DISK_WARNING", "90")))
    disk_critical: int = field(default_factory=lambda: int(os.getenv("DISK_CRITICAL", "95")))


@dataclass
class DynamicConfig:
    """Main configuration class that combines all configuration sections."""
    
    server: ServerConfig = field(default_factory=ServerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    api: APIConfig = field(default_factory=APIConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    file: FileConfig = field(default_factory=FileConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()
        self._create_directories()

    def _validate_config(self):
        """Validate configuration values."""
        # Validate server port
        if not (1 <= self.server.port <= 65535):
            raise ValueError(f"Server port must be between 1 and 65535, got {self.server.port}")
        
        # Validate file size limits
        if self.file.max_file_size_mb <= 0:
            raise ValueError(f"Max file size must be positive, got {self.file.max_file_size_mb}")
        
        # Validate timeouts
        for timeout_name, timeout_value in self.timeout.__dict__.items():
            if timeout_value <= 0:
                raise ValueError(f"Timeout {timeout_name} must be positive, got {timeout_value}")
        
        # Validate retry settings
        if self.api.max_retries <= 0:
            raise ValueError(f"API max retries must be positive, got {self.api.max_retries}")
        
        logger.info("Configuration validation completed successfully")

    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            self.file.upload_dir,
            self.file.temp_dir,
            self.file.output_dir,
            self.file.logs_dir,
            self.file.instance_dir,
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created/verified directories: {directories}")

    def get_environment_summary(self, include_values: bool = False) -> List[str]:
        """Get a summary of environment variables and their values."""
        summary = []
        
        # Server configuration
        summary.append(f"HOST={'=' + self.server.host if include_values else '=127.0.0.1'}")
        summary.append(f"PORT={'=' + str(self.server.port) if include_values else '=8501'}")
        summary.append(f"DEBUG={'=' + str(self.server.debug) if include_values else '=False'}")
        
        # Database configuration
        summary.append(f"DATABASE_URL={'=' + self.database.url if include_values else '=sqlite:///exam_grader.db'}")
        summary.append(f"DB_POOL_SIZE={'=' + str(self.database.pool_size) if include_values else '=10'}")
        
        # LLM configuration
        summary.append(f"LLM_BASE_URL={'=' + self.llm.base_url if include_values else '=https://api.deepseek.com/v1'}")
        summary.append(f"LLM_MODEL={'=' + self.llm.model if include_values else '=deepseek-chat'}")
        
        # File configuration
        summary.append(f"MAX_FILE_SIZE_MB={'=' + str(self.file.max_file_size_mb) if include_values else '=20'}")
        summary.append(f"UPLOAD_DIR={'=' + self.file.upload_dir if include_values else '=uploads'}")
        
        # Performance configuration
        summary.append(f"MAX_CONCURRENT_PROCESSES={'=' + str(self.performance.max_concurrent_processes) if include_values else '=4'}")
        summary.append(f"MEMORY_LIMIT_GB={'=' + str(self.performance.memory_limit_gb) if include_values else '=4'}")
        
        return summary

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "server": self.server.__dict__,
            "database": self.database.__dict__,
            "api": self.api.__dict__,
            "llm": self.llm.__dict__,
            "ocr": self.ocr.__dict__,
            "file": self.file.__dict__,
            "cache": self.cache.__dict__,
            "security": self.security.__dict__,
            "rate_limit": self.rate_limit.__dict__,
            "processing": self.processing.__dict__,
            "timeout": self.timeout.__dict__,
            "performance": self.performance.__dict__,
            "logging": self.logging.__dict__,
            "monitoring": self.monitoring.__dict__,
        }


# Global configuration instance
dynamic_config = DynamicConfig()


def get_dynamic_config() -> DynamicConfig:
    """Get the global dynamic configuration instance."""
    return dynamic_config


def reload_config():
    """Reload configuration from environment variables."""
    global dynamic_config
    dynamic_config = DynamicConfig()
    logger.info("Configuration reloaded from environment variables")
    return dynamic_config
