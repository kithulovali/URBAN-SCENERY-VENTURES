from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from settings import get_db
from schemas.agent_schema import AgentRequest, AgentResponse
from services.ai_agents import run_agent
router = APIRouter(prefix="/ai/agents", tags=["AI Agents"])
@router.post("/business-intelligence", response_model=AgentResponse)
def business_intelligence(payload: AgentRequest, db: Session = Depends(get_db)):
    return run_agent("business_intelligence", payload.question, db)
@router.post("/product-discovery", response_model=AgentResponse)
def product_discovery(payload: AgentRequest, db: Session = Depends(get_db)):
    return run_agent("product_discovery", payload.question, db)
@router.post("/marketing-content", response_model=AgentResponse)
def marketing_content(payload: AgentRequest, db: Session = Depends(get_db)):
    return run_agent("marketing_content", payload.question, db)
