"""
Authentication Routes

This module handles user authentication, registration, and session management.
"""

import time

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from src.database.models import User, db
from utils.logger import logger

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        try:
            # Check CSRF token first
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except Exception as csrf_error:
                logger.warning(f"CSRF validation failed for login: {csrf_error}")
                flash("Security validation failed. Please refresh the page and try again.", "error")
                return render_template("auth/login.html")

            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            remember = bool(request.form.get("remember"))

            if not username or not password:
                flash("Username and password are required", "error")
                return render_template("auth/login.html")

            # Find user with optimized query
            user = User.query.filter_by(username=username).first()

            if not user:
                # Add small delay to prevent timing attacks
                time.sleep(0.1)
                flash("Invalid username or password", "error")
                return render_template("auth/login.html")

            if user.is_locked():
                flash("Account is temporarily locked. Please try again later.", "error")
                return render_template("auth/login.html")

            # Verify password
            if not user.check_password(password):
                # Increment failed attempts
                user.failed_login_attempts += 1

                # Lock account after 5 failed attempts
                if user.failed_login_attempts >= 5:
                    user.lock_account(30)  # Lock for 30 minutes
                    flash(
                        "Too many failed attempts. Account locked for 30 minutes.",
                        "error",
                    )
                else:
                    remaining = 5 - user.failed_login_attempts
                    flash(f"Invalid password. {remaining} attempts remaining.", "error")

                db.session.commit()
                return render_template("auth/login.html")

            # Successful login
            user.failed_login_attempts = 0
            user.last_login = db.func.now()
            db.session.commit()

            login_user(user, remember=remember)

            # Redirect to next page or dashboard
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)

            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("main.dashboard"))

        except Exception as e:
            logger.error(f"Login error: {e}")
            flash("Login failed. Please try again.", "error")
            return render_template("auth/login.html")

    return render_template("auth/login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration."""
    return signup()

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        try:
            # Check CSRF token first
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except Exception as csrf_error:
                logger.warning(f"CSRF validation failed for signup: {csrf_error}")
                flash("Security validation failed. Please refresh the page and try again.", "error")
                return render_template("auth/signup.html")

            # Check database connectivity
            try:
                # Test database connection
                from sqlalchemy import text
                db.session.execute(text('SELECT 1'))
            except Exception as db_error:
                logger.error(f"Database connection failed during signup: {db_error}")
                flash("Database connection error. Please try again later.", "error")
                return render_template("auth/signup.html")

            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            # Validation
            if not all([username, email, password, confirm_password]):
                flash("All fields are required", "error")
                return render_template("auth/signup.html")

            if len(username) < 3:
                flash("Username must be at least 3 characters long", "error")
                return render_template("auth/signup.html")

            if len(password) < 8:
                flash("Password must be at least 8 characters long", "error")
                return render_template("auth/signup.html")

            if password != confirm_password:
                flash("Passwords do not match", "error")
                return render_template("auth/signup.html")

            if User.query.filter_by(username=username).first():
                flash("Username already exists", "error")
                return render_template("auth/signup.html")

            if User.query.filter_by(email=email).first():
                flash("Email already registered", "error")
                return render_template("auth/signup.html")

            # Create new user with proper ID generation
            import uuid
            user_id = str(uuid.uuid4())
            
            user = User(
                id=user_id,
                username=username, 
                email=email
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            logger.info(f"User registered successfully: {username} ({user_id})")
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("auth.login"))

        except Exception as e:
            logger.error(f"Registration error: {e}", exc_info=True)
            try:
                db.session.rollback()
            except Exception as rollback_error:
                logger.error(f"Database rollback failed: {rollback_error}")
            
            # Provide more specific error messages
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e).lower():
                if "username" in str(e).lower():
                    flash("Username already exists. Please choose a different username.", "error")
                elif "email" in str(e).lower():
                    flash("Email already registered. Please use a different email address.", "error")
                else:
                    flash("Username or email already exists. Please try different values.", "error")
            elif "database" in str(e).lower() or "connection" in str(e).lower():
                flash("Database connection error. Please try again later.", "error")
            else:
                flash("Registration failed. Please try again.", "error")
            
            return render_template("auth/signup.html")

    return render_template("auth/signup.html")

@auth_bp.route("/logout")
@login_required
def logout():
    """User logout."""
    try:
        username = current_user.username
        logout_user()
        flash(f"Goodbye, {username}!", "info")

    except Exception as e:
        logger.error(f"Logout error: {e}")
        flash("Logout completed", "info")

    return redirect(url_for("main.index"))

@auth_bp.route("/profile")
@login_required
def profile():
    """User profile page."""
    return render_template("auth/profile.html")

@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change user password."""
    if request.method == "POST":
        try:
            # Check CSRF token first
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except Exception as csrf_error:
                logger.warning(f"CSRF validation failed for change password: {csrf_error}")
                flash("Security validation failed. Please refresh the page and try again.", "error")
                return render_template("auth/change_password.html")

            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            # Validation
            if not all([current_password, new_password, confirm_password]):
                flash("All fields are required", "error")
                return render_template("auth/change_password.html")

            if not current_user.check_password(current_password):
                flash("Current password is incorrect", "error")
                return render_template("auth/change_password.html")

            if len(new_password) < 8:
                flash("New password must be at least 8 characters long", "error")
                return render_template("auth/change_password.html")

            if new_password != confirm_password:
                flash("New passwords do not match", "error")
                return render_template("auth/change_password.html")

            # Update password
            current_user.set_password(new_password)
            db.session.commit()

            flash("Password changed successfully", "success")
            return redirect(url_for("auth.profile"))

        except Exception as e:
            logger.error(f"Password change error: {e}")
            db.session.rollback()
            flash("Failed to change password", "error")
            return render_template("auth/change_password.html")

    return render_template("auth/change_password.html")
