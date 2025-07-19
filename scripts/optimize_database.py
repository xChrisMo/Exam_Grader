#!/usr/bin/env python3
"""Standalone database optimization script."""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.optimization_utils import DatabaseOptimizer
from src.config.unified_config import Config

def main():
    """Main optimization function."""
    config = Config()
    database_url = config.get_database_url()
    
    optimizer = DatabaseOptimizer(database_url)
    
    print("Starting database optimization...")
    result = optimizer.optimize_database()
    
    print("\nOptimization Results:")
    print(json.dumps(result, indent=2, default=str))
    
    if result['success']:
        print("\n✅ Database optimization completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️  Database optimization completed with issues.")
        sys.exit(1)

if __name__ == "__main__":
    main()