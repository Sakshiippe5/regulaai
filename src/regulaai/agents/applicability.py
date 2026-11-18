from regulaai.agents.extraction import StructuredLLM
from regulaai.llm.client import LLMClient
from regulaai.models.analysis import Confidence
from regulaai.models.applicability import ApplicabilityJudgement, ObligationApplicability
from regulaai.models.institution import InstitutionProfile
from regulaai.models.regulatory import Circular, Obligation

SYSTEM_PROMPT = """You decide whether a regulatory obligation applies to a specific financial institution.

You are given the circular's applicability statement, one obligation, and the institution's profile.
- applies=true if the institution falls within the circular's stated scope AND nothing in the
  obligation limits it to a group the institution is not part of (for example, a service the
  institution does not offer).
- applies=false only if the scope or the obligation clearly excludes this institution.
- If the applicability statement is missing or unclear, use confidence low.
- reason: 1 to 2 sentences naming the scope or condition that decided it.
- Use only the information provided. Do not assume anything about the institution.
"""


def judge_applicability(
    circular: Circular,
    obligation: Obligation,
    profile: InstitutionProfile,
    llm: StructuredLLM | None = None,
) -> ObligationApplicability:
    llm = llm or LLMClient()
    user = (
        f"CIRCULAR APPLICABILITY STATEMENT:\n{circular.applicability_statement or '(not stated)'}\n\n"
        f"OBLIGATION {obligation.id} (section {obligation.section}):\n{obligation.text}\n\n"
        f"INSTITUTION PROFILE:\n{profile.model_dump_json(indent=2)}"
    )
    j = llm.complete_structured(SYSTEM_PROMPT, user, ApplicabilityJudgement)
    return ObligationApplicability(
        obligation_id=obligation.id,
        applies=j.applies,
        reason=j.reason,
        confidence=j.confidence,
        needs_human_review=(
            j.confidence == Confidence.LOW or not circular.applicability_statement
        ),
    )