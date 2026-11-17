from regulaai.agents.extraction import extract_circular, find_ungrounded
from regulaai.ingestion.pdf_reader import read_pdf

doc = read_pdf("data/circulars/sample_cyber_circular.pdf")
circular = extract_circular(doc)

print(f"{circular.title} | {circular.regulator} | issued {circular.issue_date}\n")
for o in circular.obligations:
    print(f"{o.id} | §{o.section} | p.{o.source_page} | {o.obligation_type.value} | deadline={o.deadline}")
    print(f"    {o.text}\n")

bad = find_ungrounded(circular, doc)
print("All obligations verified against source." if not bad else f"NOT FOUND IN SOURCE: {bad}")