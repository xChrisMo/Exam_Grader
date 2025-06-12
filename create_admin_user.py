#!/usr/bin/env python3
"""
Create Admin User Script for Exam Grader Application.

This script creates the default admin user for the application.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv("instance/.env", override=True)

def create_admin_user():
    """Create the default admin user."""
    try:
        print("🔧 Creating admin user...")
        
        # Import required modules
        from flask import Flask
        from src.config.unified_config import config
        from src.database import db, User, DatabaseUtils
        from werkzeug.security import generate_password_hash
        import secrets
        import string
        
        # Create Flask app
        app = Flask(__name__)
        app.config.update(config.get_flask_config())
        db.init_app(app)
        
        with app.app_context():
            # Check if admin user already exists
            admin_user = User.query.filter_by(username='admin').first()
            
            if admin_user:
                print("✅ Admin user already exists")
                print(f"   Username: {admin_user.username}")
                print(f"   Email: {admin_user.email}")
                print(f"   Active: {admin_user.is_active}")
                return True
            
            # Generate secure random password
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            random_password = ''.join(secrets.choice(alphabet) for _ in range(16))
            
            # Create admin user
            admin_user = User(
                username='admin',
                email='admin@examgrader.local',
                password_hash=generate_password_hash(random_password),
                is_active=True
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("✅ Admin user created successfully!")
            print("\n" + "=" * 60)
            print("IMPORTANT SECURITY NOTICE:")
            print("=" * 60)
            print(f"Default admin username: admin")
            print(f"Default admin password: {random_password}")
            print("Please change this password immediately after first login!")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"❌ Failed to create admin user: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def check_database():
    """Check database status."""
    try:
        print("🔍 Checking database...")
        
        from flask import Flask
        from src.config.unified_config import config
        from src.database import db, User
        from sqlalchemy import inspect
        
        # Create Flask app
        app = Flask(__name__)
        app.config.update(config.get_flask_config())
        db.init_app(app)
        
        with app.app_context():
            # Check tables
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✅ Tables found: {', '.join(tables)}")
            
            if 'users' in tables:
                user_count = User.query.count()
                print(f"✅ Users in database: {user_count}")
                
                if user_count > 0:
                    users = User.query.all()
                    for user in users:
                        print(f"   - {user.username} ({user.email}) - Active: {user.is_active}")
                else:
                    print("   No users found")
            else:
                print("❌ Users table not found")
                
        return True
        
    except Exception as e:
        print(f"❌ Database check failed: {str(e)}")
        return False


def main():
    """Main entry point."""
    print("👤 ADMIN USER CREATION UTILITY")
    print("=" * 40)
    
    # Check database first
    if not check_database():
        print("❌ Database check failed")
        sys.exit(1)
    
    # Create admin user
    if create_admin_user():
        print("\n🎉 Admin user setup completed!")
        print("\nYou can now log in to the application with:")
        print("  Username: admin")
        print("  Password: (see above)")
    else:
        print("❌ Failed to create admin user")
        sys.exit(1)


if __name__ == "__main__":
    main()
