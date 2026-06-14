"""Phase 0: EntityTag / MeshingConfig as Pydantic models with a clean,
typed magnetization-direction field (no more direction-on-coercivity hack)."""

import pytest
from pydantic import ValidationError

from common.vector import Vec3
from meshing.config import EntityTag, MeshingConfig
from physical.units import U


def test_entitytag_holds_typed_magnetization_direction():
    t = EntityTag(tag="Mag_N", magnetization_direction=Vec3(0, 1, 0))
    assert isinstance(t.magnetization_direction, Vec3)
    assert (t.magnetization_direction.x, t.magnetization_direction.y, t.magnetization_direction.z) == (0, 1, 0)
    # The old hack field is gone.
    assert not hasattr(t, "magnetic_coercivity")


def test_magnetization_direction_accepts_list_and_dict():
    assert EntityTag(magnetization_direction=[1, 0, 0]).magnetization_direction.x == 1
    assert EntityTag(magnetization_direction={"x": 0, "y": 0, "z": 1}).magnetization_direction.z == 1


def test_boundary_overrides_are_unit_validated():
    t = EntityTag(tag="hot", fixed_temperature="350 K")
    assert t.fixed_temperature.check("[temperature]")
    with pytest.raises(ValidationError):
        EntityTag(fixed_temperature="5 kg")


def test_entitytag_round_trip():
    t = EntityTag(tag="Mag_E", magnetization_direction=Vec3(1, 0, 0), fixed_temperature="300 K")
    restored = EntityTag.model_validate(t.model_dump())
    assert restored.magnetization_direction.x == 1
    assert restored.fixed_temperature.to(U.K).magnitude == pytest.approx(300)


def test_entitytag_schema_exports():
    schema = EntityTag.model_json_schema()
    mag = schema["properties"]["magnetization_direction"]["anyOf"][0]
    assert mag["type"] == "object" and set(mag["required"]) == {"x", "y", "z"}
    temp = schema["properties"]["fixed_temperature"]["anyOf"][0]
    assert temp["x-unit-dimensionality"] == "[temperature]"


def test_meshing_config_defaults():
    c = MeshingConfig()
    assert c.materials == [] and c.tags == []
    assert c.STEP == "data/geometry.step"
    assert c.global_mesh_size == 1.0
