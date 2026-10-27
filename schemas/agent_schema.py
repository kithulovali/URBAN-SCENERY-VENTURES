from typing import Any
from pydantic import BaseModel, Field

class AgentRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=4000)

class AgentResponse(BaseModel):
    agent: str
    answer: str
    model: str
    warning: str | None = None
    data_summary: dict[str, Any]
