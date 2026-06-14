"""Phase 2: composable conditions (doc 02, body half).

Pure-logic tests (no gmsh / build123d), so they run in the Linux sandbox too:
each condition's ``to_elmer()`` round-trip, the discriminated-union
serialization round-trip, and the normalization behaviour of ``Magnetization``.
"""

import math

import pytest
from pydantic import TypeAdapter

from common.vector import Vec3
from elmer.physics import Physics
from physical.conditions import (
    Condition,
    ConditionTarget,
    ConditionUnion,
    Convection,
    FixedTemperature,
    HeatFlux,
    Magnetization,
)
from physical.units import U

MU0 = 1.25663706212e-6


# --- physics / target metadata --------------------------------------------


def test_conditions_carry_physics_and_target_enums():
    assert Magnetization(direction=Vec3(0, 1, 0)).physics is Physics.MAGNETOSTATICS
    assert Magnetization(direction=Vec3(0, 1, 0)).target is ConditionTarget.BODY
    assert FixedTemperature(value=350 * U.K).physics is Physics.THERMAL
    assert FixedTemperature(value=350 * U.K).target is ConditionTarget.BOUNDARY


# --- Magnetization.to_elmer ------------------------------------------------


def test_magnetization_scales_unit_direction():
    cond = Magnetization(direction=Vec3(0, 1, 0))
    data = cond.to_elmer(magnitude=1000.0)
    assert float(data["Magnetization 1"]) == pytest.approx(0.0)
    assert float(data["Magnetization 2"]) == pytest.approx(1000.0)
    assert float(data["Magnetization 3"]) == pytest.approx(0.0)


def test_magnetization_normalizes_non_unit_direction():
    # A non-unit (and non-axis-aligned) direction must be normalized before
    # scaling, so |M| ends up equal to the requested magnitude regardless of how
    # the direction vector was authored.
    cond = Magnetization(direction=Vec3(3, 4, 0))  # |v| = 5
    data = cond.to_elmer(magnitude=10.0)
    mx, my, mz = (float(data[f"Magnetization {i}"]) for i in (1, 2, 3))
    assert mx == pytest.approx(6.0)  # 10 * 3/5
    assert my == pytest.approx(8.0)  # 10 * 4/5
    assert mz == pytest.approx(0.0)
    assert math.sqrt(mx**2 + my**2 + mz**2) == pytest.approx(10.0)


# --- thermal carriers' to_elmer (round-trip the SI strip) ------------------


def test_fixed_temperature_to_elmer():
    assert FixedTemperature(value=350 * U.K).to_elmer() == {"Temperature": pytest.approx(350.0)}


def test_fixed_temperature_strips_to_kelvin():
    # Authored in a non-SI unit; to_elmer must hand Elmer bare kelvin.
    cond = FixedTemperature(value=25 * U.degC)
    assert cond.to_elmer()["Temperature"] == pytest.approx(298.15)


def test_heat_flux_to_elmer():
    cond = HeatFlux(value=500 * U.W / U.m**2)
    assert cond.to_elmer() == {"Heat Flux": pytest.approx(500.0)}


def test_convection_to_elmer():
    cond = Convection(coefficient=12 * U.W / (U.m**2 * U.K), ext_temperature=300 * U.K)
    data = cond.to_elmer()
    assert data["Heat Transfer Coefficient"] == pytest.approx(12.0)
    assert data["External Temperature"] == pytest.approx(300.0)


# --- discriminated-union round-trip ----------------------------------------


def test_condition_list_round_trips_via_discriminator():
    adapter: TypeAdapter = TypeAdapter(list[ConditionUnion])
    conditions: list[Condition] = [
        Magnetization(direction=Vec3(0, 1, 0)),
        FixedTemperature(value=350 * U.K),
        HeatFlux(value=500 * U.W / U.m**2),
        Convection(coefficient=12 * U.W / (U.m**2 * U.K), ext_temperature=300 * U.K),
    ]
    dumped = adapter.dump_python(conditions)
    # The discriminator must be present so model_validate can reconstruct types.
    assert [c["kind"] for c in dumped] == ["magnetization", "fixed_temperature", "heat_flux", "convection"]

    restored: list[Condition] = adapter.validate_python(dumped)
    assert [type(c) for c in restored] == [Magnetization, FixedTemperature, HeatFlux, Convection]
    # Values survive the round trip.
    assert restored[0].direction.x == 0 and restored[0].direction.y == 1
    assert restored[1].to_elmer()["Temperature"] == pytest.approx(350.0)
