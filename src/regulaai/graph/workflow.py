from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from regulaai.agents.applicability import judge_applicability
from regulaai.agents.extraction import StructuredLLM, extract_circular
from regulaai.agents.gap_analysis import analyze_gap
from regulaai.ingestion.pdf_reader import ParsedDocument
from regulaai.llm.client import LLMClient
from regulaai.models.analysis import GapFinding
from regulaai.models.applicability import ObligationApplicability
from regulaai.models.institution import InstitutionProfile
from regulaai.models.regulatory import Circular, Obligation
from regulaai.rag.index import PolicyIndex, SearchHit
from regulaai.agents.report import build_report
from regulaai.models.report import ComplianceReport


class RunState(BaseModel):
    """Everything the workflow knows. Each node adds to it."""

    doc: ParsedDocument
    profile: InstitutionProfile
    circular: Circular | None = None
    applicability: list[ObligationApplicability] = []
    evidence: dict[str, list[SearchHit]] = {}
    findings: list[GapFinding] = []
    report: ComplianceReport | None = None

def in_scope(state: RunState) -> list[Obligation]:
    keep = {a.obligation_id for a in state.applicability if a.proceed}
    return [o for o in state.circular.obligations if o.id in keep]


def build_graph(index: PolicyIndex, llm: StructuredLLM | None = None):
    llm = llm or LLMClient()

    def extract_node(state: RunState) -> dict:
        return {"circular": extract_circular(state.doc, llm)}

    def applicability_node(state: RunState) -> dict:
        return {
            "applicability": [
                judge_applicability(state.circular, o, state.profile, llm)
                for o in state.circular.obligations
            ]
        }

    def route_after_applicability(state: RunState) -> str:
        return "retrieve" if in_scope(state) else "report"

    def retrieve_node(state: RunState) -> dict:
        return {"evidence": {o.id: index.search(o.text, k=3) for o in in_scope(state)}}

    def analyze_node(state: RunState) -> dict:
        return {"findings": [analyze_gap(o, state.evidence[o.id], llm) for o in in_scope(state)]}

    def report_node(state: RunState) -> dict:
            return {
                "report": build_report(
                    state.profile, state.circular, state.applicability, state.findings, llm
                )
            }

    graph = StateGraph(RunState)
    graph.add_node("extract", extract_node)
    graph.add_node("applicability", applicability_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("report", report_node)
    graph.add_edge(START, "extract")
    graph.add_edge("extract", "applicability")
    graph.add_conditional_edges(
        "applicability", route_after_applicability, {"retrieve": "retrieve", "report": "report"}
    )
    graph.add_edge("retrieve", "analyze")
    graph.add_edge("analyze", "report")
    graph.add_edge("report", END)
    return graph.compile()


def run_workflow(graph, doc: ParsedDocument, profile: InstitutionProfile) -> RunState:
    result = graph.invoke(RunState(doc=doc, profile=profile))
    return result if isinstance(result, RunState) else RunState(**result)