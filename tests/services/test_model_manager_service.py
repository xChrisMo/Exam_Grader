"""
Unit tests for ModelManagerService
"""

import pytest
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.services.model_manager_service import (
    ModelManagerService,
    LLMModel,
    TrainingConfig,
    ModelProvider,
    ModelStatus
)
from webapp.types.api_responses import ValidationResult


class TestModelManagerService:
    """Test cases for ModelManagerService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = ModelManagerService()

    def test_initialization(self):
        """Test service initialization"""
        assert self.service is not None
        available_models = self.service.get_available_models()
        assert len(available_models) > 0
        
        # Check that default models are loaded
        model_ids = [model.id for model in available_models]
        assert "deepseek-chat" in model_ids
        assert "deepseek-coder" in model_ids
        assert "gpt-3.5-turbo" in model_ids

    def test_get_available_models(self):
        """Test getting available models"""
        models = self.service.get_available_models()
        assert isinstance(models, list)
        assert len(models) > 0
        
        # All returned models should be available
        for model in models:
            assert model.status == ModelStatus.AVAILABLE

    def test_get_model_by_id(self):
        """Test getting model by ID"""
        # Test existing model
        model = self.service.get_model_by_id("deepseek-chat")
        assert model is not None
        assert model.id == "deepseek-chat"
        assert model.name == "DeepSeek Chat"
        assert model.provider == ModelProvider.DEEPSEEK
        
        # Test non-existing model
        model = self.service.get_model_by_id("non-existent")
        assert model is None

    def test_get_models_by_provider(self):
        """Test getting models by provider"""
        deepseek_models = self.service.get_models_by_provider(ModelProvider.DEEPSEEK)
        assert len(deepseek_models) >= 2  # deepseek-chat and deepseek-coder
        
        for model in deepseek_models:
            assert model.provider == ModelProvider.DEEPSEEK
            assert model.status == ModelStatus.AVAILABLE
        
        openai_models = self.service.get_models_by_provider(ModelProvider.OPENAI)
        assert len(openai_models) >= 1  # gpt-3.5-turbo
        
        for model in openai_models:
            assert model.provider == ModelProvider.OPENAI

    def test_register_model(self):
        """Test registering a new model"""
        new_model = LLMModel(
            id="test-model",
            name="Test Model",
            provider=ModelProvider.HUGGINGFACE,
            capabilities=["text-generation"],
            max_tokens=2048,
            supported_formats=["txt"],
            description="Test model for unit testing"
        )
        
        # Register the model
        result = self.service.register_model(new_model)
        assert result is True
        
        # Verify it was registered
        retrieved_model = self.service.get_model_by_id("test-model")
        assert retrieved_model is not None
        assert retrieved_model.name == "Test Model"
        assert retrieved_model.created_at is not None
        assert retrieved_model.updated_at is not None

    def test_register_existing_model_updates(self):
        """Test that registering an existing model updates it"""
        # Get original model
        original_model = self.service.get_model_by_id("deepseek-chat")
        original_updated_at = original_model.updated_at
        
        # Create updated version
        updated_model = LLMModel(
            id="deepseek-chat",
            name="DeepSeek Chat Updated",
            provider=ModelProvider.DEEPSEEK,
            capabilities=["text-generation", "fine-tuning", "chat", "new-capability"],
            max_tokens=32768,
            supported_formats=["txt", "json", "pdf", "docx"],
            description="Updated description"
        )
        
        # Register the updated model
        result = self.service.register_model(updated_model)
        assert result is True
        
        # Verify it was updated
        retrieved_model = self.service.get_model_by_id("deepseek-chat")
        assert retrieved_model.name == "DeepSeek Chat Updated"
        assert "new-capability" in retrieved_model.capabilities
        assert retrieved_model.updated_at > original_updated_at

    def test_validate_configuration_valid(self):
        """Test configuration validation with valid parameters"""
        config = TrainingConfig(
            learning_rate=0.0001,
            batch_size=4,
            epochs=3,
            temperature=0.7
        )
        
        result = self.service.validate_configuration("deepseek-chat", config)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_configuration_invalid_model(self):
        """Test configuration validation with invalid model ID"""
        config = TrainingConfig(
            learning_rate=0.0001,
            batch_size=4,
            epochs=3
        )
        
        result = self.service.validate_configuration("non-existent", config)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "model_id"
        assert result.errors[0].code == "MODEL_NOT_FOUND"

    def test_validate_configuration_out_of_range(self):
        """Test configuration validation with out-of-range parameters"""
        config = TrainingConfig(
            learning_rate=0.1,  # Too high
            batch_size=100,     # Too high
            epochs=-1,          # Too low
            temperature=5.0     # Too high
        )
        
        result = self.service.validate_configuration("deepseek-chat", config)
        assert result.is_valid is False
        assert len(result.errors) > 0
        
        # Check for specific errors
        error_fields = [error.field for error in result.errors]
        assert "learning_rate" in error_fields
        assert "batch_size" in error_fields
        assert "epochs" in error_fields

    def test_validate_configuration_warnings(self):
        """Test configuration validation with warning conditions"""
        config = TrainingConfig(
            learning_rate=0.002,  # High learning rate
            batch_size=8,         # Large batch size
            epochs=3,
            temperature=1.8       # High temperature
        )
        
        result = self.service.validate_configuration("deepseek-chat", config)
        # Should be valid but with warnings
        assert len(result.warnings) > 0
        
        warning_fields = [warning.field for warning in result.warnings]
        assert "learning_rate" in warning_fields or "temperature" in warning_fields

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"})
    def test_check_model_availability_with_api_key(self):
        """Test model availability check with API key present"""
        available = self.service.check_model_availability("deepseek-chat")
        assert available is True

    @patch.dict(os.environ, {}, clear=True)
    def test_check_model_availability_without_api_key(self):
        """Test model availability check without API key"""
        available = self.service.check_model_availability("deepseek-chat")
        assert available is False

    def test_check_model_availability_non_existent(self):
        """Test model availability check for non-existent model"""
        available = self.service.check_model_availability("non-existent")
        assert available is False

    def test_get_model_capabilities(self):
        """Test getting model capabilities"""
        capabilities = self.service.get_model_capabilities("deepseek-chat")
        assert isinstance(capabilities, list)
        assert "text-generation" in capabilities
        assert "fine-tuning" in capabilities
        assert "chat" in capabilities
        
        # Test non-existent model
        capabilities = self.service.get_model_capabilities("non-existent")
        assert capabilities == []

    def test_get_default_config(self):
        """Test getting default configuration"""
        config = self.service.get_default_config("deepseek-chat")
        assert config is not None
        assert isinstance(config, TrainingConfig)
        assert config.learning_rate == 0.0001
        assert config.batch_size == 4
        assert config.epochs == 3
        assert config.temperature == 0.7
        
        # Test non-existent model
        config = self.service.get_default_config("non-existent")
        assert config is None

    def test_update_model_status(self):
        """Test updating model status"""
        # Update to maintenance
        result = self.service.update_model_status("deepseek-chat", ModelStatus.MAINTENANCE)
        assert result is True
        
        model = self.service.get_model_by_id("deepseek-chat")
        assert model.status == ModelStatus.MAINTENANCE
        
        # Model should not appear in available models
        available_models = self.service.get_available_models()
        available_ids = [model.id for model in available_models]
        assert "deepseek-chat" not in available_ids
        
        # Update back to available
        result = self.service.update_model_status("deepseek-chat", ModelStatus.AVAILABLE)
        assert result is True
        
        # Test non-existent model
        result = self.service.update_model_status("non-existent", ModelStatus.MAINTENANCE)
        assert result is False


class TestLLMModel:
    """Test cases for LLMModel data class"""

    def test_to_dict(self):
        """Test converting model to dictionary"""
        model = LLMModel(
            id="test-model",
            name="Test Model",
            provider=ModelProvider.DEEPSEEK,
            capabilities=["text-generation"],
            max_tokens=2048,
            supported_formats=["txt"],
            status=ModelStatus.AVAILABLE,
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        result = model.to_dict()
        assert result["id"] == "test-model"
        assert result["provider"] == "deepseek"
        assert result["status"] == "available"
        assert result["created_at"] == "2024-01-01T12:00:00"

    def test_from_dict(self):
        """Test creating model from dictionary"""
        data = {
            "id": "test-model",
            "name": "Test Model",
            "provider": "deepseek",
            "capabilities": ["text-generation"],
            "max_tokens": 2048,
            "supported_formats": ["txt"],
            "status": "available",
            "created_at": "2024-01-01T12:00:00"
        }
        
        model = LLMModel.from_dict(data)
        assert model.id == "test-model"
        assert model.provider == ModelProvider.DEEPSEEK
        assert model.status == ModelStatus.AVAILABLE
        assert model.created_at == datetime(2024, 1, 1, 12, 0, 0)


class TestTrainingConfig:
    """Test cases for TrainingConfig data class"""

    def test_to_dict(self):
        """Test converting config to dictionary"""
        config = TrainingConfig(
            learning_rate=0.001,
            batch_size=4,
            epochs=5,
            temperature=0.7,
            max_tokens=2048,
            custom_parameters={"param1": "value1"}
        )
        
        result = config.to_dict()
        assert result["learning_rate"] == 0.001
        assert result["batch_size"] == 4
        assert result["epochs"] == 5
        assert result["temperature"] == 0.7
        assert result["max_tokens"] == 2048
        assert result["custom_parameters"] == {"param1": "value1"}

    def test_from_dict(self):
        """Test creating config from dictionary"""
        data = {
            "learning_rate": 0.001,
            "batch_size": 4,
            "epochs": 5,
            "temperature": 0.7,
            "max_tokens": 2048,
            "custom_parameters": {"param1": "value1"}
        }
        
        config = TrainingConfig.from_dict(data)
        assert config.learning_rate == 0.001
        assert config.batch_size == 4
        assert config.epochs == 5
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.custom_parameters == {"param1": "value1"}


if __name__ == "__main__":
    pytest.main([__file__])