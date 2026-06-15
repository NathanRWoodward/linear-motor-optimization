from physical.materials.properties import MaterialProperties
from physical.property_functions import Static
from physical.units import U


class N52(MaterialProperties):
    """
    N52 neodymium magnet.

    Phase 1 migration proof (doc 05): every scalar property is now an explicit ``Static`` property function rather than a raw quantity.
    The authoring reads almost the same — ``Static(value=...)`` instead of the bare quantity — and the value flows through the same ``to_elmer(at=...)`` call site as a Calibration or ClosedForm would.
    (Air / FR4 still assign bare quantities, which the field coerces into a Static, so both styles are exercised.)
    """

    def __init__(self):
        super().__init__()

        self.name = "Neodymium Magnet (N52)"
        self.tag = "N52"

        self.mechanical.density = Static(value=7500 * U.kg / U.m**3)
        self.mechanical.elastic_modulus = Static(value=160e9 * U.Pa)
        self.mechanical.yield_strength = Static(value=100e6 * U.Pa)
        self.mechanical.ultimate_tensile_strength = Static(value=200e6 * U.Pa)

        self.thermal.conductivity = Static(value=8.7 * U.W / (U.m * U.K))
        self.thermal.specific_heat_capacity = Static(value=400 * U.J / (U.kg * U.K))
        self.thermal.convective_heat_transfer_coefficient = Static(value=10 * U.W / (U.m**2 * U.K))

        self.magnetic.rel_permeability = Static(value=1.05 * U.dimensionless)
        self.magnetic.remanence = Static(value=1.48 * U.T)
        self.magnetic.coercivity = Static(value=955e3 * U.A / U.m)

        self.electrical.conductivity = Static(value=1e6 * U.S / U.m)
        self.electrical.resistivity = Static(value=1e-6 * U.ohm * U.m)
        self.electrical.permittivity = Static(value=1e-10 * U.F / U.m)
        self.electrical.permeability = Static(value=1e-6 * U.H / U.m)
