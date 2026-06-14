"""EntityTag / MeshingConfig as Pydantic models carrying composable conditions
(doc 02). The per-region data a tag carries is a `list[Condition]`; there are no
flat scalar override fields."""

import pytest
from pydantic import ValidationError

from common.vector import Vec3
from meshing.config import EntityTag, MeshingConfig
from physical.conditions import FixedTemperature, Magnetization
from physical.units import U


def test_entitytag_holds_conditions():
    t = EntityTag(tag="Mag_N", conditions=[Magnetization(direction=Vec3(0, 1, 0))])
    assert len(t.conditions) == 1
    mag = t.conditions[0]
    assert isinstance(mag, Magnetization)
    assert (mag.direction.x, mag.direction.y, mag.direction.z) == (0, 1, 0)
    # The old scalar shim fields are gone.
    assert not hasattr(t, "magnetic_coercivity")
    assert not hasattr(t, "magnetization_direction")
    assert not hasattr(t, "fixed_temperature")


def test_condition_values_are_unit_validated():
    t = EntityTag(tag="hot", conditions=[FixedTemperature(value="350 K")])
    assert t.conditions[0].value.check("[temperature]")
    with pytest.raises(ValidationError):
        EntityTag(conditions=[FixedTemperature(value="5 kg")])


def test_entitytag_round_trip():
    t = EntityTag(
        tag="Mag_E",
        conditions=[Magnetization(direction=Vec3(1, 0, 0)), FixedTemperature(value="300 K")],
    )
    restored = EntityTag.model_validate(t.model_dump())
    assert [type(c) for c in restored.conditions] == [Magnetization, FixedTemperature]
    assert restored.conditions[0].direction.x == 1
    assert restored.conditions[1].value.to(U.K).magnitude == pytest.approx(300)


def test_entitytag_schema_exports():
    schema = EntityTag.model_json_schema()
    # The polymorphic conditions list exports as a discriminated union.
    conditions = schema["properties"]["conditions"]
    assert conditions["type"] == "array"
    assert conditions["items"]["discriminator"]["propertyName"] == "kind"
    # The Magnetization direction is a typed 3-vector in the $defs.
    mag = schema["$defs"]["Magnetization"]["properties"]["direction"]
    assert mag["type"] == "object" and set(mag["required"]) == {"x", "y", "z"}


def test_meshing_config_defaults():
    c = MeshingConfig()
    assert c.materials == [] and c.tags == []
    assert c.STEP == "data/geometry.step"
    assert c.global_mesh_size == 1.0
