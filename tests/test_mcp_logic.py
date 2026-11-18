import json

import pytest

from regulaai.mcp_tools import logic
from regulaai.rag.chunking import PolicyChunk
from regulaai.rag.index import PolicyIndex
from test_index import FakeEmbedder

TASK = dict(
    task_id="TASK-001", obligation_id="OBL-004", title="Shorten cycle",
    description="Amend policy.", priority="medium", suggested_owner="CISO",
)


def test_retrieve_returns_citable_fields():
    index = PolicyIndex(FakeEmbedder())
    index.build([PolicyChunk(id="a:1", source="a.md", section="Vulnerability",
                             text="Vulnerability assessment once a year.")])
    hit = logic.retrieve_policies(index, "vulnerability assessment", top_k=3)[0]
    assert (hit["source"], hit["section"]) == ("a.md", "Vulnerability")


def test_create_rejects_unapproved(tmp_path):
    with pytest.raises(ValueError):
        logic.create_task(output_dir=tmp_path, approval_status="proposed", reviewer="r1", **TASK)
    assert not (tmp_path / "tasks.json").exists()


def test_create_requires_reviewer(tmp_path):
    with pytest.raises(ValueError):
        logic.create_task(output_dir=tmp_path, approval_status="approved", reviewer="  ", **TASK)


def test_create_writes_task_and_audit(tmp_path):
    out = logic.create_task(output_dir=tmp_path, approval_status="approved", reviewer="r1", **TASK)
    assert out["created"] == "TASK-001"
    assert json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))[0]["status"] == "approved"
    assert logic.read_audit(tmp_path / "audit.jsonl")[0]["reviewer"] == "r1"


def test_read_audit_filters_and_limits(tmp_path):
    path = tmp_path / "audit.jsonl"
    path.write_text(
        "\n".join(json.dumps({"event": e, "n": n}) for n, e in enumerate(["a", "b", "a", "a"])),
        encoding="utf-8",
    )
    assert [r["n"] for r in logic.read_audit(path, limit=2, event="a")] == [2, 3]
    assert logic.read_audit(tmp_path / "missing.jsonl") == []