from physical.materials.properties import MaterialProperties
from physical.units import U


class Air(MaterialProperties):
    def __init__(self):
        super().__init__()

        self.name = "Air"
        self.tag = "Air"

        self.mechanical.density = 1.225 * U.kg / U.m**3  # kg/m³ at sea level
        self.mechanical.elastic_modulus = None
        self.mechanical.yield_strength = None
        self.mechanical.ultimate_tensile_strength = None

        self.thermal.conductivity = 0.0257 * U.W / (U.m * U.K)  # W/(m·K) at room temperature
        self.thermal.specific_heat_capacity = 1005 * U.J / (U.kg * U.K)  # J/(kg·K) at constant pressure
        self.thermal.convective_heat_transfer_coefficient = 10 * U.W / (U.m**2 * U.K)  # W/(m²·K) (approximate for natural convection)

        self.magnetic.rel_permeability = 1.0  # Relative permeability (dimensionless)
        self.magnetic.remanence = None
        self.magnetic.coercivity = None

        self.electrical.conductivity = 1e-14 * U.S / U.m  # S/m (approximate for dry air)
        self.electrical.resistivity = 1e14 * U.ohm * U.m  # Ω·m (approximate for dry air)
        self.electrical.permittivity = 8.854e-12 * U.F / U.m  # F/m (permittivity of free space)
        self.electrical.permeability = 1.2566370614e-6 * U.H / U.m  # H/m (permeability of free space)
