"""
Service Registry - Centralized service management for processing services.

This module provides centralized registration and management of all processing services
with dependency tracking, lifecycle management, and service discovery.
"""

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from src.services.base_service import ServiceStatus
from utils.logger import logger


class ServiceState(Enum):
    """Service lifecycle states."""

    REGISTERED = "registered"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ServiceInfo:
    """Information about a registered service."""

    name: str
    service: Any
    state: ServiceState
    dependencies: List[str]
    dependents: List[str]
    registration_time: datetime
    last_health_check: Optional[datetime]
    health_status: ServiceStatus
    metadata: Dict[str, Any]
    initialization_attempts: int
    max_initialization_attempts: int


class ServiceRegistry:
    """
    Centralized registry for managing all processing services.
    """

    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self.service_groups: Dict[str, Set[str]] = {}
        self.initialization_order: List[str] = []
        self.shutdown_order: List[str] = []
        self.lock = threading.RLock()

        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            "service_registered": [],
            "service_started": [],
            "service_stopped": [],
            "service_failed": [],
            "dependency_resolved": [],
            "dependency_failed": [],
        }

        # Configuration
        self.auto_start_services = True
        self.dependency_timeout = 60  # seconds
        self.health_check_interval = 30  # seconds

        logger.info("ServiceRegistry initialized")

    def register_service(
        self,
        name: str,
        service: Any,
        dependencies: List[str] = None,
        group: str = None,
        metadata: Dict[str, Any] = None,
        max_init_attempts: int = 3,
    ) -> bool:
        """
        Register a service with the registry.

        Args:
            name: Unique service name
            service: Service instance
            dependencies: List of service dependencies
            group: Service group name
            metadata: Additional service metadata
            max_init_attempts: Maximum initialization attempts

        Returns:
            True if registration successful
        """
        with self.lock:
            if name in self.services:
                logger.warning(f"Service '{name}' is already registered")
                return False

            # Create service info
            service_info = ServiceInfo(
                name=name,
                service=service,
                state=ServiceState.REGISTERED,
                dependencies=dependencies or [],
                dependents=[],
                registration_time=datetime.now(timezone.utc),
                last_health_check=None,
                health_status=ServiceStatus.UNKNOWN,
                metadata=metadata or {},
                initialization_attempts=0,
                max_initialization_attempts=max_init_attempts,
            )

            self.services[name] = service_info

            # Update dependency graph
            self._update_dependency_graph(name, dependencies or [])

            # Add to group
            if group:
                if group not in self.service_groups:
                    self.service_groups[group] = set()
                self.service_groups[group].add(name)
                service_info.metadata["group"] = group

            # Calculate initialization order
            self._calculate_initialization_order()

            # Trigger event
            self._trigger_event("service_registered", service_info)

            logger.info(f"Registered service: {name} with dependencies: {dependencies}")

            if self.auto_start_services and self._dependencies_ready(name):
                self._start_service_async(name)

            return True

    def get_service(self, name: str) -> Optional[Any]:
        """
        Get a service instance by name.

        Args:
            name: Service name

        Returns:
            Service instance or None if not found
        """
        with self.lock:
            service_info = self.services.get(name)
            return service_info.service if service_info else None

    def get_service_status(self, name: str) -> Optional[ServiceStatus]:
        """Get service health status by name."""
        with self.lock:
            service_info = self.services.get(name)
            return service_info.health_status if service_info else None

    def list_services(self, group: str = None, state: ServiceState = None) -> List[str]:
        """
        List registered services with optional filtering.

        Args:
            group: Filter by service group
            state: Filter by service state

        Returns:
            List of service names
        """
        with self.lock:
            services = []

            for name, service_info in self.services.items():
                # Filter by group
                if group and service_info.metadata.get("group") != group:
                    continue

                # Filter by state
                if state and service_info.state != state:
                    continue

                services.append(name)

            return services

    def start_service(self, name: str) -> bool:
        """
        Start a service and its dependencies.

        Args:
            name: Service name to start

        Returns:
            True if service started successfully
        """
        with self.lock:
            if name not in self.services:
                logger.error(f"Service '{name}' is not registered")
                return False

            service_info = self.services[name]

            if service_info.state == ServiceState.RUNNING:
                logger.info(f"Service '{name}' is already running")
                return True

            # Check dependencies
            if not self._start_dependencies(name):
                logger.error(f"Failed to start dependencies for service '{name}'")
                return False

            # Start the service
            return self._start_service(name)

    def check_service_health(self, name: str) -> Optional[ServiceStatus]:
        """
        Check health of a specific service.

        Args:
            name: Service name to check

        Returns:
            ServiceStatus or None if service not found
        """
        with self.lock:
            if name not in self.services:
                return None

            service_info = self.services[name]
            service = service_info.service

            try:
                if hasattr(service, "health_check"):
                    is_healthy = service.health_check()
                    if isinstance(is_healthy, bool):
                        status = (
                            ServiceStatus.HEALTHY
                            if is_healthy
                            else ServiceStatus.UNHEALTHY
                        )
                    elif isinstance(is_healthy, dict):
                        status_str = is_healthy.get("status", "unknown").lower()
                        status = (
                            ServiceStatus(status_str)
                            if status_str in [s.value for s in ServiceStatus]
                            else ServiceStatus.UNKNOWN
                        )
                    else:
                        status = ServiceStatus.UNKNOWN
                elif hasattr(service, "status"):
                    status = service.status
                else:
                    # Default health check based on service state
                    status = (
                        ServiceStatus.HEALTHY
                        if service_info.state == ServiceState.RUNNING
                        else ServiceStatus.UNHEALTHY
                    )

                service_info.health_status = status
                service_info.last_health_check = datetime.now(timezone.utc)

                return status

            except Exception as e:
                logger.error(f"Health check failed for service '{name}': {e}")
                service_info.health_status = ServiceStatus.UNHEALTHY
                service_info.last_health_check = datetime.now(timezone.utc)
                return ServiceStatus.UNHEALTHY

    def get_registry_status(self) -> Dict[str, Any]:
        """Get overall registry status."""
        with self.lock:
            service_states = {}
            health_statuses = {}

            for name, service_info in self.services.items():
                service_states[service_info.state.value] = (
                    service_states.get(service_info.state.value, 0) + 1
                )
                health_statuses[service_info.health_status.value] = (
                    health_statuses.get(service_info.health_status.value, 0) + 1
                )

            return {
                "total_services": len(self.services),
                "service_states": service_states,
                "health_statuses": health_statuses,
                "service_groups": {
                    group: len(services)
                    for group, services in self.service_groups.items()
                },
                "initialization_order": self.initialization_order.copy(),
                "auto_start_enabled": self.auto_start_services,
                "registry_timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def _dependencies_ready(self, service_name: str) -> bool:
        """Check if all dependencies for a service are ready."""
        service_info = self.services.get(service_name)
        if not service_info:
            return False

        for dep_name in service_info.dependencies:
            dep_info = self.services.get(dep_name)
            if not dep_info or dep_info.state != ServiceState.RUNNING:
                return False

        return True

    def _start_dependencies(self, service_name: str) -> bool:
        """Start all dependencies for a service."""
        service_info = self.services.get(service_name)
        if not service_info:
            return False

        for dep_name in service_info.dependencies:
            if not self.start_service(dep_name):
                logger.error(
                    f"Failed to start dependency '{dep_name}' for service '{service_name}'"
                )
                return False

        return True

    def _start_service(self, name: str) -> bool:
        """Start a single service."""
        service_info = self.services[name]
        service = service_info.service

        try:
            service_info.state = ServiceState.INITIALIZING
            service_info.initialization_attempts += 1

            logger.info(
                f"Starting service: {name} (attempt {service_info.initialization_attempts})"
            )

            if hasattr(service, "initialize"):
                success = service.initialize()
                if not success:
                    raise Exception("Service initialization returned False")

            service_info.state = ServiceState.RUNNING
            service_info.health_status = ServiceStatus.HEALTHY

            # Trigger event
            self._trigger_event("service_started", service_info)

            logger.info(f"Successfully started service: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to start service '{name}': {e}")

            service_info.state = ServiceState.FAILED
            service_info.health_status = ServiceStatus.UNHEALTHY

            # Trigger event
            self._trigger_event("service_failed", service_info)

            return False

    def _update_dependency_graph(self, service_name: str, dependencies: List[str]):
        """Update the dependency graph for a service."""
        for dep_name in dependencies:
            if dep_name in self.services:
                self.services[dep_name].dependents.append(service_name)

    def _calculate_initialization_order(self):
        """Calculate the order in which services should be initialized."""
        # Simple topological sort
        visited = set()
        order = []

        def visit(service_name: str):
            if service_name not in visited and service_name in self.services:
                visited.add(service_name)
                for dep_name in self.services[service_name].dependencies:
                    visit(dep_name)
                order.append(service_name)

        for service_name in self.services:
            visit(service_name)

        self.initialization_order = order
        self.shutdown_order = list(reversed(order))

    def _start_service_async(self, name: str):
        """Start a service asynchronously."""

        def start_worker():
            self.start_service(name)

        thread = threading.Thread(target=start_worker, daemon=True)
        thread.start()

    def _trigger_event(self, event_type: str, service_info: ServiceInfo):
        """Trigger event handlers for a service event."""
        for handler in self.event_handlers.get(event_type, []):
            try:
                handler(service_info)
            except Exception as e:
                logger.error(f"Event handler failed for {event_type}: {e}")


# Global instance
service_registry = ServiceRegistry()
