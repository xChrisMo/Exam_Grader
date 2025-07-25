#!/usr/bin/env python3
"""
MCP Service Initialization for Exam Grader.

This script initializes the MCP service during application startup for improved LLM performance.

Author: Augment Agent
Date: 2025-07-21
"""

import logging
import os
from src.services.mcp_llm_service import initialize_mcp_service
from src.config.unified_config import UnifiedConfig

logger = logging.getLogger(__name__)

def initialize_mcp_for_app():
    """Initialize MCP service for the application."""
    try:
        config = UnifiedConfig()
        
        # Check if API key is available
        if not config.api.deepseek_api_key:
            logger.warning("DeepSeek API key not found, MCP service disabled")
            return False
        
        # Initialize MCP service with optimized settings
        mcp_service = initialize_mcp_service(
            api_key=config.api.deepseek_api_key,
            base_url=config.api.deepseek_base_url,
            model=config.api.deepseek_model,
            max_connections=10,      # Connection pooling for reduced latency
            max_contexts=1000,       # Context management for conversation continuity
            context_ttl=3600,        # 1 hour context TTL
            enable_caching=True,     # Response caching for performance
            cache_ttl=1800          # 30 minute cache TTL
        )
        
        logger.info("MCP service initialized successfully for application")
        logger.info(f"MCP Configuration: Model={config.api.deepseek_model}, "
                   f"Connections=10, Contexts=1000, Caching=Enabled")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP service: {e}")
        return False

def get_mcp_status():
    """Get MCP service status."""
    try:
        from src.services.mcp_llm_service import get_mcp_service
        mcp_service = get_mcp_service()
        metrics = mcp_service.get_performance_metrics()
        
        return {
            'status': 'healthy',
            'metrics': metrics,
            'message': 'MCP service is running'
        }
    except RuntimeError:
        return {
            'status': 'not_initialized',
            'message': 'MCP service not initialized'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'MCP service error: {str(e)}'
        }

# Auto-initialize when imported (if not in test mode)
if __name__ != "__main__" and os.getenv('TESTING', 'false').lower() != 'true':
    initialize_mcp_for_app()

if __name__ == "__main__":
    # Direct execution for testing
    print("🚀 Initializing MCP Service...")
    success = initialize_mcp_for_app()
    
    if success:
        print("✅ MCP service initialized successfully!")
        
        # Show status
        status = get_mcp_status()
        print(f"📊 Status: {status['status']}")
        print(f"📝 Message: {status['message']}")
        
        if 'metrics' in status:
            metrics = status['metrics']
            print(f"📈 Metrics:")
            print(f"   - Total Requests: {metrics.get('total_requests', 0)}")
            print(f"   - Cache Hit Rate: {metrics.get('cache_hit_rate', 0):.1%}")
            print(f"   - Active Contexts: {metrics.get('active_contexts', 0)}")
    else:
        print("❌ MCP service initialization failed!")
        exit(1)
