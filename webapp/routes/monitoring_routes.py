"""
Monitoring Dashboard Routes

This module provides web routes for the monitoring dashboard interface.
"""

from functools import wraps

from flask import Blueprint, flash, redirect, render_template, url_for

from src.services.enhanced_alerting_system import enhanced_alerting_system
from src.services.monitoring_dashboard import monitoring_dashboard_service
from src.services.realtime_metrics_collector import realtime_metrics_collector
from utils.logger import logger

# Create blueprint
monitoring_routes_bp = Blueprint(
    "monitoring_routes", __name__, url_prefix="/monitoring"
)


def monitoring_required(f):
    """Decorator to ensure monitoring services are available"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if not monitoring_dashboard_service._running:
                monitoring_dashboard_service.start_monitoring()

            if not enhanced_alerting_system._running:
                enhanced_alerting_system.start_monitoring()

            if not realtime_metrics_collector._running:
                realtime_metrics_collector.start_collection()

            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in monitoring route: {e}")
            flash(f"Monitoring service error: {str(e)}", "error")
            return redirect(url_for("main.index"))

    return decorated_function


@monitoring_routes_bp.route("/")
@monitoring_required
def dashboard():
    """Main monitoring dashboard"""
    try:
        return render_template("monitoring_dashboard.html")
    except Exception as e:
        logger.error(f"Error rendering monitoring dashboard: {e}")
        flash(f"Error loading monitoring dashboard: {str(e)}", "error")
        return redirect(url_for("main.index"))


@monitoring_routes_bp.route("/health")
@monitoring_required
def health_dashboard():
    """Service health monitoring dashboard"""
    try:
        return render_template("monitoring_dashboard.html", focus="health")
    except Exception as e:
        logger.error(f"Error rendering health dashboard: {e}")
        flash(f"Error loading health dashboard: {str(e)}", "error")
        return redirect(url_for("monitoring_routes.dashboard"))


@monitoring_routes_bp.route("/performance")
@monitoring_required
def performance_dashboard():
    """Performance monitoring dashboard"""
    try:
        return render_template("monitoring_dashboard.html", focus="performance")
    except Exception as e:
        logger.error(f"Error rendering performance dashboard: {e}")
        flash(f"Error loading performance dashboard: {str(e)}", "error")
        return redirect(url_for("monitoring_routes.dashboard"))


@monitoring_routes_bp.route("/alerts")
@monitoring_required
def alerts_dashboard():
    """Alerts monitoring dashboard"""
    try:
        return render_template("monitoring_dashboard.html", focus="alerts")
    except Exception as e:
        logger.error(f"Error rendering alerts dashboard: {e}")
        flash(f"Error loading alerts dashboard: {str(e)}", "error")
        return redirect(url_for("monitoring_routes.dashboard"))


@monitoring_routes_bp.route("/start")
def start_monitoring():
    """Start all monitoring services"""
    try:
        # Start monitoring services
        monitoring_dashboard_service.start_monitoring()
        enhanced_alerting_system.start_monitoring()
        realtime_metrics_collector.start_collection()

        flash("Monitoring services started successfully", "success")
        logger.info("Monitoring services started via web interface")

    except Exception as e:
        logger.error(f"Error starting monitoring services: {e}")
        flash(f"Error starting monitoring services: {str(e)}", "error")

    return redirect(url_for("monitoring_routes.dashboard"))


@monitoring_routes_bp.route("/stop")
def stop_monitoring():
    """Stop all monitoring services"""
    try:
        # Stop monitoring services
        monitoring_dashboard_service.stop_monitoring()
        enhanced_alerting_system.stop_monitoring()
        realtime_metrics_collector.stop_collection()

        flash("Monitoring services stopped successfully", "success")
        logger.info("Monitoring services stopped via web interface")

    except Exception as e:
        logger.error(f"Error stopping monitoring services: {e}")
        flash(f"Error stopping monitoring services: {str(e)}", "error")

    return redirect(url_for("main.index"))


@monitoring_routes_bp.route("/restart")
def restart_monitoring():
    """Restart all monitoring services"""
    try:
        # Stop services
        monitoring_dashboard_service.stop_monitoring()
        enhanced_alerting_system.stop_monitoring()
        realtime_metrics_collector.stop_collection()

        # Start services
        monitoring_dashboard_service.start_monitoring()
        enhanced_alerting_system.start_monitoring()
        realtime_metrics_collector.start_collection()

        flash("Monitoring services restarted successfully", "success")
        logger.info("Monitoring services restarted via web interface")

    except Exception as e:
        logger.error(f"Error restarting monitoring services: {e}")
        flash(f"Error restarting monitoring services: {str(e)}", "error")

    return redirect(url_for("monitoring_routes.dashboard"))


# Error handlers
@monitoring_routes_bp.errorhandler(404)
def not_found(error):
    flash("Monitoring page not found", "error")
    return redirect(url_for("monitoring_routes.dashboard"))


@monitoring_routes_bp.errorhandler(500)
def internal_error(error):
    flash("Internal monitoring error occurred", "error")
    return redirect(url_for("main.index"))
