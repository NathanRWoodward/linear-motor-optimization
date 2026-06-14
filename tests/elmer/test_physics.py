"""Phase 0: the Physics enum replaces the magic `physics="magnetostatics"` string."""

import pytest

from elmer.physics import Physics


def test_enum_values_match_preset_keys():
    from elmer.sim import PHYSICS_PRESETS

    assert {p.value for p in Physics} == set(PHYSICS_PRESETS)


def test_enum_member_is_a_str():
    # StrEnum: comparable to / usable as the historical string.
    assert Physics.MAGNETOSTATICS == "magnetostatics"


def test_out_of_vocabulary_value_rejected():
    with pytest.raises(ValueError):
        Physics("nonsense")


def test_linear_elasticity_member_present() -> None:
    assert Physics.LINEAR_ELASTICITY == "linear_elasticity"
    assert "linear_elasticity" in {p.value for p in Physics}
