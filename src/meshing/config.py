from typing import Any, Iterable, Iterator, Optional

from pydantic import BaseModel, ConfigDict, Field
from rich.tree import Tree

from common.utils import COLORS
from common.vector import Vec3, Vec3Field
from physical.materials.properties import MaterialProperties
from physical.units import HeatFlux, HeatTransferCoefficient, Temperature


def first_tag_value(tags: Iterable["EntityTag"], field: str) -> Optional[Any]:
    """Return the first non-None value of ``field`` across ``tags``, or None.

    Replaces the repeated ``getattr(tag, field, None) is not None`` lookup so the
    "find the override a region carries" logic lives in one place.
    """
    for tag in tags:
        value: Any = getattr(tag, field, None)
        if value is not None:
            return value
    return None


class EntityTag(BaseModel):
    """A per-region override matched to a mesh entity by name.

    Carries information that is not a material property but still needs to reach
    the solver for a specific region: a magnetization direction for a magnet
    block, a fixed boundary temperature, etc.

    Note on magnetization: the magnitude |M| = Br/mu0 is a material property;
    only the direction is per-region (the same N52 block points N/E/S/W depending
    on its Halbach slot). So this carries a `magnetization_direction` unit
    vector, replacing the earlier hack of riding direction on
    `magnetic_coercivity`. The full composable-condition model arrives in Phase 2.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    tag: str = ""

    magnetization_direction: Optional[Vec3Field] = Field(
        default=None,
        description="Unit vector giving the magnetization direction for a magnet region.",
    )

    fixed_temperature: Optional[Temperature] = Field(default=None, description="Fixed temperature (K) boundary value")
    fixed_heat_flux: Optional[HeatFlux] = Field(default=None, description="Fixed heat flux (W/m^2) boundary value")
    convection_coefficient: Optional[HeatTransferCoefficient] = Field(
        default=None, description="Convective heat transfer coefficient for a convection boundary"
    )

    # (field name, human label) for the overrides this tag can carry. Used by
    # print_tree and overrides() so the set lives in one place.
    _OVERRIDE_FIELDS: tuple[tuple[str, str], ...] = (
        ("magnetization_direction", "Magnetization Direction"),
        ("fixed_temperature", "Fixed Temperature"),
        ("fixed_heat_flux", "Fixed Heat Flux"),
        ("convection_coefficient", "Convection Coefficient"),
    )

    def overrides(self) -> Iterator[tuple[str, str, Any]]:
        """Yield (field, label, value) for each override that is set (non-None)."""
        for field, label in self._OVERRIDE_FIELDS:
            value: Any = getattr(self, field)
            if value is not None:
                yield field, label, value

    def print_tree(self, tree: Tree) -> None:
        report: Tree = tree.add(COLORS.H2(f"Tag: {self.tag}"))
        for _field, label, value in self.overrides():
            report.add(COLORS.Prop(label, f"{value}"))


class MeshingConfig(BaseModel):
    """The single config that drives both the mesher and the sif writer."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    materials: list[MaterialProperties] = Field(default_factory=list)
    tags: list[EntityTag] = Field(default_factory=list)
    STEP: str = "data/geometry.step"
    global_mesh_size: float = Field(default=1.0, description="Global mesh size in meters")
