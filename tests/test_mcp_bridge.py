import json

from regulaai.graph.workflow import build_graph, pending_review, start_run, submit_review
from regulaai.mcp_tools.adapters import McpPolicySearch, mcp_task_creator
from regulaai.mcp_tools.bridge import McpBridge
from regulaai.rag.chunking import PolicyChunk
from regulaai.rag.index import PolicyIndex
from test_index import FakeEmbedder
from test_workflow import DOC, PROFILE, RoutingFakeLLM


class FakeBridge:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def call(self, name, **arguments):
        self.calls.append((name, arguments))
        return self.rows


def server_env(tmp_path):
    # warm-up off: these tests never search, so they skip loading the embedding model
    return {"REGULAAI_OUTPUT_DIR": str(tmp_path), "REGULAAI_WARMUP": "0"}


def make_index():
    index = PolicyIndex(FakeEmbedder())
    index.build([PolicyChunk(id="a:1", source="a.md", section="Vulnerability",
                             text="Vulnerability assessment is done once a year.")])
    return index


def test_policy_search_adapter_rebuilds_search_hits():
    bridge = FakeBridge([{"chunk_id": "a:1", "source": "a.md", "section": "S", "text": "t", "score": 0.5}])
    hits = McpPolicySearch(bridge).search("q", k=2)
    assert (hits[0].chunk.source, hits[0].score) == ("a.md", 0.5)
    assert bridge.calls[0] == ("retrieve_internal_policies", {"query": "q", "top_k": 2})


def test_bridge_calls_real_server_from_sync_code(tmp_path):
    with McpBridge(server_env(tmp_path)) as bridge:
        assert bridge.call("retrieve_audit_history", limit=5) == []


def test_graph_creates_approved_tasks_through_mcp(tmp_path):
    with McpBridge(server_env(tmp_path)) as bridge:
        graph = build_graph(make_index(), RoutingFakeLLM(), output_dir=tmp_path,
                            task_creator=mcp_task_creator(bridge))
        start_run(graph, DOC, PROFILE, "t1")
        task_id = pending_review(graph, "t1")["tasks"][0]["id"]
        state = submit_review(graph, "t1", "reviewer-1", {task_id: "approve"})

    assert [t.id for t in state.created_tasks] == [task_id]
    saved = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert saved[0]["status"] == "approved"
    events = [json.loads(line)["event"] for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert events == ["task_created_via_mcp", "review_completed"]


def test_rejected_task_never_reaches_the_mcp_server(tmp_path):
    with McpBridge(server_env(tmp_path)) as bridge:
        graph = build_graph(make_index(), RoutingFakeLLM(), output_dir=tmp_path,
                            task_creator=mcp_task_creator(bridge))
        start_run(graph, DOC, PROFILE, "t1")
        task_id = pending_review(graph, "t1")["tasks"][0]["id"]
        submit_review(graph, "t1", "reviewer-1", {task_id: "reject"})

    assert not (tmp_path / "tasks.json").exists()
    events = [json.loads(line)["event"] for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert events == ["review_completed"]