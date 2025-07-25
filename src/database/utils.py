"""
Database utilities for the Exam Grader application.
"""

import logging
import secrets
import string
from datetime import datetime
from typing import Any, Dict, List, Optional
from werkzeug.security import generate_password_hash

# Import performance optimization tools
try:
    from src.performance.query_cache import cached_query, monitor_performance
    PERFORMANCE_TOOLS_AVAILABLE = True
except ImportError:
    PERFORMANCE_TOOLS_AVAILABLE = False
    # Fallback decorators that do nothing
    def cached_query(timeout=300, key_prefix=""):
        def decorator(func):
            return func
        return decorator

    def monitor_performance(log_slow_queries=True, slow_threshold=1.0):
        def decorator(func):
            return func
        return decorator

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
            
            # Log security notice with high visibility
            security_notice = f"\n{'=' * 60}\nIMPORTANT SECURITY NOTICE:\nDefault admin username: admin\nDefault admin password: {random_password}\nPlease change this password immediately after first login!\n{'=' * 60}\n"
            logger.critical(security_notice)
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

    @staticmethod
    @cached_query(timeout=300, key_prefix="user_")
    @monitor_performance(slow_threshold=0.5)
    def get_user_by_id(user_id: str) -> Optional[Any]:
        """Get user by ID with caching."""
        try:
            from .models import User
            return User.query.filter_by(id=user_id).first()
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            return None

    @staticmethod
    @cached_query(timeout=600, key_prefix="guide_")
    @monitor_performance(slow_threshold=0.5)
    def get_active_marking_guides(user_id: str) -> List[Any]:
        """Get active marking guides for user with caching."""
        try:
            from .models import MarkingGuide
            return MarkingGuide.query.filter_by(
                user_id=user_id,
                is_active=True
            ).order_by(MarkingGuide.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting marking guides for user {user_id}: {str(e)}")
            return []

    @staticmethod
    @cached_query(timeout=300, key_prefix="submission_")
    @monitor_performance(slow_threshold=1.0)
    def get_submissions_by_status(user_id: str, status: str) -> List[Any]:
        """Get submissions by status with caching."""
        try:
            from .models import Submission
            return Submission.query.filter_by(
                user_id=user_id,
                processing_status=status
            ).order_by(Submission.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting submissions for user {user_id}, status {status}: {str(e)}")
            return []

    @staticmethod
    @monitor_performance(slow_threshold=2.0)
    def bulk_update_submission_status(submission_ids: List[str], new_status: str) -> bool:
        """Bulk update submission status for better performance."""
        try:
            from .models import Submission, db

            # Use bulk update for better performance
            updated = Submission.query.filter(
                Submission.id.in_(submission_ids)
            ).update(
                {Submission.processing_status: new_status},
                synchronize_session=False
            )

            db.session.commit()
            logger.info(f"Bulk updated {updated} submissions to status {new_status}")
            return True

        except Exception as e:
            logger.error(f"Error bulk updating submissions: {str(e)}")
            return False

    @staticmethod
    def clear_user_cache(user_id: str) -> None:
        """Clear cached data for a specific user."""
        if PERFORMANCE_TOOLS_AVAILABLE:
            from src.performance.query_cache import invalidate_cache_pattern
            invalidate_cache_pattern(f"user_{user_id}")
            invalidate_cache_pattern(f"guide_{user_id}")
            invalidate_cache_pattern(f"submission_{user_id}")
            logger.debug(f"Cleared cache for user {user_id}")
