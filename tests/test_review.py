import json

from regulaai.graph.workflow import (
    build_graph, get_state, pending_review, start_run, submit_review,
)
from regulaai.models.report import TaskStatus
from regulaai.rag.chunking import PolicyChunk
from regulaai.rag.index import PolicyIndex
from test_index import FakeEmbedder
from test_workflow import DOC, PROFILE, RoutingFakeLLM


def make_graph(tmp_path):
    index = PolicyIndex(FakeEmbedder())
    index.build([
        PolicyChunk(id="a:1", source="a.md", section="Vulnerability",
                    text="Vulnerability assessment is done once a year."),
    ])
    return build_graph(index, RoutingFakeLLM(), output_dir=tmp_path)


def test_run_pauses_for_review_and_creates_nothing(tmp_path):
    graph = make_graph(tmp_path)
    start_run(graph, DOC, PROFILE, "t1")
    review = pending_review(graph, "t1")
    assert review is not None
    assert len(review["tasks"]) == 1
    assert not (tmp_path / "tasks.json").exists()


def test_approved_task_is_created_and_audited(tmp_path):
    graph = make_graph(tmp_path)
    start_run(graph, DOC, PROFILE, "t1")
    task_id = pending_review(graph, "t1")["tasks"][0]["id"]

    state = submit_review(graph, "t1", "reviewer-1", {task_id: "approve"})

    assert pending_review(graph, "t1") is None
    assert [t.id for t in state.created_tasks] == [task_id]
    saved = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert saved[0]["status"] == "approved"
    audit = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert audit[0]["reviewer"] == "reviewer-1"
    assert audit[0]["tasks_created"] == [task_id]


def test_rejected_task_is_not_created(tmp_path):
    graph = make_graph(tmp_path)
    start_run(graph, DOC, PROFILE, "t1")
    task_id = pending_review(graph, "t1")["tasks"][0]["id"]

    state = submit_review(graph, "t1", "reviewer-1", {task_id: "reject"})

    assert state.created_tasks == []
    assert state.report.tasks[0].status == TaskStatus.REJECTED
    assert not (tmp_path / "tasks.json").exists()
    assert (tmp_path / "audit.jsonl").exists()  # the decision is still on record


def test_undecided_task_is_not_created(tmp_path):
    graph = make_graph(tmp_path)
    start_run(graph, DOC, PROFILE, "t1")
    state = submit_review(graph, "t1", "reviewer-1", {})
    assert state.created_tasks == []
    assert state.report.tasks[0].status == TaskStatus.PROPOSED