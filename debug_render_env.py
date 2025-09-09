#!/usr/bin/env python3
"""
Debug script specifically for Render.com environment variable loading.
This will help identify why the API key is still showing as placeholder.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def debug_render_environment():
    """Debug environment variable loading on Render.com."""
    print("🔍 Debugging Render.com Environment Variables...")
    print("=" * 60)
    
    # Check if we're on Render.com
    print("1. Environment Detection:")
    render_env = os.getenv("RENDER")
    dyno_env = os.getenv("DYNO")
    flask_env = os.getenv("FLASK_ENV")
    
    print(f"   RENDER: {render_env}")
    print(f"   DYNO: {dyno_env}")
    print(f"   FLASK_ENV: {flask_env}")
    
    if render_env == "true" or dyno_env:
        print("   ✅ Running on Render.com/Heroku")
    else:
        print("   ⚠️  Not running on Render.com/Heroku")
    
    # Check all environment variables related to API keys
    print("\n2. API Key Environment Variables:")
    api_vars = [
        "DEEPSEEK_API_KEY",
        "LLM_API_KEY", 
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY"
    ]
    
    for var in api_vars:
        value = os.getenv(var)
        if value:
            # Show first 10 and last 4 characters for security
            if len(value) > 14:
                masked = value[:10] + "..." + value[-4:]
            else:
                masked = value[:6] + "..."
            print(f"   {var}: {masked}")
            
            # Check if it's a placeholder
            if "your_" in value.lower() or "here" in value.lower():
                print(f"   ⚠️  {var} contains placeholder text!")
        else:
            print(f"   {var}: Not set")
    
    # Check if env.example is being loaded
    print("\n3. Environment File Loading:")
    env_files = [
        ".env",
        "instance/.env", 
        "env.example"
    ]
    
    for env_file in env_files:
        file_path = project_root / env_file
        if file_path.exists():
            print(f"   {env_file}: EXISTS")
            if env_file == "env.example":
                print(f"   ⚠️  env.example exists - might be loaded as fallback")
        else:
            print(f"   {env_file}: Not found")
    
    # Check secrets manager
    print("\n4. Secrets Manager Status:")
    try:
        from src.security.secrets_manager import secrets_manager
        
        # Check if secrets file exists
        secrets_file = project_root / "instance" / "secrets.enc"
        if secrets_file.exists():
            print(f"   secrets.enc: EXISTS ({secrets_file.stat().st_size} bytes)")
        else:
            print(f"   secrets.enc: Not found")
        
        # Check what the secrets manager returns
        deepseek_secret = secrets_manager.get_secret('DEEPSEEK_API_KEY')
        if deepseek_secret:
            if len(deepseek_secret) > 14:
                masked = deepseek_secret[:10] + "..." + deepseek_secret[-4:]
            else:
                masked = deepseek_secret[:6] + "..."
            print(f"   DEEPSEEK_API_KEY from secrets: {masked}")
            
            if "your_" in deepseek_secret.lower() or "here" in deepseek_secret.lower():
                print(f"   ⚠️  Secrets manager has placeholder value!")
        else:
            print(f"   DEEPSEEK_API_KEY from secrets: Not found")
            
    except Exception as e:
        print(f"   ❌ Error checking secrets manager: {e}")
    
    # Check unified config
    print("\n5. Unified Config Status:")
    try:
        from src.config.unified_config import config
        config_key = config.api.deepseek_api_key
        if config_key:
            if len(config_key) > 14:
                masked = config_key[:10] + "..." + config_key[-4:]
            else:
                masked = config_key[:6] + "..."
            print(f"   DEEPSEEK_API_KEY from config: {masked}")
            
            if "your_" in config_key.lower() or "here" in config_key.lower():
                print(f"   ⚠️  Unified config has placeholder value!")
        else:
            print(f"   DEEPSEEK_API_KEY from config: Not found")
            
    except Exception as e:
        print(f"   ❌ Error checking unified config: {e}")
    
    # Test LLM service initialization
    print("\n6. LLM Service Test:")
    try:
        from src.services.consolidated_llm_service import ConsolidatedLLMService
        
        # Create a test instance
        test_service = ConsolidatedLLMService()
        service_key = test_service.api_key
        
        if service_key:
            if len(service_key) > 14:
                masked = service_key[:10] + "..." + service_key[-4:]
            else:
                masked = service_key[:6] + "..."
            print(f"   API key from LLM service: {masked}")
            
            if "your_" in service_key.lower() or "here" in service_key.lower():
                print(f"   ⚠️  LLM service has placeholder value!")
            else:
                print(f"   ✅ LLM service has real API key")
        else:
            print(f"   ❌ LLM service has no API key")
            
    except Exception as e:
        print(f"   ❌ Error testing LLM service: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Debug complete!")
    
    # Provide recommendations
    print("\n📋 Recommendations:")
    if render_env == "true" or dyno_env:
        print("1. ✅ You're on Render.com - environment variables should be set in dashboard")
        print("2. 🔧 Check Render.com dashboard -> Environment tab")
        print("3. 🔧 Ensure DEEPSEEK_API_KEY is set with your real API key")
        print("4. 🔧 Redeploy after setting environment variables")
    else:
        print("1. ⚠️  Not on Render.com - check local .env file")
        print("2. 🔧 Create .env file with DEEPSEEK_API_KEY=your_real_key")

if __name__ == "__main__":
    debug_render_environment()
