from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from settings import get_db
from core.security import get_current_admin
from schemas.agent_schema import AgentRequest, AgentResponse
from services.ai_agents import run_agent
from services.image_generation import generate_image

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



@router.post(
    "/image-studio",
    response_model=AgentResponse,
    dependencies=[Depends(get_current_admin)],
)
def image_studio(payload: AgentRequest, db: Session = Depends(get_db)):
    """Generate a catalogue-grounded image brief; actual rendering needs an image provider."""
    return run_agent("image_studio", payload.question, db)


@router.post("/customer-shopping-assistant", response_model=AgentResponse)
def customer_shopping_assistant(
    payload: AgentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Answer shopping questions from available catalogue data; never invent product facts."""
    client_ip = request.client.host if request.client else "unknown"
    _enforce_discovery_limit(client_ip)
    return run_agent("customer_shopping_assistant", payload.question, db)


@router.post(
    "/growth-optimization",
    response_model=AgentResponse,
    dependencies=[Depends(get_current_admin)],
)
def growth_optimization(payload: AgentRequest, db: Session = Depends(get_db)):
    """Provide cautious growth recommendations grounded in loaded business records."""
    return run_agent("growth_optimization", payload.question, db)



@router.post(
    "/image-studio/render",
    dependencies=[Depends(get_current_admin)],
)
def image_studio_render(payload: AgentRequest, db: Session = Depends(get_db)):
    """Generate a product image and return it as base64 for client-side preview."""
    brief = run_agent("image_studio", payload.question, db)
    if "no image was generated" in brief["answer"].lower() or "identify a catalogue product" in brief["answer"].lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=brief["answer"],
        )
    try:
        rendered = generate_image(brief["answer"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {
        "agent": "image_studio",
        "model": rendered["model"],
        "prompt": brief["answer"],
        "mime_type": rendered["mime_type"],
        "image_base64": rendered["image_base64"],
        "warning": "AI-generated product imagery must be checked against the real item before publication.",
        "data_summary": brief["data_summary"],
    }
