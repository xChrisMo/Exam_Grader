#!/usr/bin/env python3
"""
Test script to verify environment configuration works correctly.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_env_config():
    """Test that the environment configuration works correctly."""
    
    print("Testing environment configuration...")
    
    # Test 1: With only DEEPSEEK_API_KEY set
    print("\n1. Testing with only DEEPSEEK_API_KEY set...")
    
    # Clear any existing API keys
    if 'LLM_API_KEY' in os.environ:
        del os.environ['LLM_API_KEY']
    if 'DEEPSEEK_API_KEY' in os.environ:
        del os.environ['DEEPSEEK_API_KEY']
    
    # Set only DEEPSEEK_API_KEY
    os.environ['DEEPSEEK_API_KEY'] = 'test_deepseek_key_123'
    
    try:
        # Reload the config module to pick up new environment variables
        import importlib
        import src.config.unified_config
        importlib.reload(src.config.unified_config)
        from src.config.unified_config import config
        
        print(f"✅ DEEPSEEK_API_KEY: {config.api.deepseek_api_key}")
        print(f"✅ LLM_API_KEY (should fallback): {config.api.llm_api_key}")
        
        if config.api.llm_api_key == config.api.deepseek_api_key:
            print("✅ LLM_API_KEY correctly falls back to DEEPSEEK_API_KEY")
        else:
            print("❌ LLM_API_KEY fallback not working")
            return False
            
    except Exception as e:
        print(f"❌ Error during config test: {str(e)}")
        return False
    
    # Test 2: With both keys set
    print("\n2. Testing with both keys set...")
    
    # Set both keys
    os.environ['LLM_API_KEY'] = 'test_llm_key_456'
    os.environ['DEEPSEEK_API_KEY'] = 'test_deepseek_key_123'
    
    try:
        # Reload the config module to pick up new environment variables
        importlib.reload(src.config.unified_config)
        from src.config.unified_config import config
        
        print(f"✅ DEEPSEEK_API_KEY: {config.api.deepseek_api_key}")
        print(f"✅ LLM_API_KEY: {config.api.llm_api_key}")
        
        if config.api.llm_api_key == 'test_llm_key_456':
            print("✅ LLM_API_KEY correctly uses its own value")
        else:
            print("❌ LLM_API_KEY not using its own value")
            return False
            
    except Exception as e:
        print(f"❌ Error during config test: {str(e)}")
        return False
    
    # Test 3: With no keys set
    print("\n3. Testing with no keys set...")
    
    # Clear all keys
    if 'LLM_API_KEY' in os.environ:
        del os.environ['LLM_API_KEY']
    if 'DEEPSEEK_API_KEY' in os.environ:
        del os.environ['DEEPSEEK_API_KEY']
    
    try:
        # Reload the config module to pick up new environment variables
        importlib.reload(src.config.unified_config)
        from src.config.unified_config import config
        
        print(f"✅ DEEPSEEK_API_KEY: {config.api.deepseek_api_key}")
        print(f"✅ LLM_API_KEY: {config.api.llm_api_key}")
        
        if config.api.llm_api_key == "" and config.api.deepseek_api_key == "":
            print("✅ Both keys correctly empty when not set")
        else:
            print("❌ Keys not empty when not set")
            return False
            
    except Exception as e:
        print(f"❌ Error during config test: {str(e)}")
        return False
    
    print("\n✅ All environment configuration tests passed!")
    return True

if __name__ == "__main__":
    success = test_env_config()
    sys.exit(0 if success else 1) 