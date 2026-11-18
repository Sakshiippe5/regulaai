from regulaai.models.report import RemediationTask
from regulaai.rag.chunking import PolicyChunk
from regulaai.rag.index import SearchHit


class McpPolicySearch:
    """Same .search() as PolicyIndex, but the work happens in the MCP server."""

    def __init__(self, bridge) -> None:
        self._bridge = bridge

    def search(self, query: str, k: int = 3) -> list[SearchHit]:
        rows = self._bridge.call("retrieve_internal_policies", query=query, top_k=k)
        return [
            SearchHit(
                chunk=PolicyChunk(
                    id=r["chunk_id"], source=r["source"], section=r["section"], text=r["text"]
                ),
                score=r["score"],
            )
            for r in rows
        ]


def mcp_task_creator(bridge):
    """Returns a function that creates approved tasks through the MCP server."""

    def create(tasks: list[RemediationTask], reviewer: str) -> None:
        for t in tasks:
            args = dict(
                task_id=t.id,
                obligation_id=t.obligation_id,
                title=t.title,
                description=t.description,
                priority=t.priority.value,
                suggested_owner=t.suggested_owner,
                approval_status=t.status.value,
                reviewer=reviewer,
            )
            if t.due_date:
                args["due_date"] = t.due_date.isoformat()
            bridge.call("create_remediation_task", **args)

    return create