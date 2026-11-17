from datetime import date

import pytest
from pydantic import ValidationError

from regulaai.models.regulatory import Circular, Obligation, ObligationType


def test_valid_obligation():
    ob = Obligation(
        id="OBL-001",
        section="3.1",
        text="Banks must report cyber incidents within 6 hours.",
        obligation_type=ObligationType.REPORTING,
        deadline=date(2027, 3, 31),
    )
    assert ob.deadline.year == 2027


def test_invalid_type_is_rejected():
    with pytest.raises(ValidationError):
        Obligation(id="OBL-002", section="1", text="x", obligation_type="banana")


def test_circular_holds_obligations():
    c = Circular(title="Cyber Resilience", regulator="RBI")
    assert c.obligations == []

def test_circular_without_named_regulator_is_valid():
    c = Circular(title="Untitled circular")
    assert c.regulator is None