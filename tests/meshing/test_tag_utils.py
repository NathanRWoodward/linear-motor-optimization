"""first_tag_value / EntityTag.overrides — the dedup utility for tag lookups."""

from common.vector import Vec3
from meshing.config import EntityTag, first_tag_value


def test_first_tag_value_finds_first_non_none() -> None:
    tags = [EntityTag(tag="a"), EntityTag(tag="b", fixed_temperature="300 K")]
    assert first_tag_value(tags, "fixed_temperature") is not None
    assert first_tag_value(tags, "fixed_heat_flux") is None
    assert first_tag_value([], "fixed_temperature") is None


def test_overrides_yields_only_set_fields() -> None:
    t = EntityTag(tag="Mag_N", magnetization_direction=Vec3(0, 1, 0), fixed_temperature="300 K")
    fields = {field for field, _label, _value in t.overrides()}
    assert fields == {"magnetization_direction", "fixed_temperature"}
    # an empty tag yields nothing
    assert list(EntityTag(tag="x").overrides()) == []
