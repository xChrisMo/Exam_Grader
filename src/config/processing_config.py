"""
Processing Configuration Management System.

This module provides configuration management specifically for processing services,
including retry policies, timeouts, caching, health checks, and logging configuration.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import timedelta

try:
    from utils.logger import Logger
    logger = Logger().get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

@dataclass
class RetryPolicyConfig:
    """Configuration for retry policies."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    backoff_multiplier: float = 2.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'max_attempts': self.max_attempts,
            'base_delay': self.base_delay,
            'max_delay': self.max_delay,
            'exponential_base': self.exponential_base,
            'jitter': self.jitter,
            'backoff_multiplier': self.backoff_multiplier
        }

@dataclass
class CacheSizeConfig:
    """Configuration for cache size limits."""
    max_size_mb: int = 50
    max_entries: int = 500

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'max_size_mb': self.max_size_mb,
            'max_entries': self.max_entries
        }

@dataclass
class CacheConfig:
    """Configuration for caching system."""
    enabled: bool = True
    default_ttl: int = 3600
    size_limits: Dict[str, CacheSizeConfig] = field(default_factory=dict)
    expiration_policies: Dict[str, int] = field(default_factory=dict)
    cleanup_interval: int = 300
    auto_cleanup_enabled: bool = True

    def get_size_limit(self, cache_type: str) -> CacheSizeConfig:
        """Get size limit for specific cache type."""
        return self.size_limits.get(cache_type, self.size_limits.get('default', CacheSizeConfig()))

    def get_expiration_time(self, data_type: str) -> int:
        """Get expiration time for specific data type."""
        return self.expiration_policies.get(data_type, self.default_ttl)

@dataclass
class HealthCheckThresholds:
    """Configuration for health check thresholds."""
    response_time_warning_ms: int = 5000
    response_time_critical_ms: int = 10000
    error_rate_warning: float = 0.05
    error_rate_critical: float = 0.15
    memory_usage_warning: float = 0.80
    memory_usage_critical: float = 0.95
    cpu_usage_warning: float = 0.85
    cpu_usage_critical: float = 0.95
    disk_usage_warning: float = 0.90
    disk_usage_critical: float = 0.98

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'response_time_warning_ms': self.response_time_warning_ms,
            'response_time_critical_ms': self.response_time_critical_ms,
            'error_rate_warning': self.error_rate_warning,
            'error_rate_critical': self.error_rate_critical,
            'memory_usage_warning': self.memory_usage_warning,
            'memory_usage_critical': self.memory_usage_critical,
            'cpu_usage_warning': self.cpu_usage_warning,
            'cpu_usage_critical': self.cpu_usage_critical,
            'disk_usage_warning': self.disk_usage_warning,
            'disk_usage_critical': self.disk_usage_critical
        }

@dataclass
class HealthCheckConfig:
    """Configuration for health check system."""
    enabled: bool = True
    intervals: Dict[str, int] = field(default_factory=dict)
    thresholds: HealthCheckThresholds = field(default_factory=HealthCheckThresholds)
    consecutive_failures_threshold: int = 3
    recovery_check_interval: int = 300
    health_history_retention: int = 86400

    def get_interval(self, check_type: str) -> int:
        """Get interval for specific health check type."""
        return self.intervals.get(check_type, 60)

@dataclass
class LoggingDestination:
    """Configuration for logging destination."""
    enabled: bool = True
    level: str = "INFO"
    path: Optional[str] = None
    max_size_mb: int = 50
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'level': self.level,
            'path': self.path,
            'max_size_mb': self.max_size_mb,
            'backup_count': self.backup_count,
            'format': self.format
        }

@dataclass
class LoggingConfig:
    """Configuration for logging system."""
    levels: Dict[str, str] = field(default_factory=dict)
    output_destinations: Dict[str, LoggingDestination] = field(default_factory=dict)
    structured_logging: Dict[str, bool] = field(default_factory=dict)

    def get_level(self, component: str) -> str:
        """Get log level for specific component."""
        return self.levels.get(component, "INFO")

    def get_destination(self, dest_name: str) -> Optional[LoggingDestination]:
        """Get logging destination configuration."""
        return self.output_destinations.get(dest_name)

@dataclass
class ResourceLimits:
    """Configuration for resource limits."""
    max_memory_mb: int = 1024
    max_cpu_percent: int = 80
    max_concurrent_operations: int = 10
    max_file_size_mb: int = 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'max_memory_mb': self.max_memory_mb,
            'max_cpu_percent': self.max_cpu_percent,
            'max_concurrent_operations': self.max_concurrent_operations,
            'max_file_size_mb': self.max_file_size_mb
        }

@dataclass
class FallbackStrategy:
    """Configuration for fallback strategies."""
    primary: str
    fallbacks: List[str] = field(default_factory=list)
    fallback_threshold: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'primary': self.primary,
            'fallbacks': self.fallbacks,
            'fallback_threshold': self.fallback_threshold
        }

class ProcessingConfigManager:
    """
    Manager for processing service configuration.
    
    This class loads and manages configuration settings for all processing services,
    including retry policies, timeouts, caching, health checks, and logging.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize processing configuration manager.
        
        Args:
            config_path: Path to processing configuration file
        """
        self.config_path = config_path or "config/processing.json"
        self._config_data = {}
        self._load_configuration()

    def _load_configuration(self):
        """Load configuration from file and environment variables."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self._config_data = json.load(f)
                logger.info(f"Loaded processing configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load processing configuration: {e}")
                self._config_data = {}
        else:
            logger.warning(f"Processing configuration file not found: {self.config_path}")
            self._config_data = {}

        # Override with environment variables
        self._apply_environment_overrides()

    def _apply_environment_overrides(self):
        """Apply environment variable overrides to configuration."""
        # Retry policy overrides
        for service in ['ocr_processing', 'llm_processing', 'file_processing', 'mapping_service', 'grading_service']:
            env_prefix = f"PROCESSING_{service.upper()}_"
            
            if f"retry_policies" not in self._config_data:
                self._config_data["retry_policies"] = {}
            if service not in self._config_data["retry_policies"]:
                self._config_data["retry_policies"][service] = {}
                
            for key in ['max_attempts', 'base_delay', 'max_delay']:
                env_var = f"{env_prefix}{key.upper()}"
                if env_var in os.environ:
                    try:
                        value = float(os.environ[env_var]) if 'delay' in key else int(os.environ[env_var])
                        self._config_data["retry_policies"][service][key] = value
                        logger.info(f"Applied environment override: {env_var}={value}")
                    except ValueError as e:
                        logger.error(f"Invalid environment variable value for {env_var}: {e}")

        # Timeout overrides
        timeout_env = os.getenv("PROCESSING_DEFAULT_TIMEOUT")
        if timeout_env:
            try:
                if "timeouts" not in self._config_data:
                    self._config_data["timeouts"] = {}
                self._config_data["timeouts"]["default"] = int(timeout_env)
                logger.info(f"Applied timeout override: PROCESSING_DEFAULT_TIMEOUT={timeout_env}")
            except ValueError as e:
                logger.error(f"Invalid timeout value: {e}")

        # Cache configuration overrides
        cache_enabled = os.getenv("PROCESSING_CACHE_ENABLED")
        if cache_enabled:
            if "cache_configuration" not in self._config_data:
                self._config_data["cache_configuration"] = {}
            self._config_data["cache_configuration"]["enabled"] = cache_enabled.lower() == "true"
            logger.info(f"Applied cache override: PROCESSING_CACHE_ENABLED={cache_enabled}")

        # Health check overrides
        health_enabled = os.getenv("PROCESSING_HEALTH_CHECKS_ENABLED")
        if health_enabled:
            if "health_check_configuration" not in self._config_data:
                self._config_data["health_check_configuration"] = {}
            self._config_data["health_check_configuration"]["enabled"] = health_enabled.lower() == "true"
            logger.info(f"Applied health check override: PROCESSING_HEALTH_CHECKS_ENABLED={health_enabled}")

        # Logging level overrides
        log_level = os.getenv("PROCESSING_LOG_LEVEL")
        if log_level:
            if "logging_configuration" not in self._config_data:
                self._config_data["logging_configuration"] = {}
            if "levels" not in self._config_data["logging_configuration"]:
                self._config_data["logging_configuration"]["levels"] = {}
            self._config_data["logging_configuration"]["levels"]["processing_services"] = log_level.upper()
            logger.info(f"Applied logging override: PROCESSING_LOG_LEVEL={log_level}")

    def get_retry_policy(self, service: str) -> RetryPolicyConfig:
        """
        Get retry policy configuration for a service.
        
        Args:
            service: Service name
            
        Returns:
            RetryPolicyConfig instance
        """
        retry_policies = self._config_data.get("retry_policies", {})
        policy_data = retry_policies.get(service, retry_policies.get("default", {}))
        
        return RetryPolicyConfig(
            max_attempts=policy_data.get("max_attempts", 3),
            base_delay=policy_data.get("base_delay", 1.0),
            max_delay=policy_data.get("max_delay", 30.0),
            exponential_base=policy_data.get("exponential_base", 2.0),
            jitter=policy_data.get("jitter", True),
            backoff_multiplier=policy_data.get("backoff_multiplier", 2.0)
        )

    def get_timeout(self, operation: str) -> int:
        """
        Get timeout for a specific operation.
        
        Args:
            operation: Operation name
            
        Returns:
            Timeout in seconds
        """
        timeouts = self._config_data.get("timeouts", {})
        return timeouts.get(operation, timeouts.get("default", 30))

    def get_cache_config(self) -> CacheConfig:
        """
        Get cache configuration.
        
        Returns:
            CacheConfig instance
        """
        cache_data = self._config_data.get("cache_configuration", {})
        
        # Parse size limits
        size_limits = {}
        size_limits_data = cache_data.get("size_limits", {})
        for cache_type, limits in size_limits_data.items():
            size_limits[cache_type] = CacheSizeConfig(
                max_size_mb=limits.get("max_size_mb", 50),
                max_entries=limits.get("max_entries", 500)
            )
        
        return CacheConfig(
            enabled=cache_data.get("enabled", True),
            default_ttl=cache_data.get("default_ttl", 3600),
            size_limits=size_limits,
            expiration_policies=cache_data.get("expiration_policies", {}),
            cleanup_interval=cache_data.get("cleanup_interval", 300),
            auto_cleanup_enabled=cache_data.get("auto_cleanup_enabled", True)
        )

    def get_health_check_config(self) -> HealthCheckConfig:
        """
        Get health check configuration.
        
        Returns:
            HealthCheckConfig instance
        """
        health_data = self._config_data.get("health_check_configuration", {})
        
        # Parse thresholds
        thresholds_data = health_data.get("thresholds", {})
        thresholds = HealthCheckThresholds(
            response_time_warning_ms=thresholds_data.get("response_time_warning_ms", 5000),
            response_time_critical_ms=thresholds_data.get("response_time_critical_ms", 10000),
            error_rate_warning=thresholds_data.get("error_rate_warning", 0.05),
            error_rate_critical=thresholds_data.get("error_rate_critical", 0.15),
            memory_usage_warning=thresholds_data.get("memory_usage_warning", 0.80),
            memory_usage_critical=thresholds_data.get("memory_usage_critical", 0.95),
            cpu_usage_warning=thresholds_data.get("cpu_usage_warning", 0.85),
            cpu_usage_critical=thresholds_data.get("cpu_usage_critical", 0.95),
            disk_usage_warning=thresholds_data.get("disk_usage_warning", 0.90),
            disk_usage_critical=thresholds_data.get("disk_usage_critical", 0.98)
        )
        
        return HealthCheckConfig(
            enabled=health_data.get("enabled", True),
            intervals=health_data.get("intervals", {}),
            thresholds=thresholds,
            consecutive_failures_threshold=health_data.get("consecutive_failures_threshold", 3),
            recovery_check_interval=health_data.get("recovery_check_interval", 300),
            health_history_retention=health_data.get("health_history_retention", 86400)
        )

    def get_logging_config(self) -> LoggingConfig:
        """
        Get logging configuration.
        
        Returns:
            LoggingConfig instance
        """
        logging_data = self._config_data.get("logging_configuration", {})
        
        # Parse output destinations
        destinations = {}
        destinations_data = logging_data.get("output_destinations", {})
        for dest_name, dest_config in destinations_data.items():
            destinations[dest_name] = LoggingDestination(
                enabled=dest_config.get("enabled", True),
                level=dest_config.get("level", "INFO"),
                path=dest_config.get("path"),
                max_size_mb=dest_config.get("max_size_mb", 50),
                backup_count=dest_config.get("backup_count", 5),
                format=dest_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
        
        return LoggingConfig(
            levels=logging_data.get("levels", {}),
            output_destinations=destinations,
            structured_logging=logging_data.get("structured_logging", {})
        )

    def get_resource_limits(self) -> ResourceLimits:
        """
        Get resource limits configuration.
        
        Returns:
            ResourceLimits instance
        """
        perf_data = self._config_data.get("performance_optimization", {})
        limits_data = perf_data.get("resource_limits", {})
        
        return ResourceLimits(
            max_memory_mb=limits_data.get("max_memory_mb", 1024),
            max_cpu_percent=limits_data.get("max_cpu_percent", 80),
            max_concurrent_operations=limits_data.get("max_concurrent_operations", 10),
            max_file_size_mb=limits_data.get("max_file_size_mb", 100)
        )

    def get_fallback_strategy(self, service: str) -> Optional[FallbackStrategy]:
        """
        Get fallback strategy for a service.
        
        Args:
            service: Service name
            
        Returns:
            FallbackStrategy instance or None
        """
        fallback_data = self._config_data.get("fallback_strategies", {})
        strategy_data = fallback_data.get(service)
        
        if not strategy_data:
            return None
            
        return FallbackStrategy(
            primary=strategy_data.get("primary", ""),
            fallbacks=strategy_data.get("fallbacks", []),
            fallback_threshold=strategy_data.get("fallback_threshold", 0.8)
        )

    def is_cache_enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._config_data.get("cache_configuration", {}).get("enabled", True)

    def is_health_checks_enabled(self) -> bool:
        """Check if health checks are enabled."""
        return self._config_data.get("health_check_configuration", {}).get("enabled", True)

    def is_async_processing_enabled(self) -> bool:
        """Check if async processing is enabled."""
        return self._config_data.get("performance_optimization", {}).get("async_processing", {}).get("enabled", True)

    def get_cleanup_config(self) -> Dict[str, Any]:
        """Get resource cleanup configuration."""
        return self._config_data.get("resource_management", {}).get("cleanup", {})

    def get_error_handling_config(self) -> Dict[str, Any]:
        """Get error handling configuration."""
        return self._config_data.get("error_handling", {})

    def reload_configuration(self):
        """Reload configuration from file and environment variables."""
        logger.info("Reloading processing configuration")
        self._load_configuration()
        logger.info("Processing configuration reloaded successfully")

    def validate_configuration(self) -> List[str]:
        """
        Validate configuration and return list of warnings.
        
        Returns:
            List of validation warnings
        """
        warnings = []
        
        # Validate retry policies
        retry_policies = self._config_data.get("retry_policies", {})
        for service, policy in retry_policies.items():
            if policy.get("max_attempts", 0) <= 0:
                warnings.append(f"Invalid max_attempts for {service}: must be > 0")
            if policy.get("base_delay", 0) <= 0:
                warnings.append(f"Invalid base_delay for {service}: must be > 0")
            if policy.get("max_delay", 0) <= policy.get("base_delay", 1):
                warnings.append(f"Invalid max_delay for {service}: must be > base_delay")

        # Validate timeouts
        timeouts = self._config_data.get("timeouts", {})
        for operation, timeout in timeouts.items():
            if timeout <= 0:
                warnings.append(f"Invalid timeout for {operation}: must be > 0")

        # Validate cache configuration
        cache_config = self._config_data.get("cache_configuration", {})
        if cache_config.get("enabled", True):
            size_limits = cache_config.get("size_limits", {})
            for cache_type, limits in size_limits.items():
                if limits.get("max_size_mb", 0) <= 0:
                    warnings.append(f"Invalid max_size_mb for {cache_type}: must be > 0")
                if limits.get("max_entries", 0) <= 0:
                    warnings.append(f"Invalid max_entries for {cache_type}: must be > 0")

        # Validate health check thresholds
        health_config = self._config_data.get("health_check_configuration", {})
        if health_config.get("enabled", True):
            thresholds = health_config.get("thresholds", {})
            for threshold_name, value in thresholds.items():
                if "rate" in threshold_name and not (0 <= value <= 1):
                    warnings.append(f"Invalid {threshold_name}: must be between 0 and 1")
                elif "usage" in threshold_name and not (0 <= value <= 1):
                    warnings.append(f"Invalid {threshold_name}: must be between 0 and 1")

        return warnings

    def export_config(self, include_defaults: bool = False) -> Dict[str, Any]:
        """
        Export current configuration.
        
        Args:
            include_defaults: Whether to include default values
            
        Returns:
            Configuration dictionary
        """
        if include_defaults:
            # Return full configuration with defaults
            return {
                "retry_policies": {
                    service: self.get_retry_policy(service).to_dict()
                    for service in ["ocr_processing", "llm_processing", "file_processing", "mapping_service", "grading_service"]
                },
                "timeouts": {
                    operation: self.get_timeout(operation)
                    for operation in ["ocr_processing", "llm_processing", "file_processing", "health_check", "default"]
                },
                "cache_configuration": {
                    "enabled": self.is_cache_enabled(),
                    "config": self.get_cache_config().__dict__
                },
                "health_check_configuration": {
                    "enabled": self.is_health_checks_enabled(),
                    "config": self.get_health_check_config().__dict__
                },
                "resource_limits": self.get_resource_limits().to_dict(),
                "cleanup_config": self.get_cleanup_config(),
                "error_handling": self.get_error_handling_config()
            }
        else:
            # Return raw configuration data
            return self._config_data.copy()

# Global processing configuration instance
processing_config = ProcessingConfigManager()