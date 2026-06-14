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


def _groups():
    n_tag = EntityTag(tag="Mag_N", magnetization_direction=Vec3(0, 1, 0))
    return [
        FakePhysicalGroup(1, "N52_MAG_N", N52(), [n_tag]),
        FakePhysicalGroup(2, "AIR", Air(), []),
    ]


def _write_sif(physics=Physics.MAGNETOSTATICS):
    writer = SifWriter(MeshingConfig(), _groups(), physics=physics)
    d = Path(tempfile.mkdtemp())
    writer.write(str(d))
    return (d / "case.sif").read_text()


def test_magnetostatics_sif_generates():
    sif = _write_sif()
    assert "WhitneyAVSolver" in sif
    assert "Relative Permeability" in sif


def test_magnet_body_gets_magnetization_body_force():
    sif = _write_sif()
    m = re.search(r"Magnetization 2 = ([-0-9.eE+]+)", sif)
    assert m, "expected a Magnetization 2 keyword for the N-pointing magnet"
    # N points +y, so |M| lands on component 2 ~ Br/mu0.
    assert float(m.group(1)) == pytest.approx(1.48 / MU0, rel=1e-3)


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
