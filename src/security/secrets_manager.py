"""
Secure Secrets Management System for Exam Grader Application.

This module provides secure storage and handling of API keys and other
sensitive configuration data using encryption and secure key derivation.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import base64
from typing import Any, Dict, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# Import logger with fallback
try:
    from utils.logger import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

class SecretsEncryption:
    """Handles encryption and decryption of secrets."""

    def __init__(self, master_key: str, salt: bytes = None):
        """
        Initialize encryption with master key.

        Args:
            master_key: Master key for encryption
            salt: Salt for key derivation (generated if None)
        """
        self.master_key = master_key.encode()
        self.salt = salt or os.urandom(16)
        self._fernet = None

    def _derive_key(self) -> bytes:
        """Derive encryption key from master key."""
        kdf = Scrypt(
            length=32,
            salt=self.salt,
            n=2**14,
            r=8,
            p=1,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.master_key))

    def _get_fernet(self) -> Fernet:
        """Get or create Fernet instance."""
        if self._fernet is None:
            key = self._derive_key()
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """Encrypt data."""
        if isinstance(data, str):
            data = data.encode()
        return self._get_fernet().encrypt(data)

    def decrypt(self, encrypted_data: bytes) -> str:
        """Decrypt data."""
        decrypted = self._get_fernet().decrypt(encrypted_data)
        return decrypted.decode()

    def get_salt(self) -> bytes:
        """Get the salt used for key derivation."""
        return self.salt

class SecretsManager:
    """
    Secure secrets manager for API keys and sensitive configuration.

    Features:
    - Encrypted storage of secrets
    - Key rotation support
    - Environment variable fallback
    - Audit logging
    - Secure key derivation
    """

    def __init__(self, secrets_file: str = "secrets.enc", master_key: str = None):
        """
        Initialize secrets manager.

        Args:
            secrets_file: Path to encrypted secrets file
            master_key: Master key for encryption (from env if None)
        """
        self.secrets_file = Path(secrets_file)
        self.master_key = master_key or self._get_master_key()
        self._secrets_cache = {}
        self._encryption = None
        self._load_secrets()

    def _get_master_key(self) -> str:
        """Get master key from environment or generate one."""
        master_key = os.getenv("SECRETS_MASTER_KEY")
        if not master_key:
            master_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
            logger.warning(
                "Generated temporary master key. Set SECRETS_MASTER_KEY environment variable for production."
            )
        return master_key

    def _load_secrets(self):
        """Load secrets from encrypted file."""
        try:
            if not self.secrets_file.exists():
                logger.info("Secrets file not found, creating new one")
                self._secrets_cache = {}
                self._save_secrets()
                return

            with open(self.secrets_file, "rb") as f:
                encrypted_data = f.read()

            # First 16 bytes are the salt
            salt = encrypted_data[:16]
            encrypted_secrets = encrypted_data[16:]

            self._encryption = SecretsEncryption(self.master_key, salt)

            if encrypted_secrets:
                decrypted_data = self._encryption.decrypt(encrypted_secrets)
                self._secrets_cache = json.loads(decrypted_data)
            else:
                self._secrets_cache = {}

            logger.info("Secrets loaded successfully")

        except Exception as e:
            logger.warning(f"Failed to load secrets (this is normal for first run): {str(e)}")
            self._secrets_cache = {}
            try:
                self._encryption = SecretsEncryption(self.master_key)
                # Create empty secrets file for future use
                self._save_secrets()
                logger.info("Created new secrets file")
            except Exception as init_error:
                logger.warning(f"Could not initialize secrets encryption: {init_error}")
                self._encryption = None

    def _save_secrets(self):
        """Save secrets to encrypted file."""
        try:
            if self._encryption is None:
                self._encryption = SecretsEncryption(self.master_key)

            # Serialize secrets
            secrets_json = json.dumps(self._secrets_cache, indent=2)
            encrypted_data = self._encryption.encrypt(secrets_json)

            # Save salt + encrypted data
            with open(self.secrets_file, "wb") as f:
                f.write(self._encryption.get_salt())
                f.write(encrypted_data)

            # Set restrictive permissions
            os.chmod(self.secrets_file, 0o600)

            logger.info("Secrets saved successfully")

        except Exception as e:
            logger.error(f"Failed to save secrets: {str(e)}")
            raise

    def set_secret(self, key: str, value: str, description: str = None) -> bool:
        """
        Set a secret value.

        Args:
            key: Secret key
            value: Secret value
            description: Optional description

        Returns:
            True if successful
        """
        try:
            current_time = datetime.now(timezone.utc).isoformat()
            self._secrets_cache[key] = {
                "value": value,
                "description": description or "",
                "created_at": current_time,
                "updated_at": current_time,
            }

            self._save_secrets()
            logger.info(f"Secret '{key}' set successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to set secret '{key}': {str(e)}")
            return False

    def get_secret(self, key: str, default: str = None) -> Optional[str]:
        """
        Get a secret value.

        Args:
            key: Secret key
            default: Default value if secret not found

        Returns:
            Secret value or default
        """
        try:
            env_value = os.getenv(key)
            if env_value:
                return env_value

            # Then check encrypted secrets
            if key in self._secrets_cache:
                return self._secrets_cache[key]["value"]

            return default

        except Exception as e:
            logger.error(f"Failed to get secret '{key}': {str(e)}")
            return default

    def delete_secret(self, key: str) -> bool:
        """
        Delete a secret.

        Args:
            key: Secret key to delete

        Returns:
            True if successful
        """
        try:
            if key in self._secrets_cache:
                del self._secrets_cache[key]
                self._save_secrets()
                logger.info(f"Secret '{key}' deleted successfully")
                return True
            else:
                logger.warning(f"Secret '{key}' not found")
                return False

        except Exception as e:
            logger.error(f"Failed to delete secret '{key}': {str(e)}")
            return False

    def list_secrets(self) -> Dict[str, Dict[str, Any]]:
        """
        List all secrets (without values).

        Returns:
            Dictionary of secret metadata
        """
        try:
            return {
                key: {
                    "description": data.get("description", ""),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "has_value": bool(data.get("value")),
                }
                for key, data in self._secrets_cache.items()
            }
        except Exception as e:
            logger.error(f"Failed to list secrets: {str(e)}")
            return {}

    def rotate_master_key(self, new_master_key: str) -> bool:
        """
        Rotate the master key.

        Args:
            new_master_key: New master key

        Returns:
            True if successful
        """
        try:
            # Create backup
            backup_file = self.secrets_file.with_suffix(".bak")
            if self.secrets_file.exists():
                import shutil

                shutil.copy2(self.secrets_file, backup_file)

            # Re-encrypt with new key
            old_secrets = self._secrets_cache.copy()
            self.master_key = new_master_key
            self._encryption = SecretsEncryption(new_master_key)
            self._secrets_cache = old_secrets
            self._save_secrets()

            logger.info("Master key rotated successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to rotate master key: {str(e)}")
            return False

    def import_from_env(self, env_vars: list) -> int:
        """
        Import secrets from environment variables.

        Args:
            env_vars: List of environment variable names to import

        Returns:
            Number of secrets imported
        """
        imported = 0

        for var_name in env_vars:
            value = os.getenv(var_name)
            if value:
                # Skip placeholder values
                if ("your_" in value.lower() or 
                    "here" in value.lower() or 
                    "placeholder" in value.lower() or
                    value == "your_deepseek_api_key_here" or
                    value == "your_handwriting_ocr_api_key_here"):
                    logger.debug(f"Skipping placeholder value for {var_name}")
                    continue
                    
                if self.set_secret(
                    var_name, value, "Imported from environment variable"
                ):
                    imported += 1

        logger.info(f"Imported {imported} secrets from environment variables")
        return imported

    def export_to_env_file(self, env_file: str = ".env.secrets") -> bool:
        """
        Export secrets to environment file format.

        Args:
            env_file: Path to environment file

        Returns:
            True if successful
        """
        try:
            with open(env_file, "w") as f:
                f.write("# Exported secrets from Exam Grader\n")
                f.write(f"# Generated at: {datetime.now(timezone.utc).isoformat()}\n\n")

                for key, data in self._secrets_cache.items():
                    description = data.get("description", "")
                    if description:
                        f.write(f"# {description}\n")
                    f.write(f"{key}={data['value']}\n\n")

            # Set restrictive permissions
            os.chmod(env_file, 0o600)

            logger.info(f"Secrets exported to {env_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to export secrets: {str(e)}")
            return False

    def validate_secrets(self, required_secrets: list) -> Dict[str, bool]:
        """
        Validate that required secrets are present.

        Args:
            required_secrets: List of required secret keys

        Returns:
            Dictionary mapping secret keys to presence status
        """
        validation_results = {}

        for secret_key in required_secrets:
            value = self.get_secret(secret_key)
            validation_results[secret_key] = bool(value)

        missing_secrets = [
            key for key, present in validation_results.items() if not present
        ]
        if missing_secrets:
            logger.warning(f"Missing required secrets: {missing_secrets}")

        return validation_results

# Global secrets manager instance
secrets_file_path = Path(__file__).parent.parent.parent / "instance" / "secrets.enc"
secrets_manager = SecretsManager(secrets_file=str(secrets_file_path))

# Initialize with common API keys
def initialize_secrets():
    """Initialize secrets manager with common API keys."""
    common_secrets = [
        "HANDWRITING_OCR_API_KEY",
        "DEEPSEEK_API_KEY",
        "SECRET_KEY",
        "DATABASE_URL",
    ]

    imported = secrets_manager.import_from_env(common_secrets)

    if imported > 0:
        logger.info(
            f"Initialized secrets manager with {imported} secrets from environment"
        )

    return secrets_manager
