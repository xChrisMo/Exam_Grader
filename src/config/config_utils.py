"""Configuration utilities for the Exam Grader application."""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from .unified_config import UnifiedConfig


class ConfigurationUtils:
    """Utility functions for configuration management."""

    @staticmethod
    def backup_environment_file(env_file_path: str = ".env") -> str:
        """
        Create a backup of the environment file.

        Args:
            env_file_path: Path to the environment file

        Returns:
            Path to the backup file
        """
        env_path = Path(env_file_path)
        if not env_path.exists():
            raise FileNotFoundError(f"Environment file not found: {env_file_path}")

        # Create backup with timestamp
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = env_path.with_suffix(f".backup_{timestamp}")

        shutil.copy2(env_path, backup_path)
        return str(backup_path)

    @staticmethod
    def create_environment_file(
        config: UnifiedConfig, file_path: str = ".env.example"
    ) -> None:
        """
        Create an environment file template.

        Args:
            config: UnifiedConfig instance
            file_path: Path where to create the file
        """
        template = config.export_environment_template(include_values=False)

        with open(file_path, "w") as f:
            f.write(template)

    @staticmethod
    def validate_environment_file(
        env_file_path: str = ".env",
    ) -> Tuple[bool, List[str]]:
        """
        Validate environment file for required variables.

        Args:
            env_file_path: Path to the environment file

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        if not Path(env_file_path).exists():
            issues.append(f"Environment file not found: {env_file_path}")
            return False, issues

        # Load the environment file temporarily
        from dotenv import dotenv_values

        env_vars = dotenv_values(env_file_path)

        required_vars = [
            "SECRET_KEY",
            "DATABASE_URL",
        ]

        for var in required_vars:
            if var not in env_vars or not env_vars[var]:
                issues.append(f"Required environment variable missing or empty: {var}")

        # Check SECRET_KEY length
        secret_key = env_vars.get("SECRET_KEY", "")
        if secret_key and len(secret_key) < 32:
            issues.append("SECRET_KEY should be at least 32 characters long")

        # Check database URL format
        database_url = env_vars.get("DATABASE_URL", "")
        if database_url and not (
            database_url.startswith("sqlite:///")
            or database_url.startswith("postgresql://")
            or database_url.startswith("mysql://")
        ):
            issues.append("DATABASE_URL format may be invalid")

        # Check numeric values
        numeric_vars = {
            "PORT": (1, 65535),
            "SESSION_TIMEOUT": (60, 86400),
            "MAX_FILE_SIZE_MB": (1, 100),
        }

        for var, (min_val, max_val) in numeric_vars.items():
            if var in env_vars:
                try:
                    value = int(env_vars[var])
                    if not (min_val <= value <= max_val):
                        issues.append(
                            f"{var} should be between {min_val} and {max_val}"
                        )
                except ValueError:
                    issues.append(f"{var} should be a valid integer")

        return len(issues) == 0, issues

    @staticmethod
    def compare_configurations(
        config1: UnifiedConfig, config2: UnifiedConfig
    ) -> Dict[str, Dict]:
        """
        Compare two configuration instances.

        Args:
            config1: First configuration
            config2: Second configuration

        Returns:
            Dictionary of differences
        """
        differences = {}

        # Compare each configuration section
        sections = [
            "security",
            "database",
            "files",
            "api",
            "cache",
            "logging",
            "server",
        ]

        for section in sections:
            section_diffs = {}
            obj1 = getattr(config1, section)
            obj2 = getattr(config2, section)

            attrs1 = {k: v for k, v in obj1.__dict__.items() if not k.startswith("_")}
            attrs2 = {k: v for k, v in obj2.__dict__.items() if not k.startswith("_")}

            all_attrs = set(attrs1.keys()) | set(attrs2.keys())

            for attr in all_attrs:
                val1 = attrs1.get(attr, "<missing>")
                val2 = attrs2.get(attr, "<missing>")

                if val1 != val2:
                    section_diffs[attr] = {"config1": val1, "config2": val2}

            if section_diffs:
                differences[section] = section_diffs

        return differences

    @staticmethod
    def get_environment_info() -> Dict[str, str]:
        """
        Get information about the current environment.

        Returns:
            Dictionary with environment information
        """
        return {
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "platform": os.sys.platform,
            "cwd": os.getcwd(),
            "user": os.getenv("USER", os.getenv("USERNAME", "unknown")),
            "home": os.getenv("HOME", os.getenv("USERPROFILE", "unknown")),
            "path_separator": os.pathsep,
            "flask_env": os.getenv("FLASK_ENV", "not set"),
            "flask_app": os.getenv("FLASK_APP", "not set"),
        }

    @staticmethod
    def check_configuration_health(config: UnifiedConfig) -> Dict[str, any]:
        """
        Perform a health check on the configuration.

        Args:
            config: UnifiedConfig instance

        Returns:
            Dictionary with health check results
        """
        health = {"overall_status": "healthy", "issues": [], "warnings": [], "info": []}

        # Check API keys
        if not config.api.handwriting_ocr_api_key:
            health["warnings"].append("OCR API key not configured")

        if not config.api.deepseek_api_key:
            health["warnings"].append("LLM API key not configured")

        # Check directories
        for dir_name, directory in [
            ("temp", config.files.temp_dir),
            ("output", config.files.output_dir),
            ("upload", config.files.upload_dir),
        ]:
            if not directory.exists():
                health["issues"].append(
                    f"{dir_name.title()} directory does not exist: {directory}"
                )
            elif not os.access(directory, os.W_OK):
                health["issues"].append(
                    f"{dir_name.title()} directory is not writable: {directory}"
                )
            else:
                health["info"].append(f"{dir_name.title()} directory OK: {directory}")

        # Check database
        if config.database.database_url.startswith("sqlite:///"):
            db_path = config.database.database_url.replace("sqlite:///", "")
            db_file = Path(db_path)

            if db_file.exists():
                if os.access(db_file, os.R_OK | os.W_OK):
                    health["info"].append(f"Database file accessible: {db_path}")
                else:
                    health["issues"].append(f"Database file not accessible: {db_path}")
            else:
                health["info"].append(f"Database file will be created: {db_path}")

        # Check security settings
        if config.environment == "production":
            if not config.security.session_cookie_secure:
                health["warnings"].append("Secure cookies disabled in production")

            if not config.security.csrf_enabled:
                health["warnings"].append("CSRF protection disabled in production")

        # Set overall status
        if health["issues"]:
            health["overall_status"] = "unhealthy"
        elif health["warnings"]:
            health["overall_status"] = "warning"

        return health


class ConfigurationMigrationTool:
    """Tool for migrating configuration between versions."""

    @staticmethod
    def migrate_from_old_config(old_config_path: str = "config.py") -> Dict[str, str]:
        """
        Migrate from old configuration format to new environment variables.

        Args:
            old_config_path: Path to old configuration file

        Returns:
            Dictionary of environment variables to set
        """
        env_vars = {}

        if not Path(old_config_path).exists():
            return env_vars

        # This is a simplified migration - in practice, you'd parse the old config file
        # and extract relevant settings

        # Example migration mappings
        migration_mappings = {
            "SECRET_KEY": "SECRET_KEY",
            "DEBUG": "DEBUG",
            "DATABASE_URI": "DATABASE_URL",
            "MAX_CONTENT_LENGTH": "MAX_FILE_SIZE_MB",
        }

        # In a real implementation, you would:
        # 1. Parse the old config file
        # 2. Extract values
        # 3. Map them to new environment variable names
        # 4. Return the mapping

        return env_vars

    @staticmethod
    def create_migration_script(
        old_env_path: str = ".env", new_env_path: str = ".env.new"
    ) -> str:
        """
        Create a migration script for environment variables.

        Args:
            old_env_path: Path to old environment file
            new_env_path: Path to new environment file

        Returns:
            Path to the migration script
        """
        script_content = f"""#!/bin/bash
# Configuration Migration Script
# Generated automatically

echo "Migrating configuration from {old_env_path} to {new_env_path}"

# Backup old configuration
cp {old_env_path} {old_env_path}.backup

# Create new configuration
# (Add specific migration commands here)

echo "Migration completed. Please review {new_env_path}"
"""

        script_path = "migrate_config.sh"
        with open(script_path, "w") as f:
            f.write(script_content)

        # Make script executable on Unix systems
        try:
            os.chmod(script_path, 0o755)
        except:
            pass  # Windows doesn't support chmod

        return script_path
