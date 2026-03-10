"""
core/auth.py — Middleware de autenticación por API Keys
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from core.db import (
    validate_api_key,
    increment_daily_usage,
    get_rate_limit,
    PLAN_LIMITS
)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware que valida API keys en el header X-API-Key.
    Aplica rate limiting según el plan del usuario.
    """
    
    EXCLUDED_PATHS = {"/health", "/internal/", "/docs", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return await call_next(request)
        
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="Missing X-API-Key header"
            )
        
        key_data = await validate_api_key(api_key)
        
        if not key_data:
            raise HTTPException(
                status_code=401,
                detail="Invalid or inactive API key"
            )
        
        plan = key_data["plan"]
        daily_used = key_data["daily_checks_used"]
        limit = PLAN_LIMITS.get(plan)
        
        if limit is not None and daily_used >= limit:
            raise HTTPException(
                status_code=429,
                detail="Daily rate limit exceeded",
                headers={"Retry-After": "86400"}
            )
        
        await increment_daily_usage(str(key_data["id"]))
        
        request.state.api_key_data = key_data
        request.state.plan = plan
        
        return await call_next(request)
