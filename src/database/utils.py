"""
Database utilities for the Exam Grader application.
"""

import logging
import secrets
import string
from datetime import datetime
from typing import Any, Dict
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)


class DatabaseUtils:
    """Utility class for database operations."""
    
    @staticmethod
    def create_default_user() -> bool:
        """Create default admin user if it doesn't exist."""
        try:
            from .models import User, db

            admin_user = User.query.filter_by(username='admin').first()

            if admin_user:
                logger.info("Default admin user already exists")
                return True

            # Generate secure random password
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            random_password = ''.join(secrets.choice(alphabet) for _ in range(16))

            admin_user = User(
                username='admin',
                email='admin@examgrader.local',
                password_hash=generate_password_hash(random_password),
                is_active=True
            )

            db.session.add(admin_user)
            db.session.commit()

            logger.info("Default admin user created successfully")
            logger.warning(f"IMPORTANT: Default admin password is: {random_password}")
            logger.warning("Please change this password immediately after first login!")
            print(f"\n{'='*60}")
            print("IMPORTANT SECURITY NOTICE:")
            print(f"Default admin username: admin")
            print(f"Default admin password: {random_password}")
            print("Please change this password immediately after first login!")
            print(f"{'='*60}\n")
            return True

        except Exception as e:
            logger.error(f"Failed to create default user: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
            return False
    
    @staticmethod
    def get_database_stats() -> Dict[str, Any]:
        """Get database statistics."""
        try:
            from .models import User, MarkingGuide, Submission, GradingResult
            
            stats = {
                'users': User.query.count(),
                'marking_guides': MarkingGuide.query.count(),
                'submissions': Submission.query.count(),
                'grading_results': GradingResult.query.count()
            }
            stats['total_records'] = sum(stats.values())
            stats['last_updated'] = datetime.now().isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {
                'users': 0,
                'marking_guides': 0,
                'submissions': 0,
                'grading_results': 0,
                'total_records': 0,
                'last_updated': datetime.now().isoformat(),
                'error': str(e)
            }
    
    @staticmethod
    def validate_user_data(username: str, email: str, password: str) -> Dict[str, Any]:
        """Validate user data for creation/update."""
        errors = []
        
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters long")
        elif len(username) > 80:
            errors.append("Username must be less than 80 characters")
        
        if not email or '@' not in email:
            errors.append("Valid email address is required")
        elif len(email) > 120:
            errors.append("Email must be less than 120 characters")
        
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters long")
        
        try:
            from .models import User
            
            existing_username = User.query.filter_by(username=username).first()
            if existing_username:
                errors.append("Username already exists")
                
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                errors.append("Email already exists")
                
        except Exception as e:
            logger.warning(f"Error checking existing users: {str(e)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
