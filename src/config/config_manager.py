import os
from dataclasses import dataclass
from typing import List
from pathlib import Path
from dotenv import load_dotenv

from utils.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class Config:
    """Configuration settings for the application."""
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

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.handwriting_ocr_api_key:
            raise ValueError("HandwritingOCR API key not configured")

class ConfigManager:
    """Manages application configuration."""

    _instance = None

    def __new__(cls):
        """Create singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize configuration manager."""
        if self._initialized:
            return

        # Load environment variables from root .env file
        load_dotenv('.env', override=True)

        # Create configuration object
        self.config = Config(
            # Core settings
            debug=os.getenv('DEBUG', 'False').lower() == 'true',
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            secret_key=os.getenv('SECRET_KEY', os.urandom(24).hex()),
            host=os.getenv('HOST', '127.0.0.1'),
            port=int(os.getenv('PORT', '8501').split('#')[0].strip()),

            # Directory settings
            temp_dir=os.getenv('TEMP_DIR', 'temp'),
            output_dir=os.getenv('OUTPUT_DIR', 'output'),

            # File processing settings
            max_file_size_mb=int(os.getenv('MAX_FILE_SIZE_MB', '20').split('#')[0].strip()),
            supported_formats=os.getenv('SUPPORTED_FORMATS',
                '.pdf,.docx,.doc,.txt,.jpg,.jpeg,.png,.bmp,.tiff,.gif').split(','),

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