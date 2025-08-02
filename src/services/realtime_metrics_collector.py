"""
Real-time Metrics Collector

This module provides real-time collection and analysis of system metrics
with configurable collection intervals and intelligent data aggregation.
"""

import time
import threading
import psutil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from collections import deque, defaultdict
from enum import Enum
import json

from src.config.processing_config import ProcessingConfigManager
from src.services.health_monitor import health_monitor
from src.services.performance_monitor import performance_monitor
from src.services.cache_manager import cache_manager
from utils.logger import logger

class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class MetricPoint:
    """Individual metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'labels': self.labels
        }

@dataclass
class MetricSeries:
    """Time series of metric points"""
    name: str
    metric_type: MetricType
    points: deque = field(default_factory=lambda: deque(maxlen=1000))
    description: str = ""
    unit: str = ""
    
    def add_point(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Add a metric point"""
        point = MetricPoint(
            timestamp=datetime.now(timezone.utc),
            value=value,
            labels=labels or {}
        )
        self.points.append(point)
    
    def get_latest(self) -> Optional[MetricPoint]:
        """Get latest metric point"""
        return self.points[-1] if self.points else None
    
    def get_average(self, minutes: int = 5) -> float:
        """Get average value over specified minutes"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_points = [
            p for p in self.points 
            if p.timestamp >= cutoff_time
        ]
        
        if not recent_points:
            return 0.0
        
        return sum(p.value for p in recent_points) / len(recent_points)
    
    def get_max(self, minutes: int = 5) -> float:
        """Get maximum value over specified minutes"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_points = [
            p for p in self.points 
            if p.timestamp >= cutoff_time
        ]
        
        return max((p.value for p in recent_points), default=0.0)
    
    def get_trend(self, minutes: int = 10) -> str:
        """Get trend direction over specified minutes"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_points = [
            p for p in self.points 
            if p.timestamp >= cutoff_time
        ]
        
        if len(recent_points) < 2:
            return "stable"
        
        # Simple trend calculation
        first_half = recent_points[:len(recent_points)//2]
        second_half = recent_points[len(recent_points)//2:]
        
        first_avg = sum(p.value for p in first_half) / len(first_half)
        second_avg = sum(p.value for p in second_half) / len(second_half)
        
        if second_avg > first_avg * 1.1:
            return "increasing"
        elif second_avg < first_avg * 0.9:
            return "decreasing"
        else:
            return "stable"

class RealtimeMetricsCollector:
    """
    Real-time metrics collector with configurable collection intervals
    and intelligent data aggregation.
    """
    
    def __init__(self):
        # Initialize processing configuration
        self._config_manager = ProcessingConfigManager()
        self._health_config = self._config_manager.get_health_check_config()
        
        # Metrics storage
        self._metrics: Dict[str, MetricSeries] = {}
        self._collectors: Dict[str, Callable[[], Dict[str, float]]] = {}
        
        # Collection configuration
        self._collection_interval = (
            self._health_config.get_interval('performance_metrics') 
            if self._health_config.enabled else 30
        )
        
        # Monitoring thread
        self._monitoring_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.RLock()
        
        # Setup default metrics and collectors
        self._setup_default_metrics()
        self._setup_default_collectors()
        
        logger.info(f"Real-time metrics collector initialized (interval: {self._collection_interval}s)")
    
    def _setup_default_metrics(self):
        """Setup default metric series"""
        # System metrics
        self.register_metric("system.cpu.usage", MetricType.GAUGE, "CPU usage percentage", "%")
        self.register_metric("system.memory.usage", MetricType.GAUGE, "Memory usage percentage", "%")
        self.register_metric("system.disk.usage", MetricType.GAUGE, "Disk usage percentage", "%")
        self.register_metric("system.network.bytes_sent", MetricType.COUNTER, "Network bytes sent", "bytes")
        self.register_metric("system.network.bytes_recv", MetricType.COUNTER, "Network bytes received", "bytes")
        
        # Application metrics
        self.register_metric("app.requests.total", MetricType.COUNTER, "Total requests processed", "count")
        self.register_metric("app.requests.success_rate", MetricType.GAUGE, "Request success rate", "%")
        self.register_metric("app.response_time.avg", MetricType.GAUGE, "Average response time", "ms")
        self.register_metric("app.response_time.p95", MetricType.GAUGE, "95th percentile response time", "ms")
        self.register_metric("app.errors.rate", MetricType.GAUGE, "Error rate", "%")
        
        # Service health metrics
        self.register_metric("services.health.score", MetricType.GAUGE, "Overall service health score", "score")
        self.register_metric("services.active.count", MetricType.GAUGE, "Number of active services", "count")
        self.register_metric("services.failed.count", MetricType.GAUGE, "Number of failed services", "count")
        
        # Cache metrics
        self.register_metric("cache.hit_rate", MetricType.GAUGE, "Cache hit rate", "%")
        self.register_metric("cache.size.bytes", MetricType.GAUGE, "Cache size in bytes", "bytes")
        self.register_metric("cache.evictions.rate", MetricType.GAUGE, "Cache eviction rate", "evictions/min")
        
        # Processing metrics
        self.register_metric("processing.queue.size", MetricType.GAUGE, "Processing queue size", "count")
        self.register_metric("processing.throughput", MetricType.GAUGE, "Processing throughput", "items/min")
        self.register_metric("processing.latency.avg", MetricType.GAUGE, "Average processing latency", "ms")
    
    def _setup_default_collectors(self):
        """Setup default metric collectors"""
        self.register_collector("system_metrics", self._collect_system_metrics)
        self.register_collector("application_metrics", self._collect_application_metrics)
        self.register_collector("service_health_metrics", self._collect_service_health_metrics)
        self.register_collector("cache_metrics", self._collect_cache_metrics)
        self.register_collector("processing_metrics", self._collect_processing_metrics)
    
    def register_metric(self, name: str, metric_type: MetricType, 
                       description: str = "", unit: str = ""):
        """Register a new metric series"""
        with self._lock:
            self._metrics[name] = MetricSeries(
                name=name,
                metric_type=metric_type,
                description=description,
                unit=unit
            )
        logger.debug(f"Registered metric: {name}")
    
    def register_collector(self, name: str, collector_func: Callable[[], Dict[str, float]]):
        """Register a metric collector function"""
        self._collectors[name] = collector_func
        logger.debug(f"Registered collector: {name}")
    
    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a metric value"""
        with self._lock:
            if name in self._metrics:
                self._metrics[name].add_point(value, labels)
            else:
                logger.warning(f"Metric not registered: {name}")
    
    def get_metric(self, name: str) -> Optional[MetricSeries]:
        """Get a metric series"""
        return self._metrics.get(name)
    
    def get_metric_value(self, name: str) -> Optional[float]:
        """Get latest value for a metric"""
        metric = self.get_metric(name)
        if metric:
            latest = metric.get_latest()
            return latest.value if latest else None
        return None
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics with their latest values and statistics"""
        result = {}
        
        with self._lock:
            for name, metric in self._metrics.items():
                latest = metric.get_latest()
                result[name] = {
                    'name': name,
                    'type': metric.metric_type.value,
                    'description': metric.description,
                    'unit': metric.unit,
                    'latest_value': latest.value if latest else None,
                    'latest_timestamp': latest.timestamp.isoformat() if latest else None,
                    'avg_5min': metric.get_average(5),
                    'max_5min': metric.get_max(5),
                    'trend_10min': metric.get_trend(10),
                    'points_count': len(metric.points)
                }
        
        return result
    
    def get_metric_history(self, name: str, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get metric history for specified time period"""
        metric = self.get_metric(name)
        if not metric:
            return []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return [
            point.to_dict() 
            for point in metric.points 
            if point.timestamp >= cutoff_time
        ]
    
    def start_collection(self):
        """Start background metric collection"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return
        
        self._running = True
        self._monitoring_thread = threading.Thread(target=self._collection_worker, daemon=True)
        self._monitoring_thread.start()
        logger.info("Real-time metrics collection started")
    
    def stop_collection(self):
        """Stop background metric collection"""
        self._running = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
        try:
            logger.info("Real-time metrics collection stopped")
        except Exception:
            print("Real-time metrics collection stopped")
    
    def _collection_worker(self):
        """Background collection worker"""
        while self._running:
            try:
                # Run all collectors
                for collector_name, collector_func in self._collectors.items():
                    try:
                        metrics_data = collector_func()
                        
                        # Record collected metrics
                        for metric_name, value in metrics_data.items():
                            self.record_metric(metric_name, value)
                            
                    except Exception as e:
                        logger.error(f"Error in collector {collector_name}: {e}")
                
                time.sleep(self._collection_interval)
                
            except Exception as e:
                logger.error(f"Error in metrics collection worker: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _collect_system_metrics(self) -> Dict[str, float]:
        """Collect system resource metrics"""
        try:
            # CPU usage (use non-blocking call to reduce CPU overhead)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            
            return {
                'system.cpu.usage': cpu_percent,
                'system.memory.usage': memory_percent,
                'system.disk.usage': disk_percent,
                'system.network.bytes_sent': float(network.bytes_sent),
                'system.network.bytes_recv': float(network.bytes_recv)
            }
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    def _collect_application_metrics(self) -> Dict[str, float]:
        """Collect application performance metrics"""
        try:
            # Get performance summary
            perf_summary = performance_monitor.get_performance_summary()
            if not perf_summary:
                return {}
            
            return {
                'app.requests.total': float(perf_summary.get('total_requests', 0)),
                'app.requests.success_rate': perf_summary.get('success_rate', 0.0) * 100,
                'app.response_time.avg': perf_summary.get('average_response_time', 0.0),
                'app.response_time.p95': perf_summary.get('p95_response_time', 0.0),
                'app.errors.rate': perf_summary.get('error_rate', 0.0) * 100
            }
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
            return {}
    
    def _collect_service_health_metrics(self) -> Dict[str, float]:
        """Collect service health metrics"""
        try:
            health_status = health_monitor.get_overall_health()
            if not health_status:
                return {}
            
            services = health_status.get('services', {})
            active_services = sum(1 for s in services.values() if s.get('status') == 'healthy')
            failed_services = sum(1 for s in services.values() if s.get('status') == 'unhealthy')
            total_services = len(services)
            
            # Calculate health score (0-100)
            health_score = (active_services / max(1, total_services)) * 100
            
            return {
                'services.health.score': health_score,
                'services.active.count': float(active_services),
                'services.failed.count': float(failed_services)
            }
            
        except Exception as e:
            logger.error(f"Error collecting service health metrics: {e}")
            return {}
    
    def _collect_cache_metrics(self) -> Dict[str, float]:
        """Collect cache performance metrics"""
        try:
            cache_stats = cache_manager.get_stats()
            if not cache_stats or not isinstance(cache_stats, dict):
                logger.debug(f"Cache stats is not valid, got: {type(cache_stats)}")
                return {}
            
            # Use the correct cache stats structure
            if 'levels' in cache_stats:
                total_hits = 0
                total_misses = 0
                total_size = 0
                total_evictions = 0
                
                for level_name, level_stats in cache_stats.get('levels', {}).items():
                    if isinstance(level_stats, dict):
                        total_hits += level_stats.get('hits', 0)
                        total_misses += level_stats.get('misses', 0)
                        total_size += level_stats.get('current_memory', 0)
                        total_evictions += level_stats.get('evictions', 0)
                
                # Calculate hit rate
                total_requests = total_hits + total_misses
                hit_rate = (total_hits / max(1, total_requests)) * 100
                
                return {
                    'cache.hit_rate': hit_rate,
                    'cache.size.bytes': float(total_size),
                    'cache.evictions.rate': float(total_evictions)
                }
            else:
                return {
                    'cache.hit_rate': cache_stats.get('overall_hit_rate', 0.0) * 100,
                    'cache.size.bytes': float(cache_stats.get('total_memory', 0)),
                    'cache.evictions.rate': 0.0
                }
            
        except Exception as e:
            logger.error(f"Error collecting cache metrics: {e}")
            return {}
    
    def _collect_processing_metrics(self) -> Dict[str, float]:
        """Collect processing pipeline metrics"""
        try:
            # For now, return placeholder values
            return {
                'processing.queue.size': 0.0,
                'processing.throughput': 0.0,
                'processing.latency.avg': 0.0
            }
            
        except Exception as e:
            logger.error(f"Error collecting processing metrics: {e}")
            return {}
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get formatted data for monitoring dashboard"""
        current_time = datetime.now(timezone.utc)
        
        # Get key metrics
        key_metrics = {
            'system': {
                'cpu_usage': self.get_metric_value('system.cpu.usage'),
                'memory_usage': self.get_metric_value('system.memory.usage'),
                'disk_usage': self.get_metric_value('system.disk.usage')
            },
            'application': {
                'success_rate': self.get_metric_value('app.requests.success_rate'),
                'response_time': self.get_metric_value('app.response_time.avg'),
                'error_rate': self.get_metric_value('app.errors.rate')
            },
            'services': {
                'health_score': self.get_metric_value('services.health.score'),
                'active_count': self.get_metric_value('services.active.count'),
                'failed_count': self.get_metric_value('services.failed.count')
            },
            'cache': {
                'hit_rate': self.get_metric_value('cache.hit_rate'),
                'size_bytes': self.get_metric_value('cache.size.bytes')
            }
        }
        
        return {
            'timestamp': current_time.isoformat(),
            'metrics': key_metrics,
            'collection_interval': self._collection_interval,
            'total_metrics': len(self._metrics),
            'active_collectors': len(self._collectors)
        }
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        if format.lower() == "json":
            return json.dumps(self.get_all_metrics(), indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")

# Global instance
realtime_metrics_collector = RealtimeMetricsCollector()