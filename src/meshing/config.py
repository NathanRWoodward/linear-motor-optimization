from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from rich.tree import Tree

from common.utils import COLORS
from common.vector import Vec3, Vec3Field
from physical.materials.properties import MaterialProperties
from physical.units import HeatFlux, HeatTransferCoefficient, Temperature


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

    def print_tree(self, tree: Tree):
        report = tree.add(COLORS.H2(f"Tag: {self.tag}"))
        if self.magnetization_direction is not None:
            report.add(COLORS.Prop("Magnetization Direction", f"{self.magnetization_direction}"))
        if self.fixed_temperature is not None:
            report.add(COLORS.Prop("Fixed Temperature", f"{self.fixed_temperature}"))
        if self.fixed_heat_flux is not None:
            report.add(COLORS.Prop("Fixed Heat Flux", f"{self.fixed_heat_flux}"))
        if self.convection_coefficient is not None:
            report.add(COLORS.Prop("Convection Coefficient", f"{self.convection_coefficient}"))


class MeshingConfig(BaseModel):
    """The single config that drives both the mesher and the sif writer."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    materials: list[MaterialProperties] = Field(default_factory=list)
    tags: list[EntityTag] = Field(default_factory=list)
    STEP: str = "data/geometry.step"
    global_mesh_size: float = Field(default=1.0, description="Global mesh size in meters")
