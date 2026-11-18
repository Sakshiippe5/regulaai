import argparse
import uuid
from pathlib import Path

from regulaai.agents.report import render_markdown
from regulaai.graph.workflow import (
    build_graph, get_state, pending_review, start_run, submit_review,
)
from regulaai.ingestion.pdf_reader import read_pdf
from regulaai.models.institution import InstitutionProfile

parser = argparse.ArgumentParser()
parser.add_argument("profile", nargs="?", default="data/institutions/sample_ucb.json")
parser.add_argument("--mcp", action="store_true",
                    help="use the MCP tool server for policy search and task creation")
args = parser.parse_args()

profile = InstitutionProfile.model_validate_json(Path(args.profile).read_text(encoding="utf-8"))

bridge = None
if args.mcp:
    from regulaai.mcp_tools.adapters import McpPolicySearch, mcp_task_creator
    from regulaai.mcp_tools.bridge import McpBridge

    bridge = McpBridge({
        "REGULAAI_OUTPUT_DIR": str(Path("outputs").resolve()),
        "REGULAAI_POLICY_DIR": str(Path("data/policies").resolve()),
    }).start()
    graph = build_graph(McpPolicySearch(bridge), task_creator=mcp_task_creator(bridge))
    print("Using the MCP tool server.")
else:
    from regulaai.rag.chunking import load_policies
    from regulaai.rag.embeddings import FastEmbedder
    from regulaai.rag.index import PolicyIndex

    index = PolicyIndex(FastEmbedder())
    index.build(load_policies("data/policies"))
    graph = build_graph(index)

try:
    thread_id = str(uuid.uuid4())
    start_run(graph, read_pdf("data/circulars/sample_cyber_circular.pdf"), profile, thread_id)

    state = get_state(graph, thread_id)
    Path("outputs").mkdir(exist_ok=True)
    Path("outputs/report.md").write_text(render_markdown(state.report), encoding="utf-8")

    review = pending_review(graph, thread_id)
    if review is None:
        print("Nothing to review: no remediation tasks were proposed.")
        raise SystemExit(0)

    print(f"\nThe run is PAUSED. {len(review['tasks'])} proposed tasks await your review.")
    print("Full report: outputs/report.md\n")
    reviewer = input("Reviewer role or name: ").strip() or "unknown"

    decisions = {}
    for t in review["tasks"]:
        print(f"\n{t['id']} | {t['obligation_id']} | priority={t['priority']} | owner={t['suggested_owner']} | due={t['due_date'] or '-'}")
        print(f"   {t['title']}: {t['description']}")
        choice = input("   [a]pprove / [r]eject / [s]kip: ").strip().lower()
        if choice == "a":
            decisions[t["id"]] = "approve"
        elif choice == "r":
            decisions[t["id"]] = "reject"

    final = submit_review(graph, thread_id, reviewer, decisions)
    print(f"\nDone. {len(final.created_tasks)} task(s) created in outputs/tasks.json")
    print("Audit entries added to outputs/audit.jsonl")
finally:
    if bridge:
        bridge.close()