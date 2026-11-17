from regulaai.rag.chunking import load_policies
from regulaai.rag.embeddings import FastEmbedder
from regulaai.rag.index import PolicyIndex

OBLIGATIONS = {
    "OBL-001 report incidents within 6 hours": "Banks shall report any cyber security incident to the regulator within 6 hours of detection.",
    "OBL-002 designate a CISO by June 30": "Banks shall designate a Chief Information Security Officer (CISO) by June 30, 2026.",
    "OBL-003 Board approves cyber policy annually": "The Board shall approve a Cyber Security Policy and review it at least annually.",
    "OBL-004 vulnerability assessment every 6 months": "Banks shall conduct a vulnerability assessment at least once every six months.",
    "OBL-005 disclose incidents on website in 24h": "Banks shall disclose cyber incidents affecting customers on their website within 24 hours of confirmation.",
}

index = PolicyIndex(FastEmbedder())
index.build(load_policies("data/policies"))
index.save("data/index")

for label, query in OBLIGATIONS.items():
    print(f"\n{label}")
    for hit in index.search(query, k=2):
        c = hit.chunk
        print(f"   {hit.score:.2f}  {c.source} | {c.section}")