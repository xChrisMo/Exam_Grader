"""Enhanced Security Middleware for Exam Grader Application.

This module provides comprehensive security middleware including:
- Security headers (CSP, HSTS, etc.)
- Enhanced input validation
- Request sanitization
- Security monitoring
- Attack prevention
"""

import re
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple

try:
    from flask import Flask, abort, g, request
except ImportError:
    Flask = None
    request = None
    g = None
    abort = None

from datetime import datetime, timezone

try:
    from utils.logger import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

try:
    from src.exceptions.application_errors import SecurityError, ValidationError
except ImportError:
    # Fallback error classes
    class SecurityError(Exception):
        pass

    class ValidationError(Exception):
        pass


class SecurityHeaders:
    """Manages security headers for HTTP responses."""

    # Default security headers
    DEFAULT_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        ),
        "Cross-Origin-Embedder-Policy": "unsafe-none",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
    }

    # Content Security Policy
    DEFAULT_CSP = {
        "default-src": ["'self'"],
        "script-src": [
            "'self'",
            "'unsafe-inline'",
            "'unsafe-eval'",
            "https://cdn.tailwindcss.com",
            "https://cdnjs.cloudflare.com",
        ],  # Added CDN sources
        "style-src": [
            "'self'",
            "'unsafe-inline'",
            "https://fonts.googleapis.com",
            "https://cdn.tailwindcss.com",
        ],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "https:"],
        "connect-src": ["'self'", "ws:", "wss:"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
        "object-src": ["'none'"],
        "media-src": ["'self'"],
    }

    @classmethod
    def get_csp_header(cls, custom_csp: Optional[Dict[str, List[str]]] = None) -> str:
        """Generate Content Security Policy header.

        Args:
            custom_csp: Custom CSP directives to merge with defaults

        Returns:
            CSP header string
        """
        csp = cls.DEFAULT_CSP.copy()
        if custom_csp:
            for directive, sources in custom_csp.items():
                if directive in csp:
                    csp[directive].extend(sources)
                else:
                    csp[directive] = sources

        # Build CSP string
        csp_parts = []
        for directive, sources in csp.items():
            sources_str = " ".join(sources)
            csp_parts.append(f"{directive} {sources_str}")

        return "; ".join(csp_parts)

    @classmethod
    def get_hsts_header(
        cls, max_age: int = 31536000, include_subdomains: bool = True
    ) -> str:
        """Generate HTTP Strict Transport Security header.

        Args:
            max_age: HSTS max age in seconds (default: 1 year)
            include_subdomains: Whether to include subdomains

        Returns:
            HSTS header string
        """
        hsts = f"max-age={max_age}"
        if include_subdomains:
            hsts += "; includeSubDomains"
        return hsts


class RequestValidator:
    """Validates and sanitizes incoming requests."""

    # Suspicious patterns
    SUSPICIOUS_PATTERNS = [
        # SQL injection patterns
        r"(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute)",
        r"(?i)(script|javascript|vbscript|onload|onerror|onclick)",
        r"(?i)(<script|</script|<iframe|</iframe)",
        # Path traversal
        r"\.\.[\\/]",
        r"%2e%2e[\\/]",
        # Command injection
        r"(?i)(cmd|powershell|bash|sh|exec|system|eval)",
        # LDAP injection
        r"(?i)(\*\)|\(\*|\)\(|\(\&)",
    ]

    # Rate limiting storage
    _request_counts = defaultdict(lambda: deque())
    _blocked_ips = defaultdict(float)

    @classmethod
    def validate_request(cls, request_obj) -> Tuple[bool, Optional[str]]:
        """Validate incoming request for security threats.

        Args:
            request_obj: Flask request object

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check rate limiting
            if not cls._check_rate_limit(request_obj):
                return False, "Rate limit exceeded"

            # Validate request size
            if not cls._validate_request_size(request_obj):
                return False, "Request too large"

            if not cls._check_suspicious_patterns(request_obj):
                return False, "Suspicious request detected"

            # Validate headers
            if not cls._validate_headers(request_obj):
                return False, "Invalid headers detected"

            return True, None

        except Exception as e:
            logger.error(f"Error validating request: {str(e)}")
            return False, "Request validation failed"

    @classmethod
    def _check_rate_limit(
        cls, request_obj, max_requests: int = 100, window_minutes: int = 15
    ) -> bool:
        """Check if request exceeds rate limit."""
        import os

        is_development = (
            os.getenv("FLASK_ENV") == "development"
            or os.getenv("DEBUG", "").lower() == "true"
            or request_obj.host.startswith("127.0.0.1")
            or request_obj.host.startswith("localhost")
        )

        if is_development:
            max_requests = 10000  # Very high limit for development
            window_minutes = 1  # Very short window for development

        client_ip = cls._get_client_ip(request_obj)
        current_time = time.time()

        if client_ip in cls._blocked_ips:
            if current_time < cls._blocked_ips[client_ip]:
                return False
            else:
                del cls._blocked_ips[client_ip]

        # Clean old requests
        window_start = current_time - (window_minutes * 60)
        request_times = cls._request_counts[client_ip]

        while request_times and request_times[0] < window_start:
            request_times.popleft()

        # Check rate limit
        if len(request_times) >= max_requests:
            block_duration = (
                300 if is_development else 3600
            )  # 5 minutes for dev, 1 hour for prod
            cls._blocked_ips[client_ip] = current_time + block_duration
            block_time_str = "5 minutes" if is_development else "1 hour"
            logger.warning(
                f"Rate limit exceeded for IP {client_ip}, blocking for {block_time_str}"
            )
            return False

        # Add current request
        request_times.append(current_time)
        return True

    @classmethod
    def _validate_request_size(
        cls, request_obj, max_size: int = 50 * 1024 * 1024
    ) -> bool:
        """Validate request content length."""
        content_length = request_obj.content_length
        if content_length and content_length > max_size:
            logger.warning(f"Request too large: {content_length} bytes")
            return False
        return True

    @classmethod
    def _check_suspicious_patterns(cls, request_obj) -> bool:
        """Check for suspicious patterns in request data."""
        if (
            request_obj.remote_addr == "127.0.0.1"
            or request_obj.remote_addr == "localhost"
        ):
            return True

        # Check URL (exclude legitimate application paths)
        if cls._contains_suspicious_url_pattern(request_obj.url):
            logger.warning(f"Suspicious pattern in URL: {request_obj.url}")
            return False

        # Check query parameters with context-aware validation
        for key, value in request_obj.args.items():
            if (
                request_obj.path.startswith("/auth")
                or request_obj.path.startswith("/login")
            ) and key == "next":
                if cls._contains_malicious_query_pattern(value):
                    logger.warning(
                        f"Malicious pattern in redirect param: {key}={value}"
                    )
                    return False
            else:
                # For other parameters, use standard validation
                if cls._contains_suspicious_pattern(f"{key}={value}"):
                    logger.warning(f"Suspicious pattern in query param: {key}={value}")
                    return False

        # Check form data
        if request_obj.form:
            for key, value in request_obj.form.items():
                if cls._contains_suspicious_pattern(f"{key}={value}"):
                    logger.warning(f"Suspicious pattern in form data: {key}")
                    return False

        # Check headers (exclude standard headers that may contain legitimate content)
        excluded_headers = {
            "referer",
            "user-agent",
            "accept",
            "accept-language",
            "accept-encoding",
            "connection",
            "host",
            "origin",
            "sec-fetch-dest",
            "sec-fetch-mode",
            "sec-fetch-site",
            "sec-ch-ua",
            "sec-ch-ua-mobile",
            "sec-ch-ua-platform",
            "cache-control",
            "pragma",
            "upgrade-insecure-requests",
            "cookie",  # Added cookie to excluded headers
        }

        for header, value in request_obj.headers:
            if header.lower() not in excluded_headers:
                if cls._contains_suspicious_pattern(f"{header}: {value}"):
                    logger.warning(f"Suspicious pattern in header: {header}")
                    return False

        return True

    @classmethod
    def _contains_suspicious_pattern(cls, text: str) -> bool:
        """Check if text contains suspicious patterns."""
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def _contains_suspicious_url_pattern(cls, url: str) -> bool:
        """Check if URL contains suspicious patterns, excluding legitimate app paths."""
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        query = parsed_url.query.lower()

        # Expanded legitimate application paths
        legitimate_paths = {
            "/dashboard",
            "/admin",
            "/upload",
            "/grading",
            "/results",
            "/reports",
            "/api",
            "/static",
            "/login",
            "/logout",
            "/register",
            "/profile",
            "/settings",
            "/help",
            "/about",
            "/contact",
            "/home",
            "/index",
            "/auth",
            "/api/v1/processing",  # Explicitly allow processing endpoint
        }

        # Allow any path under /api/v1
        if path.startswith("/api/v1/"):
            return False

        for legit_path in legitimate_paths:
            if path.startswith(legit_path):
                # For auth paths, be more lenient with query parameters
                if path.startswith("/auth") or path.startswith("/login"):
                    if query and cls._contains_malicious_query_pattern(query):
                        return True
                    return False
                # For other legitimate paths, still check query parameters
                elif query and cls._contains_suspicious_pattern(query):
                    return True
                return False

        # For other paths, check the full URL against suspicious patterns
        return cls._contains_suspicious_pattern(url)

    @classmethod
    def _contains_malicious_query_pattern(cls, query: str) -> bool:
        """Check for malicious patterns in query parameters, excluding legitimate redirects."""
        # Patterns that are actually malicious (not including legitimate URLs)
        malicious_patterns = [
            "union.*select",
            "drop.*table",
            "delete.*from",
            "insert.*into",
            "update.*set",
            "exec.*xp_",
            "sp_executesql",
            "xp_cmdshell",
            "../",
            "..\\",
            "/etc/passwd",
            "/proc/self/environ",
            "javascript:",
            "vbscript:",
            "data:text/html",
            "eval\\(",
            "expression\\(",
            "import\\(",
            "require\\(",
            "system\\(",
            "exec\\(",
            "shell_exec",
            "passthru",
            "file_get_contents",
            "<script",
            "</script>",
            "onload=",
            "onerror=",
            "onclick=",
        ]

        query_lower = query.lower()
        for pattern in malicious_patterns:
            if pattern in query_lower:
                return True
        return False

    @classmethod
    def _validate_headers(cls, request_obj) -> bool:
        """Validate request headers."""
        if request_obj.method == "POST":
            content_type = request_obj.headers.get("Content-Type", "")
            if not content_type:
                logger.warning("POST request missing Content-Type header")
                return False

        user_agent = request_obj.headers.get("User-Agent", "")
        if not user_agent or len(user_agent) < 10:
            logger.warning(f"Suspicious or missing User-Agent: {user_agent}")
            return False

        return True

    @classmethod
    def _get_client_ip(cls, request_obj) -> str:
        """Get client IP address from request."""
        forwarded_ips = [
            request_obj.headers.get("X-Forwarded-For"),
            request_obj.headers.get("X-Real-IP"),
            request_obj.headers.get("CF-Connecting-IP"),
        ]

        for ip in forwarded_ips:
            if ip:
                return ip.split(",")[0].strip()

        return request_obj.remote_addr or "unknown"

    @classmethod
    def reset_rate_limits(cls):
        """Reset all rate limits (useful for development)."""
        cls._request_counts.clear()
        cls._blocked_ips.clear()
        logger.info("Rate limits reset")


class SecurityMiddleware:
    """Main security middleware class."""

    def __init__(
        self, app: Optional[Flask] = None, config: Optional[Dict[str, Any]] = None
    ):
        """Initialize security middleware.

        Args:
            app: Flask application instance
            config: Security configuration (dict or SecurityConfiguration object)
        """
        self.app = app

        # Handle both dict and SecurityConfiguration objects
        if config is None:
            self.config = {}
        elif hasattr(config, "to_dict"):
            # SecurityConfiguration object
            self.config = config.to_dict()
        else:
            # Regular dictionary
            self.config = config

        self.security_headers = SecurityHeaders()
        self.request_validator = RequestValidator()

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize middleware with Flask app.

        Args:
            app: Flask application instance
        """
        self.app = app

        # Register before request handler
        app.before_request(self._before_request)

        # Register after request handler
        app.after_request(self._after_request)

        # Register error handlers
        self._register_error_handlers(app)

        logger.info("Security middleware initialized")

    def _before_request(self):
        """Handle before request processing."""
        try:
            if self._should_skip_security_check():
                return

            # Validate request
            is_valid, error_msg = self.request_validator.validate_request(request)
            if not is_valid:
                logger.warning(
                    f"Security validation failed: {error_msg} for {request.remote_addr}"
                )
                abort(403, description=error_msg)

            # Add security context to g
            g.security_context = {
                "request_id": self._generate_request_id(),
                "client_ip": self.request_validator._get_client_ip(request),
                "timestamp": datetime.now(timezone.utc),
                "validated": True,
            }

        except Exception as e:
            logger.error(f"Error in security middleware before_request: {str(e)}")
            abort(500, description="Security processing error")

    def _after_request(self, response):
        """Handle after request processing.

        Args:
            response: Flask response object

        Returns:
            Modified response with security headers
        """
        try:
            # Add security headers
            self._add_security_headers(response)

            if hasattr(g, "security_context"):
                self._log_security_event(response)

            return response

        except Exception as e:
            logger.error(f"Error in security middleware after_request: {str(e)}")
            return response

    def _add_security_headers(self, response):
        """Add security headers to response.

        Args:
            response: Flask response object
        """
        # Add default security headers
        for header, value in self.security_headers.DEFAULT_HEADERS.items():
            response.headers[header] = value

        # Add CSP header
        custom_csp = self.config.get("csp", {})
        csp_header = self.security_headers.get_csp_header(custom_csp)
        response.headers["Content-Security-Policy"] = csp_header

        if request.is_secure:
            hsts_header = self.security_headers.get_hsts_header()
            response.headers["Strict-Transport-Security"] = hsts_header

        if self._is_sensitive_page():
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

    def _should_skip_security_check(self) -> bool:
        """Check if security validation should be skipped for current request.

        Returns:
            True if security check should be skipped
        """
        skip_paths = [
            "/static/",
            "/favicon.ico",
            "/health",
            "/robots.txt",
            "/.well-known/",
        ]

        return any(request.path.startswith(path) for path in skip_paths)

    def _is_sensitive_page(self) -> bool:
        """Check if current page contains sensitive information.

        Returns:
            True if page is sensitive
        """
        sensitive_paths = [
            "/admin",
            "/settings",
            "/profile",
            "/api/",
            "/upload",
            "/results",
        ]

        return any(request.path.startswith(path) for path in sensitive_paths)

    def _generate_request_id(self) -> str:
        """Generate unique request ID.

        Returns:
            Unique request identifier
        """
        import uuid

        return str(uuid.uuid4())

    def _log_security_event(self, response):
        """Log security-related events.

        Args:
            response: Flask response object
        """
        if hasattr(g, "security_context"):
            context = g.security_context
            logger.info(
                f"Security event - Request ID: {context['request_id']}, "
                f"IP: {context['client_ip']}, Path: {request.path}, "
                f"Method: {request.method}, Status: {response.status_code}"
            )

    def _register_error_handlers(self, app: Flask):
        """Register security-related error handlers.

        Args:
            app: Flask application instance
        """

        @app.errorhandler(403)
        def handle_forbidden(error):
            """Handle forbidden errors."""
            logger.warning(
                f"403 Forbidden: {error.description} for {request.remote_addr}"
            )
            return {
                "error": "Forbidden",
                "message": "Access denied due to security policy",
                "status_code": 403,
            }, 403

        @app.errorhandler(429)
        def handle_rate_limit(error):
            """Handle rate limit errors."""
            logger.warning(f"429 Rate Limited: {request.remote_addr}")
            return {
                "error": "Rate Limited",
                "message": "Too many requests, please try again later",
                "status_code": 429,
            }, 429


# Global security middleware instance
security_middleware = SecurityMiddleware()


def init_security_middleware(app: Flask, config: Optional[Dict[str, Any]] = None):
    """Initialize security middleware with Flask app.

    Args:
        app: Flask application instance
        config: Security configuration (dict or SecurityConfiguration object)
    """
    global security_middleware
    security_middleware = SecurityMiddleware(app, config)
    return security_middleware
