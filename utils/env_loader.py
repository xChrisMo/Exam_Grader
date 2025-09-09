#!/usr/bin/env python3
"""
Centralized environment variable loading utility.

This module provides a consistent way to load environment variables
from .env files throughout the application.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

def load_environment(env_file: Optional[str] = None, project_root: Optional[Path] = None) -> None:
    """
    Load environment variables from .env file(s) with proper precedence.
    
    This function loads environment variables in the following order:
    1. instance/.env (highest priority)
    2. .env (project root)
    
    Note: env.example is never loaded to avoid placeholder values.
    
    Args:
        env_file: Specific .env file to load. If None, uses standard precedence.
        project_root: Project root directory. If None, auto-detects.
    """
    if project_root is None:
        project_root = _get_project_root()
    
    # Define environment files in order of precedence
    env_files = []
    
    if env_file:
        # Use specific file if provided
        env_files.append(env_file)
    else:
        # Standard precedence order (env.example excluded)
        env_files = [
            project_root / "instance" / ".env",  # Instance-specific (highest priority)
            project_root / ".env"                # Project root
        ]
    
    # Debug logging
    print("🔍 Environment Loading Debug:")
    print(f"   RENDER: {os.getenv('RENDER', 'Not set')}")
    print(f"   FLASK_ENV: {os.getenv('FLASK_ENV', 'Not set')}")
    print(f"   DEEPSEEK_API_KEY before loading: {os.getenv('DEEPSEEK_API_KEY', 'Not set')[:10] + '...' if os.getenv('DEEPSEEK_API_KEY') else 'Not set'}")
    
    # Load environment files
    for env_path in env_files:
        if env_path.exists():
            print(f"   Found env file: {env_path}")
            # Load .env files (env.example is never included in env_files)
            load_dotenv(env_path, override=True)
            print(f"✅ Loaded environment from: {env_path}")
            break
    else:
        print("⚠️  No .env file found, using system environment variables only")
    
    print(f"   DEEPSEEK_API_KEY after loading: {os.getenv('DEEPSEEK_API_KEY', 'Not set')[:10] + '...' if os.getenv('DEEPSEEK_API_KEY') else 'Not set'}")
    print("=" * 50)

def ensure_env_file_exists(project_root: Optional[Path] = None) -> bool:
    """
    Ensure a .env file exists.
    
    Args:
        project_root: Project root directory. If None, auto-detects.
        
    Returns:
        bool: True if .env file exists, False otherwise.
    """
    if project_root is None:
        project_root = _get_project_root()
    
    env_file = project_root / ".env"
    
    if env_file.exists():
        return True
    
    print("⚠️  No .env file found - please create one with your environment variables")
    return False

def ensure_instance_folder(project_root: Optional[Path] = None) -> None:
    """
    Ensure the instance folder exists for Flask app configuration.
    
    Args:
        project_root: Project root directory. If None, auto-detects.
    """
    if project_root is None:
        project_root = _get_project_root()
    
    instance_folder = project_root / "instance"
    instance_folder.mkdir(exist_ok=True)
    print(f"✅ Instance folder ready: {instance_folder}")

def setup_environment(project_root: Optional[Path] = None) -> None:
    """
    Complete environment setup: create folders and load .env files.
    
    This function:
    1. Ensures instance folder exists
    2. Ensures .env file exists
    3. Loads environment variables
    
    Args:
        project_root: Project root directory. If None, auto-detects.
    """
    if project_root is None:
        project_root = _get_project_root()
    
    # Ensure required folders and files exist
    ensure_instance_folder(project_root)
    ensure_env_file_exists(project_root)
    
    # Load environment variables
    load_environment(project_root=project_root)

def _get_project_root() -> Path:
    """
    Get the project root directory.
    
    Returns:
        Path: The project root directory path.
    """
    # Look for characteristic files that indicate project root
    indicators = [
        'pyproject.toml',
        'requirements.txt',
        'run_app.py',
        '.gitignore',
        'README.md'
    ]
    
    # Check current directory and parents
    current_path = Path.cwd()
    for path in [current_path] + list(current_path.parents):
        if any((path / indicator).exists() for indicator in indicators):
            return path
    
    # Fallback to current working directory
    return current_path

# Convenience function for quick setup
def init_env() -> None:
    """
    Initialize environment with complete setup.
    
    This is a convenience function that sets up everything needed
    for environment variable loading.
    """
    setup_environment()
