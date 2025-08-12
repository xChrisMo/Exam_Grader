"""Performance monitoring middleware."""

import time
from flask import request, g
from utils.logger import logger

class PerformanceMiddleware:
    """Middleware to monitor request performance."""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app."""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Record request start time."""
        g.start_time = time.time()
    
    def after_request(self, response):
        """Log slow requests."""
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            
            # Log requests that take longer than 1 second
            if duration > 1.0:
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration:.2f}s"
                )
            
            # Add performance header for debugging
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
        
        return response

# Global instance
performance_middleware = PerformanceMiddleware()