import sys
from pathlib import Path

from regulaai.graph.workflow import build_graph, run_workflow
from regulaai.ingestion.pdf_reader import read_pdf
from regulaai.models.institution import InstitutionProfile
from regulaai.rag.chunking import load_policies
from regulaai.rag.embeddings import FastEmbedder
from regulaai.rag.index import PolicyIndex
from regulaai.agents.report import render_markdown

profile_path = sys.argv[1] if len(sys.argv) > 1 else "data/institutions/sample_ucb.json"
profile = InstitutionProfile.model_validate_json(Path(profile_path).read_text(encoding="utf-8"))

index = PolicyIndex(FastEmbedder())
index.build(load_policies("data/policies"))
graph = build_graph(index)

state = run_workflow(graph, read_pdf("data/circulars/sample_cyber_circular.pdf"), profile)

print(f"Institution: {profile.name} ({profile.institution_type})")
print(f"Circular scope: {state.circular.applicability_statement}\n")

print("APPLICABILITY")
for a in state.applicability:
    flag = " [NEEDS REVIEW]" if a.needs_human_review else ""
    print(f"  {a.obligation_id} | applies={a.applies} | {a.confidence.value}{flag}")
    print(f"      {a.reason}")

print("\nGAP FINDINGS")
if not state.findings:
    print("  (none: no obligations apply to this institution)")
for f in state.findings:
    flag = " [NEEDS REVIEW]" if f.needs_human_review else ""
    print(f"  {f.obligation_id} | {f.status.value.upper()} | {f.confidence.value}{flag}")

out_dir = Path("outputs")
out_dir.mkdir(exist_ok=True)
report_path = out_dir / "report.md"
report_path.write_text(render_markdown(state.report), encoding="utf-8")
print(f"\nReport written to {report_path}")