#!/usr/bin/env python3
"""
Check Render.com environment variables during deployment.
"""

import os
import sys

def check_render_environment():
    """Check environment variables on Render.com."""
    print("🔍 Render.com Environment Check")
    print("=" * 50)
    
    # Check if we're on Render.com
    render = os.getenv("RENDER")
    dyno = os.getenv("DYNO")
    
    print(f"RENDER: {render}")
    print(f"DYNO: {dyno}")
    
    if render == "true" or dyno:
        print("✅ Running on Render.com/Heroku")
    else:
        print("⚠️  Not running on Render.com/Heroku")
    
    # Check all environment variables
    print("\n📋 All Environment Variables:")
    env_vars = sorted(os.environ.items())
    for key, value in env_vars:
        if "API" in key.upper() or "KEY" in key.upper() or "SECRET" in key.upper():
            if len(value) > 20:
                masked = value[:10] + "..." + value[-4:]
            else:
                masked = value[:6] + "..."
            print(f"   {key}: {masked}")
    
    # Check specific API keys
    print("\n🔑 API Key Check:")
    api_keys = ["DEEPSEEK_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY"]
    
    for key in api_keys:
        value = os.getenv(key)
        if value:
            if len(value) > 20:
                masked = value[:10] + "..." + value[-4:]
            else:
                masked = value[:6] + "..."
            print(f"   {key}: {masked}")
            
            if "your_" in value.lower() or "here" in value.lower():
                print(f"   ❌ {key} contains placeholder text!")
            else:
                print(f"   ✅ {key} looks real")
        else:
            print(f"   {key}: Not set")
    
    print("\n" + "=" * 50)
    
    # Provide recommendations
    if render == "true" or dyno:
        print("📋 Recommendations for Render.com:")
        print("1. Go to your service dashboard")
        print("2. Click 'Environment' tab")
        print("3. Add DEEPSEEK_API_KEY with your real API key")
        print("4. Save and redeploy")
    else:
        print("📋 Recommendations for local development:")
        print("1. Create .env file with DEEPSEEK_API_KEY=your_real_key")
        print("2. Or set environment variable: export DEEPSEEK_API_KEY=your_real_key")

if __name__ == "__main__":
    check_render_environment()
