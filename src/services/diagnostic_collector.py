"""
Diagnostic Collector - Gathers system health information and diagnostics.

This module provides comprehensive diagnostic information collection for
troubleshooting and system analysis.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import platform
import threading
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

import psutil

from src.services.monitoring.monitoring_service import health_monitor
from src.services.service_registry import service_registry
from utils.logger import logger

@dataclass
class SystemInfo:
    """System information structure."""

    platform: str
    platform_version: str
    architecture: str
    hostname: str
    python_version: str
    cpu_count: int
    memory_total_gb: float
    disk_total_gb: float
    uptime_seconds: float

@dataclass
class ProcessInfo:
    """Process information structure."""

    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    threads: int
    status: str
    create_time: datetime

@dataclass
class DiagnosticReport:
    """Comprehensive diagnostic report."""

    timestamp: datetime
    system_info: SystemInfo
    process_info: ProcessInfo
    service_health: Dict[str, Any]
    resource_usage: Dict[str, Any]
    error_summary: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    configuration_info: Dict[str, Any]
    recommendations: List[str]

class DiagnosticCollector:
    """
    Collects comprehensive diagnostic information for system analysis.
    """

    def __init__(self):
        self.collection_history: List[DiagnosticReport] = []
        self.max_history_size = 100
        self.lock = threading.RLock()

        logger.info("DiagnosticCollector initialized")

    def collect_system_info(self) -> SystemInfo:
        """Collect basic system information."""
        try:
            # Get system information
            uname = platform.uname()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Calculate uptime
            boot_time = psutil.boot_time()
            uptime = datetime.now().timestamp() - boot_time

            return SystemInfo(
                platform=uname.system,
                platform_version=uname.release,
                architecture=uname.machine,
                hostname=uname.node,
                python_version=sys.version.split()[0],
                cpu_count=psutil.cpu_count(),
                memory_total_gb=memory.total / (1024**3),
                disk_total_gb=disk.total / (1024**3),
                uptime_seconds=uptime,
            )

        except Exception as e:
            logger.error(f"Failed to collect system info: {e}")
            return SystemInfo(
                platform="unknown",
                platform_version="unknown",
                architecture="unknown",
                hostname="unknown",
                python_version=sys.version.split()[0],
                cpu_count=0,
                memory_total_gb=0.0,
                disk_total_gb=0.0,
                uptime_seconds=0.0,
            )

    def collect_process_info(self) -> ProcessInfo:
        """Collect current process information."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            return ProcessInfo(
                pid=process.pid,
                name=process.name(),
                cpu_percent=process.cpu_percent(),
                memory_percent=process.memory_percent(),
                memory_mb=memory_info.rss / (1024**2),
                threads=process.num_threads(),
                status=process.status(),
                create_time=datetime.fromtimestamp(process.create_time()),
            )

        except Exception as e:
            logger.error(f"Failed to collect process info: {e}")
            return ProcessInfo(
                pid=os.getpid(),
                name="unknown",
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_mb=0.0,
                threads=0,
                status="unknown",
                create_time=datetime.now(),
            )

    def collect_resource_usage(self) -> Dict[str, Any]:
        """Collect system resource usage information."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)

            # Memory usage
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disk usage
            disk_usage = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.mountpoint] = {
                        "total_gb": usage.total / (1024**3),
                        "used_gb": usage.used / (1024**3),
                        "free_gb": usage.free / (1024**3),
                        "percent": (usage.used / usage.total) * 100,
                    }
                except PermissionError:
                    continue

            # Network I/O
            network_io = psutil.net_io_counters()

            # Disk I/O
            disk_io = psutil.disk_io_counters()

            return {
                "cpu": {
                    "overall_percent": cpu_percent,
                    "per_core_percent": cpu_per_core,
                    "load_average": (
                        os.getloadavg() if hasattr(os, "getloadavg") else None
                    ),
                },
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "used_gb": memory.used / (1024**3),
                    "percent": memory.percent,
                    "swap_total_gb": swap.total / (1024**3),
                    "swap_used_gb": swap.used / (1024**3),
                    "swap_percent": swap.percent,
                },
                "disk": disk_usage,
                "network": (
                    {
                        "bytes_sent": network_io.bytes_sent if network_io else 0,
                        "bytes_recv": network_io.bytes_recv if network_io else 0,
                        "packets_sent": network_io.packets_sent if network_io else 0,
                        "packets_recv": network_io.packets_recv if network_io else 0,
                    }
                    if network_io
                    else {}
                ),
                "disk_io": (
                    {
                        "read_bytes": disk_io.read_bytes if disk_io else 0,
                        "write_bytes": disk_io.write_bytes if disk_io else 0,
                        "read_count": disk_io.read_count if disk_io else 0,
                        "write_count": disk_io.write_count if disk_io else 0,
                    }
                    if disk_io
                    else {}
                ),
            }

        except Exception as e:
            logger.error(f"Failed to collect resource usage: {e}")
            return {}

    def collect_service_health(self) -> Dict[str, Any]:
        """Collect service health information."""
        try:
            overall_health = health_monitor.get_overall_health()

            # Get service registry status
            registry_status = service_registry.get_registry_status()

            # Get recent alerts
            recent_alerts = health_monitor.get_alerts(limit=10)

            return {
                "overall_health": overall_health,
                "service_registry": registry_status,
                "recent_alerts": [asdict(alert) for alert in recent_alerts],
                "monitoring_active": health_monitor.monitoring_active,
            }

        except Exception as e:
            logger.error(f"Failed to collect service health: {e}")
            return {}

    def collect_error_summary(self) -> Dict[str, Any]:
        """Collect error summary information."""
        try:
            from src.services.enhanced_processing_error_system import (
                enhanced_error_system,
            )

            system_health = enhanced_error_system.get_system_health()

            # Extract error statistics
            error_stats = system_health.get("error_handler", {}).get("statistics", {})

            return {
                "error_statistics": error_stats,
                "recent_errors": error_stats.get("recent_errors", []),
                "error_categories": error_stats.get("categories", {}),
                "error_services": error_stats.get("services", {}),
                "total_errors": error_stats.get("total_errors", 0),
            }

        except Exception as e:
            logger.error(f"Failed to collect error summary: {e}")
            return {}

    def collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics."""
        try:
            metrics = {}

            for service_name in service_registry.list_services():
                service_metrics = health_monitor.get_service_metrics(service_name)
                if service_metrics:
                    metrics[service_name] = {
                        "response_times": [
                            m.value
                            for m in service_metrics
                            if m.name == "response_time"
                        ][-10:],
                        "last_response_time": (
                            service_metrics[-1].value if service_metrics else 0
                        ),
                    }

            # System performance
            metrics["system"] = {
                "cpu_usage_history": [],  # Would need to track over time
                "memory_usage_history": [],  # Would need to track over time
                "current_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {e}")
            return {}

    def collect_configuration_info(self) -> Dict[str, Any]:
        """Collect configuration information."""
        try:
            config_info = {}

            safe_env_vars = {}
            for key, value in os.environ.items():
                # Only include non-sensitive environment variables
                if not any(
                    sensitive in key.upper()
                    for sensitive in ["PASSWORD", "SECRET", "KEY", "TOKEN"]
                ):
                    safe_env_vars[key] = value

            config_info["environment_variables"] = safe_env_vars

            # Python path and modules
            config_info["python_path"] = sys.path
            config_info["installed_packages"] = (
                []
            )  # Could use pkg_resources to get this

            # Application configuration
            config_info["working_directory"] = os.getcwd()
            config_info["executable"] = sys.executable

            # File system information
            config_info["file_system"] = {
                "temp_dir_exists": Path("temp").exists(),
                "logs_dir_exists": Path("logs").exists(),
                "uploads_dir_exists": Path("uploads").exists(),
                "templates_dir_exists": Path("templates").exists(),
            }

            return config_info

        except Exception as e:
            logger.error(f"Failed to collect configuration info: {e}")
            return {}

    def generate_recommendations(self, diagnostic_data: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on diagnostic data."""
        recommendations = []

        try:
            # Check resource usage
            resource_usage = diagnostic_data.get("resource_usage", {})

            # CPU recommendations
            cpu_info = resource_usage.get("cpu", {})
            if cpu_info.get("overall_percent", 0) > 80:
                recommendations.append(
                    "High CPU usage detected. Consider optimizing processing algorithms or scaling resources."
                )

            # Memory recommendations
            memory_info = resource_usage.get("memory", {})
            if memory_info.get("percent", 0) > 85:
                recommendations.append(
                    "High memory usage detected. Consider implementing memory optimization or increasing available RAM."
                )

            # Disk recommendations
            disk_info = resource_usage.get("disk", {})
            for mount_point, disk_data in disk_info.items():
                if disk_data.get("percent", 0) > 90:
                    recommendations.append(
                        f"Disk space critical on {mount_point}. Clean up old files or increase storage capacity."
                    )

            # Service health recommendations
            service_health = diagnostic_data.get("service_health", {})
            overall_health = service_health.get("overall_health", {})

            if overall_health.get("status") == "unhealthy":
                recommendations.append(
                    "System health is unhealthy. Check service logs and restart failed services."
                )
            elif overall_health.get("status") == "degraded":
                recommendations.append(
                    "System health is degraded. Monitor service performance and consider maintenance."
                )

            # Error recommendations
            error_summary = diagnostic_data.get("error_summary", {})
            total_errors = error_summary.get("total_errors", 0)

            if total_errors > 100:
                recommendations.append(
                    "High error count detected. Review error logs and implement fixes for common issues."
                )

            # Performance recommendations
            process_info = diagnostic_data.get("process_info")
            if process_info and process_info.memory_mb > 1000:  # 1GB
                recommendations.append(
                    "High memory usage by application process. Consider memory optimization."
                )

            if not recommendations:
                recommendations.append(
                    "System appears to be running normally. Continue regular monitoring."
                )

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            recommendations.append(
                "Unable to generate recommendations due to diagnostic error."
            )

        return recommendations

    def collect_full_diagnostic(self) -> DiagnosticReport:
        """Collect comprehensive diagnostic information."""
        logger.info("Collecting full diagnostic information")

        try:
            # Collect all diagnostic data
            system_info = self.collect_system_info()
            process_info = self.collect_process_info()
            service_health = self.collect_service_health()
            resource_usage = self.collect_resource_usage()
            error_summary = self.collect_error_summary()
            performance_metrics = self.collect_performance_metrics()
            configuration_info = self.collect_configuration_info()

            diagnostic_data = {
                "system_info": asdict(system_info),
                "process_info": asdict(process_info),
                "service_health": service_health,
                "resource_usage": resource_usage,
                "error_summary": error_summary,
                "performance_metrics": performance_metrics,
                "configuration_info": configuration_info,
            }

            # Generate recommendations
            recommendations = self.generate_recommendations(diagnostic_data)

            # Create diagnostic report
            report = DiagnosticReport(
                timestamp=datetime.now(timezone.utc),
                system_info=system_info,
                process_info=process_info,
                service_health=service_health,
                resource_usage=resource_usage,
                error_summary=error_summary,
                performance_metrics=performance_metrics,
                configuration_info=configuration_info,
                recommendations=recommendations,
            )

            # Store in history
            with self.lock:
                self.collection_history.append(report)
                if len(self.collection_history) > self.max_history_size:
                    self.collection_history = self.collection_history[
                        -self.max_history_size :
                    ]

            logger.info("Full diagnostic collection completed")
            return report

        except Exception as e:
            logger.error(f"Failed to collect full diagnostic: {e}")
            # Return minimal report on error
            return DiagnosticReport(
                timestamp=datetime.now(timezone.utc),
                system_info=self.collect_system_info(),
                process_info=self.collect_process_info(),
                service_health={},
                resource_usage={},
                error_summary={},
                performance_metrics={},
                configuration_info={},
                recommendations=["Diagnostic collection failed. Check system logs."],
            )

    def get_diagnostic_history(self, limit: int = 10) -> List[DiagnosticReport]:
        """Get diagnostic collection history."""
        with self.lock:
            return self.collection_history[-limit:] if self.collection_history else []

    def export_diagnostic_report(
        self, output_file: str, report: DiagnosticReport = None
    ) -> bool:
        """Export diagnostic report to file."""
        try:
            import json

            if report is None:
                report = self.collect_full_diagnostic()

            report_dict = asdict(report)

            # Handle datetime serialization
            def datetime_handler(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2, default=datetime_handler)

            logger.info(f"Diagnostic report exported to: {output_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to export diagnostic report: {e}")
            return False

    def clear_history(self):
        """Clear diagnostic collection history."""
        with self.lock:
            self.collection_history.clear()
        logger.info("Diagnostic history cleared")

# Global instance
diagnostic_collector = DiagnosticCollector()
