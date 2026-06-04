from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class JusticeScore(BaseModel):
    case_strength: int = Field(..., ge=0, le=100)
    evidence_completeness: int = Field(..., ge=0, le=100)
    missing_items: list[str] = []
    verdict: str

class Citation(BaseModel):
    act: str
    section: str
    excerpt: str
    confidence: float
    source: str = "atlas_vector_search"

class CitationOutput(BaseModel):
    recommended_action: str
    supporting_law: list[Citation]
    overall_confidence: float

class Case(BaseModel):
    case_id: str
    user_id: str
    dispute_type: str
    status: str = "open"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    facts: dict = {}
    justice_score: Optional[JusticeScore] = None
    citation_output: Optional[CitationOutput] = None
    action_timeline: list[dict] = []
