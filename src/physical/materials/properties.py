from common.utils import COLORS, title
from rich.tree import Tree
from physical.units import Unit

# TODO: We need to figure out what exaxly Elmer needs here!
#           I'm surely missing some important properties, and maybe some of these are not needed.
#           We can start with a basic set of properties and then add more as needed.
#           We also need to figure out how to handle anisotropic materials, which may have different properties in different directions.
#           For now, we can just assume everything is isotropic and add anisotropy later if needed. (we will if dealing with composites)


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


class MagneticProperties:
    # VACUUM_PERMEABILITY = 1.2566370614e-6 * Unit.H / Unit.m

    # Remanence is often given in Tesla (T), which is a unit of magnetic flux density (B).
    # To convert remanence to remanent magnetization (M), we can use the relationship B = μ₀ * M, where μ₀ is the permeability of free space. Therefore, M = B / μ₀.

    def __init__(self):
        self.rel_permeability: Unit = None
        """μr: Relative permeability (dimensionless), where 1.0 is the permeability of free space"""

        self.remanence: Unit = None
        """Bᵣ: Remanence in Tesla (T), representing the magnetic flux density remaining in a material after an external magnetic field is removed"""

        self.coercivity: Unit = None
        """Hc: Coercivity in A/m, representing the resistance of a magnetic material to becoming demagnetized"""


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


class MaterialProperties:
    def __init__(self):
        self.name: str = ""
        self.tag: str = ""
        self.mechanical: MechanicalProperties = MechanicalProperties()
        self.thermal: ThermalProperties = ThermalProperties()
        self.magnetic: MagneticProperties = MagneticProperties()
        self.electrical: ElectricalProperties = ElectricalProperties()

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
