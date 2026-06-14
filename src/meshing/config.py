from common.vector import Vec3
from physical.materials.properties import MaterialProperties


class EntityTag:
    def __init__(self):
        self.tag: str = ""

        self.fixed_temperature: float = None
        """Fixed temperature in K, if applicable"""

        self.fixed_heat_flux: float = None
        """Fixed heat flux in W/m², if applicable"""

        self.magnetization_vector: Vec3 = None
        """Magnetization vector in A/m, representing the magnetic moment per unit volume of a material"""


class MeshingConfig:
    def __init__(self):
        self.materials: list[MaterialProperties] = []
        self.tags: list[EntityTag] = []

        self.global_mesh_size: float = 1.0
        """Global mesh size in meters, representing the target size of mesh elements across the entire geometry"""
