from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from settings import get_db
from schemas.ai_schema import AIRecommendationQuery, AIRecommendationResponse, AISmartSearchResponse
from services import ai_service
from services.request_limits import enforce_rate_limit

router = APIRouter(prefix="/ai", tags=["AI Electronics Assistant"])


@router.post("/recommend", response_model=AIRecommendationResponse)
def get_ai_product_recommendations(
    payload: AIRecommendationQuery,
    request: Request,
    db: Session = Depends(get_db),
):
    """Public product recommendations with per-client abuse protection."""
    enforce_rate_limit(request, "ai-recommend", limit=20)
    return ai_service.get_electronics_recommendations(
        session=db,
        query=payload.query,
        max_budget=payload.max_budget,
        preferred_category=payload.preferred_category,
    )


@router.get("/smart-search", response_model=AISmartSearchResponse)
def ai_smart_search(
    request: Request,
    q: str = Query(..., min_length=2, max_length=300, description="Electronics search prompt"),
    db: Session = Depends(get_db),
):
    """Public catalogue search with bounded input and per-client abuse protection."""
    enforce_rate_limit(request, "ai-smart-search", limit=30)
    return ai_service.smart_search_electronics(session=db, query=q)
