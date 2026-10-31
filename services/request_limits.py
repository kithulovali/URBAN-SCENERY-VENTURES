"""Small in-process request limits for public endpoints.

For multi-worker deployments, enforce an equivalent shared limit at the API gateway
or use a shared Redis-backed limiter. The local limiter is defense in depth.
"""
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status

_requests: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_lock = Lock()


def enforce_rate_limit(request: Request, bucket: str, limit: int, window_seconds: int = 60) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = monotonic()
    key = (bucket, client_ip)
    with _lock:
        timestamps = _requests[key]
        while timestamps and now - timestamps[0] >= window_seconds:
            timestamps.popleft()
        if len(timestamps) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Request rate limit exceeded. Please try again shortly.",
                headers={"Retry-After": str(window_seconds)},
            )
        timestamps.append(now)
