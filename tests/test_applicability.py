from regulaai.agents.applicability import judge_applicability
from regulaai.models.analysis import Confidence
from regulaai.models.applicability import ApplicabilityJudgement
from regulaai.models.institution import InstitutionProfile
from regulaai.models.regulatory import Circular, Obligation

PROFILE = InstitutionProfile(name="X", institution_type="NBFC")
OB = Obligation(id="OBL-001", section="2.1", text="Banks shall report incidents.")


class FakeLLM:
    def __init__(self, applies: bool, conf: Confidence) -> None:
        self._j = ApplicabilityJudgement(applies=applies, reason="r", confidence=conf)

    def complete_structured(self, system, user, schema):
        return self._j


def circular(statement="Applies to all UCBs."):
    return Circular(title="T", applicability_statement=statement, obligations=[OB])


def test_applicable_obligation_proceeds():
    r = judge_applicability(circular(), OB, PROFILE, FakeLLM(True, Confidence.HIGH))
    assert r.proceed and not r.needs_human_review


def test_clear_exclusion_is_dropped():
    r = judge_applicability(circular(), OB, PROFILE, FakeLLM(False, Confidence.HIGH))
    assert not r.proceed


def test_unsure_exclusion_is_kept_for_review():
    r = judge_applicability(circular(), OB, PROFILE, FakeLLM(False, Confidence.LOW))
    assert r.proceed and r.needs_human_review


def test_missing_scope_statement_forces_review():
    r = judge_applicability(circular(None), OB, PROFILE, FakeLLM(False, Confidence.HIGH))
    assert r.proceed and r.needs_human_review