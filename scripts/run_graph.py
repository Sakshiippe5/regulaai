from regulaai.graph.workflow import build_graph, run_workflow
from regulaai.ingestion.pdf_reader import read_pdf
from regulaai.rag.chunking import load_policies
from regulaai.rag.embeddings import FastEmbedder
from regulaai.rag.index import PolicyIndex

index = PolicyIndex(FastEmbedder())
index.build(load_policies("data/policies"))
graph = build_graph(index)

print(graph.get_graph().draw_mermaid())

state = run_workflow(graph, read_pdf("data/circulars/sample_cyber_circular.pdf"))
for f in state.findings:
    flag = " [NEEDS REVIEW]" if f.needs_human_review else ""
    print(f"{f.obligation_id} | {f.status.value.upper()} | {f.confidence.value}{flag}")