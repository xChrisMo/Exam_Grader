"""
Resource Validator - Validates required resources and creates missing ones.

This module provides comprehensive resource validation for the processing system,
ensuring all required files, directories, and resources are available.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utils.logger import logger

@dataclass
class ValidationResult:
    """Result of resource validation."""

    valid: bool
    resource_name: str
    resource_type: str
    message: str
    created: bool = False
    path: Optional[str] = None

@dataclass
class ResourceRequirement:
    """Definition of a required resource."""

    name: str
    type: str  # 'file', 'directory', 'template', 'config'
    path: str
    required: bool = True
    description: str = ""
    default_content: Optional[str] = None
    permissions: Optional[str] = None

class ResourceValidator:
    """
    Validates required resources exist and creates missing ones.
    """

    def __init__(self):
        self.resource_requirements: List[ResourceRequirement] = []
        self.validation_results: List[ValidationResult] = []

        # Initialize default resource requirements
        self._setup_default_requirements()

        logger.info("ResourceValidator initialized")

    def _setup_default_requirements(self):
        """Set up default resource requirements."""

        # Directory requirements
        self.add_requirement(
            ResourceRequirement(
                name="templates_dir",
                type="directory",
                path="templates",
                description="Main templates directory",
            )
        )

        self.add_requirement(
            ResourceRequirement(
                name="reports_templates_dir",
                type="directory",
                path="templates/reports",
                description="Report templates directory",
            )
        )

        self.add_requirement(
            ResourceRequirement(
                name="emails_templates_dir",
                type="directory",
                path="templates/emails",
                description="Email templates directory",
            )
        )

        self.add_requirement(
            ResourceRequirement(
                name="fallback_templates_dir",
                type="directory",
                path="templates/fallback",
                description="Fallback templates directory",
            )
        )

        self.add_requirement(
            ResourceRequirement(
                name="logs_dir",
                type="directory",
                path="logs",
                description="Logs directory",
            )
        )

        self.add_requirement(
            ResourceRequirement(
                name="uploads_dir",
                type="directory",
                path="uploads",
                description="File uploads directory",
            )
        )

        self.add_requirement(
            ResourceRequirement(
                name="temp_dir",
                type="directory",
                path="temp",
                description="Temporary files directory",
            )
        )

        # Template file requirements
        self.add_requirement(
            ResourceRequirement(
                name="default_report_template",
                type="template",
                path="templates/reports/default.html",
                description="Default report template",
                default_content=self._get_default_report_template(),
            )
        )

        self.add_requirement(
            ResourceRequirement(
                name="error_report_template",
                type="template",
                path="templates/reports/error_report.html",
                description="Error report template",
                default_content=self._get_error_report_template(),
            )
        )

        self.add_requirement(
            ResourceRequirement(
                name="processing_complete_email",
                type="template",
                path="templates/emails/processing_complete.html",
                description="Processing complete email template",
                default_content=self._get_email_template(),
            )
        )

        self.add_requirement(
            ResourceRequirement(
                name="text_fallback_template",
                type="template",
                path="templates/fallback/text_report.txt",
                description="Text fallback template",
                default_content=self._get_text_fallback_template(),
            )
        )

        # Configuration file requirements
        self.add_requirement(
            ResourceRequirement(
                name="processing_config",
                type="config",
                path="config/processing.json",
                required=False,
                description="Processing configuration file",
                default_content=self._get_default_processing_config(),
            )
        )

        # Log file requirements
        self.add_requirement(
            ResourceRequirement(
                name="error_log",
                type="file",
                path="logs/processing_errors.log",
                required=False,
                description="Processing errors log file",
                default_content="",
            )
        )

    def add_requirement(self, requirement: ResourceRequirement):
        """Add a resource requirement."""
        self.resource_requirements.append(requirement)
        logger.debug(f"Added resource requirement: {requirement.name}")

    def validate_resources(self) -> Dict[str, Any]:
        """
        Validate all required resources.

        Returns:
            Dictionary containing validation results
        """
        self.validation_results.clear()

        for requirement in self.resource_requirements:
            result = self._validate_single_resource(requirement)
            self.validation_results.append(result)

        # Compile summary
        total_resources = len(self.validation_results)
        valid_resources = len([r for r in self.validation_results if r.valid])
        created_resources = len([r for r in self.validation_results if r.created])
        failed_resources = [r for r in self.validation_results if not r.valid]

        summary = {
            "total_resources": total_resources,
            "valid_resources": valid_resources,
            "created_resources": created_resources,
            "failed_resources": len(failed_resources),
            "validation_success": len(failed_resources) == 0,
            "results": [
                {
                    "name": r.resource_name,
                    "type": r.resource_type,
                    "valid": r.valid,
                    "created": r.created,
                    "message": r.message,
                    "path": r.path,
                }
                for r in self.validation_results
            ],
            "failed_details": [
                {
                    "name": r.resource_name,
                    "type": r.resource_type,
                    "message": r.message,
                    "path": r.path,
                }
                for r in failed_resources
            ],
        }

        logger.info(
            f"Resource validation completed: {valid_resources}/{total_resources} valid, {created_resources} created"
        )

        return summary

    def _validate_single_resource(
        self, requirement: ResourceRequirement
    ) -> ValidationResult:
        """Validate a single resource requirement."""

        try:
            resource_path = Path(requirement.path)

            if resource_path.exists():
                return ValidationResult(
                    valid=True,
                    resource_name=requirement.name,
                    resource_type=requirement.type,
                    message=f"{requirement.type.title()} exists",
                    path=str(resource_path),
                )

            if not requirement.required:
                logger.info(
                    f"Optional resource '{requirement.name}' not found, skipping"
                )
                return ValidationResult(
                    valid=True,
                    resource_name=requirement.name,
                    resource_type=requirement.type,
                    message=f"Optional {requirement.type} not found (OK)",
                    path=str(resource_path),
                )

            # Try to create missing required resource
            if requirement.default_content is not None:
                created = self._create_missing_resource(requirement)
                if created:
                    return ValidationResult(
                        valid=True,
                        resource_name=requirement.name,
                        resource_type=requirement.type,
                        message=f"{requirement.type.title()} created successfully",
                        created=True,
                        path=str(resource_path),
                    )
                else:
                    return ValidationResult(
                        valid=False,
                        resource_name=requirement.name,
                        resource_type=requirement.type,
                        message=f"Failed to create {requirement.type}",
                        path=str(resource_path),
                    )
            else:
                return ValidationResult(
                    valid=False,
                    resource_name=requirement.name,
                    resource_type=requirement.type,
                    message=f"Required {requirement.type} not found and no default content available",
                    path=str(resource_path),
                )

        except Exception as e:
            logger.error(f"Error validating resource '{requirement.name}': {e}")
            return ValidationResult(
                valid=False,
                resource_name=requirement.name,
                resource_type=requirement.type,
                message=f"Validation error: {str(e)}",
                path=requirement.path,
            )

    def _create_missing_resource(self, requirement: ResourceRequirement) -> bool:
        """Create a missing resource."""

        try:
            resource_path = Path(requirement.path)

            # Ensure parent directory exists
            resource_path.parent.mkdir(parents=True, exist_ok=True)

            if requirement.type == "directory":
                resource_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {resource_path}")
                return True

            elif requirement.type in ["file", "template", "config"]:
                with open(resource_path, "w", encoding="utf-8") as f:
                    f.write(requirement.default_content or "")

                if requirement.permissions:
                    os.chmod(resource_path, int(requirement.permissions, 8))

                logger.info(f"Created {requirement.type}: {resource_path}")
                return True

            else:
                logger.error(f"Unknown resource type: {requirement.type}")
                return False

        except Exception as e:
            logger.error(f"Failed to create resource '{requirement.name}': {e}")
            return False

    def create_missing_resources(self) -> List[str]:
        """
        Create all missing resources that have default content.

        Returns:
            List of created resource names
        """
        created_resources = []

        for requirement in self.resource_requirements:
            resource_path = Path(requirement.path)

            if not resource_path.exists() and requirement.default_content is not None:
                if self._create_missing_resource(requirement):
                    created_resources.append(requirement.name)

        logger.info(f"Created {len(created_resources)} missing resources")
        return created_resources

    def get_validation_report(self) -> str:
        """Get a formatted validation report."""

        if not self.validation_results:
            return "No validation results available. Run validate_resources() first."

        report_lines = [
            "RESOURCE VALIDATION REPORT",
            "=" * 50,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Summary
        total = len(self.validation_results)
        valid = len([r for r in self.validation_results if r.valid])
        created = len([r for r in self.validation_results if r.created])
        failed = total - valid

        report_lines.extend(
            [
                "SUMMARY:",
                f"  Total Resources: {total}",
                f"  Valid Resources: {valid}",
                f"  Created Resources: {created}",
                f"  Failed Resources: {failed}",
                f"  Overall Status: {'PASS' if failed == 0 else 'FAIL'}",
                "",
            ]
        )

        # Details
        report_lines.append("DETAILS:")
        for result in self.validation_results:
            status = "✓" if result.valid else "✗"
            created_flag = " (CREATED)" if result.created else ""
            report_lines.append(
                f"  {status} {result.resource_name}: {result.message}{created_flag}"
            )

        # Failed resources
        failed_results = [r for r in self.validation_results if not r.valid]
        if failed_results:
            report_lines.extend(
                [
                    "",
                    "FAILED RESOURCES:",
                ]
            )
            for result in failed_results:
                report_lines.append(
                    f"  - {result.resource_name} ({result.resource_type}): {result.message}"
                )
                report_lines.append(f"    Path: {result.path}")

        return "\n".join(report_lines)

    def check_resource_permissions(self) -> Dict[str, Any]:
        """Check permissions for existing resources."""

        permission_results = []

        for requirement in self.resource_requirements:
            resource_path = Path(requirement.path)

            if resource_path.exists():
                try:
                    # Check basic permissions
                    readable = os.access(resource_path, os.R_OK)
                    writable = os.access(resource_path, os.W_OK)
                    executable = (
                        os.access(resource_path, os.X_OK)
                        if resource_path.is_dir()
                        else False
                    )

                    permission_results.append(
                        {
                            "name": requirement.name,
                            "path": str(resource_path),
                            "type": requirement.type,
                            "readable": readable,
                            "writable": writable,
                            "executable": executable,
                            "permissions_ok": readable
                            and (writable if requirement.type != "directory" else True),
                        }
                    )

                except Exception as e:
                    permission_results.append(
                        {
                            "name": requirement.name,
                            "path": str(resource_path),
                            "type": requirement.type,
                            "error": str(e),
                            "permissions_ok": False,
                        }
                    )

        return {
            "total_checked": len(permission_results),
            "permissions_ok": len(
                [r for r in permission_results if r.get("permissions_ok", False)]
            ),
            "results": permission_results,
        }

    def cleanup_temporary_resources(self) -> Dict[str, Any]:
        """Clean up temporary resources."""

        cleanup_results = {
            "files_removed": 0,
            "directories_removed": 0,
            "errors": [],
            "total_size_freed": 0,
        }

        # Clean up temp directory
        temp_dir = Path("temp")
        if temp_dir.exists():
            try:
                for item in temp_dir.iterdir():
                    if item.is_file():
                        size = item.stat().st_size
                        item.unlink()
                        cleanup_results["files_removed"] += 1
                        cleanup_results["total_size_freed"] += size
                    elif item.is_dir():
                        import shutil

                        shutil.rmtree(item)
                        cleanup_results["directories_removed"] += 1

            except Exception as e:
                cleanup_results["errors"].append(
                    f"Error cleaning temp directory: {str(e)}"
                )

        # Clean up old log files (older than 30 days)
        logs_dir = Path("logs")
        if logs_dir.exists():
            try:
                cutoff_time = datetime.now().timestamp() - (
                    30 * 24 * 60 * 60
                )  # 30 days

                for log_file in logs_dir.glob("*.log.*"):  # Rotated log files
                    if log_file.stat().st_mtime < cutoff_time:
                        size = log_file.stat().st_size
                        log_file.unlink()
                        cleanup_results["files_removed"] += 1
                        cleanup_results["total_size_freed"] += size

            except Exception as e:
                cleanup_results["errors"].append(f"Error cleaning old logs: {str(e)}")

        logger.info(
            f"Cleanup completed: {cleanup_results['files_removed']} files, {cleanup_results['directories_removed']} directories removed"
        )

        return cleanup_results

    # Default content methods

    def _get_default_report_template(self) -> str:
        """Get default report template content."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title or 'Processing Report' }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        .header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
        .section { margin-bottom: 20px; }
        .section h2 { color: #333; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
        .status-success { color: #28a745; font-weight: bold; }
        .status-error { color: #dc3545; font-weight: bold; }
        .status-warning { color: #ffc107; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title or 'Processing Report' }}</h1>
        <p><strong>Generated:</strong> {{ generated_at or 'N/A' }}</p>
    </div>

    {% if summary %}
    <div class="section">
        <h2>Summary</h2>
        {% for key, value in summary.items() %}
        <p><strong>{{ key.replace('_', ' ').title() }}:</strong> {{ value }}</p>
        {% endfor %}
    </div>
    {% endif %}

    {% if data %}
    <div class="section">
        <h2>Data</h2>
        <pre>{{ data }}</pre>
    </div>
    {% endif %}

    {% if errors %}
    <div class="section">
        <h2>Errors</h2>
        {% for error in errors %}
        <div class="status-error">
            <p><strong>Error:</strong> {{ error.message or error }}</p>
        </div>
        {% endfor %}
    </div>
    {% endif %}
</body>
</html>"""

    def _get_error_report_template(self) -> str:
        """Get default error report template content."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        .header { border-bottom: 2px solid #dc3545; padding-bottom: 10px; margin-bottom: 20px; }
        .error { background: #f8d7da; border: 1px solid #dc3545; padding: 10px; margin: 10px 0; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Error Report</h1>
        <p><strong>Generated:</strong> {{ generated_at or 'N/A' }}</p>
    </div>

    {% if errors %}
    {% for error in errors %}
    <div class="error">
        <h3>{{ error.error_type or 'Error' }}</h3>
        <p><strong>Message:</strong> {{ error.message }}</p>
        {% if error.timestamp %}<p><strong>Time:</strong> {{ error.timestamp }}</p>{% endif %}
    </div>
    {% endfor %}
    {% endif %}
</body>
</html>"""

    def _get_email_template(self) -> str:
        """Get default email template content."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Processing Complete</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 600px; margin: 0 auto; }
        .header { background: #007bff; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Processing Complete</h1>
        </div>
        <div class="content">
            <p>Your processing request has been completed.</p>
            <p>Generated: {{ generated_at }}</p>
        </div>
    </div>
</body>
</html>"""

    def _get_text_fallback_template(self) -> str:
        """Get default text fallback template content."""
        return """PROCESSING REPORT
==================
Generated: {{ generated_at }}

{% if summary %}
SUMMARY:
{% for key, value in summary.items() %}
{{ key.replace('_', ' ').title() }}: {{ value }}
{% endfor %}
{% endif %}

{% if data %}
DATA:
{{ data }}
{% endif %}

{% if errors %}
ERRORS:
{% for error in errors %}
- {{ error.message or error }}
{% endfor %}
{% endif %}
"""

    def _get_default_processing_config(self) -> str:
        """Get default processing configuration content."""
        config = {
            "processing": {
                "max_retries": 3,
                "timeout_seconds": 300,
                "enable_fallbacks": True,
                "enable_caching": True,
            },
            "templates": {
                "default_template": "reports/default.html",
                "error_template": "reports/error_report.html",
                "fallback_format": "html",
            },
            "logging": {"level": "INFO", "max_file_size": "10MB", "backup_count": 5},
        }
        return json.dumps(config, indent=2)

# Global instance
resource_validator = ResourceValidator()
