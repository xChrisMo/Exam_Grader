#!/usr/bin/env python3
"""
Script to change the default admin password.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def change_admin_password():
    """Change the default admin password."""
    try:
        from webapp.app import app
        from src.database.models import User, db
        from werkzeug.security import generate_password_hash
        
        with app.app_context():
            # Find the admin user
            admin_user = User.query.filter_by(username='admin').first()
            
            if not admin_user:
                print("❌ Admin user not found!")
                return
            
            # Get new password from user
            new_password = input("Enter new password for admin user: ")
            if not new_password:
                print("❌ Password cannot be empty!")
                return
            
            # Update password
            admin_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            print("✅ Admin password updated successfully!")
            print(f"Username: admin")
            print(f"New password: {new_password}")
            
    except Exception as e:
        print(f"❌ Error changing password: {e}")

if __name__ == "__main__":
    change_admin_password()
