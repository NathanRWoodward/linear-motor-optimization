from common.utils import COLORS, title
from rich.tree import Tree
from physical.units import U, Unit

# ---------------------------------------------------------------------------
# Mapping physical material properties -> Elmer sif material keywords.
#
# The properties below are stored as pint quantities (a magnitude + a unit) so
# the rest of the project can reason about them with real units. Elmer, on the
# other hand, wants *bare SI floats* in its `Material` sections (e.g. a density
# of `7500`, not `7500 kg/m^3`). Each `to_elmer()` below therefore:
#
#   1) converts the pint quantity to canonical SI base units, and
#   2) emits the magnitude under the exact keyword Elmer expects.
#
# Reference for the keyword names: the pyelmer example `my_materials.yml` and
# the Elmer Models Manual. Only properties relevant to the *currently wired*
# physics (magnetostatics) are fully exercised end-to-end; the thermal,
# electrical and mechanical mappings are implemented but marked as scaffolds so
# they can be wired up when those solvers are added.
# ---------------------------------------------------------------------------

# Vacuum permeability, used to turn a remanence Br [T] into a magnetization
# M = Br / mu0 [A/m] for permanent magnets.
MU0 = 1.25663706212e-6  # H/m (N/A^2)


def _si(value: "Unit | float | None", unit) -> float | None:
    """Convert a pint quantity to a bare float in the given SI `unit`.

    Accepts a plain float/int (assumed already in SI) or None (returns None so
    callers can omit the keyword entirely).
    """
    if value is None:
        return None
    # Plain number -> assume already SI.
    if not hasattr(value, "to"):
        return float(value)
    return float(value.to(unit).magnitude)


class MechanicalProperties:
    def __init__(self):
        self.density: Unit = None
        """kg/m³"""

        self.elastic_modulus: Unit = None
        """Elastic modulus (Young's modulus) in Pascals (Pa), representing the stiffness of a material"""

        self.yield_strength: Unit = None
        """Yield strength in Pascals (Pa), representing the stress at which a material begins to deform plastically"""

        self.ultimate_tensile_strength: Unit = None
        """Ultimate tensile strength in Pascals (Pa), representing the maximum stress a material can withstand while being stretched or pulled before breaking"""

    def to_elmer(self) -> dict:
        """Emit Elmer `Material` keywords for the mechanical domain.

        `Density` is consumed by virtually every Elmer solver (it is also used
        by the magnetostatics force integration), so it is always emitted when
        available. The strength values have no direct Elmer keyword in a linear
        elastic run; they are left out here and would feed a (future) stress
        solver's failure post-processing instead.
        """
        d = {}
        density = _si(self.density, U.kg / U.m**3)
        if density is not None:
            d["Density"] = density
        # SCAFFOLD: linear elasticity. When a StressSolver is wired, map
        #   elastic_modulus -> "Youngs Modulus", plus a Poisson Ratio (not yet
        #   stored on this class). yield/ultimate strengths are post-processing
        #   only and have no Elmer material keyword.
        youngs = _si(self.elastic_modulus, U.Pa)
        if youngs is not None:
            d["Youngs Modulus"] = youngs
        return d


class ThermalProperties:
    def __init__(self):
        self.conductivity: Unit = None
        """Thermal conductivity in W/(m·K)"""

        self.specific_heat_capacity: Unit = None
        """Specific heat capacity in J/(kg·K)"""

        self.convective_heat_transfer_coefficient: Unit = None
        """Convective heat transfer coefficient in W/(m²·K)"""

        self.glass_transition_temperature: Unit = None
        """Glass transition temperature in K, representing the temperature at which an amorphous material transitions from a hard and relatively brittle state into a viscous or rubbery state"""

    def to_elmer(self) -> dict:
        """Emit Elmer `Material` keywords for the heat equation (HeatSolve).

        Note: the convective heat-transfer coefficient is *not* a material
        keyword in Elmer; it belongs on a boundary condition ("Heat Transfer
        Coefficient"). It is therefore intentionally omitted here and is handled
        at the boundary level by the sim generator.
        """
        d = {}
        k = _si(self.conductivity, U.W / (U.m * U.K))
        if k is not None:
            d["Heat Conductivity"] = k
        cp = _si(self.specific_heat_capacity, U.J / (U.kg * U.K))
        if cp is not None:
            d["Heat Capacity"] = cp
        return d


class MagneticProperties:
    # Remanence is often given in Tesla (T), a unit of magnetic flux density (B).
    # The permanent-magnet magnetization M [A/m] used by Elmer's WhitneyAVSolver
    # is M = Br / mu0. The *direction* of M is not a material property (the same
    # N52 block points different ways depending on where it sits in the Halbach
    # array); direction is supplied per-region by the mesh tags and applied as a
    # Body Force, see ElmerMagnetization below.

    def __init__(self):
        self.rel_permeability: Unit = None
        """μr: Relative permeability (dimensionless), where 1.0 is the permeability of free space"""

        self.remanence: Unit = None
        """Bᵣ: Remanence in Tesla (T), representing the magnetic flux density remaining in a material after an external magnetic field is removed"""

        self.coercivity: Unit = None
        """Hc: Coercivity in A/m, representing the resistance of a magnetic material to becoming demagnetized"""

    def to_elmer(self) -> dict:
        """Emit Elmer `Material` keywords for magnetostatics (WhitneyAVSolver).

        For a permanent magnet, Elmer needs the *relative permeability* of the
        magnet's recoil line (~1.05 for sintered NdFeB) in the material, and the
        magnetization as a Body Force (handled separately). We expose the scalar
        magnetization magnitude here as a convenience for the sim generator.
        """
        d = {}
        mu_r = self.rel_permeability
        if mu_r is not None:
            # rel_permeability is dimensionless; accept a pint quantity or float.
            d["Relative Permeability"] = _si(mu_r, U.dimensionless) if hasattr(mu_r, "to") else float(mu_r)
        return d

    @property
    def magnetization_magnitude(self) -> float | None:
        """|M| = Br / mu0 in A/m, or None if this material has no remanence."""
        br = _si(self.remanence, U.T)
        if br is None:
            return None
        return br / MU0


class ElectricalProperties:
    def __init__(self):
        self.conductivity: Unit = None
        """Electrical conductivity in Siemens per meter (S/m), representing how well a material conducts electricity"""

        self.resistivity: Unit = None
        """Electrical resistivity in Ohm-meters (Ω·m), representing how strongly a material opposes the flow of electric current"""

        self.permittivity: Unit = None
        """Permittivity in Farads per meter (F/m), representing how an electric field affects, and is affected by, a dielectric medium"""

        self.permeability: Unit = None
        """Permeability in Henries per meter (H/m), representing how a material responds to a magnetic field, including its ability to support the formation of a magnetic field within it"""

    def to_elmer(self) -> dict:
        """Emit Elmer `Material` keywords for the electrical domain.

        - Electric Conductivity [S/m] is used by current-conduction and eddy
          solvers (StatCurrentSolve, MagnetoDynamics with eddy currents).
        - Relative Permittivity (dimensionless) is what the electrostatics
          solver wants, NOT the absolute permittivity. We derive it from the
          absolute permittivity by dividing out epsilon0.
        """
        d = {}
        sigma = _si(self.conductivity, U.S / U.m)
        if sigma is not None:
            d["Electric Conductivity"] = sigma
        # SCAFFOLD: electrostatics. Elmer wants RELATIVE permittivity.
        eps = _si(self.permittivity, U.F / U.m)
        if eps is not None:
            EPS0 = 8.8541878128e-12  # F/m
            d["Relative Permittivity"] = eps / EPS0
        return d


class MaterialProperties:
    def __init__(self):
        self.name: str = ""
        self.tag: str = ""
        self.mechanical: MechanicalProperties = MechanicalProperties()
        self.thermal: ThermalProperties = ThermalProperties()
        self.magnetic: MagneticProperties = MagneticProperties()
        self.electrical: ElectricalProperties = ElectricalProperties()

    def to_elmer(self) -> dict:
        """Aggregate all domains into a single Elmer `Material` data dict.

        The merge order is deliberate: later domains can override earlier ones
        if a keyword genuinely belongs to both, but in practice the keyword sets
        are disjoint. The result is a flat `{keyword: value}` dict ready to hand
        to `pyelmer.elmer.Material(sim, name, data=...)`.
        """
        data: dict = {}
        data.update(self.mechanical.to_elmer())
        data.update(self.thermal.to_elmer())
        data.update(self.magnetic.to_elmer())
        data.update(self.electrical.to_elmer())
        return data

    @property
    def is_magnet(self) -> bool:
        """True if this material carries a permanent-magnet remanence."""
        return self.magnetic.magnetization_magnitude is not None

    def print_tree(self, tree: Tree | None = None):
        if tree is None:
            tree = Tree(COLORS.H1(self.name))
        else:
            tree = tree.add(COLORS.H1(self.name))

        for key, value in self.__dict__.items():
            if isinstance(value, (MechanicalProperties, ThermalProperties, MagneticProperties, ElectricalProperties)):
                subtree = tree.add(COLORS.H2(title(key)))
                for subkey, subvalue in value.__dict__.items():
                    prop = COLORS.Prop(title(subkey), f"{subvalue}")
                    subtree.add(prop)
            else:
                tree.add(COLORS.Prop(title(key), f"{value}"))

        return tree
