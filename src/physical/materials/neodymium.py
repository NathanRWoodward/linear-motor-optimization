from physical.materials.properties import MaterialProperties
from physical.units import U


class N52(MaterialProperties):
    def __init__(self):
        super().__init__()

        self.name = "Neodymium Magnet (N52)"
        self.tag = "N52"

        self.mechanical.density = 7500 * U.kg / U.m**3
        self.mechanical.elastic_modulus = 160e9 * U.Pa
        self.mechanical.yield_strength = 100e6 * U.Pa
        self.mechanical.ultimate_tensile_strength = 200e6 * U.Pa

        self.thermal.conductivity = 8.7 * U.W / (U.m * U.K)
        self.thermal.specific_heat_capacity = 400 * U.J / (U.kg * U.K)
        self.thermal.convective_heat_transfer_coefficient = 10 * U.W / (U.m**2 * U.K)

        self.magnetic.permeability = 1.05  # Relative permeability (dimensionless)
        self.magnetic.remanent_magnetization = 1.48e6 * U.A / U.m
        self.magnetic.coercivity = 955e3 * U.A / U.m

        self.electrical.conductivity = 1e6 * U.S / U.m  # S/m (approximate - good conductors)
        self.electrical.resistivity = 1e-6 * U.ohm * U.m  # Ω·m (approximate)
        self.electrical.permittivity = 1e-10 * U.F / U.m  # F/m (approximate)
        self.electrical.permeability = 1e-6 * U.H / U.m  # H/m (approximate)
