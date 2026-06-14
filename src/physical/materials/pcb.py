from physical.materials.properties import MaterialProperties
from physical.units import U


class FR4(MaterialProperties):
    def __init__(self):
        super().__init__()
        self.name = "FR4"
        self.tag = "FR4"
        self.mechanical.density = 1900 * U.kg / U.m**3
        self.mechanical.elastic_modulus = 20e9 * U.Pa
        self.mechanical.yield_strength = 60e6 * U.Pa
        self.mechanical.ultimate_tensile_strength = 100e6 * U.Pa
        self.thermal.conductivity = 0.3 * U.W / (U.m * U.K)
        self.thermal.specific_heat_capacity = 1200 * U.J / (U.kg * U.K)
        self.thermal.convective_heat_transfer_coefficient = 10 * U.W / (U.m**2 * U.K)
        self.thermal.glass_transition_temperature = (130 * U.degC).to(U.K)
        self.magnetic.rel_permeability = 1.0 * U.dimensionless
        self.electrical.conductivity = 1e-10 * U.S / U.m
        self.electrical.resistivity = 1e10 * U.ohm * U.m
        self.electrical.permittivity = 4.5 * 8.854e-12 * U.F / U.m
        self.electrical.permeability = 1e-6 * U.H / U.m
