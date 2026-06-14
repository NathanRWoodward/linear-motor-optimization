class EntityTag:
    def __init__(self):
        self.tag: str = ""

        self.fixed_temperature: float = None
        """Fixed temperature in K, if applicable"""

        self.fixed_heat_flux: float = None
        """Fixed heat flux in W/m², if applicable"""


class MeshingConfig:
    def __init__(self):
        pass
