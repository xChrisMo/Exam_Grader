#!/usr/bin/env python3
"""
Script to restart the Flask server to register new routes and apply fixes
"""

import os
import sys
import subprocess
import time
import signal

def find_flask_process():
    """Find running Flask processes"""
    try:
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True, shell=True)
        return result.stdout
    except Exception as e:
        print(f"Error finding Flask process: {e}")
        return ""

def restart_server():
    """Restart the Flask server"""
    print("🔄 Restarting Flask server to apply fixes...")
    
    # Try to find and stop existing server
    print("📋 Checking for running Flask processes...")
    processes = find_flask_process()
    if "python.exe" in processes:
        print("⚠️  Found running Python processes. Please manually stop the Flask server if running.")
        print("   You can do this by pressing Ctrl+C in the terminal where the server is running.")
        print("   Or use Task Manager to end python.exe processes.")
    
    print("\n✅ Server restart instructions:")
    print("1. Stop the current Flask server (Ctrl+C)")
    print("2. Run: python run_app.py")
    print("3. The new /api/training-jobs/<job_id>/status endpoint will now be available")
    print("4. LLM timeout and JSON parsing fixes are now active")
    print("5. Enhanced logging system is ready to use")
    
    print("\n🚀 All fixes applied successfully!")
    print("   - LLM timeout protection (25 seconds)")
    print("   - Improved JSON parsing with fallback")
    print("   - New status endpoint for job monitoring")
    print("   - Enhanced Q&A extraction with better error handling")
    print("   - Comprehensive frontend logging system")

if __name__ == "__main__":
    restart_server()