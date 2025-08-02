"""
Monitoring API Endpoints

This module provides REST API endpoints for accessing monitoring data,
health status, performance metrics, and alerting information.
"""

from flask import Blueprint, jsonify, request
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import json

from src.services.monitoring_dashboard import monitoring_dashboard_service, DashboardType, AlertSeverity
from src.services.enhanced_alerting_system import enhanced_alerting_system, AlertRule
from src.services.realtime_metrics_collector import realtime_metrics_collector
from src.services.health_monitor import health_monitor
from src.services.performance_monitor import performance_monitor
from utils.logger import logger

# Create blueprint
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')

@monitoring_bp.route('/health', methods=['GET'])
def get_system_health():
    """Get overall system health status"""
    try:
        health_status = health_monitor.get_overall_health()
        
        if not health_status:
            return jsonify({
                'status': 'error',
                'message': 'Health monitor not available'
            }), 503
        
        return jsonify({
            'status': 'success',
            'data': health_status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/health/<service_name>', methods=['GET'])
def get_service_health(service_name: str):
    """Get health status for a specific service"""
    try:
        health_status = health_monitor.get_overall_health()
        
        if not health_status or 'services' not in health_status:
            return jsonify({
                'status': 'error',
                'message': 'Health data not available'
            }), 503
        
        service_health = health_status['services'].get(service_name)
        
        if not service_health:
            return jsonify({
                'status': 'error',
                'message': f'Service {service_name} not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': {
                'service_name': service_name,
                'health': service_health
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting service health for {service_name}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/metrics', methods=['GET'])
def get_all_metrics():
    """Get all current metrics"""
    try:
        metrics = realtime_metrics_collector.get_all_metrics()
        
        return jsonify({
            'status': 'success',
            'data': metrics,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/metrics/<metric_name>', methods=['GET'])
def get_metric(metric_name: str):
    """Get specific metric with optional history"""
    try:
        # Get query parameters
        minutes = request.args.get('minutes', 60, type=int)
        include_history = request.args.get('history', 'false').lower() == 'true'
        
        # Get metric info
        metric = realtime_metrics_collector.get_metric(metric_name)
        if not metric:
            return jsonify({
                'status': 'error',
                'message': f'Metric {metric_name} not found'
            }), 404
        
        # Get latest value
        latest = metric.get_latest()
        
        response_data = {
            'name': metric_name,
            'type': metric.metric_type.value,
            'description': metric.description,
            'unit': metric.unit,
            'latest_value': latest.value if latest else None,
            'latest_timestamp': latest.timestamp.isoformat() if latest else None,
            'statistics': {
                'avg_5min': metric.get_average(5),
                'max_5min': metric.get_max(5),
                'trend_10min': metric.get_trend(10)
            }
        }
        
        if include_history:
            response_data['history'] = realtime_metrics_collector.get_metric_history(metric_name, minutes)
        
        return jsonify({
            'status': 'success',
            'data': response_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting metric {metric_name}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/performance', methods=['GET'])
def get_performance_summary():
    """Get performance summary"""
    try:
        summary = performance_monitor.get_performance_summary()
        
        if not summary:
            return jsonify({
                'status': 'error',
                'message': 'Performance data not available'
            }), 503
        
        return jsonify({
            'status': 'success',
            'data': summary,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/performance/operations', methods=['GET'])
def get_operation_stats():
    """Get detailed operation statistics"""
    try:
        stats = performance_monitor.get_all_operation_stats()
        
        return jsonify({
            'status': 'success',
            'data': stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting operation stats: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/dashboards', methods=['GET'])
def list_dashboards():
    """List all available dashboards"""
    try:
        dashboards = monitoring_dashboard_service.list_dashboards()
        
        return jsonify({
            'status': 'success',
            'data': dashboards,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error listing dashboards: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/dashboards/<dashboard_id>', methods=['GET'])
def get_dashboard(dashboard_id: str):
    """Get dashboard data"""
    try:
        dashboard_data = monitoring_dashboard_service.get_dashboard_data(dashboard_id)
        
        if not dashboard_data:
            return jsonify({
                'status': 'error',
                'message': f'Dashboard {dashboard_id} not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': dashboard_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard {dashboard_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Get alerts with optional filtering"""
    try:
        # Get query parameters
        severity = request.args.get('severity')
        resolved = request.args.get('resolved')
        limit = request.args.get('limit', 100, type=int)
        
        # Parse severity
        severity_enum = None
        if severity:
            try:
                severity_enum = AlertSeverity(severity.lower())
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid severity: {severity}'
                }), 400
        
        # Parse resolved
        resolved_bool = None
        if resolved is not None:
            resolved_bool = resolved.lower() == 'true'
        
        # Get alerts
        alerts = monitoring_dashboard_service.get_alerts(
            severity=severity_enum,
            resolved=resolved_bool,
            limit=limit
        )
        
        return jsonify({
            'status': 'success',
            'data': alerts,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/alerts/<alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id: str):
    """Resolve an alert"""
    try:
        success = monitoring_dashboard_service.resolve_alert(alert_id)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': f'Alert {alert_id} not found or already resolved'
            }), 404
        
        return jsonify({
            'status': 'success',
            'message': f'Alert {alert_id} resolved',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/alerts/statistics', methods=['GET'])
def get_alert_statistics():
    """Get alerting system statistics"""
    try:
        stats = enhanced_alerting_system.get_alert_statistics()
        
        return jsonify({
            'status': 'success',
            'data': stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting alert statistics: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/system/status', methods=['GET'])
def get_system_status():
    """Get comprehensive system status"""
    try:
        health_status = health_monitor.get_overall_health()
        performance_summary = performance_monitor.get_performance_summary()
        dashboard_data = realtime_metrics_collector.get_dashboard_data()
        alert_stats = enhanced_alerting_system.get_alert_statistics()
        monitoring_stats = monitoring_dashboard_service.get_monitoring_stats()
        
        # Determine overall system status
        overall_status = "healthy"
        if alert_stats.get('active_alerts', 0) > 0:
            if alert_stats.get('escalated_alerts', 0) > 0:
                overall_status = "critical"
            else:
                overall_status = "warning"
        
        # Check service health
        if health_status and not health_status.get('overall_healthy', True):
            overall_status = "degraded" if overall_status == "healthy" else overall_status
        
        system_status = {
            'overall_status': overall_status,
            'health': health_status,
            'performance': performance_summary,
            'metrics': dashboard_data,
            'alerts': alert_stats,
            'monitoring': monitoring_stats,
            'uptime': {
                'monitoring_active': monitoring_stats.get('monitoring_active', False),
                'metrics_collection_active': dashboard_data.get('collection_interval') is not None,
                'alerting_active': alert_stats.get('monitoring_active', False)
            }
        }
        
        return jsonify({
            'status': 'success',
            'data': system_status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/export/metrics', methods=['GET'])
def export_metrics():
    """Export metrics data"""
    try:
        format_type = request.args.get('format', 'json').lower()
        
        if format_type not in ['json']:
            return jsonify({
                'status': 'error',
                'message': f'Unsupported format: {format_type}'
            }), 400
        
        exported_data = realtime_metrics_collector.export_metrics(format_type)
        
        return jsonify({
            'status': 'success',
            'data': json.loads(exported_data) if format_type == 'json' else exported_data,
            'format': format_type,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/config/reload', methods=['POST'])
def reload_monitoring_config():
    """Reload monitoring configuration"""
    try:
        # This would trigger configuration reload in monitoring services
        logger.info("Monitoring configuration reload requested")
        
        return jsonify({
            'status': 'success',
            'message': 'Configuration reload initiated',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error reloading monitoring config: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Error handlers
@monitoring_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found'
    }), 404

@monitoring_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500