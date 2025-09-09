#!/usr/bin/env python3
"""
DeepSeek API Key Test Script
This script helps you test if your DeepSeek API key is working correctly.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_deepseek_api_key():
    """Test the DeepSeek API key."""
    print("🔑 Testing DeepSeek API Key...")
    
    # Get API key from environment
    api_key = os.getenv('DEEPSEEK_API_KEY') or os.getenv('LLM_API_KEY')
    
    if not api_key:
        print("❌ No API key found in environment variables")
        print("Please set DEEPSEEK_API_KEY or LLM_API_KEY environment variable")
        return False
    
    if api_key == "your_deepseek_api_key_here":
        print("❌ API key is still set to placeholder value")
        print("Please replace with your actual DeepSeek API key")
        return False
    
    if not api_key.startswith('sk-'):
        print("⚠️  API key doesn't start with 'sk-' - this might not be a valid DeepSeek API key")
    
    print(f"✅ API key found: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        # Test the API key
        from openai import OpenAI
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        print("🧪 Testing API connectivity...")
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Hello, this is a test message."}],
            temperature=0.0,
            max_tokens=10
        )
        
        if response.choices and len(response.choices) > 0:
            print("✅ API key is working correctly!")
            print(f"Response: {response.choices[0].message.content}")
            return True
        else:
            print("❌ API returned no response")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "authentication" in error_msg.lower():
            print("❌ API key authentication failed")
            print("Please check that your API key is correct and active")
        elif "quota" in error_msg.lower() or "credit" in error_msg.lower():
            print("❌ API quota/credit limit exceeded")
            print("Please check your DeepSeek account balance")
        else:
            print(f"❌ API test failed: {error_msg}")
        return False

def main():
    """Main function."""
    print("=" * 50)
    print("DeepSeek API Key Test")
    print("=" * 50)
    
    success = test_deepseek_api_key()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 API key test completed successfully!")
        print("Your DeepSeek API key is working correctly.")
    else:
        print("💡 To get a DeepSeek API key:")
        print("1. Go to https://platform.deepseek.com/")
        print("2. Sign up or log in")
        print("3. Navigate to API Keys section")
        print("4. Create a new API key")
        print("5. Copy the key and set it as DEEPSEEK_API_KEY environment variable")
    print("=" * 50)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
