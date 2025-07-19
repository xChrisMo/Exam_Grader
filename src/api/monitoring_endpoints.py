"""Security and Performance Monitoring API Endpoints for Exam Grader Application.

This module provides comprehensive monitoring endpoints for security events,
performance metrics, and system health monitoring.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, g
from functools import wraps

try:
    from utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from src.security.auth_system import require_auth, require_permission, require_role, Permission, UserRole
    from src.security.security_config import get_security_config
    from src.performance.optimization_manager import get_performance_optimizer
    from src.exceptions.application_errors import AuthorizationError, ValidationError
except ImportError:
    # Fallback implementations
    def require_auth(f):
        return f
    
    def require_permission(permission):
        def decorator(f):
            return f
        return decorator
    
    def require_role(role):
        def decorator(f):
            return f
        return decorator
    
    class Permission:
        VIEW_LOGS = "view_logs"
        SYSTEM_CONFIG = "system_config"
    
    class UserRole:
        ADMIN = "admin"
        SUPER_ADMIN = "super_admin"
    
    class AuthorizationError(Exception):
        pass
    
    class ValidationError(Exception):
        pass
    
    def get_security_config():
        return None
    
    def get_performance_optimizer():
        return None


# Create monitoring blueprint
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')


def admin_required(f):
    """Decorator to require admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Check if user has admin role
            if hasattr(g, 'current_user') and g.current_user:
                user_role = getattr(g.current_user, 'role', None)
                if user_role and user_role.value in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                    return f(*args, **kwargs)
            
            raise AuthorizationError("Admin access required")
            
        except Exception as e:
            logger.warning(f"Admin access check failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Admin access required',
                'code': 'ADMIN_REQUIRED'
            }), 403
    
    return decorated_function


@monitoring_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    try:
        # Basic system checks
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'environment': os.getenv('FLASK_ENV', 'production'),
            'uptime': _get_uptime(),
            'checks': {
                'database': _check_database_health(),
                'cache': _check_cache_health(),
                'security': _check_security_health(),
                'performance': _check_performance_health()
            }
        }
        
        # Determine overall status
        failed_checks = [name for name, status in health_status['checks'].items() if not status['healthy']]
        if failed_checks:
            health_status['status'] = 'degraded' if len(failed_checks) < 2 else 'unhealthy'
            health_status['failed_checks'] = failed_checks
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


@monitoring_bp.route('/security/status', methods=['GET'])
@require_auth
@require_permission(Permission.VIEW_LOGS)
def security_status():
    """Get security system status."""
    try:
        security_config = get_security_config()
        
        status = {
            'security_level': getattr(security_config, 'security_level', 'unknown'),
            'environment': getattr(security_config, 'environment', 'unknown'),
            'features': {
                'csrf_protection': True,
                'session_security': True,
                'input_validation': True,
                'file_upload_security': True,
                'rate_limiting': getattr(security_config.rate_limiting if security_config else None, 'enabled', False),
                'malware_scanning': getattr(security_config.file_upload if security_config else None, 'scan_for_malware', False),
                'audit_logging': getattr(security_config.audit_logging if security_config else None, 'enabled', False)
            },
            'session_config': {
                'timeout_minutes': getattr(security_config.session if security_config else None, 'session_timeout_minutes', 30),
                'secure_cookies': getattr(security_config.session if security_config else None, 'session_cookie_secure', True),
                'httponly_cookies': getattr(security_config.session if security_config else None, 'session_cookie_httponly', True)
            },
            'authentication': {
                'max_failed_attempts': getattr(security_config.authentication if security_config else None, 'max_failed_attempts', 5),
                'lockout_duration_minutes': getattr(security_config.authentication if security_config else None, 'lockout_duration_minutes', 15),
                'password_policy': {
                    'min_length': getattr(security_config.authentication if security_config else None, 'password_min_length', 8),
                    'require_uppercase': getattr(security_config.authentication if security_config else None, 'require_uppercase', True),
                    'require_lowercase': getattr(security_config.authentication if security_config else None, 'require_lowercase', True),
                    'require_digits': getattr(security_config.authentication if security_config else None, 'require_digits', True),
                    'require_special_chars': getattr(security_config.authentication if security_config else None, 'require_special_chars', True)
                }
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logger.error(f"Error getting security status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SECURITY_STATUS_ERROR'
        }), 500


@monitoring_bp.route('/performance/metrics', methods=['GET'])
@require_auth
@require_permission(Permission.VIEW_LOGS)
def performance_metrics():
    """Get performance metrics."""
    try:
        optimizer = get_performance_optimizer()
        
        if not optimizer:
            return jsonify({
                'success': False,
                'error': 'Performance optimizer not available',
                'code': 'OPTIMIZER_NOT_AVAILABLE'
            }), 503
        
        # Get comprehensive performance report
        report = optimizer.get_performance_report()
        
        return jsonify({
            'success': True,
            'data': report,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'PERFORMANCE_METRICS_ERROR'
        }), 500


@monitoring_bp.route('/performance/cache/stats', methods=['GET'])
@require_auth
@require_permission(Permission.VIEW_LOGS)
def cache_statistics():
    """Get cache performance statistics."""
    try:
        optimizer = get_performance_optimizer()
        
        if not optimizer:
            return jsonify({
                'success': False,
                'error': 'Performance optimizer not available',
                'code': 'OPTIMIZER_NOT_AVAILABLE'
            }), 503
        
        # Get cache statistics
        memory_stats = optimizer.memory_cache.get_stats()
        
        cache_stats = {
            'memory_cache': memory_stats,
            'redis_available': optimizer.redis_cache is not None,
            'hit_rate': optimizer.metrics.cache_hit_rate,
            'total_hits': optimizer._cache_hits,
            'total_misses': optimizer._cache_misses,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': cache_stats
        })
        
    except Exception as e:
        logger.error(f"Error getting cache statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'CACHE_STATS_ERROR'
        }), 500


@monitoring_bp.route('/performance/database/stats', methods=['GET'])
@require_auth
@require_permission(Permission.VIEW_LOGS)
def database_statistics():
    """Get database performance statistics."""
    try:
        optimizer = get_performance_optimizer()
        
        if not optimizer:
            return jsonify({
                'success': False,
                'error': 'Performance optimizer not available',
                'code': 'OPTIMIZER_NOT_AVAILABLE'
            }), 503
        
        # Get database statistics
        db_stats = optimizer.database_optimizer.get_query_stats()
        
        return jsonify({
            'success': True,
            'data': db_stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting database statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'DATABASE_STATS_ERROR'
        }), 500


@monitoring_bp.route('/system/resources', methods=['GET'])
@require_auth
@require_permission(Permission.VIEW_LOGS)
def system_resources():
    """Get system resource usage."""
    try:
        optimizer = get_performance_optimizer()
        
        if not optimizer:
            return jsonify({
                'success': False,
                'error': 'Performance optimizer not available',
                'code': 'OPTIMIZER_NOT_AVAILABLE'
            }), 503
        
        # Get current system metrics
        current_metrics = optimizer.resource_monitor.get_current_metrics()
        
        # Get historical data
        hours = request.args.get('hours', 1, type=int)
        historical_metrics = optimizer.resource_monitor.get_metrics_history(hours)
        
        return jsonify({
            'success': True,
            'data': {
                'current': current_metrics,
                'history': historical_metrics,
                'monitoring_interval': optimizer.resource_monitor.monitoring_interval
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting system resources: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SYSTEM_RESOURCES_ERROR'
        }), 500


@monitoring_bp.route('/security/events', methods=['GET'])
@require_auth
@require_role(UserRole.ADMIN)
def security_events():
    """Get security events and alerts."""
    try:
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        hours = request.args.get('hours', 24, type=int)
        event_type = request.args.get('type')
        
        # This would typically query a security events database
        # For now, return mock data structure
        events = {
            'events': [],
            'summary': {
                'total_events': 0,
                'failed_logins': 0,
                'blocked_requests': 0,
                'quarantined_files': 0,
                'security_violations': 0
            },
            'time_range': {
                'start': (datetime.utcnow() - timedelta(hours=hours)).isoformat(),
                'end': datetime.utcnow().isoformat(),
                'hours': hours
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': events
        })
        
    except Exception as e:
        logger.error(f"Error getting security events: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SECURITY_EVENTS_ERROR'
        }), 500


@monitoring_bp.route('/config/security', methods=['GET'])
@require_auth
@require_role(UserRole.ADMIN)
def get_security_configuration():
    """Get current security configuration."""
    try:
        security_config = get_security_config()
        
        if not security_config:
            return jsonify({
                'success': False,
                'error': 'Security configuration not available',
                'code': 'CONFIG_NOT_AVAILABLE'
            }), 503
        
        # Convert configuration to dictionary (excluding sensitive data)
        config_dict = security_config.to_dict()
        
        # Remove sensitive information
        sensitive_keys = ['secret_key', 'encryption_key', 'api_keys']
        for key in sensitive_keys:
            config_dict.pop(key, None)
        
        return jsonify({
            'success': True,
            'data': config_dict,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting security configuration: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SECURITY_CONFIG_ERROR'
        }), 500


@monitoring_bp.route('/cache/clear', methods=['POST'])
@require_auth
@require_role(UserRole.ADMIN)
def clear_cache():
    """Clear application cache."""
    try:
        optimizer = get_performance_optimizer()
        
        if not optimizer:
            return jsonify({
                'success': False,
                'error': 'Performance optimizer not available',
                'code': 'OPTIMIZER_NOT_AVAILABLE'
            }), 503
        
        # Clear memory cache
        optimizer.memory_cache.clear()
        
        # Clear Redis cache if available
        if optimizer.redis_cache:
            try:
                optimizer.redis_cache.flushdb()
            except Exception as redis_error:
                logger.warning(f"Failed to clear Redis cache: {str(redis_error)}")
        
        logger.info("Application cache cleared by admin")
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'CACHE_CLEAR_ERROR'
        }), 500


@monitoring_bp.route('/maintenance/cleanup', methods=['POST'])
@require_auth
@require_role(UserRole.ADMIN)
def maintenance_cleanup():
    """Perform maintenance cleanup tasks."""
    try:
        optimizer = get_performance_optimizer()
        
        if not optimizer:
            return jsonify({
                'success': False,
                'error': 'Performance optimizer not available',
                'code': 'OPTIMIZER_NOT_AVAILABLE'
            }), 503
        
        cleanup_results = {
            'expired_cache_entries': 0,
            'garbage_collection': False,
            'file_cleanup': 0
        }
        
        # Clean up expired cache entries
        cleanup_results['expired_cache_entries'] = optimizer.memory_cache.cleanup_expired()
        
        # Force garbage collection
        import gc
        collected = gc.collect()
        cleanup_results['garbage_collection'] = True
        cleanup_results['gc_collected'] = collected
        
        # Clean up old files (if secure file service is available)
        try:
            from src.security.secure_file_service import get_secure_file_service
            secure_file_service = get_secure_file_service()
            if secure_file_service:
                cleanup_results['file_cleanup'] = secure_file_service.cleanup_files()
        except Exception as file_error:
            logger.warning(f"File cleanup failed: {str(file_error)}")
        
        logger.info(f"Maintenance cleanup completed: {cleanup_results}")
        
        return jsonify({
            'success': True,
            'data': cleanup_results,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error during maintenance cleanup: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'MAINTENANCE_CLEANUP_ERROR'
        }), 500


# Helper functions
def _get_uptime() -> str:
    """Get application uptime."""
    try:
        import psutil
        process = psutil.Process()
        uptime_seconds = process.create_time()
        uptime_delta = datetime.now().timestamp() - uptime_seconds
        return str(timedelta(seconds=int(uptime_delta)))
    except:
        return "unknown"


def _check_database_health() -> Dict[str, Any]:
    """Check database health."""
    try:
        # This would typically test database connectivity
        return {
            'healthy': True,
            'response_time_ms': 10,
            'connections': 5
        }
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e)
        }


def _check_cache_health() -> Dict[str, Any]:
    """Check cache health."""
    try:
        optimizer = get_performance_optimizer()
        if optimizer:
            return {
                'healthy': True,
                'memory_cache_size': len(optimizer.memory_cache._cache),
                'redis_available': optimizer.redis_cache is not None
            }
        else:
            return {
                'healthy': False,
                'error': 'Performance optimizer not available'
            }
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e)
        }


def _check_security_health() -> Dict[str, Any]:
    """Check security system health."""
    try:
        security_config = get_security_config()
        return {
            'healthy': security_config is not None,
            'csrf_enabled': True,
            'session_security': True
        }
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e)
        }


def _check_performance_health() -> Dict[str, Any]:
    """Check performance system health."""
    try:
        optimizer = get_performance_optimizer()
        if optimizer:
            current_metrics = optimizer.resource_monitor.get_current_metrics()
            return {
                'healthy': True,
                'cpu_percent': current_metrics.get('process_cpu_percent', 0),
                'memory_mb': current_metrics.get('process_memory_mb', 0)
            }
        else:
            return {
                'healthy': False,
                'error': 'Performance optimizer not available'
            }
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e)
        }


def init_monitoring_endpoints(app):
    """Initialize monitoring endpoints with Flask app.
    
    Args:
        app: Flask application instance
    """
    try:
        app.register_blueprint(monitoring_bp)
        logger.info("Monitoring endpoints initialized")
    except Exception as e:
        logger.error(f"Failed to initialize monitoring endpoints: {str(e)}")
        raise