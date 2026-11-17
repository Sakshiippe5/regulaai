from regulaai.agents.extraction import extract_circular, find_ungrounded
from regulaai.ingestion.pdf_reader import Page, ParsedDocument
from regulaai.models.regulatory import Circular, Obligation


class FakeLLM:
    """Stands in for the real LLM so tests need no network or API key."""

    def __init__(self, circular: Circular) -> None:
        self._circular = circular

    def complete_structured(self, system, user, schema):
        return self._circular


def make_doc() -> ParsedDocument:
    page = Page(number=1, text="2.1 Banks shall report incidents within 6 hours.")
    return ParsedDocument(source="t.pdf", pages=[page])


def make_circular(text: str) -> Circular:
    return Circular(
        title="T",
        regulator="RBI",
        obligations=[Obligation(id="TBD", section="2.1", text=text)],
    )


def test_ids_are_assigned_by_code():
    llm = FakeLLM(make_circular("Banks shall report incidents within 6 hours."))
    result = extract_circular(make_doc(), llm)
    assert result.obligations[0].id == "OBL-001"


def test_grounded_obligation_passes():
    circular = make_circular("Banks shall report incidents within 6 hours.")
    circular.obligations[0].id = "OBL-001"
    assert find_ungrounded(circular, make_doc()) == []


def test_invented_obligation_is_flagged():
    circular = make_circular("Banks shall hire 50 auditors.")
    circular.obligations[0].id = "OBL-001"
    assert find_ungrounded(circular, make_doc()) == ["OBL-001"]