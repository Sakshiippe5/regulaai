from datetime import date
from enum import Enum

from pydantic import BaseModel

from regulaai.models.analysis import GapFinding
from regulaai.models.applicability import ObligationApplicability
from regulaai.models.regulatory import Obligation


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class LLMTaskProposal(BaseModel):
    """Exactly what we ask the LLM to return."""

    title: str
    description: str
    suggested_owner: str


class RemediationTask(BaseModel):
    id: str
    obligation_id: str
    title: str
    description: str
    priority: Priority
    suggested_owner: str
    due_date: date | None = None
    status: TaskStatus = TaskStatus.PROPOSED


class ComplianceReport(BaseModel):
    institution_name: str
    circular_title: str
    obligations: list[Obligation]
    not_applicable: list[ObligationApplicability]
    findings: list[GapFinding]
    tasks: list[RemediationTask]