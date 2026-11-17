from regulaai.agents.extraction import extract_circular
from regulaai.agents.gap_analysis import analyze_gap
from regulaai.ingestion.pdf_reader import read_pdf
from regulaai.rag.chunking import load_policies
from regulaai.rag.embeddings import FastEmbedder
from regulaai.rag.index import PolicyIndex

doc = read_pdf("data/circulars/sample_cyber_circular.pdf")
circular = extract_circular(doc)

index = PolicyIndex(FastEmbedder())
index.build(load_policies("data/policies"))

for ob in circular.obligations:
    finding = analyze_gap(ob, index.search(ob.text, k=3))
    flag = "  [NEEDS REVIEW]" if finding.needs_human_review else ""
    print(f"\n{ob.id} | {finding.status.value.upper()} | confidence={finding.confidence.value}{flag}")
    print(f"   Requirement: {ob.text}")
    print(f"   Why: {finding.rationale}")
    for e in finding.evidence:
        print(f"   Evidence: {e.source} | {e.section}")