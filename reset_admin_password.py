#!/usr/bin/env python3
"""
Reset admin password to a known value for testing.
"""

import os
import sys
from werkzeug.security import generate_password_hash

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def reset_admin_password():
    """Reset admin password to 'admin123' for testing."""
    try:
        from flask import Flask
        from src.config.unified_config import config
        from src.database import db, User
        
        # Create Flask app
        app = Flask(__name__)
        app.config.update(config.get_flask_config())
        db.init_app(app)
        
        with app.app_context():
            # Find admin user
            admin_user = User.query.filter_by(username='admin').first()
            
            if admin_user:
                # Reset password to 'admin123'
                new_password = 'admin123'
                admin_user.password_hash = generate_password_hash(new_password)
                admin_user.is_active = True
                admin_user.failed_login_attempts = 0
                admin_user.locked_until = None
                
                db.session.commit()
                
                print("✅ Admin password reset successfully!")
                print(f"   Username: admin")
                print(f"   Password: {new_password}")
                print(f"   Email: {admin_user.email}")
                
                return True
            else:
                print("❌ Admin user not found")
                return False
                
    except Exception as e:
        print(f"❌ Password reset failed: {str(e)}")
        return False

if __name__ == '__main__':
    print("🔧 Resetting admin password...")
    success = reset_admin_password()
    sys.exit(0 if success else 1)