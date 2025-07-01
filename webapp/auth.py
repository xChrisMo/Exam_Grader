"""
Authentication module for Exam Grader application.

This module handles user registration, login, logout, and session management
with enhanced security features.
"""

import re
from datetime import datetime

from flask import (
    Blueprint,
    flash,
    has_request_context,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from src.database.models import User, db, Session as SessionModel, MarkingGuide, Submission, GradingResult
from src.security.session_manager import SecureSessionManager
from utils.input_sanitizer import InputSanitizer
from utils.logger import logger

# Create authentication blueprint
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Initialize session manager (will be set by main app)
session_manager = None

def _update_user_data_in_session(user_id):
    """Update user data in session including submission stats and guide status."""
    try:
        # Update guide uploaded status
        remaining_guides = MarkingGuide.query.filter_by(user_id=user_id).first()
        if remaining_guides:
            session["guide_uploaded"] = True
        else:
            session["guide_uploaded"] = False
            
        # Get submission stats
        total_submissions = Submission.query.filter_by(user_id=user_id).count()
        processed_submissions = Submission.query.filter_by(
            user_id=user_id, processing_status="completed"
        ).count()
        
        # Calculate average score if there are processed submissions
        avg_score = 0
        if processed_submissions > 0:
            # Get the most recent submission
            recent_submission = Submission.query.filter_by(
                user_id=user_id, processing_status="completed"
            ).order_by(Submission.created_at.desc()).first()
            
            if recent_submission:
                # Calculate average score from grading results
                grading_results = GradingResult.query.filter_by(
                    submission_id=recent_submission.id
                ).all()
                
                if grading_results:
                    total_percentage = sum(result.percentage for result in grading_results)
                    avg_score = total_percentage / len(grading_results)
        
        # Update session with stats
        session["total_submissions"] = total_submissions
        session["processed_submissions"] = processed_submissions
        session["last_score"] = avg_score
        session.modified = True
        
        logger.info(f"Updated session data for user {user_id}: submissions={total_submissions}, processed={processed_submissions}, score={avg_score}")
    except Exception as e:
        logger.error(f"Error updating user data in session: {str(e)}")


def init_auth(app, secure_session_manager):
    """Initialize authentication module with app and session manager."""
    global session_manager
    session_manager = secure_session_manager
    app.register_blueprint(auth_bp)

    # Add context processor for user information
    @app.context_processor
    def inject_user_context():
        """Inject user context into all templates."""
        current_user = get_current_user()
        return {
            "current_user": current_user,
            "username": current_user.username if current_user else None,
            "is_authenticated": current_user is not None,
        }


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login page and handler."""
    if request.method == "GET":
        # Check if user is already logged in
        # Validate session through session manager with proper error handling
        if has_request_context() and session.sid:
            try:
                # Get both session data and database record
                session_data = session_manager.get_session(session.sid)
                session_model = SessionModel.query.get(session.sid)
                
                # Check if session is fully valid
                if session_data and session_model:
                    if session_model.is_active and not session_model.is_expired():
                        # Valid session - allow access
                        return redirect(url_for("dashboard"))
                    # Session expired or inactive - clear it
                    session_manager.invalidate_session(session.sid)
                # Clear invalid session data
                session.clear()
            except Exception as e:
                logger.error(f"Session validation error: {str(e)}")
                session.clear()

        return render_template("auth/login.html", page_title="Login")

    try:
        # Get form data
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember_me = request.form.get("remember_me") == "on"

        # Validate input
        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template(
                "auth/login.html", page_title="Login", username=username
            )

        # Sanitize username
        username = InputSanitizer.sanitize_string(username, max_length=80, strict=True)

        # Find user
        user = User.query.filter_by(username=username).first()

        if not user:
            logger.warning(f"Login attempt with non-existent username: {username}")
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html", page_title="Login")

        # Check if account is locked
        if user.is_locked():
            logger.warning(f"Login attempt on locked account: {username}")
            flash("Account is temporarily locked. Please try again later.", "error")
            return render_template("auth/login.html", page_title="Login")

        # Check if account is active
        if not user.is_active:
            logger.warning(f"Login attempt on inactive account: {username}")
            flash("Account is disabled. Please contact administrator.", "error")
            return render_template("auth/login.html", page_title="Login")

        # Verify password
        if not user.check_password(password):
            # Increment failed login attempts
            user.failed_login_attempts += 1

            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.lock_account(30)  # Lock for 30 minutes
                logger.warning(
                    f"Account locked due to failed login attempts: {username}"
                )
                flash(
                    "Too many failed login attempts. Account locked for 30 minutes.",
                    "error",
                )
            else:
                remaining_attempts = 5 - user.failed_login_attempts
                flash(
                    f"Invalid username or password. {remaining_attempts} attempts remaining.",
                    "error",
                )

            db.session.commit()
            return render_template("auth/login.html", page_title="Login")

        # Successful login
        user.failed_login_attempts = 0
        user.last_login = datetime.utcnow()
        user.unlock_account()  # Clear any lock
        db.session.commit()

        # Create new secure session with client info
        session_data = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", ""),
            "login_time": datetime.utcnow().isoformat(),
            "remember_me": remember_me
        }
        new_secure_session_id = session_manager.create_session(user.id, session_data, remember_me)
        
        # Set Flask session attributes - do this only once
        session.sid = new_secure_session_id  # This is crucial for session interface
        session["user_id"] = user.id
        session["username"] = user.username
        session["logged_in"] = True
        session.permanent = remember_me
        session.new = True  # Explicitly mark as new so save_session creates a new cookie
        session.modified = True  # Mark as modified to ensure it gets saved
        
        # Update user data in session
        _update_user_data_in_session(user.id)
        
        logger.debug(f"Flask session after login: user_id={session.get('user_id')}, session_id={session.sid}")

        logger.info(f"User logged in successfully: {username}")
        flash(f"Welcome back, {user.username}!", "success")

        # Redirect to intended page or dashboard
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("dashboard"))

    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        flash("An error occurred during login. Please try again.", "error")
        return render_template("auth/login.html", page_title="Login")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """User registration page and handler."""
    if request.method == "GET":
        # Check if user is already logged in
        if session.get("user_id"):
            return redirect(url_for("dashboard"))

        return render_template("auth/signup.html", page_title="Sign Up")

    try:
        # Get form data
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        terms_accepted = request.form.get("terms_accepted") == "on"

        # Validate input
        errors = []

        if not username:
            errors.append("Username is required.")
        elif len(username) < 3:
            errors.append("Username must be at least 3 characters long.")
        elif len(username) > 80:
            errors.append("Username must be less than 80 characters.")
        elif not all(c.isalnum() or c in ('-', '_') for c in username):
            errors.append(
                "Username can only contain letters, numbers, hyphens, and underscores."
            )

        if not email:
            errors.append("Email is required.")
        elif '@' not in email or '.' not in email or email.find('@') > email.rfind('.'):
            errors.append("Please enter a valid email address.")
        elif len(email) > 120:
            errors.append("Email must be less than 120 characters.")

        if not password:
            errors.append("Password is required.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        elif not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter.")
        elif not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter.")
        elif not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number.")
        elif not any(c in '!@#$%^&*(),.?":{}|<>' for c in password):
            errors.append("Password must contain at least one special character.")

        if password != confirm_password:
            errors.append("Passwords do not match.")

        if not terms_accepted:
            errors.append("You must accept the terms and conditions.")

        # Check for existing users
        if username and User.query.filter_by(username=username).first():
            errors.append("Username already exists. Please choose a different one.")

        if email and User.query.filter_by(email=email).first():
            errors.append(
                "Email already registered. Please use a different email or login."
            )

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "auth/signup.html", page_title="Sign Up", username=username, email=email
            )

        # Sanitize input
        username = InputSanitizer.sanitize_string(username, max_length=80, strict=True)
        email = InputSanitizer.sanitize_string(email, max_length=120, strict=True)

        # Create new user
        user = User(username=username, email=email, is_active=True)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        logger.info(f"New user registered: {username} ({email})")
        flash("Account created successfully! You can now log in.", "success")

        return redirect(url_for("auth.login"))

    except Exception as e:
        logger.error(f"Error during signup: {str(e)}")
        db.session.rollback()
        flash("An error occurred during registration. Please try again.", "error")
        return render_template("auth/signup.html", page_title="Sign Up")


@auth_bp.route("/logout")
def logout():
    """User logout handler."""
    try:
        user_id = session.get("user_id")
        session_id = session.sid
        username = session.get("username", "Unknown")

        # Invalidate secure session
        if session_id and session_manager:
            session_manager.invalidate_session(session_id)

        # Clear Flask session
        session.clear()

        logger.info(f"User logged out: {username}")
        flash("You have been logged out successfully.", "info")

        return redirect(url_for("auth.login"))

    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        session.clear()  # Clear session anyway
        return redirect(url_for("auth.login"))


@auth_bp.route("/profile")
def profile():
    """User profile page."""
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    try:
        user = User.query.get(session["user_id"])
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("auth.logout"))

        # Get user statistics
        from src.database.models import MarkingGuide, Submission

        stats = {
            "guides_created": MarkingGuide.query.filter_by(user_id=user.id).count(),
            "submissions_processed": Submission.query.filter_by(
                user_id=user.id
            ).count(),
            "account_created": user.created_at.strftime("%B %d, %Y"),
            "last_login": (
                user.last_login.strftime("%B %d, %Y at %I:%M %p")
                if user.last_login
                else "Never"
            ),
        }

        return render_template(
            "auth/profile.html", page_title="Profile", user=user, stats=stats
        )

    except Exception as e:
        logger.error(f"Error loading profile: {str(e)}")
        flash("Error loading profile. Please try again.", "error")
        return redirect(url_for("dashboard"))


@auth_bp.route("/change-password", methods=["POST"])
def change_password():
    """Change user password."""
    if not session.get("user_id"):
        return jsonify({"success": False, "error": "Not logged in"}), 401

    try:
        user = User.query.get(session["user_id"])
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate current password
        if not user.check_password(current_password):
            return (
                jsonify({"success": False, "error": "Current password is incorrect"}),
                400,
            )

        # Validate new password
        if len(new_password) < 8:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "New password must be at least 8 characters long",
                    }
                ),
                400,
            )

        if new_password != confirm_password:
            return (
                jsonify({"success": False, "error": "New passwords do not match"}),
                400,
            )

        # Update password
        user.set_password(new_password)
        db.session.commit()

        logger.info(f"Password changed for user: {user.username}")
        return jsonify({"success": True, "message": "Password changed successfully"})

    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        db.session.rollback()
        return jsonify({"success": False, "error": "Internal server error"}), 500


def get_current_user():
    """Get the current logged-in user."""
    user_id = session.get("user_id")
    if not user_id:
        return None

    try:
        user = User.query.get(user_id)
        return user
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return None


def login_required(f):
    """Decorator to require login for routes."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        session_sid = session.sid
        logger.debug(f"login_required: Checking session. user_id: {user_id}, session.sid: {session_sid}")

        if not user_id or not session_sid:
            logger.debug(
                f"login_required: Missing session data. Redirecting to login. Next URL: {request.url}"
            )
            flash("Please log in to access this page.", "warning")
            # Clear any invalid session data
            session.clear()
            return redirect(url_for("auth.login", next=request.url))
        
        try:
            # Validate secure session
            secure_session = session_manager.get_session(session_sid)
            if not secure_session or secure_session.get('user_id') != user_id:
                logger.warning(f"Invalid secure session for user {user_id}")
                session.clear()
                flash("Session invalid. Please log in again.", "warning")
                return redirect(url_for("auth.login"))
            
            return f(*args, **kwargs)
        
        except Exception as e:
            logger.error(f"Session validation error: {str(e)}")
            session.clear()
            flash("Session error. Please log in again.", "error")
            return redirect(url_for("auth.login"))

    return decorated_function
