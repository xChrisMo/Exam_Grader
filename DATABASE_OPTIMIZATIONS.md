# Database Optimizations for Exam Grader

This document describes the comprehensive database optimizations implemented for the Exam Grader application, including indexes, foreign key constraints, data validation rules, migration scripts, and performance monitoring.

## Overview

The database optimizations focus on:
- **Performance**: Advanced composite indexes for complex queries
- **Data Integrity**: Foreign key constraints and validation triggers
- **Monitoring**: Performance views and statistics
- **Maintainability**: Comprehensive migration system
- **Testing**: Complete model unit test coverage

## Database Schema Optimizations

### 1. Performance Indexes

#### Composite Indexes
Optimized for common query patterns:

**Users Table:**
- `idx_user_active_login`: (is_active, last_login) - Active user queries
- `idx_user_created_active`: (created_at, is_active) - User registration analytics
- `idx_user_email_verified_active`: (email_verified, is_active) - Email verification status
- `idx_user_locked_until_active`: (locked_until, is_active) - Account security queries
- `idx_user_password_changed`: (password_changed_at) - Password policy enforcement

**Marking Guides Table:**
- `idx_guide_user_active`: (user_id, is_active) - User's active guides
- `idx_guide_created_active`: (created_at, is_active) - Recent guides
- `idx_guide_hash_size`: (content_hash, file_size) - Duplicate detection
- `idx_guide_file_type_size`: (file_type, file_size) - File management
- `idx_guide_total_marks_active`: (total_marks, is_active) - Grade distribution
- `idx_guide_questions_marks`: (question_count, total_marks) - Guide complexity

**Submissions Table:**
- `idx_submission_hash_guide`: (content_hash, marking_guide_id) - Duplicate detection
- `idx_submission_status_confidence`: (processing_status, confidence_score) - Processing queue
- `idx_submission_student_guide`: (student_id, marking_guide_id) - Student submissions
- `idx_submission_archived_processed`: (is_archived, processing_status) - Archive management

**Mappings Table:**
- `idx_mapping_score`: (match_score, max_score) - Score analysis
- `idx_mapping_method`: (mapping_method) - Method performance
- `idx_mapping_submission_question`: (submission_id, question_number) - Question mapping
- `idx_mapping_score_method`: (match_score, mapping_method) - Method comparison

**Grading Results Table:**
- `idx_grading_progress_id`: (progress_id) - Progress tracking
- `idx_grading_score_confidence`: (score, confidence) - Quality analysis
- `idx_grading_method_progress`: (grading_method, progress_id) - Method tracking
- `idx_grading_percentage_method`: (percentage, grading_method) - Grade distribution

**Sessions Table:**
- `idx_session_expires`: (expires_at) - Session cleanup
- `idx_session_ip`: (ip_address) - Security monitoring
- `idx_session_user_active_expires`: (user_id, is_active, expires_at) - Active sessions
- `idx_session_ip_user_agent`: (ip_address, user_agent) - Security analysis

**Grading Sessions Table:**
- `idx_grading_session_status_step`: (status, current_step) - Workflow tracking
- `idx_grading_session_progress_status`: (progress_percentage, status) - Progress monitoring
- `idx_grading_session_user_guide`: (user_id, marking_guide_id) - User sessions
- `idx_grading_session_questions_mapped`: (total_questions, questions_mapped) - Completion tracking

### 2. Foreign Key Constraints

All relationships are properly constrained with CASCADE DELETE for data integrity:

- `marking_guides.user_id` → `users.id`
- `submissions.user_id` → `users.id`
- `submissions.marking_guide_id` → `marking_guides.id`
- `mappings.submission_id` → `submissions.id`
- `grading_results.submission_id` → `submissions.id`
- `grading_results.mapping_id` → `mappings.id`
- `sessions.user_id` → `users.id`
- `grading_sessions.submission_id` → `submissions.id`
- `grading_sessions.marking_guide_id` → `marking_guides.id`
- `grading_sessions.user_id` → `users.id`

### 3. Data Validation Rules

Implemented as SQLite triggers for runtime validation:

#### Email Format Validation
```sql
-- Validates email format using regex pattern
CREATE TRIGGER validate_user_email_format
BEFORE INSERT ON users
FOR EACH ROW
WHEN NEW.email NOT GLOB '*@*.*'
BEGIN
    SELECT RAISE(ABORT, 'Invalid email format');
END;
```

#### Status Validation
```sql
-- Validates submission processing status
CREATE TRIGGER validate_submission_status
BEFORE INSERT ON submissions
FOR EACH ROW
WHEN NEW.processing_status NOT IN ('pending', 'processing', 'completed', 'failed')
BEGIN
    SELECT RAISE(ABORT, 'Invalid processing status');
END;
```

#### Grading Session Validation
```sql
-- Validates grading session status and steps
CREATE TRIGGER validate_grading_session_status
BEFORE INSERT ON grading_sessions
FOR EACH ROW
WHEN NEW.status NOT IN ('active', 'paused', 'completed', 'cancelled')
BEGIN
    SELECT RAISE(ABORT, 'Invalid grading session status');
END;
```

### 4. Performance Monitoring Views

#### User Activity Statistics
```sql
CREATE VIEW user_activity_stats AS
SELECT 
    COUNT(*) as total_users,
    COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_users,
    COUNT(CASE WHEN email_verified = 1 THEN 1 END) as verified_users,
    COUNT(CASE WHEN locked_until > datetime('now') THEN 1 END) as locked_users,
    AVG(failed_login_attempts) as avg_failed_attempts
FROM users;
```

#### Submission Processing Statistics
```sql
CREATE VIEW submission_processing_stats AS
SELECT 
    processing_status,
    COUNT(*) as count,
    AVG(file_size) as avg_file_size,
    AVG(confidence_score) as avg_confidence
FROM submissions 
GROUP BY processing_status;
```

#### Grading Session Performance
```sql
CREATE VIEW grading_session_performance AS
SELECT 
    status,
    COUNT(*) as session_count,
    AVG(progress_percentage) as avg_progress,
    AVG(total_questions) as avg_questions,
    AVG(questions_mapped) as avg_mapped
FROM grading_sessions 
GROUP BY status;
```

## Migration System

The migration system is implemented in `src/database/schema_migrations.py` with the following migrations:

### Migration 001: Performance Indexes
Adds basic performance indexes to all tables for common query patterns.

### Migration 002: Security Enhancements
Adds security-related columns:
- `password_changed_at`
- `email_verified`
- `two_factor_enabled`

### Migration 003: Timestamp Indexes
Adds indexes on timestamp columns for temporal queries.

### Migration 004: Advanced Composite Indexes
Implements sophisticated composite indexes for complex query optimization.

### Migration 005: Data Validation Triggers
Adds SQLite triggers for runtime data validation.

### Migration 006: Performance Monitoring Views
Creates views for system performance monitoring and analytics.

## Optimization Utilities

### DatabaseOptimizer Class
Location: `src/database/optimization_utils.py`

Provides comprehensive database optimization and validation:

```python
from src.database.optimization_utils import DatabaseOptimizer

# Initialize optimizer
optimizer = DatabaseOptimizer(database_url)

# Apply all migrations
results = optimizer.apply_all_migrations()

# Generate optimization report
report = optimizer.generate_optimization_report()

# Full optimization
result = optimizer.optimize_database()
```

### Validation Methods

- `validate_indexes()`: Check index existence
- `validate_foreign_keys()`: Verify foreign key constraints
- `validate_constraints()`: Check validation triggers
- `validate_views()`: Verify performance views
- `generate_optimization_report()`: Comprehensive status report

## Scripts and Tools

### Database Initialization
```bash
# Initialize optimized database
python scripts/init_optimized_database.py

# Initialize with sample data
python scripts/init_optimized_database.py --with-sample-data
```

### Database Optimization
```bash
# Apply all optimizations
python scripts/optimize_database.py
```

### Database Validation
```bash
# Basic validation
python scripts/validate_database.py

# Verbose validation with performance tests
python scripts/validate_database.py --verbose --performance

# Save results to file
python scripts/validate_database.py --output validation_report.json
```

### Schema Migration
```bash
# Migrate existing database to optimized schema
python scripts/migrate_to_optimized_schema.py
```

## Model Unit Tests

Comprehensive unit tests are provided in the `tests/database/` directory:

- `test_user_model.py`: User model validation and relationships
- `test_marking_guide_model.py`: Marking guide functionality
- `test_submission_model.py`: Submission processing and validation
- `test_mapping_model.py`: Question mapping functionality
- `test_grading_result_model.py`: Grading results and scoring
- `test_session_model.py`: User session management
- `test_grading_session_model.py`: Grading workflow sessions

### Running Tests
```bash
# Run all database tests
pytest tests/database/ -v

# Run specific model tests
pytest tests/database/test_user_model.py -v

# Run with coverage
pytest tests/database/ --cov=src.database --cov-report=html
```

## Performance Considerations

### Query Optimization
1. **Use composite indexes** for multi-column WHERE clauses
2. **Leverage covering indexes** to avoid table lookups
3. **Monitor query execution plans** using EXPLAIN QUERY PLAN
4. **Use appropriate data types** for optimal storage and comparison

### Index Maintenance
1. **Regular ANALYZE** to update statistics
2. **Monitor index usage** with performance views
3. **Remove unused indexes** to reduce write overhead
4. **Consider partial indexes** for filtered queries

### Memory and Storage
1. **Configure SQLite cache size** appropriately
2. **Use WAL mode** for better concurrency
3. **Regular VACUUM** for storage optimization
4. **Monitor database file size** growth

## Monitoring and Maintenance

### Performance Monitoring
Use the provided performance views to monitor:
- User activity patterns
- Submission processing efficiency
- Grading session performance
- System resource utilization

### Regular Maintenance Tasks
1. **Weekly**: Run validation script
2. **Monthly**: Analyze query performance
3. **Quarterly**: Review and optimize indexes
4. **Annually**: Full database optimization review

### Troubleshooting

#### Common Issues
1. **Slow queries**: Check index usage with EXPLAIN QUERY PLAN
2. **Lock contention**: Consider WAL mode and connection pooling
3. **Storage growth**: Regular VACUUM and archive old data
4. **Validation errors**: Check trigger logic and data consistency

#### Debug Tools
```bash
# Check database integrity
python scripts/validate_database.py --verbose

# Performance analysis
python scripts/validate_database.py --performance

# Migration status
python -c "from src.database.schema_migrations import MigrationManager; print(MigrationManager().get_migration_status())"
```

## Security Considerations

### Data Protection
1. **Password hashing**: Using secure bcrypt hashing
2. **Email verification**: Enforced through database constraints
3. **Session security**: IP and user agent tracking
4. **Account locking**: Automatic lockout after failed attempts

### Access Control
1. **Foreign key constraints**: Prevent orphaned records
2. **Validation triggers**: Enforce business rules at database level
3. **Audit trails**: Timestamp tracking on all models
4. **Data integrity**: Comprehensive constraint system

## Future Enhancements

### Planned Optimizations
1. **Partitioning**: For large submission tables
2. **Read replicas**: For analytics workloads
3. **Caching layer**: Redis integration for session management
4. **Full-text search**: For content searching capabilities

### Monitoring Improvements
1. **Real-time metrics**: Performance dashboard
2. **Alerting system**: For performance degradation
3. **Automated optimization**: Self-tuning indexes
4. **Capacity planning**: Growth prediction models

This optimization framework provides a solid foundation for scalable, maintainable, and high-performance database operations in the Exam Grader application.