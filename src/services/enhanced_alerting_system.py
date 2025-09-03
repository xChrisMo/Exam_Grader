"""
Enhanced Alerting System

This module provides comprehensive alerting capabilities with configurable thresholds,
multiple notification channels, and intelligent alert management.
"""

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from src.config.processing_config import ProcessingConfigManager
from src.services.monitoring.monitoring_service import (
    health_monitor,
    performance_monitor,
)
from src.services.monitoring_dashboard import (
    AlertSeverity,
    MonitoringAlert,
    monitoring_dashboard_service,
)
from utils.logger import logger


class AlertChannel(Enum):
    """Alert notification channels"""

    LOG = "log"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    CONSOLE = "console"


class AlertRule(Enum):
    """Predefined alert rules"""

    HIGH_ERROR_RATE = "high_error_rate"
    SERVICE_DOWN = "service_down"
    HIGH_RESPONSE_TIME = "high_response_time"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CACHE_MISS_RATE = "cache_miss_rate"
    PROCESSING_FAILURE = "processing_failure"


@dataclass
class AlertThreshold:
    """Alert threshold configuration"""

    metric_name: str
    warning_value: float
    critical_value: float
    comparison: str = "greater_than"  # greater_than, less_than, equals
    duration_minutes: int = 5  # How long condition must persist

    def check_threshold(self, value: float) -> Optional[AlertSeverity]:
        """Check if value exceeds thresholds"""
        if self.comparison == "greater_than":
            if value >= self.critical_value:
                return AlertSeverity.CRITICAL
            elif value >= self.warning_value:
                return AlertSeverity.HIGH
        elif self.comparison == "less_than":
            if value <= self.critical_value:
                return AlertSeverity.CRITICAL
            elif value <= self.warning_value:
                return AlertSeverity.HIGH
        elif self.comparison == "equals":
            if value == self.critical_value:
                return AlertSeverity.CRITICAL
            elif value == self.warning_value:
                return AlertSeverity.HIGH

        return None


@dataclass
class AlertNotificationConfig:
    """Alert notification configuration"""

    channels: List[AlertChannel] = field(default_factory=list)
    email_recipients: List[str] = field(default_factory=list)
    webhook_urls: List[str] = field(default_factory=list)
    slack_webhook_url: Optional[str] = None
    cooldown_minutes: int = 15
    escalation_minutes: int = 60


@dataclass
class AlertState:
    """State tracking for alerts"""

    rule: AlertRule
    first_triggered: datetime
    last_triggered: datetime
    last_sent: Optional[datetime] = None
    count: int = 1
    current_severity: AlertSeverity = AlertSeverity.LOW
    escalated: bool = False


class EnhancedAlertingSystem:
    """
    Enhanced alerting system with configurable thresholds and multiple notification channels.
    """

    def __init__(self):
        # Initialize processing configuration
        self._config_manager = ProcessingConfigManager()
        self._error_config = self._config_manager.get_error_handling_config()
        self._health_config = self._config_manager.get_health_check_config()

        # Alert state tracking
        self._alert_states: Dict[str, AlertState] = {}
        self._alert_history: List[MonitoringAlert] = []
        self._notification_config = AlertNotificationConfig()

        # Monitoring thread
        self._monitoring_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.RLock()

        self._setup_alert_thresholds()

        # Setup notification channels
        self._setup_notification_channels()

        logger.info("Enhanced alerting system initialized")

    def _setup_alert_thresholds(self):
        """Setup alert thresholds from processing configuration"""
        self._thresholds: Dict[AlertRule, AlertThreshold] = {}

        if self._health_config and self._health_config.enabled:
            thresholds = self._health_config.thresholds

            # Response time thresholds
            self._thresholds[AlertRule.HIGH_RESPONSE_TIME] = AlertThreshold(
                metric_name="response_time_ms",
                warning_value=thresholds.response_time_warning_ms,
                critical_value=thresholds.response_time_critical_ms,
                comparison="greater_than",
                duration_minutes=2,
            )

            # Error rate thresholds
            self._thresholds[AlertRule.HIGH_ERROR_RATE] = AlertThreshold(
                metric_name="error_rate",
                warning_value=thresholds.error_rate_warning,
                critical_value=thresholds.error_rate_critical,
                comparison="greater_than",
                duration_minutes=5,
            )

            # Resource usage thresholds
            self._thresholds[AlertRule.RESOURCE_EXHAUSTION] = AlertThreshold(
                metric_name="resource_usage",
                warning_value=thresholds.memory_usage_warning,
                critical_value=thresholds.memory_usage_critical,
                comparison="greater_than",
                duration_minutes=10,
            )

        if not self._thresholds:
            self._thresholds = {
                AlertRule.HIGH_ERROR_RATE: AlertThreshold("error_rate", 0.05, 0.15),
                AlertRule.HIGH_RESPONSE_TIME: AlertThreshold(
                    "response_time_ms", 5000, 10000
                ),
                AlertRule.RESOURCE_EXHAUSTION: AlertThreshold(
                    "resource_usage", 0.80, 0.95
                ),
                AlertRule.CACHE_MISS_RATE: AlertThreshold(
                    "cache_miss_rate", 0.70, 0.90
                ),
            }

    def _setup_notification_channels(self):
        """Setup notification channels from configuration"""
        if self._error_config and self._error_config.get("notification", {}).get(
            "enabled"
        ):
            notification_config = self._error_config["notification"]

            # Parse channels
            channels = notification_config.get("channels", ["log"])
            self._notification_config.channels = [
                AlertChannel(channel)
                for channel in channels
                if channel in [c.value for c in AlertChannel]
            ]

            # Set cooldown
            self._notification_config.cooldown_minutes = notification_config.get(
                "cooldown_minutes", 15
            )

            logger.info(
                f"Configured notification channels: {[c.value for c in self._notification_config.channels]}"
            )
        else:
            # Default to log only
            self._notification_config.channels = [AlertChannel.LOG]

    def start_monitoring(self):
        """Start background alert monitoring"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return

        self._running = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_worker, daemon=True
        )
        self._monitoring_thread.start()

        # Register with monitoring dashboard
        monitoring_dashboard_service.add_alert_handler(self._handle_dashboard_alert)

        logger.info("Enhanced alerting system monitoring started")

    def stop_monitoring(self):
        """Stop background alert monitoring"""
        self._running = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
        try:
            logger.info("Enhanced alerting system monitoring stopped")
        except Exception:
            # Ignore logging errors during shutdown
            pass

    def _monitoring_worker(self):
        """Background monitoring worker"""
        while self._running:
            try:
                # Check all alert rules
                self._check_service_health_alerts()
                self._check_performance_alerts()
                self._check_resource_alerts()
                self._check_processing_alerts()

                # Process escalations
                self._process_escalations()

                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in alerting monitoring worker: {e}")
                time.sleep(60)  # Wait longer on error

    def _check_service_health_alerts(self):
        """Check for service health alerts"""
        try:
            health_status = health_monitor.get_overall_health()
            if not health_status:
                return

            # Check individual service health
            for service_name, service_health in health_status.get(
                "services", {}
            ).items():
                if service_health.get("status") == "unhealthy":
                    self._trigger_alert(
                        AlertRule.SERVICE_DOWN,
                        f"Service {service_name} is unhealthy",
                        f"Service {service_name} has failed health checks",
                        AlertSeverity.CRITICAL,
                        {"service": service_name, "health_data": service_health},
                    )
                elif service_health.get("error_count", 0) > 5:
                    self._trigger_alert(
                        AlertRule.HIGH_ERROR_RATE,
                        f"High error count for {service_name}",
                        f"Service {service_name} has {service_health.get('error_count')} errors",
                        AlertSeverity.HIGH,
                        {
                            "service": service_name,
                            "error_count": service_health.get("error_count"),
                        },
                    )

        except Exception as e:
            logger.error(f"Error checking service health alerts: {e}")

    def _check_performance_alerts(self):
        """Check for performance-related alerts"""
        try:
            # Get performance summary
            perf_summary = performance_monitor.get_performance_summary()
            if not perf_summary:
                return

            # Check response times
            avg_response_time = perf_summary.get("average_response_time", 0)
            threshold = self._thresholds.get(AlertRule.HIGH_RESPONSE_TIME)
            if threshold:
                severity = threshold.check_threshold(avg_response_time)
                if severity:
                    self._trigger_alert(
                        AlertRule.HIGH_RESPONSE_TIME,
                        "High response time detected",
                        f"Average response time is {avg_response_time:.2f}ms",
                        severity,
                        {
                            "response_time": avg_response_time,
                            "threshold": threshold.warning_value,
                        },
                    )

            # Check error rates
            error_rate = perf_summary.get("error_rate", 0)
            threshold = self._thresholds.get(AlertRule.HIGH_ERROR_RATE)
            if threshold:
                severity = threshold.check_threshold(error_rate)
                if severity:
                    self._trigger_alert(
                        AlertRule.HIGH_ERROR_RATE,
                        "High error rate detected",
                        f"Error rate is {error_rate:.2%}",
                        severity,
                        {
                            "error_rate": error_rate,
                            "threshold": threshold.warning_value,
                        },
                    )

        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")

    def _check_resource_alerts(self):
        """Check for resource usage alerts"""
        try:
            from src.services.resource_optimizer import resource_optimizer

            resources = resource_optimizer.get_system_resources()

            threshold = self._thresholds.get(AlertRule.RESOURCE_EXHAUSTION)
            if not threshold:
                return

            for resource_name, resource_info in resources.items():
                usage = resource_info.usage_percentage / 100.0  # Convert to decimal
                severity = threshold.check_threshold(usage)

                if severity:
                    self._trigger_alert(
                        AlertRule.RESOURCE_EXHAUSTION,
                        f"High {resource_name} usage",
                        f"{resource_name} usage is {usage:.1%}",
                        severity,
                        {
                            "resource": resource_name,
                            "usage": usage,
                            "threshold": threshold.warning_value,
                        },
                    )

        except Exception as e:
            logger.error(f"Error checking resource alerts: {e}")

    def _check_processing_alerts(self):
        """Check for processing-related alerts"""
        try:
            # Check cache performance
            from src.services.cache_manager import cache_manager

            cache_stats = cache_manager.get_stats()

            if not isinstance(cache_stats, dict):
                logger.debug(f"Cache stats is not a dict, got: {type(cache_stats)}")
                return

            if isinstance(cache_stats, dict) and "levels" in cache_stats:
                # Check overall cache performance
                overall_hit_rate = cache_stats.get("overall_hit_rate", 0.0)
                miss_rate = 1.0 - overall_hit_rate
                threshold = self._thresholds.get(AlertRule.CACHE_MISS_RATE)

                if threshold:
                    severity = threshold.check_threshold(miss_rate)
                    if severity:
                        self._trigger_alert(
                            AlertRule.CACHE_MISS_RATE,
                            f"High cache miss rate",
                            f"Overall cache miss rate is {miss_rate:.1%}",
                            severity,
                            {"miss_rate": miss_rate, "hit_rate": overall_hit_rate},
                        )

                # Check individual cache levels
                for cache_name, stats in cache_stats.get("levels", {}).items():
                    if isinstance(stats, dict):
                        hits = stats.get("hits", 0)
                        misses = stats.get("misses", 0)
                        total = hits + misses
                        if total > 0:
                            level_miss_rate = misses / total
                            if threshold:
                                severity = threshold.check_threshold(level_miss_rate)
                                if severity:
                                    self._trigger_alert(
                                        AlertRule.CACHE_MISS_RATE,
                                        f"High cache miss rate for {cache_name}",
                                        f"Cache miss rate is {level_miss_rate:.1%}",
                                        severity,
                                        {
                                            "cache": cache_name,
                                            "miss_rate": level_miss_rate,
                                        },
                                    )

        except Exception as e:
            logger.error(f"Error checking processing alerts: {e}")

    def _trigger_alert(
        self,
        rule: AlertRule,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Dict[str, Any],
    ):
        """Trigger an alert with cooldown and escalation logic"""
        with self._lock:
            rule_key = rule.value
            current_time = datetime.now(timezone.utc)

            if rule_key in self._alert_states:
                alert_state = self._alert_states[rule_key]

                # Check cooldown period
                if (
                    alert_state.last_sent
                    and current_time - alert_state.last_sent
                    < timedelta(minutes=self._notification_config.cooldown_minutes)
                ):
                    return  # Still in cooldown

                # Update existing state
                alert_state.last_triggered = current_time
                alert_state.count += 1
                alert_state.current_severity = severity
            else:
                # Create new alert state
                alert_state = AlertState(
                    rule=rule,
                    first_triggered=current_time,
                    last_triggered=current_time,
                    current_severity=severity,
                )
                self._alert_states[rule_key] = alert_state

            # Send notification
            self._send_alert_notification(title, message, severity, metadata)
            alert_state.last_sent = current_time

    def _send_alert_notification(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Dict[str, Any],
    ):
        """Send alert notification through configured channels"""
        # Create monitoring dashboard alert
        alert_id = monitoring_dashboard_service.create_alert(
            title, message, severity, "enhanced_alerting", metadata
        )

        # Send through configured channels
        for channel in self._notification_config.channels:
            try:
                if channel == AlertChannel.LOG:
                    self._send_log_alert(title, message, severity, metadata)
                elif channel == AlertChannel.EMAIL:
                    self._send_email_alert(title, message, severity, metadata)
                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook_alert(title, message, severity, metadata)
                elif channel == AlertChannel.CONSOLE:
                    self._send_console_alert(title, message, severity, metadata)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel.value}: {e}")

    def _send_log_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Dict[str, Any],
    ):
        """Send alert to log"""
        log_message = f"ALERT [{severity.value.upper()}] {title}: {message}"
        if severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
            logger.error(log_message)
        else:
            logger.warning(log_message)

    def _send_email_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Dict[str, Any],
    ):
        """Send alert via email"""
        # This would require email configuration
        logger.info(f"Email alert would be sent: {title}")

    def _send_webhook_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Dict[str, Any],
    ):
        """Send alert via webhook"""
        # This would require webhook configuration
        logger.info(f"Webhook alert would be sent: {title}")

    def _send_console_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Dict[str, Any],
    ):
        """Send alert to console"""
        print(f"\n🚨 ALERT [{severity.value.upper()}] {title}")
        print(f"   {message}")
        print(
            f"   Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        if metadata:
            print(f"   Metadata: {json.dumps(metadata, indent=2)}")
        print()

    def _process_escalations(self):
        """Process alert escalations"""
        current_time = datetime.now(timezone.utc)

        with self._lock:
            for rule_key, alert_state in self._alert_states.items():
                if (
                    not alert_state.escalated
                    and current_time - alert_state.first_triggered
                    > timedelta(minutes=self._notification_config.escalation_minutes)
                ):

                    # Escalate alert
                    self._send_alert_notification(
                        f"ESCALATED: {rule_key}",
                        f"Alert {rule_key} has been active for {self._notification_config.escalation_minutes} minutes",
                        AlertSeverity.CRITICAL,
                        {"escalated": True, "original_rule": rule_key},
                    )
                    alert_state.escalated = True

    def _handle_dashboard_alert(self, alert: MonitoringAlert):
        """Handle alerts from monitoring dashboard"""
        logger.info(f"Received dashboard alert: {alert.title}")

    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alerting system statistics"""
        with self._lock:
            active_alerts = len(self._alert_states)
            escalated_alerts = sum(
                1 for state in self._alert_states.values() if state.escalated
            )

            return {
                "active_alerts": active_alerts,
                "escalated_alerts": escalated_alerts,
                "total_alert_rules": len(self._thresholds),
                "notification_channels": [
                    c.value for c in self._notification_config.channels
                ],
                "monitoring_active": self._running,
                "alert_states": {
                    rule_key: {
                        "first_triggered": state.first_triggered.isoformat(),
                        "last_triggered": state.last_triggered.isoformat(),
                        "count": state.count,
                        "severity": state.current_severity.value,
                        "escalated": state.escalated,
                    }
                    for rule_key, state in self._alert_states.items()
                },
            }

    def clear_alert_state(self, rule: AlertRule) -> bool:
        """Clear alert state for a rule"""
        with self._lock:
            rule_key = rule.value
            if rule_key in self._alert_states:
                del self._alert_states[rule_key]
                logger.info(f"Cleared alert state for rule: {rule_key}")
                return True
            return False

    def update_threshold(self, rule: AlertRule, threshold: AlertThreshold):
        """Update alert threshold for a rule"""
        self._thresholds[rule] = threshold
        logger.info(f"Updated threshold for rule {rule.value}")


# Global instance
enhanced_alerting_system = EnhancedAlertingSystem()
