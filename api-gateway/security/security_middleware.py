from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import os
from typing import Dict, Optional

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # HSTS (only in production)
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limiting with Redis"""
    
    def __init__(self, app, redis_client, limits):
        super().__init__(app)
        self.redis = redis_client
        self.limits = limits  # {"ip": "100/hour", "user": "1000/hour"}
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        
        # Check IP-based rate limiting
        ip_key = f"rate_limit:ip:{client_ip}"
        if not self.check_limit(ip_key, self.limits["ip"]):
            return Response(
                status_code=429,
                content="Too many requests from this IP",
                headers={"Retry-After": "3600"}
            )
        
        # Check user-based rate limiting (if authenticated)
        user_id = self.get_user_id(request)
        if user_id:
            user_key = f"rate_limit:user:{user_id}"
            if not self.check_limit(user_key, self.limits["user"]):
                return Response(
                    status_code=429,
                    content="Too many requests for this user",
                    headers={"Retry-After": "300"}
                )
        
        response = await call_next(request)
        return response
    
    def check_limit(self, key: str, limit_str: str) -> bool:
        """Check if request is within rate limit"""
        count, period = self.parse_limit(limit_str)
        
        # Get current window
        current_window = int(time.time() // period)
        window_key = f"{key}:{current_window}"
        
        # Increment counter
        current = self.redis.incr(window_key)
        if current == 1:  # First request in this window
            self.redis.expire(window_key, period)
        
        return current <= count
    
    def parse_limit(self, limit_str: str) -> tuple:
        """Parse limit string like '100/hour'"""
        count, period = limit_str.split("/")
        count = int(count)
        
        period_seconds = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }.get(period, 60)
        
        return count, period_seconds
    
    def get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request"""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                import jwt
                payload = jwt.decode(token, options={"verify_signature": False})
                return payload.get("sub")
            except:
                pass
        return None

class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize all inputs"""
    
    async def dispatch(self, request: Request, call_next):
        # Validate Content-Type
        content_type = request.headers.get("Content-Type", "")
        if request.method in ["POST", "PUT", "PATCH"]:
            if not content_type.startswith("application/json"):
                return Response(
                    status_code=415,
                    content="Unsupported Media Type. Use application/json"
                )
        
        # Validate request size
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
            return Response(
                status_code=413,
                content="Request too large"
            )
        
        # Sanitize query parameters
        if request.query_params:
            sanitized_query = {}
            for key, value in request.query_params.items():
                # Remove potential injection attempts
                sanitized_key = self.sanitize_string(key)
                sanitized_value = self.sanitize_string(value)
                sanitized_query[sanitized_key] = sanitized_value
            
            # Replace query params
            request.scope["query_string"] = self.dict_to_query_string(sanitized_query)
        
        response = await call_next(request)
        return response
    
    def sanitize_string(self, value: str) -> str:
        """Sanitize string to prevent injection"""
        import html
        
        # HTML escape
        value = html.escape(value)
        
        # Remove potentially dangerous characters
        dangerous = ["<", ">", "'", '"', "\\", ";", "(", ")", "&", "|"]
        for char in dangerous:
            value = value.replace(char, "")
        
        # Limit length
        if len(value) > 1000:
            value = value[:1000]
        
        return value
    
    def dict_to_query_string(self, params: Dict) -> str:
        """Convert dict to query string"""
        from urllib.parse import urlencode
        return urlencode(params).encode()
