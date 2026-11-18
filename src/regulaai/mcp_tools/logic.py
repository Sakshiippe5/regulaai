import json
from pathlib import Path

from regulaai.models.report import RemediationTask, TaskStatus
from regulaai.tools.tasks import append_audit, create_remediation_tasks


def retrieve_policies(index, query: str, top_k: int = 3) -> list[dict]:
    """`index` is a PolicyIndex. Returns citable hits."""
    k = max(1, min(top_k, 10))
    return [
        {
            "chunk_id": h.chunk.id,
            "source": h.chunk.source,
            "section": h.chunk.section,
            "text": h.chunk.text,
            "score": round(h.score, 3),
        }
        for h in index.search(query, k=k)
    ]


def create_task(
    *,
    output_dir: str | Path,
    task_id: str,
    obligation_id: str,
    title: str,
    description: str,
    priority: str,
    suggested_owner: str,
    approval_status: str,
    reviewer: str,
    due_date: str | None = None,
) -> dict:
    if approval_status != TaskStatus.APPROVED.value:
        raise ValueError("Tasks can only be created after human approval: approval_status must be 'approved'.")
    if not reviewer.strip():
        raise ValueError("reviewer is required for the audit trail.")

    task = RemediationTask(
        id=task_id,
        obligation_id=obligation_id,
        title=title,
        description=description,
        priority=priority,
        suggested_owner=suggested_owner,
        due_date=due_date,
        status=TaskStatus.APPROVED,
    )
    output_dir = Path(output_dir)
    create_remediation_tasks([task], output_dir / "tasks.json")
    append_audit(
        {"event": "task_created_via_mcp", "task_id": task.id, "reviewer": reviewer.strip()},
        output_dir / "audit.jsonl",
    )
    return {"created": task.id, "stored_in": "tasks.json"}


def read_audit(path: str | Path, limit: int = 20, event: str | None = None) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if event:
        rows = [r for r in rows if r.get("event") == event]
    return rows[-max(1, min(limit, 100)):]