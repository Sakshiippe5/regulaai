import asyncio
import json

from regulaai.mcp_tools.client import open_tools

TASK = dict(
    task_id="TASK-001", obligation_id="OBL-004", title="Shorten cycle",
    description="Amend policy.", priority="medium", suggested_owner="CISO",
)


def test_server_exposes_tools_and_enforces_approval(tmp_path):
    async def scenario():
        async with open_tools({"REGULAAI_OUTPUT_DIR": str(tmp_path), "REGULAAI_WARMUP": "0"}) as tools:
            names = await tools.list_names()
            try:
                await tools.call("create_remediation_task", approval_status="proposed", reviewer="r1", **TASK)
                refused = False
            except RuntimeError:
                refused = True
            created = await tools.call(
                "create_remediation_task", approval_status="approved", reviewer="r1", **TASK
            )
            history = await tools.call("retrieve_audit_history", limit=5)
        return names, refused, created, history

    names, refused, created, history = asyncio.run(scenario())

    assert {"retrieve_internal_policies", "create_remediation_task", "retrieve_audit_history"} <= set(names)
    assert refused
    assert created["created"] == "TASK-001"
    assert history[-1]["event"] == "task_created_via_mcp"
    assert json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))[0]["status"] == "approved"