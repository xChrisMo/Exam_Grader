#!/usr/bin/env python3
"""
Configuration Migration Script

This script helps migrate from hardcoded configuration values to environment-based
configuration. It can be used to:
1. Generate a .env file from current hardcoded values
2. Validate existing configuration
3. Show configuration differences
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.dynamic_config import get_dynamic_config
from utils.logger import logger


def generate_env_file(output_path: str = ".env") -> None:
    """Generate a .env file with current configuration values."""
    config = get_dynamic_config()
    
    env_content = []
    env_content.append("# Generated .env file from current configuration")
    env_content.append("# Review and customize these values for your environment")
    env_content.append("")
    
    # Server configuration
    env_content.append("# =============================================================================")
    env_content.append("# SERVER CONFIGURATION")
    env_content.append("# =============================================================================")
    env_content.append(f"HOST={config.server.host}")
    env_content.append(f"PORT={config.server.port}")
    env_content.append(f"DEBUG={config.server.debug}")
    env_content.append(f"TESTING={config.server.testing}")
    env_content.append(f"THREADED={config.server.threaded}")
    env_content.append(f"MAX_BATCH_WORKERS={config.server.max_batch_processing_workers}")
    env_content.append(f"BATCH_PROCESSING_SIZE={config.server.batch_processing_size}")
    env_content.append("")
    
    # Database configuration
    env_content.append("# =============================================================================")
    env_content.append("# DATABASE CONFIGURATION")
    env_content.append("# =============================================================================")
    env_content.append(f"DATABASE_URL={config.database.url}")
    env_content.append(f"DB_POOL_SIZE={config.database.pool_size}")
    env_content.append(f"DB_POOL_TIMEOUT={config.database.pool_timeout}")
    env_content.append(f"DB_POOL_RECYCLE={config.database.pool_recycle}")
    env_content.append(f"DB_BUSY_TIMEOUT={config.database.busy_timeout}")
    env_content.append(f"DB_CACHE_SIZE={config.database.cache_size}")
    env_content.append("")
    
    # LLM configuration
    env_content.append("# =============================================================================")
    env_content.append("# LLM SERVICE CONFIGURATION")
    env_content.append("# =============================================================================")
    env_content.append(f"LLM_BASE_URL={config.llm.base_url}")
    env_content.append(f"LLM_MODEL={config.llm.model}")
    env_content.append(f"DEEPSEEK_API_KEY={config.llm.api_key or 'your_deepseek_api_key_here'}")
    env_content.append(f"LLM_CONNECTION_POOL_SIZE={config.llm.connection_pool_size}")
    env_content.append(f"LLM_RETRY_ATTEMPTS={config.llm.retry_attempts}")
    env_content.append(f"LLM_RETRY_DELAY={config.llm.retry_delay}")
    env_content.append(f"LLM_JSON_TIMEOUT={config.llm.json_timeout}")
    env_content.append(f"LLM_RETRY_ON_JSON_ERROR={config.llm.retry_on_json_error}")
    env_content.append(f"LLM_VISION_MAX_FILE_SIZE={config.llm.vision_max_file_size}")
    env_content.append("")
    
    # OCR configuration
    env_content.append("# =============================================================================")
    env_content.append("# OCR SERVICE CONFIGURATION")
    env_content.append("# =============================================================================")
    env_content.append(f"HANDWRITING_OCR_API_KEY={config.ocr.api_key or 'your_handwriting_ocr_api_key_here'}")
    env_content.append(f"OCR_BASE_URL={config.ocr.base_url}")
    env_content.append(f"OCR_REQUEST_TIMEOUT={config.ocr.request_timeout}")
    env_content.append(f"OCR_RETRY_DELAY={config.ocr.retry_delay}")
    env_content.append(f"OCR_MAX_RETRIES={config.ocr.max_retries}")
    env_content.append("")
    
    # File configuration
    env_content.append("# =============================================================================")
    env_content.append("# FILE PROCESSING CONFIGURATION")
    env_content.append("# =============================================================================")
    env_content.append(f"MAX_FILE_SIZE_MB={config.file.max_file_size_mb}")
    env_content.append(f"MAX_STORAGE_SIZE_MB={config.file.max_storage_size_mb}")
    env_content.append(f"UPLOAD_DIR={config.file.upload_dir}")
    env_content.append(f"TEMP_DIR={config.file.temp_dir}")
    env_content.append(f"OUTPUT_DIR={config.file.output_dir}")
    env_content.append(f"LOGS_DIR={config.file.logs_dir}")
    env_content.append(f"INSTANCE_DIR={config.file.instance_dir}")
    env_content.append(f"CLEANUP_INTERVAL_HOURS={config.file.cleanup_interval_hours}")
    env_content.append(f"STORAGE_EXPIRATION_DAYS={config.file.storage_expiration_days}")
    env_content.append("")
    
    # Security configuration
    env_content.append("# =============================================================================")
    env_content.append("# SECURITY CONFIGURATION")
    env_content.append("# =============================================================================")
    env_content.append(f"SECRET_KEY={config.security.secret_key or 'your_secret_key_here'}")
    env_content.append(f"SESSION_TIMEOUT={config.security.session_timeout}")
    env_content.append(f"MAX_CONCURRENT_SESSIONS={config.security.max_concurrent_sessions}")
    env_content.append(f"MAX_FAILED_ATTEMPTS={config.security.max_failed_attempts}")
    env_content.append(f"LOCKOUT_DURATION={config.security.lockout_duration}")
    env_content.append(f"PASSWORD_MAX_LENGTH={config.security.password_max_length}")
    env_content.append(f"MIN_SECRET_KEY_LENGTH={config.security.min_secret_key_length}")
    env_content.append("")
    
    # Performance configuration
    env_content.append("# =============================================================================")
    env_content.append("# PERFORMANCE CONFIGURATION")
    env_content.append("# =============================================================================")
    env_content.append(f"MAX_MEMORY_MB={config.performance.max_memory_mb}")
    env_content.append(f"MAX_CPU_PERCENT={config.performance.max_cpu_percent}")
    env_content.append(f"MAX_CONCURRENT_OPERATIONS={config.performance.max_concurrent_operations}")
    env_content.append(f"MAX_CONCURRENT_PROCESSES={config.performance.max_concurrent_processes}")
    env_content.append(f"MEMORY_LIMIT_GB={config.performance.memory_limit_gb}")
    env_content.append(f"CONNECTION_LIMIT={config.performance.connection_limit}")
    env_content.append(f"MAX_REQUEST_BODY_SIZE={config.performance.max_request_body_size}")
    env_content.append("")
    
    # Timeout configuration
    env_content.append("# =============================================================================")
    env_content.append("# TIMEOUT CONFIGURATION")
    env_content.append("# =============================================================================")
    env_content.append(f"TIMEOUT_OCR_PROCESSING={config.timeout.ocr_processing}")
    env_content.append(f"TIMEOUT_LLM_PROCESSING={config.timeout.llm_processing}")
    env_content.append(f"TIMEOUT_FILE_PROCESSING={config.timeout.file_processing}")
    env_content.append(f"TIMEOUT_MAPPING_SERVICE={config.timeout.mapping_service}")
    env_content.append(f"TIMEOUT_GRADING_SERVICE={config.timeout.grading_service}")
    env_content.append(f"TIMEOUT_HEALTH_CHECK={config.timeout.health_check}")
    env_content.append(f"TIMEOUT_SERVICE_INIT={config.timeout.service_initialization}")
    env_content.append(f"TIMEOUT_DEFAULT={config.timeout.default}")
    env_content.append(f"TIMEOUT_STANDARD_REQUEST={config.timeout.standard_request}")
    env_content.append(f"TIMEOUT_ANTIWORD={config.timeout.antiword}")
    env_content.append(f"TIMEOUT_TESSERACT={config.timeout.tesseract}")
    env_content.append("")
    
    # Logging configuration
    env_content.append("# =============================================================================")
    env_content.append("# LOGGING CONFIGURATION")
    env_content.append("# =============================================================================")
    env_content.append(f"LOG_LEVEL={config.logging.level}")
    env_content.append(f"LOG_MAX_BYTES={config.logging.max_bytes}")
    env_content.append(f"LOG_BACKUP_COUNT={config.logging.backup_count}")
    env_content.append(f"LOG_ENCODING={config.logging.encoding}")
    env_content.append("")
    
    # Monitoring configuration
    env_content.append("# =============================================================================")
    env_content.append("# MONITORING CONFIGURATION")
    env_content.append("# =============================================================================")
    env_content.append(f"MONITORING_ENABLED={config.monitoring.enabled}")
    env_content.append(f"MONITORING_CHECK_INTERVAL={config.monitoring.check_interval}")
    env_content.append(f"RESPONSE_TIME_WARNING_MS={config.monitoring.response_time_warning_ms}")
    env_content.append(f"RESPONSE_TIME_CRITICAL_MS={config.monitoring.response_time_critical_ms}")
    env_content.append(f"ERROR_RATE_WARNING={config.monitoring.error_rate_warning}")
    env_content.append(f"ERROR_RATE_CRITICAL={config.monitoring.error_rate_critical}")
    env_content.append(f"CPU_WARNING={config.monitoring.cpu_warning}")
    env_content.append(f"CPU_CRITICAL={config.monitoring.cpu_critical}")
    env_content.append(f"MEMORY_WARNING={config.monitoring.memory_warning}")
    env_content.append(f"MEMORY_CRITICAL={config.monitoring.memory_critical}")
    env_content.append(f"DISK_WARNING={config.monitoring.disk_warning}")
    env_content.append(f"DISK_CRITICAL={config.monitoring.disk_critical}")
    env_content.append("")
    
    # Write the file
    with open(output_path, 'w') as f:
        f.write('\n'.join(env_content))
    
    logger.info(f"Generated .env file at {output_path}")
    print(f"✅ Generated .env file at {output_path}")
    print("📝 Please review and customize the values for your environment")


def validate_configuration() -> bool:
    """Validate the current configuration."""
    try:
        config = get_dynamic_config()
        logger.info("Configuration validation completed successfully")
        print("✅ Configuration validation passed")
        return True
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        print(f"❌ Configuration validation failed: {e}")
        return False


def show_configuration_summary() -> None:
    """Show a summary of the current configuration."""
    config = get_dynamic_config()
    
    print("\n📊 Current Configuration Summary:")
    print("=" * 50)
    
    print(f"🌐 Server: {config.server.host}:{config.server.port}")
    print(f"🗄️  Database: {config.database.url}")
    print(f"🤖 LLM Model: {config.llm.model}")
    print(f"🔗 LLM Base URL: {config.llm.base_url}")
    print(f"📁 Upload Directory: {config.file.upload_dir}")
    print(f"📏 Max File Size: {config.file.max_file_size_mb}MB")
    print(f"⏱️  Session Timeout: {config.security.session_timeout}s")
    print(f"🔄 Max Retries: {config.api.max_retries}")
    print(f"💾 Cache Size: {config.cache.default_size}")
    print(f"📊 Monitoring: {'Enabled' if config.monitoring.enabled else 'Disabled'}")
    
    print("\n🔧 Environment Variables in Use:")
    print("=" * 50)
    env_vars = config.get_environment_summary(include_values=True)
    for var in env_vars:
        print(f"  {var}")


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python migrate_config.py <command>")
        print("Commands:")
        print("  generate    - Generate a .env file from current configuration")
        print("  validate    - Validate current configuration")
        print("  summary     - Show configuration summary")
        print("  help        - Show this help message")
        return
    
    command = sys.argv[1].lower()
    
    if command == "generate":
        output_file = sys.argv[2] if len(sys.argv) > 2 else ".env"
        generate_env_file(output_file)
    elif command == "validate":
        validate_configuration()
    elif command == "summary":
        show_configuration_summary()
    elif command == "help":
        print("Configuration Migration Script")
        print("=" * 30)
        print("This script helps migrate from hardcoded configuration values")
        print("to environment-based configuration.")
        print("")
        print("Commands:")
        print("  generate [file]  - Generate a .env file (default: .env)")
        print("  validate         - Validate current configuration")
        print("  summary          - Show configuration summary")
        print("  help             - Show this help message")
    else:
        print(f"Unknown command: {command}")
        print("Use 'python migrate_config.py help' for usage information")


if __name__ == "__main__":
    main()
