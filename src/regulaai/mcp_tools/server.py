import contextlib
import json
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from regulaai.mcp_tools import logic

OUTPUT_DIR = Path(os.environ.get("REGULAAI_OUTPUT_DIR", "outputs"))
POLICY_DIR = Path(os.environ.get("REGULAAI_POLICY_DIR", "data/policies"))

mcp = FastMCP("regulaai-tools")
_index = None


def get_index():
    """Built once, at server start (see the bottom of this file), so no search call waits for it."""
    global _index
    if _index is None:
        # stdout is the MCP protocol channel: keep library output off it
        with contextlib.redirect_stdout(sys.stderr):
            from regulaai.rag.chunking import load_policies
            from regulaai.rag.embeddings import FastEmbedder
            from regulaai.rag.index import PolicyIndex

            index = PolicyIndex(FastEmbedder())
            index.build(load_policies(POLICY_DIR))
        _index = index
    return _index


@mcp.tool()
def retrieve_internal_policies(query: str, top_k: int = 3) -> str:
    """Search the bank's internal policies. Returns the most relevant policy sections as JSON,
    each with source file, section heading, text and a similarity score. A similarity score
    says where to look, not whether a requirement is met."""
    return json.dumps(logic.retrieve_policies(get_index(), query, top_k))


@mcp.tool()
def create_remediation_task(
    task_id: str,
    obligation_id: str,
    title: str,
    description: str,
    priority: str,
    suggested_owner: str,
    approval_status: str,
    reviewer: str,
    due_date: str | None = None,
) -> str:
    """Create a remediation task. Refuses unless approval_status is 'approved' and a reviewer
    is named. priority is high, medium or low. due_date is YYYY-MM-DD or omitted."""
    return json.dumps(
        logic.create_task(
            output_dir=OUTPUT_DIR,
            task_id=task_id,
            obligation_id=obligation_id,
            title=title,
            description=description,
            priority=priority,
            suggested_owner=suggested_owner,
            approval_status=approval_status,
            reviewer=reviewer,
            due_date=due_date,
        )
    )


@mcp.tool()
def retrieve_audit_history(limit: int = 20, event: str | None = None) -> str:
    """Return the most recent audit log entries as JSON, optionally filtered by event name."""
    return json.dumps(logic.read_audit(OUTPUT_DIR / "audit.jsonl", limit, event))


if __name__ == "__main__":
    if os.environ.get("REGULAAI_WARMUP", "1") == "1":
        get_index()  # build before serving; set REGULAAI_WARMUP=0 to skip (used by fast tests)
    mcp.run(transport="stdio")