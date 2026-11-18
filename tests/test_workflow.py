from regulaai.graph.workflow import build_graph, run_workflow
from regulaai.ingestion.pdf_reader import Page, ParsedDocument
from regulaai.models.analysis import Confidence, GapStatus, LLMGapJudgement
from regulaai.models.applicability import ApplicabilityJudgement
from regulaai.models.institution import InstitutionProfile
from regulaai.models.regulatory import Circular, Obligation
from regulaai.rag.chunking import PolicyChunk
from regulaai.rag.index import PolicyIndex
from test_index import FakeEmbedder
from regulaai.models.report import LLMTaskProposal

TEXT = "3.2 Banks shall conduct a vulnerability assessment every six months."
PROFILE = InstitutionProfile(name="X", institution_type="Urban Co-operative Bank")


class RoutingFakeLLM:
    """Returns a canned answer depending on which schema is requested."""

    def __init__(self, applies: bool = True, conf: Confidence = Confidence.HIGH) -> None:
        self.applies, self.conf = applies, conf

    def complete_structured(self, system, user, schema):
        if schema is Circular:
            return Circular(
                title="T",
                applicability_statement="Applies to all Urban Co-operative Banks.",
                obligations=[Obligation(id="TBD", section="3.2", text=TEXT[4:], source_page=1)],
            )
        if schema is ApplicabilityJudgement:
            return ApplicabilityJudgement(applies=self.applies, reason="r", confidence=self.conf)
        if schema is LLMTaskProposal:
            return LLMTaskProposal(
                title="Update policy", description="Shorten the cycle.", suggested_owner="CISO"
            )
        return LLMGapJudgement(
            status=GapStatus.PARTIAL, rationale="yearly, not six-monthly",
            evidence_ids=["a:1"], confidence=Confidence.HIGH,
        )


def make_graph(llm):
    index = PolicyIndex(FakeEmbedder())
    index.build([
        PolicyChunk(id="a:1", source="a.md", section="Vulnerability",
                    text="Vulnerability assessment is done once a year."),
        PolicyChunk(id="b:1", source="b.md", section="Other", text="Unrelated text."),
    ])
    return build_graph(index, llm)


DOC = ParsedDocument(source="t.pdf", pages=[Page(number=1, text=TEXT)])


def test_applicable_obligation_goes_through_full_pipeline():
    state = run_workflow(make_graph(RoutingFakeLLM()), DOC, PROFILE)
    assert state.circular.obligations[0].id == "OBL-001"
    assert state.findings[0].status == GapStatus.PARTIAL
    assert state.findings[0].evidence[0].source == "a.md"


def test_nothing_applicable_stops_early():
    state = run_workflow(make_graph(RoutingFakeLLM(applies=False)), DOC, PROFILE)
    assert state.applicability[0].applies is False
    assert state.findings == []
    assert state.evidence == {}


def test_unsure_exclusion_still_gets_analyzed():
    llm = RoutingFakeLLM(applies=False, conf=Confidence.LOW)
    state = run_workflow(make_graph(llm), DOC, PROFILE)
    assert len(state.findings) == 1

def test_report_is_built_for_both_branches():
    full = run_workflow(make_graph(RoutingFakeLLM()), DOC, PROFILE)
    assert len(full.report.tasks) == 1
    assert full.report.tasks[0].obligation_id == "OBL-001"

    empty = run_workflow(make_graph(RoutingFakeLLM(applies=False)), DOC, PROFILE)
    assert empty.report is not None
    assert empty.report.tasks == []
    assert len(empty.report.not_applicable) == 1