import time
from uuid import uuid4

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import RequestResponseEndpoint


async def log_requests(request: Request, call_next: RequestResponseEndpoint) -> Response:
    started_at = time.perf_counter()
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id

    bound_logger = logger.bind(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )
    bound_logger.info("HTTP request started")

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        bound_logger.exception(f"HTTP request failed in {duration_ms} ms")
        raise

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    bound_logger.bind(
        status_code=response.status_code,
        duration_ms=duration_ms,
    ).info("HTTP request completed")
    return response
