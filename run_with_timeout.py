#!/usr/bin/env python3
"""
Enhanced Application Runner with Timeout Configuration
Optimized for AI processing with extended timeouts.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Run the application with optimized timeout settings."""
    
    # Set environment variables for extended timeouts
    os.environ['USE_WAITRESS'] = 'true'
    os.environ['REQUEST_TIMEOUT'] = '600'  # 10 minutes
    os.environ['SOCKET_TIMEOUT'] = '600'
    os.environ['DEBUG'] = 'false'
    
    # Import and run the main app
    from run_app import main as run_main
    
    print("🚀 Starting Exam Grader with extended timeouts for AI processing...")
    print("⏱️  Request timeout: 10 minutes")
    print("🔧 Optimized for long-running grading operations")
    print("=" * 60)
    
    try:
        run_main()
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()