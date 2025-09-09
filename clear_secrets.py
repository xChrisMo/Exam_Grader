#!/usr/bin/env python3
"""
Clear encrypted secrets file to force reload from environment variables.
This is useful when the secrets file contains placeholder values.
"""

import os
import sys
from pathlib import Path

def clear_secrets():
    """Clear the encrypted secrets file."""
    secrets_file = Path("instance/secrets.enc")
    
    if secrets_file.exists():
        try:
            secrets_file.unlink()
            print("✅ Cleared encrypted secrets file")
            print("   The application will now use environment variables directly")
        except Exception as e:
            print(f"❌ Failed to clear secrets file: {e}")
            return False
    else:
        print("ℹ️  No encrypted secrets file found")
    
    return True

if __name__ == "__main__":
    print("🧹 Clearing encrypted secrets file...")
    if clear_secrets():
        print("\n✅ Done! The application will now use environment variables.")
        print("\n📝 Next steps:")
        print("   1. Set your DEEPSEEK_API_KEY environment variable on Render.com")
        print("   2. Redeploy your application")
        print("   3. The LLM service should now use your real API key")
    else:
        print("\n❌ Failed to clear secrets file")
        sys.exit(1)
