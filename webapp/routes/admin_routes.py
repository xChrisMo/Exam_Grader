"""
Admin Routes

This module handles administrative functionality including system monitoring,
cache management, and service health checks.
"""

from datetime import datetime
from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from src.database.models import GradingResult, MarkingGuide, Submission, User, db
from src.services.core_service import core_service
from utils.logger import logger

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Decorator to require admin privileges."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For now, all authenticated users have admin access
        # In production, you'd check user.is_admin or similar
        if not current_user.is_authenticated:
            flash("Admin access required", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    """Admin dashboard."""
    try:
        # Get system statistics
        stats = {
            "total_users": User.query.count(),
            "total_guides": MarkingGuide.query.count(),
            "total_submissions": Submission.query.count(),
            "total_results": GradingResult.query.count(),
            "active_users": User.query.filter_by(is_active=True).count(),
        }

        # Get recent activity
        recent_submissions = (
            Submission.query.order_by(Submission.created_at.desc()).limit(10).all()
        )

        recent_results = (
            GradingResult.query.order_by(GradingResult.created_at.desc())
            .limit(10)
            .all()
        )

        # Get service health
        service_health = core_service.get_health_status()

        return render_template(
            "admin/dashboard.html",
            stats=stats,
            recent_submissions=recent_submissions,
            recent_results=recent_results,
            service_health=service_health,
        )

    except Exception as e:
        logger.error(f"Admin dashboard error: {e}")
        flash("Error loading admin dashboard", "error")
        return render_template(
            "admin/dashboard.html",
            stats={},
            recent_submissions=[],
            recent_results=[],
            service_health={},
        )


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    """User management."""
    try:
        page = request.args.get("page", 1, type=int)
        users = User.query.paginate(page=page, per_page=20, error_out=False)

        return render_template("admin/users.html", users=users)

    except Exception as e:
        logger.error(f"User management error: {e}")
        flash("Error loading users", "error")
        return render_template("admin/users.html", users=None)


@admin_bp.route("/system-info")
@login_required
@admin_required
def system_info():
    """System information and health checks."""
    try:
        import platform
        import sys
        from datetime import datetime

        import psutil

        # System information
        system_info = {
            "platform": platform.platform(),
            "python_version": sys.version,
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage("/").percent,
            "uptime": datetime.now().isoformat(),
        }

        # Database information
        db_info = {
            "engine": str(db.engine.url),
            "pool_size": db.engine.pool.size(),
            "checked_out": db.engine.pool.checkedout(),
            "overflow": db.engine.pool.overflow(),
        }

        # Service health
        service_health = core_service.get_health_status()

        return render_template(
            "admin/system_info.html",
            system_info=system_info,
            db_info=db_info,
            service_health=service_health,
        )

    except Exception as e:
        logger.error(f"System info error: {e}")
        flash("Error loading system information", "error")
        return render_template(
            "admin/system_info.html", system_info={}, db_info={}, service_health={}
        )


@admin_bp.route("/cache-management")
@login_required
@admin_required
def cache_management():
    """Cache management interface."""
    return render_template("admin/cache_management.html")


@admin_bp.route("/api/cache/clear", methods=["POST"])
@login_required
@admin_required
def clear_cache():
    """Clear application cache."""
    try:
        # Clear core service cache
        if hasattr(core_service, "_processing_cache"):
            core_service._processing_cache.clear()

        # Clear other caches as needed
        # This would depend on your caching implementation

        return jsonify({"success": True, "message": "Cache cleared successfully"})

    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return jsonify({"success": False, "error": "Failed to clear cache"}), 500


@admin_bp.route("/api/system/restart", methods=["POST"])
@login_required
@admin_required
def restart_services():
    """Restart system services."""
    try:
        # Restart core service
        core_service._initialize_engines()

        return jsonify({"success": True, "message": "Services restarted successfully"})

    except Exception as e:
        logger.error(f"Service restart error: {e}")
        return jsonify({"success": False, "error": "Failed to restart services"}), 500


@admin_bp.route("/logs")
@login_required
@admin_required
def logs():
    """View application logs."""
    try:
        log_file = request.args.get("file", "app.log")
        lines = request.args.get("lines", 100, type=int)

        # Read log file
        from pathlib import Path

        log_path = Path("logs") / log_file

        if not log_path.exists():
            flash(f"Log file {log_file} not found", "error")
            return render_template("admin/logs.html", logs=[], log_files=[])

        # Get available log files
        log_files = (
            [f.name for f in Path("logs").glob("*.log")]
            if Path("logs").exists()
            else []
        )

        # Read last N lines
        with open(log_path, "r") as f:
            all_lines = f.readlines()
            log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return render_template(
            "admin/logs.html",
            logs=log_lines,
            log_files=log_files,
            current_file=log_file,
        )

    except Exception as e:
        logger.error(f"Log viewing error: {e}")
        flash("Error loading logs", "error")
        return render_template("admin/logs.html", logs=[], log_files=[])


@admin_bp.route("/api/cache/stats", methods=["GET"])
@login_required
@admin_required
def cache_stats():
    """Get cache statistics."""
    try:
        # Get cache statistics
        stats = {"memory_usage": "N/A", "cache_entries": 0, "hit_rate": "N/A"}

        if hasattr(core_service, "_processing_cache"):
            cache = core_service._processing_cache
            if hasattr(cache, "info"):
                cache_info = cache.info()
                stats.update(
                    {
                        "cache_entries": (
                            cache_info.currsize
                            if hasattr(cache_info, "currsize")
                            else 0
                        ),
                        "hit_rate": (
                            f"{cache_info.hits / (cache_info.hits + cache_info.misses) * 100:.1f}%"
                            if hasattr(cache_info, "hits")
                            and (cache_info.hits + cache_info.misses) > 0
                            else "N/A"
                        ),
                    }
                )

        return jsonify({"success": True, "stats": stats})

    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return (
            jsonify({"success": False, "error": "Failed to get cache statistics"}),
            500,
        )


@admin_bp.route("/api/logs/clear", methods=["POST"])
@login_required
@admin_required
def clear_logs():
    """Clear a specific log file."""
    try:
        data = request.get_json()
        log_file = data.get("file", "app.log")

        # Validate log file name
        from pathlib import Path

        log_path = Path("logs") / log_file

        if not log_path.exists():
            return (
                jsonify({"success": False, "error": f"Log file {log_file} not found"}),
                404,
            )

        # Clear the log file
        with open(log_path, "w") as f:
            f.write("")

        logger.info(f"Log file {log_file} cleared by admin user {current_user.id}")

        return jsonify(
            {"success": True, "message": f"Log file {log_file} cleared successfully"}
        )

    except Exception as e:
        logger.error(f"Log clear error: {e}")
        return jsonify({"success": False, "error": "Failed to clear log file"}), 500


@admin_bp.route("/api/health")
@login_required
@admin_required
def api_health():
    """API health check for admin."""
    try:
        # Check database
        db.session.execute("SELECT 1")

        # Check core service
        service_health = core_service.get_health_status()

        # Check file system
        from pathlib import Path

        temp_dir = Path("temp")
        uploads_dir = Path("uploads")

        return jsonify(
            {
                "success": True,
                "database": "healthy",
                "core_service": service_health,
                "filesystem": {
                    "temp_dir": temp_dir.exists(),
                    "uploads_dir": uploads_dir.exists(),
                },
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Admin health check failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 503
