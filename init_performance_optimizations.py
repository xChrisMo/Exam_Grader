#!/usr/bin/env python3
"""Initialize performance optimizations for the exam grader application."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from webapp.app_factory import create_app
from src.database.performance_indexes import create_performance_indexes

def main():
    """Initialize performance optimizations."""
    print("Initializing performance optimizations...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Create performance indexes
        print("Creating database indexes...")
        create_performance_indexes()
        
        print("Performance optimizations initialized successfully!")
        print("\nOptimizations applied:")
        print("✓ Database indexes for faster queries")
        print("✓ In-memory caching for frequently accessed data")
        print("✓ Optimized database queries with eager loading")
        print("✓ Removed expensive operations from context processor")
        print("✓ Performance monitoring middleware")

if __name__ == "__main__":
    main()