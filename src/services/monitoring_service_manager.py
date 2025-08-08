"""
Monitoring Service Manager

This module manages the initialization and coordination of monitoring services.
"""

from typing import Dict, Any, List
from utils.logger import logger


class MonitoringServiceManager:
    """Manager for coordinating monitoring services"""
    
    def __init__(self):
        self.services = {}
        self.initialized = False
        
    def initialize(self) -> bool:
        """Initialize all monitoring services"""
        try:
            # Import monitoring services
            from src.services.monitoring.monitoring_service import monitoring_service
            
            # Register services
            self.services['monitoring'] = monitoring_service
            
            # Initialize services
            for name, service in self.services.items():
                if hasattr(service, 'initialize'):
                    service.initialize()
                logger.info(f"Initialized monitoring service: {name}")
            
            self.initialized = True
            logger.info("Monitoring service manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring service manager: {e}")
            return False
    
    def get_service(self, name: str):
        """Get a monitoring service by name"""
        return self.services.get(name)
    
    def start_all_services(self) -> bool:
        """Start all monitoring services"""
        try:
            for name, service in self.services.items():
                if hasattr(service, 'start'):
                    service.start()
                    logger.info(f"Started monitoring service: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to start monitoring services: {e}")
            return False
    
    def stop_all_services(self) -> bool:
        """Stop all monitoring services"""
        try:
            for name, service in self.services.items():
                if hasattr(service, 'stop'):
                    service.stop()
                    logger.info(f"Stopped monitoring service: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop monitoring services: {e}")
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all monitoring services"""
        status = {
            'overall': 'healthy',
            'services': {}
        }
        
        for name, service in self.services.items():
            try:
                if hasattr(service, 'health_check'):
                    service_health = service.health_check()
                    status['services'][name] = 'healthy' if service_health else 'unhealthy'
                else:
                    status['services'][name] = 'unknown'
            except Exception as e:
                status['services'][name] = f'error: {str(e)}'
                status['overall'] = 'degraded'
        
        return status


# Global instance
monitoring_service_manager = MonitoringServiceManager()