"""
Database URL fix for Heroku PostgreSQL compatibility.
"""
import os

def fix_database_url():
    """Fix DATABASE_URL for SQLAlchemy 2.0+ compatibility."""
    database_url = os.getenv('DATABASE_URL', '')
    if database_url.startswith('postgres://'):
        # Convert postgres:// to postgresql:// for SQLAlchemy 2.0+ compatibility
        fixed_url = database_url.replace('postgres://', 'postgresql://', 1)
        os.environ['DATABASE_URL'] = fixed_url
        return fixed_url
    return database_url
