"""
Phase 0: the pint <-> Pydantic keystone (`quantity_type`) and its aliases.

Pure-logic tests: no gmsh / build123d imports, so they run anywhere.
"""

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from physical.units import U, Conductivity, Density, Temperature, quantity_type


class _Sample(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    density: Density
    conductivity: Conductivity
    temperature: Temperature


def _sample(**over):
    base = dict(density="7500 kg/m**3", conductivity="8.7 W/(m*K)", temperature="300 K")
    base.update(over)
    return _Sample(**base)


def test_valid_quantity_is_stored_as_pint():
    s = _sample()
    assert isinstance(s.density, U.Quantity)
    assert s.density.check("[mass]/[length]**3")
    assert pytest.approx(s.conductivity.to(U.W / (U.m * U.K)).magnitude) == 8.7


def test_wrong_dimensionality_raises_at_construction():
    # A mass given where a density belongs must fail at construction, not later.
    with pytest.raises(ValidationError):
        _sample(density="5 kg")
    with pytest.raises(ValidationError):
        _sample(conductivity="5 kg")


def test_json_schema_includes_unit_annotation():
    schema = _Sample.model_json_schema()
    dens = schema["properties"]["density"]
    assert dens["x-unit-dimensionality"] == "[mass]/[length]**3"
    assert dens["type"] == "string"


def test_round_trip_preserves_quantity():
    s = _sample()
    restored = _Sample.model_validate(s.model_dump())
    assert restored.density.to_base_units() == s.density.to_base_units()
    assert restored.conductivity.to_base_units() == s.conductivity.to_base_units()


def test_serialized_form_is_ascii_parseable():
    # The serializer must emit something pint can read back (no unicode superscripts, no Rich markup) so model_dump JSON survives a round trip.
    dumped = _sample().model_dump()
    assert U.Quantity(dumped["density"]).check("[mass]/[length]**3")
    assert "³" not in dumped["density"]
    assert "[" not in dumped["density"]


def test_quantity_type_accepts_already_constructed_quantity():
    s = _sample(density=7500 * U.kg / U.m**3)
    assert s.density.check("[mass]/[length]**3")
