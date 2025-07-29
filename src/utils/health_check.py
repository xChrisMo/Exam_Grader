"""
Comprehensive Health Check System for Exam Grader Application.

This module provides health checks for all critical components including
database, external APIs, file system, and internal services.
"""
from typing import Any, Dict

import os
import time
import psutil
from pathlib import Path
from dataclasses import dataclass, asdict

try:
    from utils.logger import logger
    from src.database import db
    from src.utils.circuit_breaker import get_all_circuit_breakers
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    """Health status for a component."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    details: Dict[str, Any]
    response_time_ms: float
    last_checked: str

class HealthChecker:
    """
    Comprehensive health checker for all application components.
    
    Checks:
    - Database connectivity and performance
    - External API availability
    - File system access and disk space
    - Memory and CPU usage
    - Service dependencies
    """

    def __init__(self):
        """Initialize health checker."""
        self.checks = {}
        self.last_full_check = None
        self.cache_duration = 30  # Cache results for 30 seconds
        
    def register_check(self, name: str, check_func, critical: bool = True):
        """
        Register a health check function.
        
        Args:
            name: Check name
            check_func: Function that returns HealthStatus
            critical: Whether this check is critical for overall health
        """
        self.checks[name] = {
            "func": check_func,
            "critical": critical,
            "last_result": None,
            "last_run": None
        }

    def check_database(self) -> HealthStatus:
        """Check database connectivity and performance."""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            db.session.execute(db.text("SELECT 1"))
            
            # Test table access
            from src.database.models import User
            user_count = User.query.count()
            
            response_time = (time.time() - start_time) * 1000
            
            # Check performance
            if response_time > 1000:  # > 1 second
                status = "degraded"
                message = f"Database slow ({response_time:.0f}ms)"
            else:
                status = "healthy"
                message = "Database operational"
                
            return HealthStatus(
                name="database",
                status=status,
                message=message,
                details={
                    "user_count": user_count,
                    "response_time_ms": response_time,
                    "connection_pool": self._get_db_pool_info()
                },
                response_time_ms=response_time,
                last_checked=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                name="database",
                status="unhealthy",
                message=f"Database error: {str(e)}",
                details={"error": str(e)},
                response_time_ms=response_time,
                last_checked=datetime.utcnow().isoformat()
            )

    def check_file_system(self) -> HealthStatus:
        """Check file system access and disk space."""
        start_time = time.time()
        
        try:
            # Check temp directory
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            
            # Check output directory
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            # Test write access
            test_file = temp_dir / "health_check.tmp"
            test_file.write_text("health check")
            test_file.unlink()
            
            # Check disk space
            disk_usage = psutil.disk_usage('.')
            free_gb = disk_usage.free / (1024**3)
            total_gb = disk_usage.total / (1024**3)
            used_percent = (disk_usage.used / disk_usage.total) * 100
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on disk space
            if free_gb < 1:  # Less than 1GB free
                status = "unhealthy"
                message = f"Low disk space ({free_gb:.1f}GB free)"
            elif used_percent > 90:
                status = "degraded"
                message = f"High disk usage ({used_percent:.1f}%)"
            else:
                status = "healthy"
                message = "File system operational"
                
            return HealthStatus(
                name="file_system",
                status=status,
                message=message,
                details={
                    "temp_dir_exists": temp_dir.exists(),
                    "output_dir_exists": output_dir.exists(),
                    "free_space_gb": round(free_gb, 2),
                    "total_space_gb": round(total_gb, 2),
                    "used_percent": round(used_percent, 1)
                },
                response_time_ms=response_time,
                last_checked=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                name="file_system",
                status="unhealthy",
                message=f"File system error: {str(e)}",
                details={"error": str(e)},
                response_time_ms=response_time,
                last_checked=datetime.utcnow().isoformat()
            )

    def check_system_resources(self) -> HealthStatus:
        """Check system memory and CPU usage."""
        start_time = time.time()
        
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status
            if memory_percent > 90 or cpu_percent > 90:
                status = "unhealthy"
                message = f"High resource usage (CPU: {cpu_percent}%, RAM: {memory_percent}%)"
            elif memory_percent > 80 or cpu_percent > 80:
                status = "degraded"
                message = f"Elevated resource usage (CPU: {cpu_percent}%, RAM: {memory_percent}%)"
            else:
                status = "healthy"
                message = "System resources normal"
                
            return HealthStatus(
                name="system_resources",
                status=status,
                message=message,
                details={
                    "cpu_percent": round(cpu_percent, 1),
                    "memory_percent": round(memory_percent, 1),
                    "memory_available_gb": round(memory_available_gb, 2),
                    "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
                },
                response_time_ms=response_time,
                last_checked=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                name="system_resources",
                status="unhealthy",
                message=f"System resources error: {str(e)}",
                details={"error": str(e)},
                response_time_ms=response_time,
                last_checked=datetime.utcnow().isoformat()
            )

    def check_external_services(self) -> HealthStatus:
        """Check external service circuit breakers."""
        start_time = time.time()
        
        try:
            circuit_states = get_all_circuit_breakers()
            
            # Count service states
            healthy_count = 0
            total_count = len(circuit_states)
            service_details = {}
            
            for service_name, state in circuit_states.items():
                service_details[service_name] = {
                    "state": state["state"],
                    "failure_count": state["failure_count"],
                    "time_since_last_failure": state.get("time_since_last_failure", 0)
                }
                
                if state["state"] == "closed":
                    healthy_count += 1
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine overall status
            if healthy_count == total_count:
                status = "healthy"
                message = "All external services operational"
            elif healthy_count > 0:
                status = "degraded"
                message = f"{healthy_count}/{total_count} external services operational"
            else:
                status = "unhealthy"
                message = "All external services unavailable"
                
            return HealthStatus(
                name="external_services",
                status=status,
                message=message,
                details={
                    "services": service_details,
                    "healthy_count": healthy_count,
                    "total_count": total_count
                },
                response_time_ms=response_time,
                last_checked=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                name="external_services",
                status="unhealthy",
                message=f"External services check error: {str(e)}",
                details={"error": str(e)},
                response_time_ms=response_time,
                last_checked=datetime.utcnow().isoformat()
            )

    def _get_db_pool_info(self) -> Dict[str, Any]:
        """Get database connection pool information."""
        try:
            # This is database-specific, implement based on your DB
            return {
                "pool_size": "unknown",
                "checked_out": "unknown",
                "overflow": "unknown"
            }
        except:
            return {}

    def run_all_checks(self, force: bool = False) -> Dict[str, Any]:
        """
        Run all health checks.
        
        Args:
            force: Force checks even if cached results are available
            
        Returns:
            Dictionary with overall health status and individual check results
        """
        # Check cache
        if not force and self.last_full_check:
            cache_age = (datetime.utcnow() - self.last_full_check).total_seconds()
            if cache_age < self.cache_duration:
                logger.debug("Using cached health check results")
                return self._get_cached_results()
        
        start_time = time.time()
        
        # Run individual checks
        results = {
            "database": self.check_database(),
            "file_system": self.check_file_system(),
            "system_resources": self.check_system_resources(),
            "external_services": self.check_external_services()
        }
        
        # Calculate overall status
        critical_checks = ["database", "file_system"]
        overall_status = "healthy"
        
        for check_name, result in results.items():
            if check_name in critical_checks and result.status == "unhealthy":
                overall_status = "unhealthy"
                break
            elif result.status in ["degraded", "unhealthy"]:
                overall_status = "degraded"
        
        total_time = (time.time() - start_time) * 1000
        
        health_report = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "total_check_time_ms": round(total_time, 2),
            "checks": {name: asdict(result) for name, result in results.items()},
            "summary": {
                "healthy": sum(1 for r in results.values() if r.status == "healthy"),
                "degraded": sum(1 for r in results.values() if r.status == "degraded"),
                "unhealthy": sum(1 for r in results.values() if r.status == "unhealthy"),
                "total": len(results)
            }
        }
        
        self.last_full_check = datetime.utcnow()
        self._cache_results(health_report)
        
        return health_report

    def _get_cached_results(self) -> Dict[str, Any]:
        """Get cached health check results."""
        # Implement caching logic here
        return {"status": "unknown", "message": "No cached results available"}

    def _cache_results(self, results: Dict[str, Any]):
        """Cache health check results."""
        # Implement caching logic here
        pass

# Global health checker instance
health_checker = HealthChecker()
