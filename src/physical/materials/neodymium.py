from physical.materials.properties import MaterialProperties


class N52(MaterialProperties):
    def __init__(self):
        super().__init__()

        self.name = "N52 Neodymium Magnet"
        self.tag = "N52"

        self.mechanical.density = 7500  # kg/m³
        self.mechanical.elastic_modulus = 160e9  # Pa
        self.mechanical.yield_strength = 100e6  # Pa
        self.mechanical.ultimate_tensile_strength = 200e6  # Pa

        self.thermal.conductivity = 8.7  # W/(m·K)
        self.thermal.specific_heat_capacity = 400  # J/(kg·K)
        self.thermal.convective_heat_transfer_coefficient = 10  # W/(m²·K)

        self.magnetic.permeability = 1.05  # Relative permeability (dimensionless)
        self.magnetic.remanent_magnetization = 1.48e6  # A/m
        self.magnetic.coercivity = 955e3  # A/m

        self.electrical.conductivity = 1e6  # S/m (approximate - good conductors)
        self.electrical.resistivity = 1e-6  # Ω·m (approximate)
        self.electrical.permittivity = 1e-10  # F/m (approximate)
        self.electrical.permeability = 1e-6  # H/m (approximate)
