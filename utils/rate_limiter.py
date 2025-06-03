"""
Rate limiting utilities for the Exam Grader application.
"""
import time
import threading
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify, session
from utils.logger import setup_logger

logger = setup_logger(__name__)

class RateLimiter:
    """Thread-safe rate limiter with multiple strategies."""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._requests = defaultdict(deque)  # IP -> deque of timestamps
        self._user_requests = defaultdict(deque)  # User session -> deque of timestamps
        self._global_requests = deque()  # Global request timestamps
        
        # Rate limiting rules (requests per time window in seconds)
        self.rules = {
            'upload_guide': {'limit': 5, 'window': 300},  # 5 uploads per 5 minutes
            'upload_submission': {'limit': 20, 'window': 300},  # 20 uploads per 5 minutes
            'process_mapping': {'limit': 10, 'window': 60},  # 10 mappings per minute
            'process_grading': {'limit': 10, 'window': 60},  # 10 gradings per minute
            'api_general': {'limit': 100, 'window': 60},  # 100 API calls per minute
            'global': {'limit': 1000, 'window': 60},  # 1000 total requests per minute
        }
        
        # Cleanup interval
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
    
    def _cleanup_old_requests(self, current_time: float) -> None:
        """Remove old request timestamps to prevent memory leaks."""
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        with self._lock:
            # Clean up IP-based requests
            for ip, requests in list(self._requests.items()):
                # Remove requests older than the longest window (5 minutes)
                while requests and current_time - requests[0] > 300:
                    requests.popleft()
                # Remove empty deques
                if not requests:
                    del self._requests[ip]
            
            # Clean up user-based requests
            for user, requests in list(self._user_requests.items()):
                while requests and current_time - requests[0] > 300:
                    requests.popleft()
                if not requests:
                    del self._user_requests[user]
            
            # Clean up global requests
            while self._global_requests and current_time - self._global_requests[0] > 60:
                self._global_requests.popleft()
            
            self._last_cleanup = current_time
            logger.debug("Cleaned up old rate limiting data")
    
    def _get_client_identifier(self) -> Tuple[str, str]:
        """Get client IP and user session identifier."""
        # Get real IP address (considering proxies)
        ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
        
        # Get user session identifier
        user_id = session.get('user_id', session.get('session_id', 'anonymous'))
        
        return ip or 'unknown', str(user_id)
    
    def is_allowed(self, rule_name: str, identifier: Optional[str] = None) -> Tuple[bool, Dict]:
        """
        Check if request is allowed under rate limiting rules.
        
        Args:
            rule_name: Name of the rate limiting rule
            identifier: Optional custom identifier (defaults to IP + session)
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        self._cleanup_old_requests(current_time)
        
        if rule_name not in self.rules:
            logger.warning(f"Unknown rate limiting rule: {rule_name}")
            return True, {}
        
        rule = self.rules[rule_name]
        limit = rule['limit']
        window = rule['window']
        
        with self._lock:
            # Check global rate limit first
            global_rule = self.rules['global']
            while (self._global_requests and 
                   current_time - self._global_requests[0] > global_rule['window']):
                self._global_requests.popleft()
            
            if len(self._global_requests) >= global_rule['limit']:
                return False, {
                    'rule': 'global',
                    'limit': global_rule['limit'],
                    'window': global_rule['window'],
                    'current_count': len(self._global_requests),
                    'reset_time': self._global_requests[0] + global_rule['window']
                }
            
            # Get client identifier
            if identifier:
                client_id = identifier
                requests_deque = self._requests[client_id]
            else:
                ip, user_id = self._get_client_identifier()
                client_id = f"{ip}:{user_id}"
                requests_deque = self._user_requests[client_id]
            
            # Remove old requests outside the window
            while requests_deque and current_time - requests_deque[0] > window:
                requests_deque.popleft()
            
            # Check if limit is exceeded
            if len(requests_deque) >= limit:
                return False, {
                    'rule': rule_name,
                    'limit': limit,
                    'window': window,
                    'current_count': len(requests_deque),
                    'reset_time': requests_deque[0] + window,
                    'client_id': client_id
                }
            
            # Record the request
            requests_deque.append(current_time)
            self._global_requests.append(current_time)
            
            return True, {
                'rule': rule_name,
                'limit': limit,
                'window': window,
                'current_count': len(requests_deque),
                'remaining': limit - len(requests_deque)
            }
    
    def get_rate_limit_headers(self, rule_name: str, rate_info: Dict) -> Dict[str, str]:
        """Generate rate limit headers for HTTP responses."""
        if not rate_info:
            return {}
        
        headers = {}
        if 'limit' in rate_info:
            headers['X-RateLimit-Limit'] = str(rate_info['limit'])
        if 'remaining' in rate_info:
            headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
        if 'reset_time' in rate_info:
            headers['X-RateLimit-Reset'] = str(int(rate_info['reset_time']))
        if 'window' in rate_info:
            headers['X-RateLimit-Window'] = str(rate_info['window'])
        
        return headers
    
    def get_stats(self) -> Dict:
        """Get rate limiting statistics."""
        current_time = time.time()
        
        with self._lock:
            return {
                'active_ips': len(self._requests),
                'active_users': len(self._user_requests),
                'global_requests_last_minute': len([
                    t for t in self._global_requests 
                    if current_time - t <= 60
                ]),
                'total_tracked_requests': sum(len(deq) for deq in self._requests.values()),
                'rules': self.rules,
                'last_cleanup': self._last_cleanup
            }

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(rule_name: str, identifier: Optional[str] = None):
    """
    Decorator for rate limiting Flask routes.
    
    Args:
        rule_name: Name of the rate limiting rule
        identifier: Optional custom identifier
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            allowed, rate_info = rate_limiter.is_allowed(rule_name, identifier)
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for {rule_name}: {rate_info}")
                
                # Determine reset time for user-friendly message
                reset_time = rate_info.get('reset_time', time.time() + rate_info.get('window', 60))
                wait_time = max(0, int(reset_time - time.time()))
                
                response_data = {
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please wait {wait_time} seconds before trying again.',
                    'rate_limit': {
                        'rule': rate_info.get('rule'),
                        'limit': rate_info.get('limit'),
                        'window': rate_info.get('window'),
                        'reset_in_seconds': wait_time
                    }
                }
                
                response = jsonify(response_data)
                response.status_code = 429  # Too Many Requests
                
                # Add rate limit headers
                headers = rate_limiter.get_rate_limit_headers(rule_name, rate_info)
                for key, value in headers.items():
                    response.headers[key] = value
                
                return response
            
            # Execute the original function
            result = f(*args, **kwargs)
            
            # Add rate limit headers to successful responses
            if hasattr(result, 'headers'):
                headers = rate_limiter.get_rate_limit_headers(rule_name, rate_info)
                for key, value in headers.items():
                    result.headers[key] = value
            
            return result
        
        return decorated_function
    return decorator

def check_rate_limit(rule_name: str, identifier: Optional[str] = None) -> Tuple[bool, Dict]:
    """
    Check rate limit without recording a request.
    
    Args:
        rule_name: Name of the rate limiting rule
        identifier: Optional custom identifier
        
    Returns:
        Tuple of (is_allowed, rate_limit_info)
    """
    return rate_limiter.is_allowed(rule_name, identifier)

def get_rate_limit_status() -> Dict:
    """Get current rate limiting status and statistics."""
    return rate_limiter.get_stats()

class IPWhitelist:
    """IP whitelist for bypassing rate limits."""
    
    def __init__(self):
        self._whitelist = set()
        self._lock = threading.RLock()
        
        # Add localhost by default
        self.add_ip('127.0.0.1')
        self.add_ip('::1')
    
    def add_ip(self, ip: str) -> None:
        """Add IP to whitelist."""
        with self._lock:
            self._whitelist.add(ip)
            logger.info(f"Added IP to whitelist: {ip}")
    
    def remove_ip(self, ip: str) -> None:
        """Remove IP from whitelist."""
        with self._lock:
            self._whitelist.discard(ip)
            logger.info(f"Removed IP from whitelist: {ip}")
    
    def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted."""
        with self._lock:
            return ip in self._whitelist
    
    def get_whitelist(self) -> set:
        """Get copy of current whitelist."""
        with self._lock:
            return self._whitelist.copy()

# Global IP whitelist instance
ip_whitelist = IPWhitelist()

def rate_limit_with_whitelist(rule_name: str, identifier: Optional[str] = None):
    """
    Rate limiting decorator that respects IP whitelist.
    
    Args:
        rule_name: Name of the rate limiting rule
        identifier: Optional custom identifier
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if IP is whitelisted
            ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            if ip and ',' in ip:
                ip = ip.split(',')[0].strip()
            
            if ip and ip_whitelist.is_whitelisted(ip):
                logger.debug(f"Request from whitelisted IP {ip}, bypassing rate limit")
                return f(*args, **kwargs)
            
            # Apply normal rate limiting
            return rate_limit(rule_name, identifier)(f)(*args, **kwargs)
        
        return decorated_function
    return decorator
