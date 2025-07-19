#!/usr/bin/env python3
"""Database initialization script for optimized models.

This script initializes a fresh database with the optimized schema,
applies all migrations, and sets up initial data if needed.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from src.database.optimized_models import db, User, MarkingGuide
from src.database.schema_migrations import MigrationManager
from src.database.optimization_utils import DatabaseOptimizer
from src.config.unified_config import UnifiedConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_database_tables(engine):
    """Create all database tables.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    logger.info("Creating database tables...")
    
    try:
        # Create all tables
        db.metadata.create_all(engine)
        logger.info("Database tables created successfully")
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Created tables: {', '.join(tables)}")
        
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def apply_migrations(database_url):
    """Apply all database migrations using the optimization utilities.
    
    Args:
        database_url: Database connection URL
    """
    logger.info("Applying database migrations...")
    
    try:
        # Use the new DatabaseOptimizer for comprehensive migration handling
        optimizer = DatabaseOptimizer(database_url)
        
        # Apply all migrations
        migration_results = optimizer.apply_all_migrations()
        
        # Check results
        failed_migrations = [version for version, success in migration_results.items() if not success]
        
        if failed_migrations:
            logger.error(f"Failed migrations: {failed_migrations}")
            raise Exception(f"Migrations failed: {failed_migrations}")
        
        logger.info(f"Successfully applied {len(migration_results)} migrations")
        
        # Generate optimization report
        report = optimizer.generate_optimization_report()
        
        if report['recommendations']:
            logger.info("Optimization recommendations:")
            for rec in report['recommendations']:
                if "fully optimized" in rec:
                    logger.info(f"✓ {rec}")
                else:
                    logger.warning(f"⚠ {rec}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


def create_admin_user(engine):
    """Create an admin user if it doesn't exist.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    logger.info("Checking for admin user...")
    
    try:
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if admin user exists
        admin_user = session.query(User).filter_by(username='admin').first()
        
        if not admin_user:
            logger.info("Creating admin user...")
            
            admin_user = User(
                username='admin',
                email='admin@examgrader.local'
            )
            admin_user.set_password('admin123')  # Default password - should be changed
            
            session.add(admin_user)
            session.commit()
            
            logger.info("Admin user created successfully")
            logger.warning("Default admin password is 'admin123' - please change it!")
        else:
            logger.info("Admin user already exists")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        raise


def verify_database_integrity(database_url):
    """Verify database integrity and constraints using optimization utilities.
    
    Args:
        database_url: Database connection URL
    """
    logger.info("Verifying database integrity...")
    
    try:
        # Use DatabaseOptimizer for comprehensive validation
        optimizer = DatabaseOptimizer(database_url)
        
        # Generate comprehensive optimization report
        report = optimizer.generate_optimization_report()
        
        logger.info("Database Integrity Report:")
        logger.info("=" * 40)
        
        # Check indexes
        if report['indexes']['existing']:
            logger.info(f"✓ Found {len(report['indexes']['existing'])} indexes")
            for idx in report['indexes']['existing'][:5]:  # Show first 5
                logger.info(f"  - {idx}")
            if len(report['indexes']['existing']) > 5:
                logger.info(f"  ... and {len(report['indexes']['existing']) - 5} more")
        
        if report['indexes']['missing']:
            logger.warning(f"⚠ Missing {len(report['indexes']['missing'])} indexes")
            for idx in report['indexes']['missing']:
                logger.warning(f"  - {idx}")
        
        # Check foreign keys
        if report['foreign_keys']['existing']:
            logger.info(f"✓ Found {len(report['foreign_keys']['existing'])} foreign keys")
        
        if report['foreign_keys']['missing']:
            logger.warning(f"⚠ Missing {len(report['foreign_keys']['missing'])} foreign keys")
            for fk in report['foreign_keys']['missing']:
                logger.warning(f"  - {fk}")
        
        # Check constraints (triggers)
        if report['constraints']['existing']:
            logger.info(f"✓ Found {len(report['constraints']['existing'])} validation triggers")
        
        if report['constraints']['missing']:
            logger.warning(f"⚠ Missing {len(report['constraints']['missing'])} validation triggers")
            for constraint in report['constraints']['missing']:
                logger.warning(f"  - {constraint}")
        
        # Check views
        if report['views']['existing']:
            logger.info(f"✓ Found {len(report['views']['existing'])} performance views")
        
        if report['views']['missing']:
            logger.warning(f"⚠ Missing {len(report['views']['missing'])} performance views")
            for view in report['views']['missing']:
                logger.warning(f"  - {view}")
        
        # Overall status
        if not any([report['indexes']['missing'], report['foreign_keys']['missing'], 
                   report['constraints']['missing'], report['views']['missing']]):
            logger.info("✅ Database is fully optimized!")
        else:
            logger.warning("⚠️  Database has optimization opportunities")
        
        logger.info("Database integrity verification completed")
        
    except Exception as e:
        logger.error(f"Database integrity check failed: {e}")
        raise


def initialize_sample_data(engine):
    """Initialize sample data for testing (optional).
    
    Args:
        engine: SQLAlchemy engine instance
    """
    logger.info("Initializing sample data...")
    
    try:
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if sample data already exists
        sample_guide = session.query(MarkingGuide).filter_by(title='Sample Marking Guide').first()
        
        if not sample_guide:
            # Get admin user
            admin_user = session.query(User).filter_by(username='admin').first()
            
            if admin_user:
                # Create sample marking guide
                sample_guide = MarkingGuide(
                    user_id=admin_user.id,
                    title='Sample Marking Guide',
                    description='A sample marking guide for testing purposes',
                    filename='sample_guide.pdf',
                    file_path='/uploads/sample_guide.pdf',
                    file_size=1024,
                    file_type='application/pdf',
                    content_text='Sample marking guide content',
                    total_marks=100.0,
                    questions={
                        'q1': {
                            'text': 'What is the capital of France?',
                            'answer': 'Paris',
                            'marks': 10
                        },
                        'q2': {
                            'text': 'Explain the concept of inheritance in OOP.',
                            'answer': 'Inheritance allows a class to inherit properties and methods from another class.',
                            'marks': 20
                        }
                    }
                )
                sample_guide.generate_content_hash()
                
                session.add(sample_guide)
                session.commit()
                
                logger.info("Sample data created successfully")
            else:
                logger.warning("Admin user not found - skipping sample data creation")
        else:
            logger.info("Sample data already exists")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Failed to initialize sample data: {e}")
        # Don't raise - sample data is optional


def main():
    """Main initialization function."""
    logger.info("=" * 60)
    logger.info("Initializing Exam Grader Optimized Database")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        config = UnifiedConfig()
        
        # Create database engine
        engine = create_engine(config.database.database_url, echo=False)
        logger.info(f"Connected to database: {config.database.database_url}")
        
        # Step 1: Create tables
        create_database_tables(engine)
        
        # Step 2: Apply migrations
        apply_migrations(config.database.database_url)
        
        # Step 3: Create admin user
        create_admin_user(engine)
        
        # Step 4: Verify database integrity
        verify_database_integrity(config.DATABASE_URL)
        
        # Step 5: Initialize sample data (optional)
        if '--with-sample-data' in sys.argv:
            initialize_sample_data(engine)
        
        logger.info("=" * 60)
        logger.info("Database initialization completed successfully!")
        logger.info("=" * 60)
        
        # Print usage information
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Change the default admin password")
        logger.info("2. Configure your application settings")
        logger.info("3. Start the application")
        logger.info("")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()