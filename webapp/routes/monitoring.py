"""
Monitoring and health check API routes.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
import logging
from datetime import datetime, timezone, timedelta

from src.services.system_monitoring import monitoring_service
from utils.logger import logger

monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')

@monitoring_bp.route('/health', methods=['GET'])
@login_required
def get_system_health():
    """Get overall system health status."""
    try:
        status = monitoring_service.get_system_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_bp.route('/metrics', methods=['GET'])
@login_required
def get_system_metrics():
    """Get current system metrics."""
    try:
        metrics = monitoring_service.collect_system_metrics()
        return jsonify({
            'success': True,
            'data': metrics.to_dict()
        })
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_bp.route('/health-checks', methods=['GET'])
@login_required
def get_health_checks():
    """Get detailed health checks for all services."""
    try:
        health_checks = monitoring_service.perform_health_checks()
        return jsonify({
            'success': True,
            'data': {k: v.to_dict() for k, v in health_checks.items()}
        })
    except Exception as e:
        logger.error(f"Error performing health checks: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_bp.route('/dashboard', methods=['GET'])
@login_required
def get_performance_dashboard():
    """Get performance dashboard data."""
    try:
        dashboard_data = monitoring_service.get_performance_dashboard()
        return jsonify({
            'success': True,
            'data': dashboard_data
        })
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_bp.route('/alerts', methods=['GET'])
@login_required
def get_alerts():
    """Get system alerts."""
    try:
        # Get query parameters
        resolved = request.args.get('resolved', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))
        
        # Filter alerts
        alerts = monitoring_service.alerts
        if not resolved:
            alerts = [alert for alert in alerts if not alert.get('resolved', False)]
        
        # Limit results
        alerts = alerts[-limit:] if limit > 0 else alerts
        
        return jsonify({
            'success': True,
            'data': {
                'alerts': alerts,
                'total': len(alerts)
            }
        })
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_bp.route('/alerts/<alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    """Resolve a specific alert."""
    try:
        # Find and resolve the alert
        resolved = False
        for alert in monitoring_service.alerts:
            if alert['id'] == alert_id and not alert.get('resolved', False):
                alert['resolved'] = True
                alert['resolved_at'] = datetime.now(timezone.utc)
                alert['resolved_by'] = current_user.id
                resolved = True
                break
        
        if resolved:
            logger.info(f"Alert {alert_id} resolved by user {current_user.id}")
            return jsonify({
                'success': True,
                'message': 'Alert resolved successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Alert not found or already resolved'
            }), 404
            
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@monitoring_bp.route('/status/simple', methods=['GET'])
def get_simple_status():
    """Get simple system status (no authentication required for basic monitoring)."""
    try:
        # Perform basic health checks
        health_checks = monitoring_service.perform_health_checks()
        overall_status = monitoring_service._determine_overall_status(health_checks)
        
        return jsonify({
            'status': overall_status.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'services': {k: v.status.value for k, v in health_checks.items()}
        })
    except Exception as e:
        logger.error(f"Error getting simple status: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@monitoring_bp.route('/metrics/history', methods=['GET'])
@login_required
def get_metrics_history():
    """Get historical metrics data."""
    try:
        # Get query parameters
        hours = int(request.args.get('hours', 24))
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        historical_metrics = [
            m.to_dict() for m in monitoring_service.metrics_history 
            if m.timestamp > cutoff_time
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'metrics': historical_metrics,
                'period_hours': hours,
                'total_points': len(historical_metrics)
            }
        })
    except Exception as e:
        logger.error(f"Error getting metrics history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Error handlers
@monitoring_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@monitoring_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500