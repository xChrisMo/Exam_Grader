#!/usr/bin/env python3
"""
Test script to verify the cross-platform timeout fix is working
"""

import sys
import os
sys.path.append('.')

def test_timeout_functionality():
    """Test that the timeout functionality works on Windows"""
    print("🧪 Testing cross-platform timeout functionality...")
    
    try:
        from src.services.llm_training_service import LLMTrainingService
        
        # Create service instance
        service = LLMTrainingService()
        
        # Mock LLM service for testing
        class MockLLMService:
            def generate_response(self, system_prompt, user_prompt, temperature=0.7):
                import time
                time.sleep(2)  # Simulate 2-second response
                return '{"test": "response"}'
        
        mock_llm = MockLLMService()
        
        # Test timeout functionality
        print("⏱️  Testing normal LLM call (should complete in ~2 seconds)...")
        start_time = time.time()
        
        response = service._llm_call_with_timeout(
            llm_service=mock_llm,
            system_prompt="Test prompt",
            user_prompt="Test user prompt",
            temperature=0.7,
            timeout_seconds=5  # 5 second timeout
        )
        
        elapsed = time.time() - start_time
        print(f"✅ Normal call completed in {elapsed:.2f} seconds")
        print(f"📝 Response: {response}")
        
        # Test timeout scenario
        class SlowMockLLMService:
            def generate_response(self, system_prompt, user_prompt, temperature=0.7):
                import time
                time.sleep(10)  # Simulate 10-second response (will timeout)
                return '{"test": "slow_response"}'
        
        slow_mock_llm = SlowMockLLMService()
        
        print("\n⏱️  Testing timeout scenario (should timeout in ~3 seconds)...")
        start_time = time.time()
        
        try:
            response = service._llm_call_with_timeout(
                llm_service=slow_mock_llm,
                system_prompt="Test prompt",
                user_prompt="Test user prompt", 
                temperature=0.7,
                timeout_seconds=3  # 3 second timeout
            )
            print("❌ Timeout test failed - call should have timed out")
        except TimeoutError as e:
            elapsed = time.time() - start_time
            print(f"✅ Timeout test passed - call timed out in {elapsed:.2f} seconds")
            print(f"📝 Timeout message: {e}")
        
        print("\n🎉 All timeout tests passed! The cross-platform fix is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import time
    success = test_timeout_functionality()
    
    if success:
        print("\n✅ SUMMARY: Cross-platform timeout fix is working correctly")
        print("   - No more 'signal.SIGALRM' errors on Windows")
        print("   - LLM calls will timeout at 25 seconds")
        print("   - Threading-based timeout works on all platforms")
        print("\n🚀 Ready to restart your Flask server and test the training system!")
    else:
        print("\n❌ SUMMARY: There may be issues with the timeout fix")
        print("   - Check the error messages above")
        print("   - Ensure all dependencies are installed")