from regulaai.graph.workflow import build_graph, run_workflow
from regulaai.ingestion.pdf_reader import Page, ParsedDocument
from regulaai.models.analysis import Confidence, GapStatus, LLMGapJudgement
from regulaai.models.regulatory import Circular, Obligation
from regulaai.rag.chunking import PolicyChunk
from regulaai.rag.index import PolicyIndex
from test_index import FakeEmbedder  # reuse the fake from the previous step

TEXT = "3.2 Banks shall conduct a vulnerability assessment every six months."


class RoutingFakeLLM:
    """Returns a canned answer depending on which schema is requested."""

    def complete_structured(self, system, user, schema):
        if schema is Circular:
            return Circular(
                title="T",
                obligations=[Obligation(id="TBD", section="3.2", text=TEXT[4:], source_page=1)],
            )
        return LLMGapJudgement(
            status=GapStatus.PARTIAL, rationale="yearly, not six-monthly",
            evidence_ids=["a:1"], confidence=Confidence.HIGH,
        )


def test_workflow_runs_end_to_end_with_fakes():
    index = PolicyIndex(FakeEmbedder())
    index.build([
        PolicyChunk(id="a:1", source="a.md", section="Vulnerability",
                    text="Vulnerability assessment is done once a year."),
        PolicyChunk(id="b:1", source="b.md", section="Other", text="Unrelated text."),
    ])
    doc = ParsedDocument(source="t.pdf", pages=[Page(number=1, text=TEXT)])

    state = run_workflow(build_graph(index, RoutingFakeLLM()), doc)

    assert state.circular.obligations[0].id == "OBL-001"
    assert state.findings[0].status == GapStatus.PARTIAL
    assert state.findings[0].evidence[0].source == "a.md"