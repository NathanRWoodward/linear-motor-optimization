from physical.materials.properties import MaterialProperties
from materials.conversions import Covnert


class FR4(MaterialProperties):
    def __init__(self):
        self.name = "FR4"
        self.tag = "FR4"

        self.mechanical.density = 1900  # kg/m³
        self.mechanical.elastic_modulus = 20e9  # Pa
        self.mechanical.yield_strength = 60e6  # Pa
        self.mechanical.ultimate_tensile_strength = 100e6  # Pa

        self.thermal.conductivity = 0.3  # W/(m·K)
        self.thermal.specific_heat_capacity = 1200  # J/(kg·K)
        self.thermal.convective_heat_transfer_coefficient = 10  # W/(m²·K)
        self.thermal.glass_transition_temperature = Covnert.celsius_to_kelvin(130)  # K, typical for FR4

        self.magnetic.permeability = 1.0  # Relative permeability (dimensionless)
        self.magnetic.remanent_magnetization = None
        self.magnetic.coercivity = None

        self.electrical.conductivity = 1e-10  # S/m (approximate for FR4)
        self.electrical.resistivity = 1e10  # Ω·m (approximate for FR4)
        self.electrical.permittivity = 4.5 * 8.854e-12  # F/m (relative permittivity times permittivity of free space)
        self.electrical.permeability = 1e-6  # H/m (approximate for non-magnetic materials)
