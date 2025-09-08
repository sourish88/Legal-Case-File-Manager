"""
Security utilities and middleware for the Legal Case File Manager.

This module provides additional security layers including rate limiting,
request logging, and security headers.
"""

import hashlib
import hmac
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional, Tuple

from flask import current_app, g, jsonify, request

# Configure security logger
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self):
        self.requests = defaultdict(deque)
        self.blocked_ips = {}

    def is_allowed(self, identifier: str, max_requests: int = 100, window_seconds: int = 3600) -> bool:
        """
        Check if request is allowed based on rate limiting

        Args:
            identifier: IP address or user identifier
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()
        window_start = now - window_seconds

        # Clean old requests
        while self.requests[identifier] and self.requests[identifier][0] < window_start:
            self.requests[identifier].popleft()

        # Check if blocked
        if identifier in self.blocked_ips:
            if now < self.blocked_ips[identifier]:
                return False
            else:
                # Unblock if block time has passed
                del self.blocked_ips[identifier]

        # Check rate limit
        if len(self.requests[identifier]) >= max_requests:
            # Block for 1 hour
            self.blocked_ips[identifier] = now + 3600
            security_logger.warning(f"Rate limit exceeded for {identifier}. Blocked for 1 hour.")
            return False

        # Add current request
        self.requests[identifier].append(now)
        return True

    def block_ip(self, ip: str, duration_seconds: int = 3600):
        """Manually block an IP address"""
        self.blocked_ips[ip] = time.time() + duration_seconds
        security_logger.warning(f"IP {ip} manually blocked for {duration_seconds} seconds")


# Global rate limiter instance
rate_limiter = RateLimiter()


class SecurityMiddleware:
    """Security middleware for Flask application"""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize security middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        """Process request before handling"""
        # Log request
        self.log_request()

        # Check rate limiting
        if not self.check_rate_limit():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Rate limit exceeded",
                        "message": "Too many requests. Please try again later.",
                    }
                ),
                429,
            )

        # Validate request size
        if not self.check_request_size():
            return (
                jsonify({"success": False, "error": "Request too large", "message": "Request payload is too large."}),
                413,
            )

        # Check for suspicious patterns
        if self.detect_suspicious_request():
            security_logger.warning(f"Suspicious request detected from {request.remote_addr}: {request.url}")
            return (
                jsonify(
                    {"success": False, "error": "Request blocked", "message": "Request contains suspicious patterns."}
                ),
                403,
            )

    def after_request(self, response):
        """Process response after handling"""
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers[
            "Content-Security-Policy"
        ] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response

    def log_request(self):
        """Log incoming request for security monitoring"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "ip": request.remote_addr,
            "method": request.method,
            "url": request.url,
            "user_agent": request.headers.get("User-Agent", ""),
            "referer": request.headers.get("Referer", ""),
            "content_length": request.content_length or 0,
        }

        # Log to security logger
        security_logger.info(f"Request: {log_data}")

    def check_rate_limit(self) -> bool:
        """Check if request passes rate limiting"""
        # Use IP address as identifier
        identifier = request.remote_addr

        # Different limits for different endpoints
        if request.endpoint and "search" in request.endpoint:
            return rate_limiter.is_allowed(identifier, max_requests=200, window_seconds=3600)
        else:
            return rate_limiter.is_allowed(identifier, max_requests=100, window_seconds=3600)

    def check_request_size(self) -> bool:
        """Check if request size is within limits"""
        max_size = current_app.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)  # 16MB
        content_length = request.content_length or 0
        return content_length <= max_size

    def detect_suspicious_request(self) -> bool:
        """Detect suspicious request patterns"""
        # Check for common attack patterns in URL
        url_lower = request.url.lower()
        suspicious_patterns = [
            "../",
            "..\\",
            "etc/passwd",
            "boot.ini",
            "windows/system32",
            "union select",
            "drop table",
            "insert into",
            "update set",
            "<script",
            "javascript:",
            "vbscript:",
            "onload=",
            "onerror=",
            "eval(",
            "exec(",
            "system(",
            "shell_exec(",
        ]

        for pattern in suspicious_patterns:
            if pattern in url_lower:
                return True

        # Check User-Agent for common attack tools
        user_agent = request.headers.get("User-Agent", "").lower()
        attack_agents = [
            "sqlmap",
            "nikto",
            "burp",
            "nessus",
            "openvas",
            "nmap",
            "dirb",
            "dirbuster",
            "gobuster",
            "wfuzz",
            "hydra",
        ]

        for agent in attack_agents:
            if agent in user_agent:
                return True

        # Check for excessive special characters in query parameters
        for key, value in request.args.items():
            if isinstance(value, str):
                special_chars = sum(1 for c in value if not c.isalnum() and c not in " -_.")
                if len(value) > 0 and special_chars / len(value) > 0.5:  # More than 50% special chars
                    return True

        return False


def require_api_key(func):
    """Decorator to require API key for certain endpoints"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")

        if not api_key:
            return (
                jsonify({"success": False, "error": "API key required", "message": "Please provide a valid API key."}),
                401,
            )

        # Validate API key (implement your own validation logic)
        if not validate_api_key(api_key):
            return (
                jsonify(
                    {"success": False, "error": "Invalid API key", "message": "The provided API key is not valid."}
                ),
                401,
            )

        return func(*args, **kwargs)

    return wrapper


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key

    Args:
        api_key: API key to validate

    Returns:
        True if valid, False otherwise
    """
    # Implement your API key validation logic here
    # For now, we'll use a simple check against environment variable
    import os

    valid_keys = os.getenv("VALID_API_KEYS", "").split(",")
    return api_key in valid_keys


def generate_csrf_token() -> str:
    """Generate CSRF token for forms"""
    import secrets

    return secrets.token_hex(32)


def validate_csrf_token(token: str) -> bool:
    """Validate CSRF token"""
    # Implement CSRF token validation logic
    # This is a simplified version - in production, you'd want to store tokens securely
    from flask import session

    return session.get("csrf_token") == token


def secure_headers(func):
    """Decorator to add security headers to response"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)

        # Add security headers if response is a Flask response object
        if hasattr(response, "headers"):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"

        return response

    return wrapper


def log_security_event(event_type: str, details: Dict[str, Any]):
    """Log security events for monitoring"""
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "ip": request.remote_addr if request else "unknown",
        "user_agent": request.headers.get("User-Agent", "") if request else "",
        "details": details,
    }

    security_logger.warning(f"Security Event: {log_data}")


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Hash password with salt

    Args:
        password: Password to hash
        salt: Optional salt (will generate if not provided)

    Returns:
        Tuple of (hashed_password, salt)
    """
    import hashlib
    import secrets

    if salt is None:
        salt = secrets.token_hex(32)

    # Use PBKDF2 for password hashing
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return hashed.hex(), salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify password against hash

    Args:
        password: Password to verify
        hashed_password: Stored hash
        salt: Salt used for hashing

    Returns:
        True if password matches, False otherwise
    """
    import hashlib

    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return hmac.compare_digest(hashed.hex(), hashed_password)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import os
    import re

    # Remove path components
    filename = os.path.basename(filename)

    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"

    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[: 255 - len(ext)] + ext

    return filename
