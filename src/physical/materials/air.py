from physical.materials.properties import MaterialProperties


class Air(MaterialProperties):
    def __init__(self):
        super().__init__()

        self.name = "Air"
        self.tag = "Air"

        self.mechanical.density = 1.225  # kg/m³ at sea level
        self.mechanical.elastic_modulus = None
        self.mechanical.yield_strength = None
        self.mechanical.ultimate_tensile_strength = None

        self.thermal.conductivity = 0.0257  # W/(m·K) at room temperature
        self.thermal.specific_heat_capacity = 1005  # J/(kg·K) at constant pressure
        self.thermal.convective_heat_transfer_coefficient = 10  # W/(m²·K) (approximate for natural convection)

        self.magnetic.permeability = 1.0  # Relative permeability (dimensionless)
        self.magnetic.remanent_magnetization = None
        self.magnetic.coercivity = None

        self.electrical.conductivity = 1e-14  # S/m (approximate for dry air)
        self.electrical.resistivity = 1e14  # Ω·m (approximate for dry air)
        self.electrical.permittivity = 8.854e-12  # F/m (permittivity of free space)
        self.electrical.permeability = 1.2566370614e-6  # H/m (permeability of free space)
