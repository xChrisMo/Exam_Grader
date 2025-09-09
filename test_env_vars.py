#!/usr/bin/env python3
"""
Simple test to check environment variables on Render.com
"""

import os

def test_environment_variables():
    """Test environment variables."""
    print("🔍 Testing Environment Variables...")
    print("=" * 40)
    
    # Check if we're on Render.com
    render = os.getenv("RENDER")
    dyno = os.getenv("DYNO")
    
    print(f"RENDER: {render}")
    print(f"DYNO: {dyno}")
    
    # Check API key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        print(f"DEEPSEEK_API_KEY: {api_key[:10]}...{api_key[-4:]}")
        if "your_" in api_key or "here" in api_key:
            print("❌ API key contains placeholder text!")
        else:
            print("✅ API key looks real")
    else:
        print("❌ DEEPSEEK_API_KEY not set")
    
    # Check LLM API key
    llm_key = os.getenv("LLM_API_KEY")
    if llm_key:
        print(f"LLM_API_KEY: {llm_key[:10]}...{llm_key[-4:]}")
        if "your_" in llm_key or "here" in llm_key:
            print("❌ LLM API key contains placeholder text!")
        else:
            print("✅ LLM API key looks real")
    else:
        print("ℹ️  LLM_API_KEY not set (this is OK)")
    
    print("=" * 40)

if __name__ == "__main__":
    test_environment_variables()
