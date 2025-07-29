#!/usr/bin/env python3
"""
Demonstration script for the unified configuration system.

This script shows how to use the unified configuration system and its utilities.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config.unified_config import UnifiedConfig
from src.config.config_utils import ConfigurationUtils

def main():
    """Demonstrate the unified configuration system."""
    print("🔧 Exam Grader - Unified Configuration System Demo")
    print("=" * 60)
    
    # Initialize configuration
    print("\n1. Initializing Configuration...")
    config = UnifiedConfig()
    print(f"   ✓ Environment: {config.environment}")
    print(f"   ✓ Configuration loaded successfully")
    
    # Show configuration summary
    print("\n2. Configuration Summary:")
    summary = config.get_configuration_summary()
    
    print(f"   Server: {summary['server']['host']}:{summary['server']['port']}")
    print(f"   Debug: {summary['server']['debug']}")
    print(f"   Database: {summary['database']['type']}")
    print(f"   Max file size: {summary['files']['max_size_mb']}MB")
    print(f"   Supported formats: {summary['files']['supported_formats']} types")
    print(f"   OCR configured: {summary['api']['ocr_configured']}")
    print(f"   LLM configured: {summary['api']['llm_configured']}")
    print(f"   CSRF enabled: {summary['security']['csrf_enabled']}")
    print(f"   Log level: {summary['logging']['level']}")
    
    # Validate configuration
    print("\n3. Configuration Validation:")
    try:
        is_valid = config.validate()
        print(f"   ✓ Configuration is {'valid' if is_valid else 'invalid'}")
    except Exception as e:
        print(f"   ✗ Configuration validation failed: {e}")
    
    # Health check
    print("\n4. Configuration Health Check:")
    health = ConfigurationUtils.check_configuration_health(config)
    print(f"   Overall status: {health['overall_status'].upper()}")
    
    if health['issues']:
        print("   Issues:")
        for issue in health['issues']:
            print(f"     ✗ {issue}")
    
    if health['warnings']:
        print("   Warnings:")
        for warning in health['warnings']:
            print(f"     ⚠ {warning}")
    
    if health['info']:
        print("   Info:")
        for info in health['info'][:3]:  # Show first 3 info items
            print(f"     ℹ {info}")
    
    # Environment information
    print("\n5. Environment Information:")
    env_info = ConfigurationUtils.get_environment_info()
    print(f"   Python: {env_info['python_version']}")
    print(f"   Platform: {env_info['platform']}")
    print(f"   Flask environment: {env_info['flask_env']}")
    print(f"   Working directory: {env_info['cwd']}")
    
    # Flask configuration
    print("\n6. Flask Configuration Sample:")
    flask_config = config.get_flask_config()
    important_keys = ['SECRET_KEY', 'DEBUG', 'SQLALCHEMY_DATABASE_URI', 'MAX_CONTENT_LENGTH']
    
    for key in important_keys:
        if key in flask_config:
            value = flask_config[key]
            # Mask sensitive values
            if key == 'SECRET_KEY' and value:
                value = f"{value[:8]}...{value[-8:]}" if len(value) > 16 else "***"
            print(f"   {key}: {value}")
    
    # Configuration template
    print("\n7. Environment Template Generation:")
    try:
        template = config.export_environment_template(include_values=False)
        lines = template.split('\n')
        print(f"   ✓ Generated template with {len(lines)} lines")
        print("   Sample lines:")
        for line in lines[:5]:  # Show first 5 lines
            if line.strip():
                print(f"     {line}")
        print("     ...")
    except Exception as e:
        print(f"   ✗ Template generation failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Configuration system demonstration completed!")
    print("\nThe unified configuration system provides:")
    print("  • Centralized configuration management")
    print("  • Environment-specific settings")
    print("  • Automatic validation and migration")
    print("  • Health checking and monitoring")
    print("  • Flask integration")
    print("  • Configuration utilities")

if __name__ == "__main__":
    main()