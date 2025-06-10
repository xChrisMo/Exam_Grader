"""
Rate limiting utilities for the Exam Grader application.

This module provides rate limiting functionality to prevent
abuse and ensure fair usage of the application.
"""

import time
import logging
from collections import defaultdict, deque
from functools import wraps
from typing import Dict, List, Optional, Tuple
from flask import request, jsonify, flash, redirect, url_for

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        """Initialize rate limiter."""
        self.requests = defaultdict(deque)
        self.whitelist = set()
    
    def is_rate_limited(self, identifier: str, limit: int, window: int) -> bool:
        """Check if identifier is rate limited.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            limit: Maximum number of requests allowed
            window: Time window in seconds
            
        Returns:
            True if rate limited, False otherwise
        """
        now = time.time()
        
        # Clean old requests outside the window
        while self.requests[identifier] and self.requests[identifier][0] <= now - window:
            self.requests[identifier].popleft()
        
        # Check if limit exceeded
        if len(self.requests[identifier]) >= limit:
            return True
        
        # Add current request
        self.requests[identifier].append(now)
        return False
    
    def add_to_whitelist(self, identifier: str):
        """Add identifier to whitelist.
        
        Args:
            identifier: Identifier to whitelist
        """
        self.whitelist.add(identifier)
        logger.info(f"Added {identifier} to rate limit whitelist")
    
    def remove_from_whitelist(self, identifier: str):
        """Remove identifier from whitelist.
        
        Args:
            identifier: Identifier to remove from whitelist
        """
        self.whitelist.discard(identifier)
        logger.info(f"Removed {identifier} from rate limit whitelist")
    
    def is_whitelisted(self, identifier: str) -> bool:
        """Check if identifier is whitelisted.
        
        Args:
            identifier: Identifier to check
            
        Returns:
            True if whitelisted, False otherwise
        """
        return identifier in self.whitelist
    
    def get_remaining_requests(self, identifier: str, limit: int, window: int) -> int:
        """Get remaining requests for identifier.
        
        Args:
            identifier: Unique identifier
            limit: Maximum number of requests allowed
            window: Time window in seconds
            
        Returns:
            Number of remaining requests
        """
        now = time.time()
        
        # Clean old requests
        while self.requests[identifier] and self.requests[identifier][0] <= now - window:
            self.requests[identifier].popleft()
        
        return max(0, limit - len(self.requests[identifier]))
    
    def get_reset_time(self, identifier: str, window: int) -> Optional[float]:
        """Get time when rate limit resets.
        
        Args:
            identifier: Unique identifier
            window: Time window in seconds
            
        Returns:
            Timestamp when rate limit resets, None if no requests
        """
        if not self.requests[identifier]:
            return None
        
        return self.requests[identifier][0] + window


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_identifier() -> str:
    """Get client identifier for rate limiting.
    
    Returns:
        Client identifier string
    """
    # Try to get real IP from headers (for reverse proxy setups)
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(',')[0].strip()
    
    # Fallback to remote address
    return request.remote_addr or 'unknown'


def rate_limit_with_whitelist(limit: int = 100, window: int = 3600, per: str = 'hour'):
    """Rate limiting decorator with whitelist support.
    
    Args:
        limit: Maximum number of requests
        window: Time window in seconds
        per: Human-readable time period (for error messages)
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identifier = get_client_identifier()
            
            # Check whitelist first
            if rate_limiter.is_whitelisted(identifier):
                return f(*args, **kwargs)
            
            # Check rate limit
            if rate_limiter.is_rate_limited(identifier, limit, window):
                logger.warning(f"Rate limit exceeded for {identifier}")
                
                # Return appropriate response based on request type
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': f'Too many requests. Limit: {limit} per {per}',
                        'limit': limit,
                        'window': window,
                        'reset_time': rate_limiter.get_reset_time(identifier, window)
                    }), 429
                else:
                    flash(f'Too many requests. Please wait before trying again. Limit: {limit} per {per}', 'warning')
                    return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def get_rate_limit_status(identifier: Optional[str] = None) -> Dict:
    """Get rate limit status for identifier.
    
    Args:
        identifier: Client identifier (uses current client if None)
        
    Returns:
        Dictionary with rate limit status
    """
    if identifier is None:
        identifier = get_client_identifier()
    
    # Default limits (can be made configurable)
    default_limit = 100
    default_window = 3600  # 1 hour
    
    remaining = rate_limiter.get_remaining_requests(identifier, default_limit, default_window)
    reset_time = rate_limiter.get_reset_time(identifier, default_window)
    is_whitelisted = rate_limiter.is_whitelisted(identifier)
    
    return {
        'identifier': identifier,
        'limit': default_limit,
        'remaining': remaining,
        'reset_time': reset_time,
        'window': default_window,
        'is_whitelisted': is_whitelisted
    }


def add_to_whitelist(identifier: str):
    """Add identifier to rate limit whitelist.
    
    Args:
        identifier: Identifier to whitelist
    """
    rate_limiter.add_to_whitelist(identifier)


def remove_from_whitelist(identifier: str):
    """Remove identifier from rate limit whitelist.
    
    Args:
        identifier: Identifier to remove from whitelist
    """
    rate_limiter.remove_from_whitelist(identifier)


def clear_rate_limit_data():
    """Clear all rate limit data (for testing/admin purposes)."""
    rate_limiter.requests.clear()
    logger.info("Cleared all rate limit data")


# Predefined rate limit decorators for common use cases
def api_rate_limit(f):
    """Rate limit for API endpoints (stricter)."""
    return rate_limit_with_whitelist(limit=50, window=3600, per='hour')(f)


def upload_rate_limit(f):
    """Rate limit for file uploads (more restrictive)."""
    return rate_limit_with_whitelist(limit=20, window=3600, per='hour')(f)


def general_rate_limit(f):
    """General rate limit for web pages."""
    return rate_limit_with_whitelist(limit=200, window=3600, per='hour')(f)


def strict_rate_limit(f):
    """Strict rate limit for sensitive operations."""
    return rate_limit_with_whitelist(limit=10, window=3600, per='hour')(f)
