"""Phase 0 smoke test: the magnetostatics sif still generates correctly.

Uses a fake PhysicalGroup (the standalone fake-group pattern) so it needs no
gmsh — just the typed config + materials + the SifWriter.
"""

import re
import tempfile
from pathlib import Path

import pytest

from common.vector import Vec3
from elmer.physics import Physics
from elmer.sim import SifWriter
from meshing.config import EntityTag, MeshingConfig
from physical.conditions import Magnetization
from physical.materials.air import Air
from physical.materials.neodymium import N52

MU0 = 1.25663706212e-6


class FakePhysicalGroup:
    """Mimics meshing.generator.PhysicalGroup without requiring gmsh."""

    def __init__(self, gid, name, material, tags):
        self.dim = 3
        self.id = gid
        self.name = name
        self.material = material
        self.tags = tags
        self.entity_tags = [gid]


def _groups(n_tag=None):
    if n_tag is None:
        n_tag = EntityTag(tag="Mag_N", conditions=[Magnetization(direction=Vec3(0, 1, 0))])
    return [
        FakePhysicalGroup(1, "N52_MAG_N", N52(), [n_tag]),
        FakePhysicalGroup(2, "AIR", Air(), []),
    ]


def _write_sif(physics=Physics.MAGNETOSTATICS, groups=None, validate=True):
    writer = SifWriter(
        MeshingConfig(),
        groups if groups is not None else _groups(),
        physics=physics,
        validate=validate,
    )
    d = Path(tempfile.mkdtemp())
    writer.write(str(d))
    return (d / "case.sif").read_text()


def test_magnetostatics_sif_generates():
    sif = _write_sif()
    assert "WhitneyAVSolver" in sif
    assert "Relative Permeability" in sif


def test_magnet_body_gets_magnetization_body_force():
    # The N-pointing magnet's orientation is carried by a Magnetization condition;
    # |M| = Br/mu0 comes from the N52 material.
    sif = _write_sif()
    m = re.search(r"Magnetization 2 = ([-0-9.eE+]+)", sif)
    assert m, "expected a Magnetization 2 keyword for the N-pointing magnet"
    # N points +y, so |M| lands on component 2 ~ Br/mu0.
    assert float(m.group(1)) == pytest.approx(1.48 / MU0, rel=1e-3)


def test_magnet_without_direction_emits_missing_marker():
    # N52 is a magnet, but this region carries no orientation at all. With
    # validation on this now raises (see test_sif_validation.py); the commented
    # MISSING DIRECTION TAG marker is the validate=False fallback and must be
    # preserved for experiments.
    n_tag = EntityTag(tag="Mag_N")
    sif = _write_sif(groups=_groups(n_tag=n_tag), validate=False)
    assert "MISSING DIRECTION TAG" in sif
    assert "Magnetization 2 =" not in sif


def test_physics_accepts_enum_or_string():
    assert _write_sif(physics=Physics.MAGNETOSTATICS)
    assert _write_sif(physics="magnetostatics")


def test_bad_physics_raises_at_construction():
    with pytest.raises(ValueError):
        SifWriter(MeshingConfig(), _groups(), physics="nonsense")


def test_linear_elasticity_sif_generates() -> None:
    sif = _write_sif(physics=Physics.LINEAR_ELASTICITY)
    assert "StressSolver" in sif
    # material Youngs Modulus reaches the sif (FR4/N52 carry elastic_modulus)
    # via the standard material block.


def test_linear_elasticity_is_selectable_by_string() -> None:
    assert _write_sif(physics="linear_elasticity")
