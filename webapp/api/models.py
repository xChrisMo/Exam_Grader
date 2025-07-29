"""
Model management API routes for LLM Training Page
"""

import logging
from flask import jsonify, request
from . import api_bp
from ..types.api_responses import ApiResponse, ErrorResponse, ErrorType
from src.services.model_manager_service import model_manager_service, TrainingConfig

logger = logging.getLogger(__name__)

@api_bp.route('/models', methods=['GET'])
def get_models():
    """Get list of available LLM models"""
    try:
        models = model_manager_service.get_available_models()
        models_data = [model.to_dict() for model in models]
        logger.debug(f"Retrieved {len(models_data)} available models")
        return jsonify(ApiResponse.success(models_data))
    except Exception as e:
        logger.error(f"Error retrieving models: {str(e)}")
        error = ErrorResponse(
            type=ErrorType.API_ERROR,
            message="Failed to retrieve models",
            details={"error": str(e)}
        )
        return jsonify(ApiResponse.error(error)), 500

@api_bp.route('/models/<model_id>', methods=['GET'])
def get_model(model_id):
    """Get specific model details"""
    try:
        model = model_manager_service.get_model_by_id(model_id)
        if not model:
            error = ErrorResponse(
                type=ErrorType.MODEL_ERROR,
                message=f"Model {model_id} not found"
            )
            return jsonify(ApiResponse.error(error)), 404
        
        logger.debug(f"Retrieved model details for {model_id}")
        return jsonify(ApiResponse.success(model.to_dict()))
    except Exception as e:
        logger.error(f"Error retrieving model {model_id}: {str(e)}")
        error = ErrorResponse(
            type=ErrorType.API_ERROR,
            message="Failed to retrieve model details",
            details={"error": str(e)}
        )
        return jsonify(ApiResponse.error(error)), 500

@api_bp.route('/models/<model_id>/validate', methods=['POST'])
def validate_model_config(model_id):
    """Validate training configuration for a model"""
    try:
        config_data = request.get_json()
        if not config_data:
            error = ErrorResponse(
                type=ErrorType.VALIDATION_ERROR,
                message="Configuration data is required"
            )
            return jsonify(ApiResponse.error(error)), 400
        
        try:
            config = TrainingConfig.from_dict(config_data)
        except (TypeError, ValueError) as e:
            error = ErrorResponse(
                type=ErrorType.VALIDATION_ERROR,
                message="Invalid configuration format",
                details={"error": str(e)}
            )
            return jsonify(ApiResponse.error(error)), 400
        
        # Validate configuration
        validation_result = model_manager_service.validate_configuration(model_id, config)
        logger.debug(f"Configuration validation for {model_id}: {'valid' if validation_result.is_valid else 'invalid'}")
        
        return jsonify(ApiResponse.success(validation_result.to_dict()))
    except Exception as e:
        logger.error(f"Error validating configuration for {model_id}: {str(e)}")
        error = ErrorResponse(
            type=ErrorType.API_ERROR,
            message="Failed to validate configuration",
            details={"error": str(e)}
        )
        return jsonify(ApiResponse.error(error)), 500

@api_bp.route('/models/<model_id>/capabilities', methods=['GET'])
def get_model_capabilities(model_id):
    """Get model capabilities"""
    try:
        capabilities = model_manager_service.get_model_capabilities(model_id)
        if not capabilities and not model_manager_service.get_model_by_id(model_id):
            error = ErrorResponse(
                type=ErrorType.MODEL_ERROR,
                message=f"Model {model_id} not found"
            )
            return jsonify(ApiResponse.error(error)), 404
        
        logger.debug(f"Retrieved capabilities for {model_id}")
        return jsonify(ApiResponse.success(capabilities))
    except Exception as e:
        logger.error(f"Error retrieving capabilities for {model_id}: {str(e)}")
        error = ErrorResponse(
            type=ErrorType.API_ERROR,
            message="Failed to retrieve model capabilities",
            details={"error": str(e)}
        )
        return jsonify(ApiResponse.error(error)), 500

@api_bp.route('/models/<model_id>/default-config', methods=['GET'])
def get_model_default_config(model_id):
    """Get default training configuration for a model"""
    try:
        config = model_manager_service.get_default_config(model_id)
        if not config:
            if not model_manager_service.get_model_by_id(model_id):
                error = ErrorResponse(
                    type=ErrorType.MODEL_ERROR,
                    message=f"Model {model_id} not found"
                )
                return jsonify(ApiResponse.error(error)), 404
            else:
                error = ErrorResponse(
                    type=ErrorType.MODEL_ERROR,
                    message=f"No default configuration available for model {model_id}"
                )
                return jsonify(ApiResponse.error(error)), 404
        
        logger.debug(f"Retrieved default configuration for {model_id}")
        return jsonify(ApiResponse.success(config.to_dict()))
    except Exception as e:
        logger.error(f"Error retrieving default config for {model_id}: {str(e)}")
        error = ErrorResponse(
            type=ErrorType.API_ERROR,
            message="Failed to retrieve default configuration",
            details={"error": str(e)}
        )
        return jsonify(ApiResponse.error(error)), 500

@api_bp.route('/models/<model_id>/availability', methods=['GET'])
def check_model_availability(model_id):
    """Check if a model is available for training"""
    try:
        available = model_manager_service.check_model_availability(model_id)
        logger.debug(f"Model {model_id} availability: {available}")
        return jsonify(ApiResponse.success({"available": available}))
    except Exception as e:
        logger.error(f"Error checking availability for {model_id}: {str(e)}")
        error = ErrorResponse(
            type=ErrorType.API_ERROR,
            message="Failed to check model availability",
            details={"error": str(e)}
        )
        return jsonify(ApiResponse.error(error)), 500