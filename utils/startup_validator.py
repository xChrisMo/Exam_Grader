#!/usr/bin/env python3
"""
Startup Validator - Validates Critical Functionality on Application Start
Ensures that critical features are intact before the application starts.
"""

import sys
import os
from pathlib import Path
import logging
from typing import Dict, List, Tuple

from utils.project_init import init_project
project_root = init_project(__file__, levels_up=2)

logger = logging.getLogger(__name__)

class StartupValidator:
    """Validates critical functionality on application startup."""

    def __init__(self, project_root: str = None):
        self.project_root = (
            Path(project_root) if project_root else Path(__file__).parent.parent
        )
        self.validation_results = {}

    def validate_batch_processing_integration(self) -> Tuple[bool, List[str]]:
        """Validate that batch processing is properly integrated."""
        errors = []

        # Check main app file
        app_file = self.project_root / "webapp/app.py"
        if not app_file.exists():
            errors.append("Main application file missing: webapp/app.py")
            return False, errors

        try:
            app_content = app_file.read_text()

            if "process_batch_submission" not in app_content:
                errors.append("Missing function: process_batch_submission")

            if "process_single_submission" not in app_content:
                errors.append("Missing function: process_single_submission")

            if "upload_submission_multiple.html" not in app_content:
                errors.append("Not using multiple file upload template")

            if "BatchProcessingService" not in app_content:
                errors.append("BatchProcessingService not integrated")

            if "parse_student_submission" not in app_content:
                errors.append("parse_student_submission not imported")

            # Check that old template is not referenced
            if (
                "upload_submission.html" in app_content
                and "upload_submission_multiple.html" in app_content
            ):
                errors.append(
                    "Both old and new templates referenced - potential conflict"
                )

        except Exception as e:
            errors.append(f"Error reading app file: {e}")

        return len(errors) == 0, errors

    def validate_template_files(self) -> Tuple[bool, List[str]]:
        """Validate template files."""
        errors = []

        # Check that multiple upload template exists
        multiple_template = (
            self.project_root / "webapp/templates/upload_submission_multiple.html"
        )
        if not multiple_template.exists():
            errors.append("Missing template: upload_submission_multiple.html")
        else:
            try:
                template_content = multiple_template.read_text()

                required_elements = [
                    'name="uploadMode"',
                    'id="batch-options"',
                    'id="selected-files"',
                    'id="batch-progress"',
                    "processBatch",
                    "processFile",
                ]

                for element in required_elements:
                    if element not in template_content:
                        errors.append(f"Missing template element: {element}")

            except Exception as e:
                errors.append(f"Error reading template file: {e}")

        # Check that old template is removed
        old_template = self.project_root / "webapp/templates/upload_submission.html"
        if old_template.exists():
            errors.append(
                "Old template still exists: upload_submission.html (should be removed)"
            )

        return len(errors) == 0, errors

    def validate_batch_service(self) -> Tuple[bool, List[str]]:
        """Validate batch processing service."""
        errors = []

        service_file = self.project_root / "src/services/batch_processing_service.py"
        if not service_file.exists():
            errors.append("Missing service: batch_processing_service.py")
            return False, errors

        try:
            service_content = service_file.read_text()

            required_methods = [
                "process_files_batch",
                "_process_parallel",
                "_process_sequential",
                "_process_single_file",
            ]

            for method in required_methods:
                if f"def {method}" not in service_content:
                    errors.append(f"Missing method in batch service: {method}")

            if "from werkzeug.datastructures import FileStorage" not in service_content:
                errors.append("Missing FileStorage import in batch service")

        except Exception as e:
            errors.append(f"Error reading batch service file: {e}")

        return len(errors) == 0, errors

    def validate_parse_function(self) -> Tuple[bool, List[str]]:
        """Validate parse function availability."""
        errors = []

        parse_file = self.project_root / "src/parsing/parse_submission.py"
        if not parse_file.exists():
            errors.append("Missing file: parse_submission.py")
            return False, errors

        try:
            parse_content = parse_file.read_text()

            if "def parse_student_submission" not in parse_content:
                errors.append("Missing function: parse_student_submission")

        except Exception as e:
            errors.append(f"Error reading parse file: {e}")

        return len(errors) == 0, errors

    def validate_all(self) -> Dict[str, any]:
        """Run all validations."""
        validations = {
            "batch_processing_integration": self.validate_batch_processing_integration(),
            "template_files": self.validate_template_files(),
            "batch_service": self.validate_batch_service(),
            "parse_function": self.validate_parse_function(),
        }

        results = {
            "overall_valid": True,
            "validations": {},
            "total_errors": 0,
            "all_errors": [],
        }

        for validation_name, (is_valid, errors) in validations.items():
            results["validations"][validation_name] = {
                "valid": is_valid,
                "errors": errors,
                "error_count": len(errors),
            }

            if not is_valid:
                results["overall_valid"] = False

            results["total_errors"] += len(errors)
            results["all_errors"].extend(errors)

        return results

    def print_validation_report(self, results: Dict[str, any]):
        """Print a formatted validation report."""

        logger = logging.getLogger(__name__)

        logger.info("\n" + "=" * 60)
        logger.info("🔍 STARTUP VALIDATION REPORT")
        logger.info("=" * 60)

        if results["overall_valid"]:
            logger.info("✅ ALL VALIDATIONS PASSED")
            logger.info(
                "🚀 Application is ready to start with batch processing functionality"
            )
        else:
            logger.error("❌ VALIDATION FAILURES DETECTED")
            logger.error(f"📊 Total errors: {results['total_errors']}")

        logger.info("\n📋 DETAILED RESULTS:")
        logger.info("-" * 40)

        for validation_name, validation_result in results["validations"].items():
            status = "✅" if validation_result["valid"] else "❌"
            logger.info(f"{status} {validation_name.replace('_', ' ').title()}")

            if validation_result["errors"]:
                for error in validation_result["errors"]:
                    logger.error(f"   • {error}")

        if not results["overall_valid"]:
            logger.warning("\n⚠️ CRITICAL ISSUES FOUND:")
            logger.warning(
                "The application may not function correctly with batch processing."
            )
            logger.warning(
                "Please fix the above issues before starting the application."
            )

        logger.info("\n" + "=" * 60)

def validate_on_startup(project_root: str = None) -> bool:
    """Run startup validation and return success status.

    Set environment variable SKIP_STARTUP_VALIDATION=1 to bypass validation.
    """
    if os.getenv("SKIP_STARTUP_VALIDATION") == "1":
        logging.getLogger(__name__).info(
            "Startup validation skipped via SKIP_STARTUP_VALIDATION=1"
        )
        return True

    validator = StartupValidator(project_root)
    results = validator.validate_all()
    validator.print_validation_report(results)
    return results["overall_valid"]

if __name__ == "__main__":
    # Run validation when called directly
    success = validate_on_startup()
    sys.exit(0 if success else 1)
