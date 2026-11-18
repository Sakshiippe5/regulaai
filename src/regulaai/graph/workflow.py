from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel

from regulaai.agents.applicability import judge_applicability
from regulaai.agents.extraction import StructuredLLM, extract_circular
from regulaai.agents.gap_analysis import analyze_gap
from regulaai.agents.report import build_report
from regulaai.ingestion.pdf_reader import ParsedDocument
from regulaai.llm.client import LLMClient
from regulaai.models.analysis import GapFinding
from regulaai.models.applicability import ObligationApplicability
from regulaai.models.institution import InstitutionProfile
from regulaai.models.regulatory import Circular, Obligation
from regulaai.models.report import ComplianceReport, RemediationTask, TaskStatus
from regulaai.rag.index import PolicyIndex, SearchHit
from regulaai.tools.tasks import append_audit, create_remediation_tasks


class RunState(BaseModel):
    """Everything the workflow knows. Each node adds to it."""

    doc: ParsedDocument
    profile: InstitutionProfile
    circular: Circular | None = None
    applicability: list[ObligationApplicability] = []
    evidence: dict[str, list[SearchHit]] = {}
    findings: list[GapFinding] = []
    report: ComplianceReport | None = None
    reviewer: str | None = None
    created_tasks: list[RemediationTask] = []


def in_scope(state: RunState) -> list[Obligation]:
    keep = {a.obligation_id for a in state.applicability if a.proceed}
    return [o for o in state.circular.obligations if o.id in keep]


def build_graph(
    index: PolicyIndex,
    llm: StructuredLLM | None = None,
    output_dir: str | Path = "outputs",
):
    llm = llm or LLMClient()
    output_dir = Path(output_dir)

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

    def route_after_report(state: RunState) -> str:
        return "review" if state.report.tasks else "end"

    def review_node(state: RunState) -> dict:
        # Everything BEFORE interrupt() runs again on resume, so keep it free of side effects.
        answer = interrupt(
            {
                "message": "Review the proposed remediation tasks.",
                "tasks": [t.model_dump(mode="json") for t in state.report.tasks],
            }
        )
        decisions = answer.get("decisions", {})
        verdicts = {"approve": TaskStatus.APPROVED, "reject": TaskStatus.REJECTED}
        updated = [
            t.model_copy(update={"status": verdicts.get(decisions.get(t.id), t.status)})
            for t in state.report.tasks
        ]
        return {
            "report": state.report.model_copy(update={"tasks": updated}),
            "reviewer": answer.get("reviewer") or "unknown",
        }

    def finalize_node(state: RunState) -> dict:
        approved = [t for t in state.report.tasks if t.status == TaskStatus.APPROVED]
        create_remediation_tasks(approved, output_dir / "tasks.json")
        append_audit(
            {
                "event": "review_completed",
                "reviewer": state.reviewer,
                "circular": state.report.circular_title,
                "institution": state.report.institution_name,
                "decisions": {t.id: t.status.value for t in state.report.tasks},
                "tasks_created": [t.id for t in approved],
            },
            output_dir / "audit.jsonl",
        )
        return {"created_tasks": approved}

    graph = StateGraph(RunState)
    graph.add_node("extract", extract_node)
    graph.add_node("applicability", applicability_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("report", report_node)
    graph.add_node("review", review_node)
    graph.add_node("finalize", finalize_node)
    graph.add_edge(START, "extract")
    graph.add_edge("extract", "applicability")
    graph.add_conditional_edges(
        "applicability", route_after_applicability, {"retrieve": "retrieve", "report": "report"}
    )
    graph.add_edge("retrieve", "analyze")
    graph.add_edge("analyze", "report")
    graph.add_conditional_edges("report", route_after_report, {"review": "review", "end": END})
    graph.add_edge("review", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=MemorySaver())


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def get_state(graph, thread_id: str) -> RunState:
    values = graph.get_state(_config(thread_id)).values
    return values if isinstance(values, RunState) else RunState(**values)


def start_run(graph, doc: ParsedDocument, profile: InstitutionProfile, thread_id: str) -> None:
    graph.invoke(RunState(doc=doc, profile=profile), _config(thread_id))


def pending_review(graph, thread_id: str) -> dict | None:
    """The payload the graph is waiting on, or None if the run is not paused."""
    for task in graph.get_state(_config(thread_id)).tasks:
        for pause in task.interrupts:
            return pause.value
    return None


def submit_review(
    graph, thread_id: str, reviewer: str, decisions: dict[str, str]
) -> RunState:
    """decisions maps task id to 'approve' or 'reject'. Undecided tasks are not created."""
    graph.invoke(
        Command(resume={"reviewer": reviewer, "decisions": decisions}), _config(thread_id)
    )
    return get_state(graph, thread_id)


def run_workflow(
    graph, doc: ParsedDocument, profile: InstitutionProfile, thread_id: str = "run-1"
) -> RunState:
    """Runs until the end, or until the graph pauses for human review."""
    start_run(graph, doc, profile, thread_id)
    return get_state(graph, thread_id)