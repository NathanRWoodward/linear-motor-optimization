from rich.tree import Tree
from common.utils import COLORS
from common.vector import Vec3
from physical.materials.properties import MaterialProperties


class EntityTag:
    def __init__(self, tag: str = ""):
        self.tag: str = tag

        self.fixed_temperature: float = None
        """Fixed temperature in K, if applicable"""

        self.fixed_heat_flux: float = None
        """Fixed heat flux in W/m², if applicable"""

        self.magnetic_coercivity: Vec3 = None
        """Coercivity vector in A/m, representing the magnetic moment per unit volume of a material"""

    def print_tree(self, tree: Tree):
        report = tree.add(COLORS.H2(f"Tag: {self.tag}"))

        if self.fixed_temperature is not None:
            report.add(COLORS.Prop("Fixed Temperature", f"{self.fixed_temperature} K"))

        if self.fixed_heat_flux is not None:
            report.add(COLORS.Prop("Fixed Heat Flux", f"{self.fixed_heat_flux} W/m²"))

        if self.magnetic_coercivity is not None:
            report.add(COLORS.Prop("Magnetic Coercivity", f"{self.magnetic_coercivity}"))


class MeshingConfig:
    def __init__(self):
        self.materials: list[MaterialProperties] = []
        self.tags: list[EntityTag] = []
        self.STEP: str = "data/geometry.step"

        self.global_mesh_size: float = 1.0
        """Global mesh size in meters, representing the target size of mesh elements across the entire geometry"""
