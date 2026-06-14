"""Phase 0: MaterialProperties as Pydantic models + the material registry."""

import pytest
from pydantic import ValidationError

from physical.materials.air import Air
from physical.materials.neodymium import N52
from physical.materials.pcb import FR4
from physical.materials.properties import MaterialProperties, ThermalProperties
from physical.materials.registry import all_materials, available_materials, material
from physical.units import U


def test_materials_construct_and_emit_si_floats():
    elmer = N52().to_elmer()
    # Elmer wants bare SI floats, not pint quantities.
    assert elmer["Density"] == pytest.approx(7500.0)
    assert elmer["Heat Conductivity"] == pytest.approx(8.7)
    assert elmer["Relative Permeability"] == pytest.approx(1.05)
    assert all(isinstance(v, (int, float)) for v in elmer.values())


def test_magnet_detection_and_magnitude():
    n52 = N52()
    assert n52.is_magnet
    # |M| = Br / mu0  ~ 1.48 / 1.2566e-6
    assert n52.magnetic.magnetization_magnitude == pytest.approx(1.48 / 1.25663706212e-6, rel=1e-6)
    assert not Air().is_magnet


def test_wrong_dimensionality_raises_on_construction():
    with pytest.raises(ValidationError):
        ThermalProperties(conductivity=5 * U.kg)


def test_wrong_dimensionality_raises_on_assignment():
    n = N52()
    with pytest.raises(ValidationError):
        n.thermal.conductivity = 5 * U.kg


def test_round_trip_preserves_to_elmer():
    for factory in (N52, Air, FR4):
        m = factory()
        restored = MaterialProperties.model_validate(m.model_dump())
        assert restored.to_elmer() == m.to_elmer()


def test_schema_has_unit_annotated_quantity_field():
    schema = MaterialProperties.model_json_schema()
    cond = schema["$defs"]["ThermalProperties"]["properties"]["conductivity"]
    inner = cond["anyOf"][0]
    assert inner["x-unit-dimensionality"] == "[power]/[length]/[temperature]"


def test_registry_replaces_hardcoded_known_materials():
    assert set(available_materials()) == {"N52", "Air", "FR4"}
    assert material("N52").is_magnet
    assert len(all_materials()) == 3


def test_registry_unknown_tag_raises():
    with pytest.raises(KeyError):
        material("Copper")


def test_registry_returns_fresh_instances():
    a, b = material("N52"), material("N52")
    assert a is not b
