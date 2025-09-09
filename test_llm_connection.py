#!/usr/bin/env python3
"""
Test LLM connection to verify API key is working.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_llm_connection():
    """Test LLM connection."""
    try:
        from src.services.consolidated_llm_service import ConsolidatedLLMService
        
        print("🔍 Testing LLM Connection...")
        print("=" * 40)
        
        # Create LLM service
        llm_service = ConsolidatedLLMService()
        
        # Check API key
        if llm_service.api_key:
            if len(llm_service.api_key) > 14:
                masked = llm_service.api_key[:10] + "..." + llm_service.api_key[-4:]
            else:
                masked = llm_service.api_key[:6] + "..."
            print(f"API Key: {masked}")
            
            if "your_" in llm_service.api_key or "here" in llm_service.api_key:
                print("❌ API key contains placeholder text!")
                return False
            else:
                print("✅ API key looks real")
        else:
            print("❌ No API key found!")
            return False
        
        # Test connection
        print("\n🧪 Testing API connection...")
        try:
            # Simple test call
            response = llm_service.generate_response(
                "Hello, this is a test. Please respond with 'API connection successful!'",
                max_tokens=50
            )
            
            if response and response.choices:
                print("✅ API connection successful!")
                print(f"Response: {response.choices[0].message.content}")
                return True
            else:
                print("❌ API connection failed - no response")
                return False
                
        except Exception as e:
            print(f"❌ API connection failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing LLM connection: {e}")
        return False

if __name__ == "__main__":
    success = test_llm_connection()
    if success:
        print("\n🎉 LLM service is working correctly!")
    else:
        print("\n💥 LLM service has issues - check API key configuration")
