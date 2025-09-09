#!/usr/bin/env python3
"""
Environment Setup Script

This script helps set up the development environment by:
1. Creating the instance folder
2. Creating .env file from env.example if needed
3. Loading environment variables
4. Testing the setup

Usage:
    python setup_env.py
"""

import sys
from pathlib import Path

# Add project root to Python path
from utils.project_init import init_project
from utils.env_loader import setup_environment

def main():
    """Main setup function."""
    print("🔧 Setting up Exam Grader environment...")
    
    try:
        # Initialize project
        project_root = init_project(__file__)
        print(f"📁 Project root: {project_root}")
        
        # Setup environment
        setup_environment(project_root)
        
        # Test imports
        print("\n🧪 Testing imports...")
        try:
            import webapp.app
            print("✅ Webapp imports successfully")
        except Exception as e:
            print(f"❌ Webapp import failed: {e}")
            return 1
        
        try:
            from src.services.consolidated_llm_service import ConsolidatedLLMService
            print("✅ Services import successfully")
        except Exception as e:
            print(f"❌ Services import failed: {e}")
            return 1
        
        print("\n🎉 Environment setup completed successfully!")
        print("You can now run the application with: python run_app.py")
        return 0
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
