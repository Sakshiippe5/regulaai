import re
from typing import Any, Protocol

from regulaai.ingestion.pdf_reader import ParsedDocument
from regulaai.llm.client import LLMClient
from regulaai.models.regulatory import Circular

SYSTEM_PROMPT = """You extract regulatory obligations from circulars issued to banks.

Rules:
- An obligation is a concrete requirement ("shall", "must", "required to").
  Do NOT include background text, definitions, or statements about who the circular applies to.
- text: copy the requirement VERBATIM from the document. Do not paraphrase.
- section: the clause number, e.g. "2.1".
- source_page: the integer from the [Page N] marker above that clause.
- deadline: an ISO date (YYYY-MM-DD) ONLY if the clause states an explicit calendar date.
  Relative time limits such as "within 6 hours" are NOT dates: use null and keep them in text.
- obligation_type: one of reporting, policy, process, disclosure, other.
- title, regulator, issue_date: take them from the document header.
- Use id "TBD" for every obligation. IDs are assigned later.
- Never invent information. If something is not stated, use null.
- applicability_statement: copy VERBATIM the clause stating which institutions the circular applies to (e.g. section 1.1). null if the document has none.
"""


class StructuredLLM(Protocol):
    def complete_structured(self, system: str, user: str, schema: Any) -> Any: ...


def extract_circular(doc: ParsedDocument, llm: StructuredLLM | None = None) -> Circular:
    llm = llm or LLMClient()
    circular = llm.complete_structured(SYSTEM_PROMPT, doc.full_text, Circular)
    for number, obligation in enumerate(circular.obligations, start=1):
        obligation.id = f"OBL-{number:03d}"
    return circular


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def find_ungrounded(circular: Circular, doc: ParsedDocument) -> list[str]:
    """IDs of obligations whose text does not appear in the source document."""
    source = _normalize(doc.full_text)
    return [o.id for o in circular.obligations if _normalize(o.text) not in source]