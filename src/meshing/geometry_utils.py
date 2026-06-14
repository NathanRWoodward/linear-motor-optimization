"""Per-entity geometric extraction helpers.

Relocated from the now-deleted ``geometry/mesh.py`` prototype (doc 06 de-dup
step 1). The bounding-box / center-of-mass extraction is the one useful bit of
that dead module; it is kept here as a small reusable helper because the Phase 4
adjacency code (doc 01) will reuse it to reason about which faces bound which
bodies.

The pure dataclass (`EntityGeometry`) carries no gmsh dependency so it can be
constructed and tested anywhere. The gmsh-reading function lives behind a lazy
import so importing this module does not pull gmsh into pure-logic test runs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityGeometry:
    """Axis-aligned bounding box, center of mass, and volume of one entity.

    Coordinates are in the STEP file's length unit (mm for build123d exports).
    """

    dim: int
    tag: int
    bbox_min: tuple[float, float, float]
    bbox_max: tuple[float, float, float]
    center_of_mass: tuple[float, float, float]
    volume: float

    @property
    def extent(self) -> tuple[float, float, float]:
        """Size of the bounding box along each axis."""
        return (
            self.bbox_max[0] - self.bbox_min[0],
            self.bbox_max[1] - self.bbox_min[1],
            self.bbox_max[2] - self.bbox_min[2],
        )


def extract_entity_geometry(dim: int, tag: int) -> EntityGeometry:
    """Read an entity's bounding box / center of mass / volume from gmsh.

    Requires an initialized gmsh model with the geometry already imported and
    synchronized. gmsh is imported lazily so this module stays importable (and
    its dataclass usable) in environments without gmsh.
    """
    import gmsh

    bb = gmsh.model.getBoundingBox(dim, tag)
    com = gmsh.model.occ.getCenterOfMass(dim, tag)
    volume = gmsh.model.occ.getMass(dim, tag)
    return EntityGeometry(
        dim=dim,
        tag=tag,
        bbox_min=(bb[0], bb[1], bb[2]),
        bbox_max=(bb[3], bb[4], bb[5]),
        center_of_mass=(com[0], com[1], com[2]),
        volume=volume,
    )
