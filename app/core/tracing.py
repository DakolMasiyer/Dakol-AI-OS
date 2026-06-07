import contextvars
import uuid
import os
from typing import Optional, Any
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

VALIDATION_MODE = os.getenv("VALIDATION_MODE", "OBSERVABILITY")

import time
from app.core.logging import get_logger

logger = get_logger(__name__)

# Context variables for request and workflow ID tracking
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
workflow_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("workflow_id", default=None)


def get_request_id() -> Optional[str]:
    """Retrieve the current request ID from context."""
    return request_id_var.get()


def get_workflow_id() -> Optional[str]:
    """Retrieve the current workflow ID from context."""
    return workflow_id_var.get()


def set_request_id(request_id: str) -> Any:
    """Set the request ID in context, returning a reset token."""
    return request_id_var.set(request_id)


def set_workflow_id(workflow_id: str) -> Any:
    """Set the workflow ID in context, returning a reset token."""
    return workflow_id_var.set(workflow_id)


def reset_request_id(token: Any) -> None:
    """Reset the request ID in context using a token."""
    request_id_var.reset(token)


def reset_workflow_id(token: Any) -> None:
    """Reset the workflow ID in context using a token."""
    workflow_id_var.reset(token)


def assert_clean_outputs(outputs: dict):
    forbidden_keys = {"_request_id", "_workflow_id"}
    for k in forbidden_keys:
        assert k not in outputs, f"Metadata leakage detected: {k}"
    for v in outputs.values():
        if isinstance(v, dict):
            assert_clean_outputs(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    assert_clean_outputs(item)


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates or propagates a unique Request ID (X-Request-ID)
    for every incoming HTTP request and returns it in the response headers.
    It does not modify response JSON bodies. Logs started and completed events.
    """
    async def dispatch(self, request: Request, call_next):
        # Extract X-Request-ID from headers, or generate a new UUID4 if not provided
        req_id = request.headers.get("x-request-id") or request.headers.get("X-Request-ID")
        if not req_id:
            req_id = str(uuid.uuid4())

        # Set the request ID context variable
        token = set_request_id(req_id)
        start_time = time.perf_counter()

        logger.info(
            "Request started",
            extra={
                "event": "request_started",
                "request_id": req_id,
                "method": request.method,
                "path": request.url.path,
            }
        )

        try:
            response = await call_next(request)
            
            # Add X-Request-ID to the HTTP response headers
            response.headers["X-Request-ID"] = req_id
            
            # If a workflow ID was generated internally during the request, expose it in response headers
            work_id = get_workflow_id()
            if work_id:
                response.headers["X-Workflow-ID"] = work_id

            # Verify the API response serialization layer
            if "application/json" in response.headers.get("content-type", ""):
                body_bytes = b""
                async for chunk in response.body_iterator:
                    body_bytes += chunk
                
                async def body_stream():
                    yield body_bytes
                response.body_iterator = body_stream()

                # 1. Performance Guard: Skip parsing for very large responses (> 1MB)
                if len(body_bytes) > 1024 * 1024:
                    logger.warning("Skipping response body validation: response size exceeds 1MB limit")
                # 2. Fast Pre-scan: Only parse if the target forbidden keys are found in raw bytes
                elif b'"_request_id"' in body_bytes or b'"_workflow_id"' in body_bytes:
                    try:
                        import json
                        res_data = json.loads(body_bytes.decode("utf-8"))
                        
                        def check_nested(val: Any):
                            if isinstance(val, dict):
                                assert_clean_outputs(val)
                                for v in val.values():
                                    check_nested(v)
                            elif isinstance(val, list):
                                for item in val:
                                    check_nested(item)
                                    
                        check_nested(res_data)
                    except AssertionError as exc:
                        logger.error(f"API Serialization Leakage detected: {exc}", exc_info=True)
                        if VALIDATION_MODE == "STRICT":
                            raise exc
                    except Exception as exc:
                        # Log parsing or evaluation errors, and propagate if STRICT mode is enabled
                        logger.error(f"Failed to parse or validate JSON response body: {exc}", exc_info=True)
                        if VALIDATION_MODE == "STRICT":
                            raise exc
                
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "Request completed",
                extra={
                    "event": "request_completed",
                    "request_id": req_id,
                    "workflow_id": work_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            )
            return response
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            work_id = get_workflow_id()
            logger.error(
                "Request failed",
                extra={
                    "event": "request_failed",
                    "request_id": req_id,
                    "workflow_id": work_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
                exc_info=True
            )
            raise exc
        finally:
            # Clean up request_id context variable
            reset_request_id(token)

