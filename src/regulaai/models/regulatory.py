from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class ObligationType(str, Enum):
    REPORTING = "reporting"
    POLICY = "policy"
    PROCESS = "process"
    DISCLOSURE = "disclosure"
    OTHER = "other"


class Obligation(BaseModel):
    """One concrete thing a regulator requires a bank to do."""

    id: str = Field(description="Short unique id, e.g. 'OBL-001'")
    section: str = Field(description="Section or paragraph in the circular")
    text: str = Field(description="The requirement, close to the original wording")
    obligation_type: ObligationType = ObligationType.OTHER
    deadline: date | None = None
    source_page: int | None = None


class Circular(BaseModel):
    """A regulatory document after the Extraction Agent has processed it."""

    title: str
    regulator: str = Field(description="e.g. RBI, SEBI")
    issue_date: date | None = None
    obligations: list[Obligation] = []