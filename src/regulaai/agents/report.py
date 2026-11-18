from collections import Counter

from regulaai.agents.extraction import StructuredLLM
from regulaai.llm.client import LLMClient
from regulaai.models.analysis import GapFinding, GapStatus
from regulaai.models.applicability import ObligationApplicability
from regulaai.models.institution import InstitutionProfile
from regulaai.models.regulatory import Circular, Obligation
from regulaai.models.report import (
    ComplianceReport, LLMTaskProposal, Priority, RemediationTask,
)

SYSTEM_PROMPT = """You write one remediation task for a compliance gap at a bank.

You are given the regulatory obligation, the gap status, the analyst's rationale, and the
policy excerpts that were found.
- title: short and imperative (for example "Shorten vulnerability assessment cycle to six months").
- description: 1 to 3 sentences on exactly what must change. Name the policy and section to amend
  when evidence exists, and state the specific mismatch. If no policy was found, say a new
  control or policy section is needed.
- suggested_owner: a ROLE (for example CISO, Board, Compliance Officer), never a person's name.
- Do not invent policies, systems, or facts that are not in the input.
"""


def _priority(finding: GapFinding, obligation: Obligation) -> Priority:
    if finding.status == GapStatus.MISSING or obligation.deadline is not None:
        return Priority.HIGH
    return Priority.MEDIUM


def propose_tasks(
    obligations: list[Obligation],
    findings: list[GapFinding],
    llm: StructuredLLM | None = None,
) -> list[RemediationTask]:
    llm = llm or LLMClient()
    by_id = {o.id: o for o in obligations}
    tasks: list[RemediationTask] = []
    for f in findings:
        if f.status == GapStatus.COVERED:
            continue
        ob = by_id[f.obligation_id]
        evidence = "\n".join(f"- {e.source} | {e.section}: {e.text}" for e in f.evidence)
        user = (
            f"OBLIGATION {ob.id} (circular section {ob.section}): {ob.text}\n"
            f"GAP STATUS: {f.status.value}\n"
            f"RATIONALE: {f.rationale}\n"
            f"POLICY EVIDENCE:\n{evidence or '(no relevant policy found)'}"
        )
        p = llm.complete_structured(SYSTEM_PROMPT, user, LLMTaskProposal)
        tasks.append(
            RemediationTask(
                id=f"TASK-{len(tasks) + 1:03d}",
                obligation_id=ob.id,
                title=p.title,
                description=p.description,
                priority=_priority(f, ob),
                suggested_owner=p.suggested_owner,
                due_date=ob.deadline,
            )
        )
    return tasks


def build_report(
    profile: InstitutionProfile,
    circular: Circular,
    applicability: list[ObligationApplicability],
    findings: list[GapFinding],
    llm: StructuredLLM | None = None,
) -> ComplianceReport:
    return ComplianceReport(
        institution_name=profile.name,
        circular_title=circular.title,
        obligations=circular.obligations,
        not_applicable=[a for a in applicability if not a.proceed],
        findings=findings,
        tasks=propose_tasks(circular.obligations, findings, llm),
    )


def render_markdown(report: ComplianceReport) -> str:
    ob = {o.id: o for o in report.obligations}
    counts = Counter(f.status for f in report.findings)
    review = sum(f.needs_human_review for f in report.findings)

    lines = [
        "# Compliance Gap Report",
        "",
        f"**Institution:** {report.institution_name}",
        f"**Circular:** {report.circular_title}",
        "",
        "## Summary",
        "",
        f"- Obligations extracted: {len(report.obligations)}",
        f"- Not applicable to this institution: {len(report.not_applicable)}",
        f"- Analyzed: {len(report.findings)} "
        f"(covered {counts[GapStatus.COVERED]}, partial {counts[GapStatus.PARTIAL]}, "
        f"missing {counts[GapStatus.MISSING]})",
        f"- Findings needing human review: {review}",
        f"- Proposed remediation tasks: {len(report.tasks)}",
        "",
        "## Findings",
        "",
    ]
    if not report.findings:
        lines += ["_No obligations in scope._", ""]
    for f in report.findings:
        o = ob[f.obligation_id]
        page = f", page {o.source_page}" if o.source_page else ""
        flag = " (needs human review)" if f.needs_human_review else ""
        lines += [
            f"### {f.obligation_id}: {f.status.value.upper()}{flag}",
            f"**Requirement** (circular section {o.section}{page}): {o.text}",
        ]
        if o.deadline:
            lines.append(f"**Deadline:** {o.deadline.isoformat()}")
        lines += [f"**Assessment** (confidence: {f.confidence.value}): {f.rationale}"]
        if f.evidence:
            lines.append("**Evidence:**")
            lines += [f"- {e.source}, {e.section}" for e in f.evidence]
        else:
            lines.append("**Evidence:** none found in internal policies")
        lines.append("")

    lines += ["## Proposed remediation tasks (pending approval)", ""]
    if not report.tasks:
        lines += ["_No tasks proposed._", ""]
    else:
        lines += [
            "| ID | Obligation | Priority | Owner | Due | Task |",
            "|---|---|---|---|---|---|",
        ]
        for t in report.tasks:
            due = t.due_date.isoformat() if t.due_date else "-"
            lines.append(
                f"| {t.id} | {t.obligation_id} | {t.priority.value} | "
                f"{t.suggested_owner} | {due} | **{t.title}**: {t.description} |"
            )
        lines.append("")

    if report.not_applicable:
        lines += ["## Excluded as not applicable", ""]
        lines += [f"- {a.obligation_id}: {a.reason}" for a in report.not_applicable]
        lines.append("")
    return "\n".join(lines)