from enum import Enum

from pydantic import BaseModel


class GapStatus(str, Enum):
    COVERED = "covered"
    PARTIAL = "partial"
    MISSING = "missing"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LLMGapJudgement(BaseModel):
    """Exactly what we ask the LLM to return."""

    status: GapStatus
    rationale: str
    evidence_ids: list[str] = []
    confidence: Confidence


class Evidence(BaseModel):
    chunk_id: str
    source: str
    section: str
    text: str


class GapFinding(BaseModel):
    """The final, verified finding that goes into the report."""

    obligation_id: str
    obligation_text: str
    status: GapStatus
    rationale: str
    evidence: list[Evidence]
    confidence: Confidence
    needs_human_review: bool