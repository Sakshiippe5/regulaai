from datetime import date

from regulaai.agents.report import propose_tasks, render_markdown
from regulaai.models.analysis import Confidence, Evidence, GapFinding, GapStatus
from regulaai.models.report import ComplianceReport, LLMTaskProposal, Priority
from regulaai.models.regulatory import Obligation


class FakeLLM:
    def complete_structured(self, system, user, schema):
        return LLMTaskProposal(title="Fix it", description="Amend policy.", suggested_owner="CISO")


def finding(ob_id: str, status: GapStatus, with_evidence: bool = True) -> GapFinding:
    ev = [Evidence(chunk_id="p:1", source="isp.md", section="2. Vulnerability", text="t")]
    return GapFinding(
        obligation_id=ob_id, obligation_text="x", status=status, rationale="why",
        evidence=ev if with_evidence else [], confidence=Confidence.HIGH,
        needs_human_review=False,
    )


def ob(ob_id: str, deadline: date | None = None, page: int | None = 2) -> Obligation:
    return Obligation(id=ob_id, section="3.2", text="Do the thing.", deadline=deadline,
                      source_page=page)


def test_covered_findings_get_no_task():
    tasks = propose_tasks([ob("OBL-001")], [finding("OBL-001", GapStatus.COVERED)], FakeLLM())
    assert tasks == []


def test_missing_is_high_priority_partial_is_medium():
    obs = [ob("OBL-001"), ob("OBL-002")]
    fs = [finding("OBL-001", GapStatus.MISSING, False), finding("OBL-002", GapStatus.PARTIAL)]
    tasks = propose_tasks(obs, fs, FakeLLM())
    assert [t.id for t in tasks] == ["TASK-001", "TASK-002"]
    assert tasks[0].priority == Priority.HIGH
    assert tasks[1].priority == Priority.MEDIUM


def test_explicit_deadline_makes_partial_high_and_sets_due_date():
    tasks = propose_tasks(
        [ob("OBL-001", deadline=date(2026, 9, 30))],
        [finding("OBL-001", GapStatus.PARTIAL)],
        FakeLLM(),
    )
    assert tasks[0].priority == Priority.HIGH
    assert tasks[0].due_date == date(2026, 9, 30)


def test_markdown_cites_circular_page_and_policy_source():
    obs = [ob("OBL-001")]
    fs = [finding("OBL-001", GapStatus.PARTIAL)]
    report = ComplianceReport(
        institution_name="Test Bank", circular_title="Test Circular",
        obligations=obs, not_applicable=[], findings=fs,
        tasks=propose_tasks(obs, fs, FakeLLM()),
    )
    md = render_markdown(report)
    assert "circular section 3.2, page 2" in md
    assert "isp.md, 2. Vulnerability" in md
    assert "TASK-001" in md