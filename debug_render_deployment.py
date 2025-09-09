#!/usr/bin/env python3
"""
Debug script to check what's happening on Render.com deployment.
"""

import os
import sys

def debug_render_deployment():
    """Debug Render.com deployment environment."""
    print("🔍 Render.com Deployment Debug")
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
    
    # Check all environment variables that contain "API" or "KEY"
    print("\n🔑 All API/KEY Environment Variables:")
    api_vars = []
    for key, value in os.environ.items():
        if "API" in key.upper() or "KEY" in key.upper():
            api_vars.append((key, value))
    
    if api_vars:
        for key, value in api_vars:
            if len(value) > 20:
                masked = value[:10] + "..." + value[-4:]
            else:
                masked = value[:6] + "..."
            print(f"   {key}: {masked}")
    else:
        print("   ❌ No API/KEY environment variables found!")
    
    # Check specific variables
    print("\n🎯 Specific API Key Check:")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    llm_key = os.getenv("LLM_API_KEY")
    
    print(f"DEEPSEEK_API_KEY: {deepseek_key[:10] + '...' if deepseek_key else 'Not set'}")
    print(f"LLM_API_KEY: {llm_key[:10] + '...' if llm_key else 'Not set'}")
    
    if deepseek_key:
        if "your_" in deepseek_key or "here" in deepseek_key:
            print("❌ DEEPSEEK_API_KEY contains placeholder text!")
        else:
            print("✅ DEEPSEEK_API_KEY looks real")
    else:
        print("❌ DEEPSEEK_API_KEY is not set!")
    
    # Check if env.example is being loaded
    print("\n📁 Environment File Check:")
    import os
    from pathlib import Path
    
    project_root = Path.cwd()
    env_files = [
        project_root / ".env",
        project_root / "instance" / ".env",
        project_root / "env.example"
    ]
    
    for env_file in env_files:
        if env_file.exists():
            print(f"   {env_file}: EXISTS")
            if env_file.name == "env.example":
                print(f"   ⚠️  env.example exists - might be loaded as fallback")
        else:
            print(f"   {env_file}: Not found")
    
    print("\n" + "=" * 50)
    print("📋 Next Steps:")
    if not deepseek_key or "your_" in deepseek_key or "here" in deepseek_key:
        print("1. Go to Render.com dashboard")
        print("2. Click on your service")
        print("3. Go to 'Environment' tab")
        print("4. Add DEEPSEEK_API_KEY with your real API key")
        print("5. Save and redeploy")
    else:
        print("✅ Environment variable is set correctly!")

if __name__ == "__main__":
    debug_render_deployment()
