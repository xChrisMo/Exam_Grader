#!/usr/bin/env python3
"""
Project initialization utility to standardize path setup across all modules.

This module provides a centralized way to set up the project root path
and ensure consistent imports throughout the application.
"""

import sys
from pathlib import Path
from typing import Optional

def setup_project_path(file_path: Optional[str] = None, levels_up: int = 1) -> Path:
    """
    Set up project root path and add it to sys.path if not already present.

    Args:
        file_path: Path of the calling file (__file__). If None, uses caller's location.
        levels_up: Number of directory levels to go up to reach project root.
                  Default is 1 (for files in project root).
                  Use 2 for files in subdirectories, 3 for nested subdirectories, etc.

    Returns:
        Path: The project root directory path.

    Example:
        # For files in project root (like run_app.py)
        project_root = setup_project_path(__file__)

        # For files in src/ directory
        project_root = setup_project_path(__file__, levels_up=2)

        # For files in src/services/ directory
        project_root = setup_project_path(__file__, levels_up=3)
    """
    if file_path is None:
        # Try to determine caller's file path
        import inspect
        frame = inspect.currentframe().f_back
        file_path = frame.f_globals.get('__file__')
        if file_path is None:
            raise ValueError("Could not determine caller's file path")

    # Calculate project root
    current_file = Path(file_path).resolve()
    project_root = current_file

    for _ in range(levels_up):
        project_root = project_root.parent

    # Add to sys.path if not already present
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    return project_root

def get_project_root() -> Path:
    """
    Get the project root directory without modifying sys.path.

    Returns:
        Path: The project root directory path.
    """
    # Find the project root by looking for key files
    current_path = Path.cwd()

    # Look for characteristic files that indicate project root
    indicators = [
        'pyproject.toml',
        'requirements.txt',
        'run_app.py',
        '.gitignore',
        'README.md'
    ]

    # Check current directory and parents
    for path in [current_path] + list(current_path.parents):
        if any((path / indicator).exists() for indicator in indicators):
            return path

    # Fallback to current working directory
    return current_path

def ensure_project_imports() -> None:
    """
    Ensure project directories are in sys.path for imports.

    This function adds the main project directories to sys.path
    if they're not already present.
    """
    project_root = get_project_root()

    # Directories that should be in sys.path
    import_paths = [
        project_root,
        project_root / 'src',
        project_root / 'webapp',
        project_root / 'utils',
    ]

    for path in import_paths:
        if path.exists():
            path_str = str(path)
            if path_str not in sys.path:
                sys.path.insert(0, path_str)

# Convenience function for common use case
def init_project(file_path: str, levels_up: int = 1) -> Path:
    """
    Initialize project with standard setup.

    This is a convenience function that:
    1. Sets up the project path
    2. Ensures all import paths are available

    Args:
        file_path: Path of the calling file (__file__)
        levels_up: Number of directory levels to go up to reach project root

    Returns:
        Path: The project root directory path
    """
    project_root = setup_project_path(file_path, levels_up)
    ensure_project_imports()
    return project_root

# For backward compatibility
def add_project_to_path(file_path: str, levels_up: int = 1) -> None:
    """
    Legacy function for backward compatibility.
    Use init_project() for new code.
    """
    setup_project_path(file_path, levels_up)
