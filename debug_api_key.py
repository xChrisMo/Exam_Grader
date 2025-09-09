#!/usr/bin/env python3
"""
Debug script to check API key loading from different sources.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def debug_api_key_loading():
    """Debug API key loading from different sources."""
    print("🔍 Debugging API key loading...")
    print("=" * 50)
    
    # Check environment variables
    print("1. Environment Variables:")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    llm_key = os.getenv("LLM_API_KEY")
    
    print(f"   DEEPSEEK_API_KEY: {deepseek_key[:10] + '...' if deepseek_key and len(deepseek_key) > 10 else deepseek_key}")
    print(f"   LLM_API_KEY: {llm_key[:10] + '...' if llm_key and len(llm_key) > 10 else llm_key}")
    
    # Check if they're placeholder values
    if deepseek_key == "your_deepseek_api_key_here":
        print("   ⚠️  DEEPSEEK_API_KEY is placeholder value!")
    if llm_key == "your_deepseek_api_key_here":
        print("   ⚠️  LLM_API_KEY is placeholder value!")
    
    # Check secrets manager
    print("\n2. Secrets Manager:")
    try:
        from src.security.secrets_manager import secrets_manager
        secret_key = secrets_manager.get_secret('DEEPSEEK_API_KEY')
        print(f"   DEEPSEEK_API_KEY from secrets: {secret_key[:10] + '...' if secret_key and len(secret_key) > 10 else secret_key}")
        
        if secret_key == "your_deepseek_api_key_here":
            print("   ⚠️  Secrets manager has placeholder value!")
    except Exception as e:
        print(f"   ❌ Error loading secrets manager: {e}")
    
    # Check unified config
    print("\n3. Unified Config:")
    try:
        from src.config.unified_config import config
        config_key = config.api.deepseek_api_key
        print(f"   DEEPSEEK_API_KEY from config: {config_key[:10] + '...' if config_key and len(config_key) > 10 else config_key}")
        
        if config_key == "your_deepseek_api_key_here":
            print("   ⚠️  Unified config has placeholder value!")
    except Exception as e:
        print(f"   ❌ Error loading unified config: {e}")
    
    # Check LLM service initialization
    print("\n4. LLM Service API Key Loading:")
    try:
        from src.services.consolidated_llm_service import ConsolidatedLLMService
        
        # Create a test instance to see what API key it gets
        test_service = ConsolidatedLLMService()
        service_key = test_service.api_key
        print(f"   API key from LLM service: {service_key[:10] + '...' if service_key and len(service_key) > 10 else service_key}")
        
        if service_key == "your_deepseek_api_key_here":
            print("   ⚠️  LLM service has placeholder value!")
            
    except Exception as e:
        print(f"   ❌ Error creating LLM service: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Debug complete!")

if __name__ == "__main__":
    debug_api_key_loading()
