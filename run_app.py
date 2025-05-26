#!/usr/bin/env python3
"""
Runner script for Exam Grader core application.

This script provides a command-line interface for the Exam Grader application
without the web interface. It validates the environment and provides access
to core functionality through a simple CLI.
"""

import os
import sys
from pathlib import Path
import logging


def setup_environment() -> bool:
    """
    Set up the application environment and validate requirements.

    Returns:
        bool: True if setup successful, False otherwise
    """
    try:
        # Get the absolute path to the project root directory
        project_root = os.path.dirname(os.path.abspath(__file__))

        # Add the project root to the Python path
        sys.path.insert(0, project_root)

        # Create required directories if they don't exist
        required_dirs = ["temp", "temp/uploads", "output", "logs", "results"]
        for directory in required_dirs:
            dir_path = Path(os.path.join(project_root, directory))
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"✓ Created directory: {directory}")

        return True
    except Exception as e:
        print(f"❌ Environment setup failed: {e}")
        return False


def setup_logging(project_root: str) -> None:
    """
    Configure application logging.

    Args:
        project_root: Path to the project root directory
    """
    try:
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(project_root, "logs", "app.log")),
                logging.StreamHandler()
            ]
        )
        print("✓ Logging configured successfully")
    except Exception as e:
        print(f"⚠️  Logging setup failed: {e}")


def validate_dependencies() -> bool:
    """
    Validate that critical dependencies are available.

    Returns:
        bool: True if all critical dependencies are available
    """
    critical_imports = [
        ('src.config.config_manager', 'Configuration manager'),
        ('utils.logger', 'Logging utilities'),
        ('src.parsing.parse_submission', 'Document parsing'),
        ('src.services.llm_service', 'LLM service'),
    ]

    missing_deps = []
    for module, description in critical_imports:
        try:
            __import__(module)
        except ImportError as e:
            missing_deps.append(f"{module} ({description}): {e}")

    if missing_deps:
        print("❌ Missing critical dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\n💡 Run: pip install -r requirements.txt")
        return False

    print("✓ All critical dependencies available")
    return True


def show_usage() -> None:
    """Display usage information."""
    print("\n📖 USAGE:")
    print("This is the core Exam Grader application without web interface.")
    print("\nAvailable functionality:")
    print("  • Document parsing (PDF, DOCX, images, text)")
    print("  • OCR text extraction")
    print("  • LLM-powered grading and mapping")
    print("  • Result storage and caching")
    print("\n🔧 To use the application programmatically:")
    print("  from src.parsing.parse_submission import parse_student_submission")
    print("  from src.services.llm_service import LLMService")
    print("  from src.services.mapping_service import MappingService")
    print("\n📚 Example:")
    print("  # Parse a document")
    print("  result, text, error = parse_student_submission('exam.pdf')")
    print("  if not error:")
    print("      print(f'Extracted text: {text}')")


def main() -> None:
    """
    Main application entry point.
    """
    print("🚀 Starting Exam Grader Core Application")
    print("=" * 50)

    # Setup environment
    if not setup_environment():
        sys.exit(1)

    # Validate dependencies
    if not validate_dependencies():
        sys.exit(1)

    # Setup logging
    project_root = os.path.dirname(os.path.abspath(__file__))
    setup_logging(project_root)

    try:
        print("\n📦 Importing application modules...")

        # Import core modules to verify they work
        from src.config.config_manager import ConfigManager
        from src.parsing.parse_submission import parse_student_submission
        from utils.logger import logger

        print("✓ Core modules imported successfully")

        # Initialize configuration
        config = ConfigManager()
        print("✓ Configuration loaded successfully")

        print("\n" + "=" * 50)
        print("🎉 Exam Grader Core Application Ready!")
        print("=" * 50)

        # Show usage information
        show_usage()

        print(f"\n📁 Working directory: {os.getcwd()}")
        print(f"📝 Logs: {os.path.join(project_root, 'logs', 'app.log')}")
        print(f"💾 Output: {config.config.output_dir}")
        print(f"🗂️  Temp: {config.config.temp_dir}")

        print("\n✅ Application initialized successfully!")
        print("You can now use the Exam Grader modules in your Python code.")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Application startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()