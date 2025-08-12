#!/usr/bin/env python3
"""Clear application cache to ensure fresh data after optimizations."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.cache_service import app_cache

def main():
    """Clear all cached data."""
    print("Clearing application cache...")
    
    # Clear all cache entries
    app_cache.clear()
    
    print("✅ Cache cleared successfully!")
    print("All cached data has been removed. Fresh data will be loaded on next page visit.")

if __name__ == "__main__":
    main()