from regulaai.agents.gap_analysis import analyze_gap
from regulaai.models.analysis import Confidence, GapStatus, LLMGapJudgement
from regulaai.models.regulatory import Obligation
from regulaai.rag.chunking import PolicyChunk
from regulaai.rag.index import SearchHit


class FakeLLM:
    def __init__(self, judgement: LLMGapJudgement) -> None:
        self._judgement = judgement

    def complete_structured(self, system, user, schema):
        return self._judgement


OBLIGATION = Obligation(id="OBL-004", section="3.2", text="Conduct a vulnerability assessment every six months.")
HITS = [SearchHit(
    chunk=PolicyChunk(id="isp:2", source="isp.md", section="2. Vulnerability",
                      text="Assessment once a year."),
    score=0.6,
)]


def judge(status=GapStatus.PARTIAL, ids=("isp:2",), conf=Confidence.HIGH):
    return LLMGapJudgement(status=status, rationale="r", evidence_ids=list(ids), confidence=conf)


def test_valid_citation_needs_no_review():
    f = analyze_gap(OBLIGATION, HITS, FakeLLM(judge()))
    assert f.status == GapStatus.PARTIAL
    assert f.evidence[0].source == "isp.md"
    assert f.needs_human_review is False


def test_invented_citation_is_flagged():
    f = analyze_gap(OBLIGATION, HITS, FakeLLM(judge(ids=("made_up:9",))))
    assert f.needs_human_review is True
    assert f.evidence == []


def test_covered_without_evidence_is_flagged():
    f = analyze_gap(OBLIGATION, HITS, FakeLLM(judge(status=GapStatus.COVERED, ids=())))
    assert f.needs_human_review is True


def test_missing_without_evidence_is_fine():
    f = analyze_gap(OBLIGATION, HITS, FakeLLM(judge(status=GapStatus.MISSING, ids=())))
    assert f.needs_human_review is False


def test_low_confidence_is_flagged():
    f = analyze_gap(OBLIGATION, HITS, FakeLLM(judge(conf=Confidence.LOW)))
    assert f.needs_human_review is True