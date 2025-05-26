"""
Configuration manager for the exam grader application.

This module provides centralized configuration management for the application,
loading settings from environment variables and providing validation.
"""
import os
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class Config:
    """
    Configuration settings for the application.

    This dataclass holds all configuration values loaded from environment
    variables with appropriate defaults and validation.
    """
    # Core settings
    debug: bool
    log_level: str
    secret_key: str
    host: str
    port: int

    # Directory settings
    temp_dir: str
    output_dir: str

    # File processing settings
    max_file_size_mb: int
    supported_formats: List[str]

    # OCR settings
    ocr_confidence_threshold: float
    ocr_language: str
    handwriting_ocr_api_key: str
    handwriting_ocr_delete_after: int

    def __post_init__(self) -> None:
        """
        Validate configuration after initialization.

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        if not self.handwriting_ocr_api_key:
            logger.warning("HandwritingOCR API key not configured - OCR features will be disabled")
            # Don't raise error, allow app to run without OCR

class ConfigManager:
    """
    Manages application configuration using singleton pattern.

    This class loads configuration from environment variables and provides
    a centralized access point for all application settings.
    """

    _instance: Optional['ConfigManager'] = None

    def __new__(cls) -> 'ConfigManager':
        """
        Create singleton instance.

        Returns:
            ConfigManager: The singleton instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """
        Initialize configuration manager.

        Loads configuration from environment variables and validates settings.
        """
        if getattr(self, '_initialized', False):
            return

        # Load environment variables from .env file
        load_dotenv('.env')

        # Create configuration object
        self.config = Config(
            # Core settings
            debug=os.getenv('DEBUG', 'False').lower() == 'true',
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            secret_key=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            host=os.getenv('HOST', '0.0.0.0'),
            port=int(os.getenv('PORT', '5000').split('#')[0].strip()),

            # Directory settings
            temp_dir=os.getenv('TEMP_DIR', 'temp'),
            output_dir=os.getenv('OUTPUT_DIR', 'output'),

            # File processing settings
            max_file_size_mb=int(os.getenv('MAX_FILE_SIZE_MB', '10').split('#')[0].strip()),
            supported_formats=os.getenv('SUPPORTED_FORMATS',
                '.txt,.docx,.pdf,.jpg,.jpeg,.png,.tiff,.bmp,.gif').split(','),

            # OCR settings
            ocr_confidence_threshold=float(os.getenv('OCR_CONFIDENCE_THRESHOLD', '0.7').split('#')[0].strip()),
            ocr_language=os.getenv('OCR_LANGUAGE', 'en'),

            # API settings
            handwriting_ocr_api_key=os.getenv('HANDWRITING_OCR_API_KEY', ''),
            handwriting_ocr_delete_after=int(os.getenv('HANDWRITING_OCR_DELETE_AFTER', '86400').split('#')[0].strip())
        )

        # Create necessary directories
        self._create_directories()

        # Validate configuration
        self._validate_config()

        self._initialized = True
        logger.debug("Configuration initialized successfully")

    def _create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        try:
            os.makedirs(self.config.temp_dir, exist_ok=True)
            os.makedirs(self.config.output_dir, exist_ok=True)
            logger.debug("Created necessary directories")
        except Exception as e:
            logger.error(f"Error creating directories: {str(e)}")
            raise

    def _validate_config(self) -> None:
        """Validate configuration settings."""
        if self.config.max_file_size_mb <= 0:
            logger.warning("Invalid max file size, using default of 10MB")
            self.config.max_file_size_mb = 10

        if not self.config.supported_formats:
            logger.warning("No supported formats specified, using defaults")
            self.config.supported_formats = [
                '.txt', '.docx', '.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'
            ]

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats.

        Returns:
            List[str]: List of supported file extensions
        """
        return self.config.supported_formats

    def is_file_supported(self, filename: str) -> bool:
        """Check if a file is supported based on its extension.

        Args:
            filename: Name of the file to check

        Returns:
            bool: True if the file format is supported
        """
        ext = Path(filename).suffix.lower()
        return ext in self.config.supported_formats

    def get_max_file_size(self) -> int:
        """Get maximum allowed file size in bytes.

        Returns:
            int: Maximum file size in bytes
        """
        return self.config.max_file_size_mb * 1024 * 1024  # Convert MB to bytes

    @property
    def max_file_size_mb(self) -> int:
        """Get maximum file size in MB."""
        return self.config.max_file_size_mb

    @property
    def supported_formats(self) -> List[str]:
        """Get supported file formats."""
        return self.config.supported_formats

    @property
    def temp_dir(self) -> str:
        """Get temporary directory path."""
        return self.config.temp_dir

    @property
    def secret_key(self) -> str:
        """Get secret key."""
        return self.config.secret_key

    @property
    def debug(self) -> bool:
        """Get debug mode."""
        return self.config.debug

    @property
    def host(self) -> str:
        """Get host."""
        return self.config.host

    @property
    def port(self) -> int:
        """Get port."""
        return self.config.port