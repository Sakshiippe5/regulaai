from regulaai.agents.extraction import StructuredLLM
from regulaai.llm.client import LLMClient
from regulaai.models.analysis import (
    Confidence, Evidence, GapFinding, GapStatus, LLMGapJudgement,
)
from regulaai.models.regulatory import Obligation
from regulaai.rag.index import SearchHit

SYSTEM_PROMPT = """You are a compliance analyst comparing a regulatory obligation against
excerpts from a bank's internal policies.

Decide the status:
- covered: an excerpt fully meets the obligation.
- partial: a related control exists but falls short.
- missing: no excerpt addresses the obligation.

How to judge:
- Compare the specifics: time limits, frequency, who is responsible, scope, and conditions.
  A control that is slower, less frequent, narrower, or only applies in some cases is PARTIAL.
- Use ONLY the excerpts provided. Never assume a control exists.
- evidence_ids: list the ids in square brackets (e.g. "policy_name:2") of the excerpts you
  relied on. Cite only ids that appear below. Use [] if status is missing.
- rationale: 1 to 3 sentences naming the exact mismatch or match (for example, "policy says
  24 hours, obligation requires 6 hours").
- confidence: low, medium, or high. Use low if the excerpts are ambiguous.
"""


def analyze_gap(
    obligation: Obligation,
    hits: list[SearchHit],
    llm: StructuredLLM | None = None,
) -> GapFinding:
    llm = llm or LLMClient()

    excerpts = "\n\n".join(
        f"[{h.chunk.id}] {h.chunk.source} - {h.chunk.section}\n{h.chunk.text}" for h in hits
    )
    user = (
        f"OBLIGATION {obligation.id} (circular section {obligation.section}):\n"
        f"{obligation.text}\n\nINTERNAL POLICY EXCERPTS:\n{excerpts}"
    )
    judgement = llm.complete_structured(SYSTEM_PROMPT, user, LLMGapJudgement)

    retrieved = {h.chunk.id: h.chunk for h in hits}
    cited = [retrieved[i] for i in judgement.evidence_ids if i in retrieved]
    invented_citation = len(cited) != len(judgement.evidence_ids)
    unsupported_claim = judgement.status != GapStatus.MISSING and not cited

    return GapFinding(
        obligation_id=obligation.id,
        obligation_text=obligation.text,
        status=judgement.status,
        rationale=judgement.rationale,
        evidence=[
            Evidence(chunk_id=c.id, source=c.source, section=c.section, text=c.text)
            for c in cited
        ],
        confidence=judgement.confidence,
        needs_human_review=(
            judgement.confidence == Confidence.LOW or invented_citation or unsupported_claim
        ),
    )