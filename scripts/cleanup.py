#!/usr/bin/env python3
"""
Codebase cleanup script for Exam Grader
Removes temporary files, cache, and logs.
"""

import os
import shutil
import glob
from pathlib import Path

def cleanup_cache():
    """Remove Python cache files."""
    print("🧹 Cleaning Python cache files...")
    
    # Remove __pycache__ directories
    for pycache_dir in Path('.').rglob('__pycache__'):
        if pycache_dir.is_dir():
            shutil.rmtree(pycache_dir)
            print(f"   Removed: {pycache_dir}")
    
    # Remove .pyc files
    for pyc_file in Path('.').rglob('*.pyc'):
        pyc_file.unlink()
        print(f"   Removed: {pyc_file}")

def cleanup_logs():
    """Clean old log files."""
    print("📝 Cleaning log files...")
    
    log_files = glob.glob('logs/*.log')
    for log_file in log_files:
        os.remove(log_file)
        print(f"   Removed: {log_file}")

def cleanup_temp():
    """Clean temporary directories."""
    print("🗂️  Cleaning temporary files...")
    
    temp_dirs = ['temp', 'output']
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"   Removed: {file_path}")

def cleanup_node():
    """Clean Node.js files if they exist."""
    print("📦 Cleaning Node.js files...")
    
    if os.path.exists('node_modules'):
        print("   Found node_modules (keeping for Tailwind CSS)")
    
    # Clean npm cache files
    npm_files = ['.npm', 'package-lock.json.bak']
    for npm_file in npm_files:
        if os.path.exists(npm_file):
            if os.path.isdir(npm_file):
                shutil.rmtree(npm_file)
            else:
                os.remove(npm_file)
            print(f"   Removed: {npm_file}")

def main():
    """Main cleanup function."""
    print("🚀 Starting codebase cleanup...")
    print("-" * 40)
    
    cleanup_cache()
    cleanup_logs()
    cleanup_temp()
    cleanup_node()
    
    print("-" * 40)
    print("✅ Cleanup completed!")

if __name__ == "__main__":
    main()