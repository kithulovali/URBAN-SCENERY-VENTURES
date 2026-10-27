from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from settings import get_db
from core.security import get_current_admin
from schemas.agent_schema import AgentRequest, AgentResponse
from services.ai_agents import run_agent

router = APIRouter(prefix="/ai/agents", tags=["AI Agents"])

# Per-process protection for the public, Gemini-backed discovery endpoint.
# Production deployments with multiple workers should enforce a shared gateway limit too.
_DISCOVERY_LIMIT = 10
_DISCOVERY_WINDOW_SECONDS = 60
_discovery_requests: dict[str, deque[float]] = defaultdict(deque)
_discovery_lock = Lock()


def _enforce_discovery_limit(client_ip: str) -> None:
    now = monotonic()
    with _discovery_lock:
        timestamps = _discovery_requests[client_ip]
        while timestamps and now - timestamps[0] >= _DISCOVERY_WINDOW_SECONDS:
            timestamps.popleft()
        if len(timestamps) >= _DISCOVERY_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Product discovery rate limit exceeded. Try again in one minute.",
                headers={"Retry-After": str(_DISCOVERY_WINDOW_SECONDS)},
            )
        timestamps.append(now)


@router.post(
    "/business-intelligence",
    response_model=AgentResponse,
    dependencies=[Depends(get_current_admin)],
)
def business_intelligence(payload: AgentRequest, db: Session = Depends(get_db)):
    """Business metrics can expose operational data, so require an administrator."""
    return run_agent("business_intelligence", payload.question, db)


@router.post("/product-discovery", response_model=AgentResponse)
def product_discovery(
    payload: AgentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Public shopping discovery is rate-limited to reduce provider quota abuse."""
    client_ip = request.client.host if request.client else "unknown"
    _enforce_discovery_limit(client_ip)
    return run_agent("product_discovery", payload.question, db)


@router.post(
    "/marketing-content",
    response_model=AgentResponse,
    dependencies=[Depends(get_current_admin)],
)
def marketing_content(payload: AgentRequest, db: Session = Depends(get_db)):
    """Marketing drafts are an internal tool and require an administrator."""
    return run_agent("marketing_content", payload.question, db)
