import sys
import uuid
from pathlib import Path

from regulaai.agents.report import render_markdown
from regulaai.graph.workflow import (
    build_graph, get_state, pending_review, start_run, submit_review,
)
from regulaai.ingestion.pdf_reader import read_pdf
from regulaai.models.institution import InstitutionProfile
from regulaai.rag.chunking import load_policies
from regulaai.rag.embeddings import FastEmbedder
from regulaai.rag.index import PolicyIndex

profile_path = sys.argv[1] if len(sys.argv) > 1 else "data/institutions/sample_ucb.json"
profile = InstitutionProfile.model_validate_json(Path(profile_path).read_text(encoding="utf-8"))

index = PolicyIndex(FastEmbedder())
index.build(load_policies("data/policies"))
graph = build_graph(index)

thread_id = str(uuid.uuid4())
start_run(graph, read_pdf("data/circulars/sample_cyber_circular.pdf"), profile, thread_id)

state = get_state(graph, thread_id)
Path("outputs").mkdir(exist_ok=True)
Path("outputs/report.md").write_text(render_markdown(state.report), encoding="utf-8")

review = pending_review(graph, thread_id)
if review is None:
    print("Nothing to review: no remediation tasks were proposed.")
    sys.exit(0)

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
print("Audit entry added to outputs/audit.jsonl")