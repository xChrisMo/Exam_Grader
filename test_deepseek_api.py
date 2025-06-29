import os
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.services.llm_service import LLMService
from src.config.unified_config import UnifiedConfig

def test_deepseek_connection():
    print("Attempting to test DeepSeek API connection...")
    try:
        # Load configuration
        config = UnifiedConfig()

        # Initialize LLMService
        llm_service = LLMService(config.api.deepseek_api_key, config.api.deepseek_api_url, config.api.deepseek_model)
        
        # Test API connection
        llm_service._test_api_connection()
        print("DeepSeek API connection successful!")
    except Exception as e:
        print(f"DeepSeek API connection failed: {e}")
        print("Please ensure your DEEPSEEK_API_KEY and DEEPSEEK_BASE_URL are correctly set in your .env file.")

if __name__ == "__main__":
    test_deepseek_connection()