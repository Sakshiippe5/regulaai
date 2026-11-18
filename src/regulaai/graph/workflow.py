from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from regulaai.agents.extraction import StructuredLLM, extract_circular
from regulaai.agents.gap_analysis import analyze_gap
from regulaai.ingestion.pdf_reader import ParsedDocument
from regulaai.llm.client import LLMClient
from regulaai.models.analysis import GapFinding
from regulaai.models.regulatory import Circular
from regulaai.rag.index import PolicyIndex, SearchHit


class RunState(BaseModel):
    """Everything the workflow knows. Each node adds to it."""

    doc: ParsedDocument
    circular: Circular | None = None
    evidence: dict[str, list[SearchHit]] = {}
    findings: list[GapFinding] = []


def build_graph(index: PolicyIndex, llm: StructuredLLM | None = None):
    llm = llm or LLMClient()

    def extract_node(state: RunState) -> dict:
        return {"circular": extract_circular(state.doc, llm)}

    def retrieve_node(state: RunState) -> dict:
        return {"evidence": {o.id: index.search(o.text, k=3) for o in state.circular.obligations}}

    def analyze_node(state: RunState) -> dict:
        return {
            "findings": [
                analyze_gap(o, state.evidence[o.id], llm) for o in state.circular.obligations
            ]
        }

    graph = StateGraph(RunState)
    graph.add_node("extract", extract_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("analyze", analyze_node)
    graph.add_edge(START, "extract")
    graph.add_edge("extract", "retrieve")
    graph.add_edge("retrieve", "analyze")
    graph.add_edge("analyze", END)
    return graph.compile()


def run_workflow(graph, doc: ParsedDocument) -> RunState:
    result = graph.invoke(RunState(doc=doc))
    return result if isinstance(result, RunState) else RunState(**result)