from rich.tree import Tree


class MechanicalProperties:
    def __init__(self):
        self.density: float = None
        """kg/m³"""

        self.elastic_modulus: float = None
        """Elastic modulus (Young's modulus) in Pascals (Pa), representing the stiffness of a material"""

        self.yield_strength: float = None
        """Yield strength in Pascals (Pa), representing the stress at which a material begins to deform plastically"""

        self.ultimate_tensile_strength: float = None
        """Ultimate tensile strength in Pascals (Pa), representing the maximum stress a material can withstand while being stretched or pulled before breaking"""


class ThermalProperties:
    def __init__(self):
        self.conductivity: float = None
        """Thermal conductivity in W/(m·K)"""

        self.specific_heat_capacity: float = None
        """Specific heat capacity in J/(kg·K)"""

        self.convective_heat_transfer_coefficient: float = None
        """Convective heat transfer coefficient in W/(m²·K)"""

        self.glass_transition_temperature: float = None
        """Glass transition temperature in K, representing the temperature at which an amorphous material transitions from a hard and relatively brittle state into a viscous or rubbery state"""


class MagneticProperties:
    def __init__(self):
        self.permeability: float = None
        """Relative permeability (dimensionless), where 1.0 is the permeability of free space"""

        self.remanent_magnetization: float = None
        """Remanent magnetization in A/m, representing the strength of a permanent magnet"""

        self.coercivity: float = None
        """Coercivity in A/m, representing the resistance of a magnetic material to becoming demagnetized"""


class ElectricalProperties:
    def __init__(self):
        self.conductivity: float = None
        """Electrical conductivity in Siemens per meter (S/m), representing how well a material conducts electricity"""

        self.resistivity: float = None
        """Electrical resistivity in Ohm-meters (Ω·m), representing how strongly a material opposes the flow of electric current"""

        self.permittivity: float = None
        """Permittivity in Farads per meter (F/m), representing how an electric field affects, and is affected by, a dielectric medium"""

        self.permeability: float = None
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
            tree = Tree(f"Material: {self.name}")

        for key, value in self.__dict__.items():
            if isinstance(value, (MechanicalProperties, ThermalProperties, MagneticProperties, ElectricalProperties)):
                subtree = tree.add(key.replace("_", " ").title())
                for subkey, subvalue in value.__dict__.items():
                    subtree.add(f"{subkey.replace('_', ' ').title()}: {subvalue}")
            else:
                tree.add(f"{key.replace('_', ' ').title()}: {value}")

        return tree
