"""
Database package for the Exam Grader application.

This package provides database models, migrations, and utilities for
persistent data storage replacing the session-based storage system.

Components:
- Models: SQLAlchemy ORM models for all application entities
- Migrations: Alembic-based database migration system
- Utilities: Helper functions for common database operations
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize SQLAlchemy instance
db = SQLAlchemy()

class MigrationManager:
    """Handles database migrations using Alembic."""
    
    def __init__(self, app):
        """Initialize migration manager with Flask application."""
        self.migrate = Migrate(app, db)
    
    def init_migrations(self):
        """Initialize migrations directory."""
        # Typically handled by Flask-Migrate CLI commands
        pass
    
    def migrate_database(self):
        """Run database migrations."""
        # Typically handled by Flask-Migrate CLI commands
        pass
    
    def upgrade_database(self):
        """Upgrade database to latest version."""
        # Typically handled by Flask-Migrate CLI commands
        pass

class User(db.Model):
    """User model representing application users."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='grader')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), 
                          onupdate=db.func.now())
    
    sessions = db.relationship('Session', backref='user', lazy=True)
    submissions = db.relationship('Submission', backref='user', lazy=True)

class MarkingGuide(db.Model):
    """Marking guide model containing grading criteria."""
    
    __tablename__ = 'marking_guides'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    max_score = db.Column(db.Integer, nullable=False)
    criteria = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), 
                          onupdate=db.func.now())
    
    sessions = db.relationship('Session', backref='marking_guide', lazy=True)

class Submission(db.Model):
    """Student submission model."""
    
    __tablename__ = 'submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    exam_id = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    submitted_at = db.Column(db.DateTime, server_default=db.func.now())
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    grading_results = db.relationship('GradingResult', backref='submission', lazy=True)

class Session(db.Model):
    """Grading session model."""
    
    __tablename__ = 'sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    closed_at = db.Column(db.DateTime)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    marking_guide_id = db.Column(db.Integer, db.ForeignKey('marking_guides.id'), nullable=False)
    submissions = db.relationship('Submission', backref='session', lazy=True)
    mappings = db.relationship('Mapping', backref='session', lazy=True)

class Mapping(db.Model):
    """Mapping between questions and marking guide criteria."""
    
    __tablename__ = 'mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    question_number = db.Column(db.Integer, nullable=False)
    criteria_key = db.Column(db.String(50), nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    grading_results = db.relationship('GradingResult', backref='mapping', lazy=True)

class GradingResult(db.Model):
    """Result of grading a specific question in a submission."""
    
    __tablename__ = 'grading_results'
    
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Float, nullable=False)
    comments = db.Column(db.Text)
    graded_at = db.Column(db.DateTime, server_default=db.func.now())
    
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False)
    mapping_id = db.Column(db.Integer, db.ForeignKey('mappings.id'), nullable=False)

class DatabaseUtils:
    """Utility class for common database operations."""
    
    @staticmethod
    def init_app(app):
        """Initialize database with Flask application."""
        db.init_app(app)
        return MigrationManager(app)
    
    @staticmethod
    def create_all():
        """Create all database tables."""
        db.create_all()
    
    @staticmethod
    def drop_all():
        """Drop all database tables."""
        db.drop_all()
    
    @staticmethod
    def add_user(username, email, password_hash, role='grader'):
        """Add a new user to the database."""
        user = User(username=username, email=email, 
                   password_hash=password_hash, role=role)
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def get_user_by_username(username):
        """Retrieve a user by username."""
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def get_active_sessions(user_id):
        """Get active sessions for a user."""
        return Session.query.filter_by(user_id=user_id, status='active').all()

# Export all public classes and instances
__all__ = [
    "db",
    "User",
    "MarkingGuide",
    "Submission",
    "Mapping",
    "GradingResult",
    "Session",
    "MigrationManager",
    "DatabaseUtils",
]