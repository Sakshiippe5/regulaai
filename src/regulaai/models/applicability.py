from pydantic import BaseModel

from regulaai.models.analysis import Confidence


class ApplicabilityJudgement(BaseModel):
    """What we ask the LLM to return."""

    applies: bool
    reason: str
    confidence: Confidence


class ObligationApplicability(BaseModel):
    obligation_id: str
    applies: bool
    reason: str
    confidence: Confidence
    needs_human_review: bool

    @property
    def proceed(self) -> bool:
        """Keep in the analysis if it applies OR we are not sure."""
        return self.applies or self.needs_human_review