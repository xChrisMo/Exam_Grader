"""
Model Manager Service for LLM Training Page

This service handles model registration, validation, and management for different LLM providers.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

# We'll define it locally to avoid the circular dependency
class ValidationResult:
    """Validation result helper class"""
    
    def __init__(self, is_valid: bool = True):
        self.errors = []
        self.warnings = []
        self._is_valid = is_valid
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0 and self._is_valid
    
    def add_error(self, field: str, message: str, code: str, value: Any = None):
        self.errors.append({
            'field': field,
            'message': message,
            'code': code,
            'value': value
        })
        self._is_valid = False
    
    def add_warning(self, field: str, message: str, suggestion: str = None):
        self.warnings.append({
            'field': field,
            'message': message,
            'suggestion': suggestion
        })
    
    def get_error_summary(self) -> str:
        if not self.errors:
            return ""
        return "; ".join([error['message'] for error in self.errors])

logger = logging.getLogger(__name__)

class ModelProvider(Enum):
    """Supported model providers"""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"

class ModelStatus(Enum):
    """Model availability status"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"

@dataclass
class LLMModel:
    """LLM Model data structure"""
    id: str
    name: str
    provider: ModelProvider
    capabilities: List[str]
    max_tokens: int
    supported_formats: List[str]
    status: ModelStatus = ModelStatus.AVAILABLE
    description: Optional[str] = None
    version: Optional[str] = None
    api_endpoint: Optional[str] = None
    requires_api_key: bool = True
    default_parameters: Optional[Dict[str, Any]] = None
    parameter_ranges: Optional[Dict[str, Dict[str, Any]]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['provider'] = self.provider.value
        result['status'] = self.status.value
        if self.created_at:
            result['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            result['updated_at'] = self.updated_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMModel':
        """Create from dictionary"""
        # Convert enum fields
        if 'provider' in data:
            data['provider'] = ModelProvider(data['provider'])
        if 'status' in data:
            data['status'] = ModelStatus(data['status'])
        
        # Convert datetime fields
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        return cls(**data)

@dataclass
class TrainingConfig:
    """Training configuration data structure"""
    learning_rate: float
    batch_size: int
    epochs: int
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    custom_parameters: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainingConfig':
        """Create from dictionary"""
        return cls(**data)

class ModelManagerService:
    """Service for managing LLM models and their configurations"""

    def __init__(self):
        self._models: Dict[str, LLMModel] = {}
        self._initialize_default_models()
        logger.info("ModelManagerService initialized")

    def _initialize_default_models(self):
        """Initialize default model configurations"""
        default_models = [
            LLMModel(
                id="deepseek-chat",
                name="DeepSeek Chat",
                provider=ModelProvider.DEEPSEEK,
                capabilities=["text-generation", "fine-tuning", "chat"],
                max_tokens=32768,
                supported_formats=["txt", "json", "pdf", "docx"],
                description="DeepSeek's flagship chat model with fine-tuning capabilities",
                version="v1.0",
                api_endpoint="https://api.deepseek.com/v1/chat/completions",
                default_parameters={
                    "learning_rate": 0.0001,
                    "batch_size": 4,
                    "epochs": 3,
                    "temperature": 0.7
                },
                parameter_ranges={
                    "learning_rate": {"min": 0.00001, "max": 0.01, "step": 0.00001},
                    "batch_size": {"min": 1, "max": 32, "step": 1},
                    "epochs": {"min": 1, "max": 100, "step": 1},
                    "temperature": {"min": 0.1, "max": 2.0, "step": 0.1}
                },
                created_at=datetime.now()
            ),
            LLMModel(
                id="deepseek-coder",
                name="DeepSeek Coder",
                provider=ModelProvider.DEEPSEEK,
                capabilities=["code-generation", "fine-tuning", "text-generation"],
                max_tokens=16384,
                supported_formats=["txt", "json", "py", "js", "md"],
                description="DeepSeek's specialized coding model",
                version="v1.0",
                api_endpoint="https://api.deepseek.com/v1/chat/completions",
                default_parameters={
                    "learning_rate": 0.0002,
                    "batch_size": 2,
                    "epochs": 5,
                    "temperature": 0.3
                },
                parameter_ranges={
                    "learning_rate": {"min": 0.00001, "max": 0.01, "step": 0.00001},
                    "batch_size": {"min": 1, "max": 16, "step": 1},
                    "epochs": {"min": 1, "max": 50, "step": 1},
                    "temperature": {"min": 0.1, "max": 1.5, "step": 0.1}
                },
                created_at=datetime.now()
            ),
            LLMModel(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider=ModelProvider.OPENAI,
                capabilities=["text-generation", "fine-tuning", "chat"],
                max_tokens=4096,
                supported_formats=["txt", "json"],
                description="OpenAI's GPT-3.5 Turbo with fine-tuning support",
                version="0613",
                api_endpoint="https://api.openai.com/v1/chat/completions",
                default_parameters={
                    "learning_rate": 0.0001,
                    "batch_size": 1,
                    "epochs": 4,
                    "temperature": 0.7
                },
                parameter_ranges={
                    "learning_rate": {"min": 0.00001, "max": 0.001, "step": 0.00001},
                    "batch_size": {"min": 1, "max": 8, "step": 1},
                    "epochs": {"min": 1, "max": 20, "step": 1},
                    "temperature": {"min": 0.0, "max": 2.0, "step": 0.1}
                },
                created_at=datetime.now()
            )
        ]

        for model in default_models:
            self._models[model.id] = model
            logger.debug(f"Registered default model: {model.name} ({model.id})")

    def get_available_models(self) -> List[LLMModel]:
        """Get list of all available models"""
        try:
            available_models = [
                model for model in self._models.values()
                if model.status == ModelStatus.AVAILABLE
            ]
            logger.debug(f"Retrieved {len(available_models)} available models")
            return available_models
        except Exception as e:
            logger.error(f"Error retrieving available models: {str(e)}")
            return []

    def get_model_by_id(self, model_id: str) -> Optional[LLMModel]:
        """Get specific model by ID"""
        try:
            model = self._models.get(model_id)
            if model:
                logger.debug(f"Retrieved model: {model.name} ({model_id})")
            else:
                logger.warning(f"Model not found: {model_id}")
            return model
        except Exception as e:
            logger.error(f"Error retrieving model {model_id}: {str(e)}")
            return None

    def get_models_by_provider(self, provider: ModelProvider) -> List[LLMModel]:
        """Get models by provider"""
        try:
            provider_models = [
                model for model in self._models.values()
                if model.provider == provider and model.status == ModelStatus.AVAILABLE
            ]
            logger.debug(f"Retrieved {len(provider_models)} models for provider {provider.value}")
            return provider_models
        except Exception as e:
            logger.error(f"Error retrieving models for provider {provider.value}: {str(e)}")
            return []

    def register_model(self, model: LLMModel) -> bool:
        """Register a new model"""
        try:
            if model.id in self._models:
                logger.warning(f"Model {model.id} already exists, updating")
            
            model.updated_at = datetime.now()
            if not model.created_at:
                model.created_at = datetime.now()
            
            self._models[model.id] = model
            logger.info(f"Registered model: {model.name} ({model.id})")
            return True
        except Exception as e:
            logger.error(f"Error registering model {model.id}: {str(e)}")
            return False

    def validate_configuration(self, model_id: str, config: TrainingConfig) -> ValidationResult:
        """Validate training configuration for a specific model"""
        result = ValidationResult()
        
        try:
            model = self.get_model_by_id(model_id)
            if not model:
                result.add_error("model_id", f"Model {model_id} not found", "MODEL_NOT_FOUND")
                return result

            if model.status != ModelStatus.AVAILABLE:
                result.add_error("model_id", f"Model {model_id} is not available", "MODEL_UNAVAILABLE")
                return result

            # Validate parameters against model ranges
            if model.parameter_ranges:
                self._validate_parameter_ranges(config, model.parameter_ranges, result)

            # Model-specific validations
            self._validate_model_specific_config(model, config, result)

            logger.debug(f"Configuration validation for {model_id}: {'valid' if result.is_valid else 'invalid'}")
            
        except Exception as e:
            logger.error(f"Error validating configuration for {model_id}: {str(e)}")
            result.add_error("validation", f"Validation error: {str(e)}", "VALIDATION_ERROR")

        return result

    def _validate_parameter_ranges(self, config: TrainingConfig, ranges: Dict[str, Dict[str, Any]], result: ValidationResult):
        """Validate parameters against defined ranges"""
        config_dict = config.to_dict()
        
        for param_name, param_value in config_dict.items():
            if param_value is None or param_name not in ranges:
                continue
                
            param_range = ranges[param_name]
            min_val = param_range.get("min")
            max_val = param_range.get("max")
            
            if min_val is not None and param_value < min_val:
                result.add_error(
                    param_name,
                    f"{param_name} must be at least {min_val}",
                    "VALUE_TOO_LOW",
                    param_value
                )
            
            if max_val is not None and param_value > max_val:
                result.add_error(
                    param_name,
                    f"{param_name} must be at most {max_val}",
                    "VALUE_TOO_HIGH",
                    param_value
                )

    def _validate_model_specific_config(self, model: LLMModel, config: TrainingConfig, result: ValidationResult):
        """Apply model-specific validation rules"""
        # DeepSeek specific validations
        if model.provider == ModelProvider.DEEPSEEK:
            if config.batch_size > 8 and config.learning_rate > 0.001:
                result.add_warning(
                    "learning_rate",
                    "High learning rate with large batch size may cause instability",
                    "Consider reducing learning rate to 0.0005 or lower"
                )
        
        # OpenAI specific validations
        elif model.provider == ModelProvider.OPENAI:
            if config.epochs > 10:
                result.add_warning(
                    "epochs",
                    "High epoch count may lead to overfitting",
                    "Consider using early stopping or reducing epochs"
                )
        
        # General validations
        if config.temperature and config.temperature > 1.5:
            result.add_warning(
                "temperature",
                "High temperature may produce inconsistent results",
                "Consider using temperature between 0.3 and 1.0"
            )

    def check_model_availability(self, model_id: str) -> bool:
        """Check if a model is available for training"""
        try:
            model = self.get_model_by_id(model_id)
            if not model:
                return False
            
            if model.requires_api_key:
                api_key_available = self._check_api_key_availability(model.provider)
                if not api_key_available:
                    logger.warning(f"API key not available for {model.provider.value}")
                    return False
            
            return model.status == ModelStatus.AVAILABLE
        except Exception as e:
            logger.error(f"Error checking availability for model {model_id}: {str(e)}")
            return False

    def _check_api_key_availability(self, provider: ModelProvider) -> bool:
        """Check if API key is available for the provider"""
        try:
            if provider == ModelProvider.DEEPSEEK:
                return bool(os.getenv("DEEPSEEK_API_KEY"))
            elif provider == ModelProvider.OPENAI:
                return bool(os.getenv("OPENAI_API_KEY"))
            elif provider == ModelProvider.ANTHROPIC:
                return bool(os.getenv("ANTHROPIC_API_KEY"))
            else:
                return True  # Assume available for other providers
        except Exception as e:
            logger.error(f"Error checking API key for {provider.value}: {str(e)}")
            return False

    def get_model_capabilities(self, model_id: str) -> List[str]:
        """Get capabilities for a specific model"""
        try:
            model = self.get_model_by_id(model_id)
            return model.capabilities if model else []
        except Exception as e:
            logger.error(f"Error getting capabilities for model {model_id}: {str(e)}")
            return []

    def get_default_config(self, model_id: str) -> Optional[TrainingConfig]:
        """Get default training configuration for a model"""
        try:
            model = self.get_model_by_id(model_id)
            if not model or not model.default_parameters:
                return None
            
            return TrainingConfig.from_dict(model.default_parameters)
        except Exception as e:
            logger.error(f"Error getting default config for model {model_id}: {str(e)}")
            return None

    def update_model_status(self, model_id: str, status: ModelStatus) -> bool:
        """Update model status"""
        try:
            model = self.get_model_by_id(model_id)
            if not model:
                return False
            
            model.status = status
            model.updated_at = datetime.now()
            logger.info(f"Updated model {model_id} status to {status.value}")
            return True
        except Exception as e:
            logger.error(f"Error updating status for model {model_id}: {str(e)}")
            return False

# Global instance
model_manager_service = ModelManagerService()