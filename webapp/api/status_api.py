"""
Status API Endpoints

This module provides comprehensive status and health check endpoints
for monitoring system health, service availability, and performance metrics.
"""

import time
import psutil
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from src.services.core_service import core_service
from src.services.consolidated_llm_service import ConsolidatedLLMService
from src.services.file_processing_service import FileProcessingService
from src.services.cache_manager import cache_manager
from src.services.performance_monitor import performance_monitor
from src.services.processing_error_handler import processing_error_handler
from src.services.health_monitor import health_monitor
from src.database.models import db, MarkingGuide, Submission, GradingResult
from .error_handlers import api_error_handler
from utils.logger import logger

status_api_bp = Blueprint('status_api', __name__, url_prefix='/api/status')

@status_api_bp.route('/health', methods=['GET'])
def system_health():
    """Comprehensive system health check endpoint"""
    try:
        start_time = time.time()
        request_id = f"health_{int(time.time() * 1000)}"
        
        health_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'request_id': request_id,
            'overall_status': 'healthy',
            'services': {},
            'system': {},
            'database': {},
            'performance': {}
        }
        
        # Check core service health
        try:
            core_health = core_service.get_health_status()
            health_data['services']['core_service'] = {
                'status': core_health.get('status', 'unknown'),
                'details': core_health
            }
        except Exception as e:
            health_data['services']['core_service'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_data['overall_status'] = 'degraded'
        
        # Check LLM service health
        try:
            llm_service = ConsolidatedLLMService()
            llm_health = llm_service.validate_service_health()
            health_data['services']['llm_service'] = {
                'status': llm_health.get('overall_health', 'unknown'),
                'details': llm_health
            }
            
            if llm_health.get('overall_health') in ['unhealthy', 'error']:
                health_data['overall_status'] = 'degraded'
                
        except Exception as e:
            health_data['services']['llm_service'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_data['overall_status'] = 'degraded'
        
        # Check file processing service health
        try:
            file_service = FileProcessingService()
            dependency_status = file_service.dependency_status
            
            available_deps = sum(1 for dep in dependency_status.values() if dep.get('available', False))
            total_deps = len(dependency_status)
            
            if available_deps == 0:
                file_status = 'unhealthy'
                health_data['overall_status'] = 'degraded'
            elif available_deps < total_deps * 0.5:
                file_status = 'degraded'
                health_data['overall_status'] = 'degraded'
            else:
                file_status = 'healthy'
            
            health_data['services']['file_processing'] = {
                'status': file_status,
                'details': {
                    'available_dependencies': available_deps,
                    'total_dependencies': total_deps,
                    'dependency_status': dependency_status
                }
            }
            
        except Exception as e:
            health_data['services']['file_processing'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_data['overall_status'] = 'degraded'
        
        # Check database health
        try:
            db.session.execute(db.text('SELECT 1'))
            db.session.commit()
            
            # Get database statistics
            guide_count = MarkingGuide.query.count()
            submission_count = Submission.query.count()
            result_count = GradingResult.query.count()
            
            health_data['database'] = {
                'status': 'healthy',
                'connection': 'active',
                'statistics': {
                    'marking_guides': guide_count,
                    'submissions': submission_count,
                    'grading_results': result_count
                }
            }
            
        except Exception as e:
            health_data['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_data['overall_status'] = 'unhealthy'
        
        # Check system resources
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=1)
            
            health_data['system'] = {
                'status': 'healthy',
                'resources': {
                    'memory': {
                        'total_gb': round(memory.total / (1024**3), 2),
                        'available_gb': round(memory.available / (1024**3), 2),
                        'used_percent': memory.percent
                    },
                    'disk': {
                        'total_gb': round(disk.total / (1024**3), 2),
                        'free_gb': round(disk.free / (1024**3), 2),
                        'used_percent': round((disk.used / disk.total) * 100, 2)
                    },
                    'cpu': {
                        'usage_percent': cpu_percent
                    }
                }
            }
            
            if memory.percent > 90 or disk.used / disk.total > 0.95 or cpu_percent > 95:
                health_data['system']['status'] = 'warning'
                if health_data['overall_status'] == 'healthy':
                    health_data['overall_status'] = 'degraded'
                    
        except Exception as e:
            health_data['system'] = {
                'status': 'unknown',
                'error': str(e)
            }
        
        # Get performance metrics
        try:
            perf_summary = performance_monitor.get_performance_summary()
            health_data['performance'] = {
                'status': 'healthy',
                'metrics': perf_summary
            }
            
            if perf_summary.get('overall_error_rate', 0) > 0.1:  # 10% error rate
                health_data['performance']['status'] = 'degraded'
                if health_data['overall_status'] == 'healthy':
                    health_data['overall_status'] = 'degraded'
                    
        except Exception as e:
            health_data['performance'] = {
                'status': 'unknown',
                'error': str(e)
            }
        
        # Calculate response time
        processing_time = (time.time() - start_time) * 1000
        
        response = api_error_handler.create_success_response(
            data=health_data,
            message="Health check completed",
            metadata={
                'processing_time_ms': processing_time,
                'health_check_version': '1.0'
            },
            request_id=request_id
        )
        
        # Return appropriate status code based on overall health
        status_code = 200
        if health_data['overall_status'] == 'degraded':
            status_code = 200  # Still return 200 but with degraded status
        elif health_data['overall_status'] == 'unhealthy':
            status_code = 503  # Service unavailable
        
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        response, status = api_error_handler.create_error_response(
            error=e,
            status_code=500,
            message="Health check failed"
        )
        return jsonify(response), status

@status_api_bp.route('/services', methods=['GET'])
def service_status():
    """Get detailed status of all services"""
    try:
        request_id = f"services_{int(time.time() * 1000)}"
        
        services_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'services': {}
        }
        
        # Core service status
        try:
            services_data['services']['core_service'] = core_service.get_health_status()
        except Exception as e:
            services_data['services']['core_service'] = {'status': 'error', 'error': str(e)}
        
        # LLM service status
        try:
            llm_service = ConsolidatedLLMService()
            services_data['services']['llm_service'] = llm_service.get_performance_stats()
        except Exception as e:
            services_data['services']['llm_service'] = {'status': 'error', 'error': str(e)}
        
        # File processing service status
        try:
            file_service = FileProcessingService()
            services_data['services']['file_processing'] = {
                'dependency_status': file_service.dependency_status,
                'supported_formats': file_service.get_supported_formats()
            }
        except Exception as e:
            services_data['services']['file_processing'] = {'status': 'error', 'error': str(e)}
        
        # Cache service status
        try:
            services_data['services']['cache'] = cache_manager.get_stats()
        except Exception as e:
            services_data['services']['cache'] = {'status': 'error', 'error': str(e)}
        
        response = api_error_handler.create_success_response(
            data=services_data,
            message="Service status retrieved",
            request_id=request_id
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Service status check failed: {e}")
        response, status = api_error_handler.create_error_response(
            error=e,
            status_code=500,
            message="Service status check failed"
        )
        return jsonify(response), status

@status_api_bp.route('/performance', methods=['GET'])
def performance_metrics():
    """Get system performance metrics"""
    try:
        request_id = f"perf_{int(time.time() * 1000)}"
        
        hours = request.args.get('hours', 24, type=int)
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        performance_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'time_range_hours': hours,
            'metrics': {}
        }
        
        # Get performance summary
        try:
            performance_data['metrics']['summary'] = performance_monitor.get_performance_summary()
        except Exception as e:
            performance_data['metrics']['summary'] = {'error': str(e)}
        
        # Get operation statistics
        try:
            performance_data['metrics']['operations'] = performance_monitor.get_all_operation_stats()
        except Exception as e:
            performance_data['metrics']['operations'] = {'error': str(e)}
        
        # Get error statistics
        try:
            performance_data['metrics']['errors'] = processing_error_handler.get_error_statistics()
        except Exception as e:
            performance_data['metrics']['errors'] = {'error': str(e)}
        
        # Get cache performance
        try:
            performance_data['metrics']['cache'] = cache_manager.get_stats()
        except Exception as e:
            performance_data['metrics']['cache'] = {'error': str(e)}
        
        response = api_error_handler.create_success_response(
            data=performance_data,
            message="Performance metrics retrieved",
            request_id=request_id
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Performance metrics retrieval failed: {e}")
        response, status = api_error_handler.create_error_response(
            error=e,
            status_code=500,
            message="Performance metrics retrieval failed"
        )
        return jsonify(response), status

@status_api_bp.route('/processing/<task_id>', methods=['GET'])
@login_required
def processing_status(task_id):
    """Get processing status for a specific task"""
    try:
        request_id = f"proc_status_{int(time.time() * 1000)}"
        
        from webapp.routes.main_routes import progress_store
        
        if task_id not in progress_store:
            response, status = api_error_handler.handle_not_found_error(
                resource=f"Processing task {task_id}",
                request_id=request_id
            )
            return jsonify(response), status
        
        progress_data = progress_store[task_id]
        
        # Enhance progress data with additional information
        enhanced_data = {
            'task_id': task_id,
            'status': progress_data['status'],
            'progress': progress_data['progress'],
            'message': progress_data['message'],
            'current_file': progress_data.get('current_file', ''),
            'guide_title': progress_data.get('guide_title', ''),
            'started_at': progress_data.get('started_at'),
            'updated_at': progress_data.get('updated_at', datetime.now(timezone.utc).isoformat()),
            'results': {
                'total_count': progress_data['total_count'],
                'processed_count': progress_data['processed_count'],
                'successful_count': progress_data['successful_count'],
                'failed_count': progress_data['failed_count'],
                'details': progress_data.get('results', [])
            },
            'estimated_completion': progress_data.get('estimated_completion'),
            'processing_rate': progress_data.get('processing_rate', 0)
        }
        
        response = api_error_handler.create_success_response(
            data=enhanced_data,
            message="Processing status retrieved",
            request_id=request_id
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Processing status retrieval failed: {e}")
        response, status = api_error_handler.create_error_response(
            error=e,
            status_code=500,
            message="Processing status retrieval failed"
        )
        return jsonify(response), status

@status_api_bp.route('/database', methods=['GET'])
def database_status():
    """Get database status and statistics"""
    try:
        request_id = f"db_status_{int(time.time() * 1000)}"
        
        db_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'connection': {},
            'statistics': {},
            'health': {}
        }
        
        # Test database connection
        try:
            start_time = time.time()
            db.session.execute(db.text('SELECT 1'))
            db.session.commit()
            connection_time = (time.time() - start_time) * 1000
            
            db_data['connection'] = {
                'status': 'connected',
                'response_time_ms': round(connection_time, 2)
            }
            
        except Exception as e:
            db_data['connection'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        # Get database statistics
        try:
            db_data['statistics'] = {
                'marking_guides': MarkingGuide.query.count(),
                'submissions': Submission.query.count(),
                'grading_results': GradingResult.query.count(),
                'recent_activity': {
                    'guides_last_24h': MarkingGuide.query.filter(
                        MarkingGuide.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)
                    ).count(),
                    'submissions_last_24h': Submission.query.filter(
                        Submission.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)
                    ).count(),
                    'results_last_24h': GradingResult.query.filter(
                        GradingResult.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)
                    ).count()
                }
            }
            
        except Exception as e:
            db_data['statistics'] = {'error': str(e)}
        
        # Database health assessment
        if db_data['connection']['status'] == 'connected':
            if db_data['connection']['response_time_ms'] < 100:
                db_data['health']['status'] = 'excellent'
            elif db_data['connection']['response_time_ms'] < 500:
                db_data['health']['status'] = 'good'
            else:
                db_data['health']['status'] = 'slow'
        else:
            db_data['health']['status'] = 'unhealthy'
        
        response = api_error_handler.create_success_response(
            data=db_data,
            message="Database status retrieved",
            request_id=request_id
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        response, status = api_error_handler.create_error_response(
            error=e,
            status_code=500,
            message="Database status check failed"
        )
        return jsonify(response), status

@status_api_bp.route('/alerts', methods=['GET'])
def system_alerts():
    """Get system alerts and warnings"""
    try:
        request_id = f"alerts_{int(time.time() * 1000)}"
        
        level = request.args.get('level', 'all')
        limit = request.args.get('limit', 50, type=int)
        
        alerts_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'filter': {
                'level': level,
                'limit': limit
            },
            'alerts': []
        }
        
        # Get performance alerts
        try:
            if level == 'all' or level == 'performance':
                perf_alerts = performance_monitor.get_alerts(limit=limit)
                for alert in perf_alerts:
                    alerts_data['alerts'].append({
                        'type': 'performance',
                        'level': alert.get('level', 'info'),
                        'message': alert.get('message', ''),
                        'timestamp': alert.get('timestamp', ''),
                        'details': alert
                    })
        except Exception as e:
            logger.warning(f"Failed to get performance alerts: {e}")
        
        try:
            if level == 'all' or level == 'error':
                error_stats = processing_error_handler.get_error_statistics()
                
                if error_stats.get('total_errors', 0) > 0:
                    recent_errors = error_stats.get('recent_errors', [])
                    for error in recent_errors[-10:]:  # Last 10 errors
                        alerts_data['alerts'].append({
                            'type': 'error',
                            'level': 'warning',
                            'message': f"Error in {error.get('service', 'unknown')}: {error.get('operation', 'unknown')}",
                            'timestamp': error.get('timestamp', ''),
                            'details': error
                        })
        except Exception as e:
            logger.warning(f"Failed to get error alerts: {e}")
        
        # Sort alerts by timestamp (most recent first)
        alerts_data['alerts'].sort(
            key=lambda x: x.get('timestamp', ''), 
            reverse=True
        )
        
        # Apply limit
        alerts_data['alerts'] = alerts_data['alerts'][:limit]
        alerts_data['total_alerts'] = len(alerts_data['alerts'])
        
        response = api_error_handler.create_success_response(
            data=alerts_data,
            message="System alerts retrieved",
            request_id=request_id
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"System alerts retrieval failed: {e}")
        response, status = api_error_handler.create_error_response(
            error=e,
            status_code=500,
            message="System alerts retrieval failed"
        )
        return jsonify(response), status