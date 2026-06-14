from physical.materials.properties import MaterialProperties
from physical.units import U


class Air(MaterialProperties):
    def __init__(self):
        super().__init__()
        self.name = "Air"
        self.tag = "Air"
        self.mechanical.density = 1.225 * U.kg / U.m**3
        self.thermal.conductivity = 0.0257 * U.W / (U.m * U.K)
        self.thermal.specific_heat_capacity = 1005 * U.J / (U.kg * U.K)
        self.thermal.convective_heat_transfer_coefficient = 10 * U.W / (U.m**2 * U.K)
        self.magnetic.rel_permeability = 1.0 * U.dimensionless
        self.electrical.conductivity = 1e-14 * U.S / U.m
        self.electrical.resistivity = 1e14 * U.ohm * U.m
        self.electrical.permittivity = 8.854e-12 * U.F / U.m
        self.electrical.permeability = 1.2566370614e-6 * U.H / U.m
