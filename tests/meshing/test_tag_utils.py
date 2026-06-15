"""
conditions_for — the dedup utility that resolves which conditions of a given (physics, target) apply to a region's tags.
"""

from common.vector import Vec3
from elmer.physics import Physics
from meshing.config import EntityTag, conditions_for
from physical.conditions import ConditionTarget, FixedTemperature, Magnetization


def test_conditions_for_filters_by_physics_and_target() -> None:
    tags = [
        EntityTag(tag="Mag_N", conditions=[Magnetization(direction=Vec3(0, 1, 0))]),
        EntityTag(tag="Hot", conditions=[FixedTemperature(value="350 K")]),
    ]
    body_mag = conditions_for(tags, Physics.MAGNETOSTATICS, ConditionTarget.BODY)
    assert len(body_mag) == 1 and isinstance(body_mag[0], Magnetization)

    bnd_thermal = conditions_for(tags, Physics.THERMAL, ConditionTarget.BOUNDARY)
    assert len(bnd_thermal) == 1 and isinstance(bnd_thermal[0], FixedTemperature)

    # No magnetostatics boundary conditions exist in this set.
    assert conditions_for(tags, Physics.MAGNETOSTATICS, ConditionTarget.BOUNDARY) == []


def test_conditions_for_aggregates_across_tags() -> None:
    # Multiple tags on a region each contributing a matching condition.
    tags = [
        EntityTag(tag="a", conditions=[Magnetization(direction=Vec3(1, 0, 0))]),
        EntityTag(tag="b", conditions=[Magnetization(direction=Vec3(0, 1, 0))]),
    ]
    found = conditions_for(tags, Physics.MAGNETOSTATICS, ConditionTarget.BODY)
    assert len(found) == 2


def test_conditions_for_empty() -> None:
    assert conditions_for([], Physics.MAGNETOSTATICS, ConditionTarget.BODY) == []
    assert conditions_for([EntityTag(tag="x")], Physics.THERMAL, ConditionTarget.BOUNDARY) == []
