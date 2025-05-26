#!/usr/bin/env python3
"""
Setup Validation Script for Exam Grader

This script validates that all required dependencies and configurations
are properly set up before running the application.
"""

import os
import sys
import importlib
from pathlib import Path
from typing import List


class SetupValidator:
    """Validates the application setup and configuration."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def validate_python_version(self) -> bool:
        """Validate Python version is 3.8 or higher."""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.errors.append(f"Python 3.8+ required, found {version.major}.{version.minor}")
            return False

        self.info.append(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
        return True

    def validate_dependencies(self) -> bool:
        """Validate all required dependencies are installed."""
        required_packages = [
            ('requests', '2.31.0'),
            ('python-dotenv', '1.0.1'),
            ('numpy', '1.26.4'),
            ('pandas', '2.2.0'),
            ('openpyxl', '3.1.2'),
            ('openai', '1.12.0'),
            ('validators', '0.22.0'),
            ('packaging', '23.0'),
            ('PyMuPDF', '1.23.8'),
            ('python-docx', '1.1.0'),
            ('Pillow', '10.2.0'),
            ('nltk', '3.8.1'),
            ('scikit-learn', '1.4.0'),
        ]

        missing_packages = []

        for package, _min_version in required_packages:
            try:
                module = importlib.import_module(package.lower().replace('-', '_'))

                # Check version if available
                if hasattr(module, '__version__'):
                    installed_version = module.__version__
                    self.info.append(f"✓ {package}: {installed_version}")
                else:
                    self.info.append(f"✓ {package}: installed (version unknown)")

            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            self.errors.append(f"Missing packages: {', '.join(missing_packages)}")
            return False

        return True

    def validate_directories(self) -> bool:
        """Validate required directories exist or can be created."""
        required_dirs = [
            'temp',
            'temp/uploads',
            'output',
            'logs',
            'results'
        ]

        for dir_path in required_dirs:
            try:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                self.info.append(f"✓ Directory: {dir_path}")
            except Exception as e:
                self.errors.append(f"Cannot create directory {dir_path}: {e}")
                return False

        return True

    def validate_environment(self) -> bool:
        """Validate environment configuration."""
        # Load .env file if it exists
        env_file = Path('.env')
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv()
            self.info.append("✓ .env file loaded")
        else:
            self.warnings.append("No .env file found (using defaults)")

        # Check critical environment variables
        critical_vars = {
            'DEEPSEEK_API_KEY': 'DeepSeek API key for LLM functionality',
            'HANDWRITING_OCR_API_KEY': 'HandwritingOCR API key for image processing'
        }

        missing_critical = []
        for var, description in critical_vars.items():
            if not os.getenv(var):
                missing_critical.append(f"{var} ({description})")
            else:
                self.info.append(f"✓ {var}: configured")

        if missing_critical:
            self.warnings.append(f"Missing API keys: {', '.join(missing_critical)}")
            self.warnings.append("Some features may not work without proper API keys")

        # Check optional environment variables
        optional_vars = {
            'DEBUG': 'false',
            'LOG_LEVEL': 'INFO',
            'HOST': '0.0.0.0',
            'PORT': '5000',
            'MAX_FILE_SIZE_MB': '10'
        }

        for var, default in optional_vars.items():
            value = os.getenv(var, default)
            self.info.append(f"✓ {var}: {value}")

        return True

    def validate_file_permissions(self) -> bool:
        """Validate file system permissions."""
        test_dirs = ['temp', 'output', 'logs']

        for dir_path in test_dirs:
            try:
                # Test write permission
                test_file = Path(dir_path) / 'test_write.tmp'
                test_file.write_text('test')
                test_file.unlink()
                self.info.append(f"✓ Write permission: {dir_path}")
            except Exception as e:
                self.errors.append(f"No write permission in {dir_path}: {e}")
                return False

        return True

    def validate_api_connectivity(self) -> bool:
        """Test API connectivity (optional)."""
        # Only test if API keys are available
        deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        ocr_key = os.getenv('HANDWRITING_OCR_API_KEY')

        if deepseek_key:
            try:
                from src.services.llm_service import LLMService
                llm = LLMService(api_key=deepseek_key)
                llm.test_connection()
                self.info.append("✓ DeepSeek API: connection successful")
            except Exception as e:
                self.warnings.append(f"DeepSeek API connection failed: {e}")

        if ocr_key:
            try:
                from src.services.ocr_service import OCRService
                OCRService(api_key=ocr_key)  # Just test initialization
                self.info.append("✓ HandwritingOCR API: service initialized")
            except Exception as e:
                self.warnings.append(f"HandwritingOCR API initialization failed: {e}")

        return True

    def run_validation(self) -> bool:
        """Run all validation checks."""
        print("🔍 Validating Exam Grader Setup...")
        print("=" * 50)

        checks = [
            ("Python Version", self.validate_python_version),
            ("Dependencies", self.validate_dependencies),
            ("Directories", self.validate_directories),
            ("Environment", self.validate_environment),
            ("File Permissions", self.validate_file_permissions),
            ("API Connectivity", self.validate_api_connectivity),
        ]

        all_passed = True
        for check_name, check_func in checks:
            print(f"\n📋 {check_name}:")
            try:
                result = check_func()
                if not result:
                    all_passed = False
            except Exception as e:
                self.errors.append(f"{check_name} validation failed: {e}")
                all_passed = False

        # Print results
        print("\n" + "=" * 50)
        print("📊 VALIDATION RESULTS")
        print("=" * 50)

        if self.info:
            print("\n✅ SUCCESS:")
            for msg in self.info:
                print(f"  {msg}")

        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for msg in self.warnings:
                print(f"  {msg}")

        if self.errors:
            print("\n❌ ERRORS:")
            for msg in self.errors:
                print(f"  {msg}")

        print("\n" + "=" * 50)
        if all_passed and not self.errors:
            print("🎉 SETUP VALIDATION PASSED!")
            print("Your Exam Grader application is ready to run.")
            return True
        else:
            print("❌ SETUP VALIDATION FAILED!")
            print("Please fix the errors above before running the application.")
            return False


def main():
    """Main validation function."""
    validator = SetupValidator()
    success = validator.run_validation()

    if not success:
        print("\n💡 NEXT STEPS:")
        print("1. Install missing dependencies: pip install -r requirements.txt")
        print("2. Copy .env.example to .env and configure your API keys")
        print("3. Run this script again to validate your setup")
        sys.exit(1)
    else:
        print("\n🚀 You can now run the application with: python run_app.py")
        sys.exit(0)


if __name__ == "__main__":
    main()
