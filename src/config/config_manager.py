from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

@dataclass
class Config:
    api_key: str
    api_url: str
    output_dir: str
    temp_dir: str
    log_level: str
    similarity_threshold: float
    ocr_confidence_threshold: float
    max_tokens: int
    temperature: float
    tesseract_cmd_path: Optional[str] = None

class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        load_dotenv()
        self.config = Config(
            api_key=os.getenv('DEEPSEEK_API_KEY', ''),
            api_url=os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions'),
            output_dir=os.getenv('OUTPUT_DIR', 'output'),
            temp_dir=os.getenv('TEMP_DIR', 'temp'),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            similarity_threshold=float(os.getenv('SIMILARITY_THRESHOLD', '0.8')),
            ocr_confidence_threshold=float(os.getenv('OCR_CONFIDENCE_THRESHOLD', '0.7')),
            max_tokens=int(os.getenv('MAX_TOKENS', '1000')),
            temperature=float(os.getenv('TEMPERATURE', '0.0')),
            tesseract_cmd_path=os.getenv('TESSERACT_CMD_PATH')
        )
    
    def validate(self) -> bool:
        """Validate configuration values."""
        if not self.config.api_key:
            raise ValueError("API key is required")
        if not os.path.exists(self.config.output_dir):
            os.makedirs(self.config.output_dir)
        if not os.path.exists(self.config.temp_dir):
            os.makedirs(self.config.temp_dir)
        return True 