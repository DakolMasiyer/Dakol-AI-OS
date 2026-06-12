from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Any
import time

class GatewayMiddleware(BaseHTTPMiddleware):
    """
    Middleware for operational request logging, execution fingerprints,
    and replay-safe tracing.
    """
    async def dispatch(self, request: Request, call_next: Any):
        # We can implement specific gateway trace logging here 
        # or quota checking prior to route handlers.
        
        # Currently just passing through, as the core tracing is in app.core.tracing.
        start = time.perf_counter()
        
        # We can set custom gateway headers or context vars here if needed.
        
        response = await call_next(request)
        
        # Add a custom gateway header for observability
        response.headers["X-Gateway-Processed"] = "true"
        response.headers["X-Gateway-Latency-Ms"] = str(int((time.perf_counter() - start) * 1000))
        
        return response
