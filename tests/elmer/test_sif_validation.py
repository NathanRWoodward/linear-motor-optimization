"""
Phase 3 (doc 03): SifWriter.validate() catches solver misconfig at construction, so a broken config fails in CI rather than at ElmerSolver runtime.

Pure-logic: a fake PhysicalGroup (the standalone fake-group pattern) and a fake material a real one can't be, so the suite needs no gmsh / build123d.
"""

from typing import Mapping

import pytest

from common.vector import Vec3
from elmer.physics import Physics
from elmer.sim import SifWriter
from meshing.config import EntityTag, MeshingConfig
from physical.conditions import Magnetization
from physical.materials.air import Air
from physical.materials.neodymium import N52
from physical.materials.properties import MaterialProperties
from physical.units import Quantity, U


class FakePhysicalGroup:
    """Mimics meshing.generator.PhysicalGroup without requiring gmsh."""

    def __init__(self, gid: int, name: str, material, tags: list[EntityTag]) -> None:
        self.dim: int = 3
        self.id: int = gid
        self.name: str = name
        self.material = material
        self.tags: list[EntityTag] = tags
        self.entity_tags: list[int] = [gid]


class LeakyMaterial:
    """
    A material whose to_elmer() forgets to strip units (returns a pint Quantity).
    Stands in for a buggy real material, which can't reach this state because its property functions always strip to floats.
    """

    name: str = "Leaky"
    is_magnet: bool = False

    def to_elmer(self, *, at: Mapping[str, Quantity]) -> dict:
        # The required key is present (so check 1 passes) but its value leaked a pint Quantity (so check 2 must fire).
        return {"Relative Permeability": 1.05 * U.dimensionless}


def _magnet_tag(direction: Vec3 = Vec3(0, 1, 0)) -> EntityTag:
    return EntityTag(tag="Mag_N", conditions=[Magnetization(direction=direction)])


def test_valid_magnetostatics_config_passes_silently() -> None:
    groups: list[FakePhysicalGroup] = [
        FakePhysicalGroup(1, "N52_MAG_N", N52(), [_magnet_tag()]),
        FakePhysicalGroup(2, "AIR", Air(), []),
    ]
    # Construction must not raise (validate=True is the default).
    SifWriter(MeshingConfig(), groups, physics=Physics.MAGNETOSTATICS)


def test_missing_required_material_property_raises() -> None:
    # A plain material with no magnetic properties emits no "Relative Permeability", which magnetostatics requires on every body.
    plain: MaterialProperties = MaterialProperties(name="Vacuum-ish")
    groups: list[FakePhysicalGroup] = [FakePhysicalGroup(1, "PLAIN", plain, [])]
    with pytest.raises(ValueError) as exc:
        SifWriter(MeshingConfig(), groups, physics=Physics.MAGNETOSTATICS)
    assert "Relative Permeability" in str(exc.value)
    assert "PLAIN" in str(exc.value)


def test_leaked_pint_quantity_raises() -> None:
    groups: list[FakePhysicalGroup] = [FakePhysicalGroup(1, "LEAK", LeakyMaterial(), [])]
    with pytest.raises(ValueError) as exc:
        SifWriter(MeshingConfig(), groups, physics=Physics.MAGNETOSTATICS)
    assert "Relative Permeability" in str(exc.value)
    assert "Quantity" in str(exc.value)


def test_magnet_without_direction_raises() -> None:
    # N52 is a magnet but this region carries no Magnetization condition.
    groups: list[FakePhysicalGroup] = [
        FakePhysicalGroup(1, "N52_MAG_N", N52(), [EntityTag(tag="Mag_N")]),
        FakePhysicalGroup(2, "AIR", Air(), []),
    ]
    with pytest.raises(ValueError) as exc:
        SifWriter(MeshingConfig(), groups, physics=Physics.MAGNETOSTATICS)
    assert "Magnetization" in str(exc.value)
    assert "N52_MAG_N" in str(exc.value)


def test_magnet_with_zero_direction_raises() -> None:
    # A Magnetization condition is present but its direction is the zero vector, which would emit a zero field — still a misconfiguration.
    groups: list[FakePhysicalGroup] = [
        FakePhysicalGroup(1, "N52_MAG_N", N52(), [_magnet_tag(direction=Vec3(0, 0, 0))]),
        FakePhysicalGroup(2, "AIR", Air(), []),
    ]
    with pytest.raises(ValueError):
        SifWriter(MeshingConfig(), groups, physics=Physics.MAGNETOSTATICS)


def test_validate_false_suppresses_magnet_direction_error() -> None:
    # The escape hatch: validate=False skips the checks and the wiring falls back to its in-sif marker rather than raising.
    groups: list[FakePhysicalGroup] = [
        FakePhysicalGroup(1, "N52_MAG_N", N52(), [EntityTag(tag="Mag_N")]),
        FakePhysicalGroup(2, "AIR", Air(), []),
    ]
    SifWriter(MeshingConfig(), groups, physics=Physics.MAGNETOSTATICS, validate=False)


def test_all_problems_reported_together() -> None:
    # Two distinct misconfigurations in one config must both appear in the single raised error (problems are accumulated, not short-circuited).
    plain: MaterialProperties = MaterialProperties(name="Vacuum-ish")
    groups: list[FakePhysicalGroup] = [
        FakePhysicalGroup(1, "PLAIN", plain, []),
        FakePhysicalGroup(2, "N52_MAG_N", N52(), [EntityTag(tag="Mag_N")]),
    ]
    with pytest.raises(ValueError) as exc:
        SifWriter(MeshingConfig(), groups, physics=Physics.MAGNETOSTATICS)
    message: str = str(exc.value)
    assert "PLAIN" in message
    assert "N52_MAG_N" in message
