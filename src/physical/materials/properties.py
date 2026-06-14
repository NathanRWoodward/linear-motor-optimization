from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from rich.tree import Tree

from common.utils import COLORS, title
from physical.units import (
    U,
    Density,
    Dimensionless,
    ElectricalConductivity,
    FieldStrength,
    FluxDensity,
    HeatTransferCoefficient,
    Permeability,
    Permittivity,
    Pressure,
    Resistivity,
    SpecificHeat,
    Temperature,
    ThermalConductivity,
)

MU0 = 1.25663706212e-6  # H/m (N/A^2)


def _si(value, unit) -> Optional[float]:
    """Convert a pint quantity to a bare float in the given SI `unit`."""
    if value is None:
        return None
    if not hasattr(value, "to"):
        return float(value)
    return float(value.to(unit).magnitude)


class _PropertyModel(BaseModel):
    """Base for per-domain property models. Holds real pint quantities and
    validates on assignment so the material-definition authoring style stays
    honest (a wrong-dimensionality value raises at the point of assignment)."""

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)


class MechanicalProperties(_PropertyModel):
    density: Optional[Density] = Field(default=None, description="kg/m³")
    elastic_modulus: Optional[Pressure] = Field(default=None, description="Elastic (Young's) modulus in Pa")
    yield_strength: Optional[Pressure] = Field(default=None, description="Yield strength in Pa")
    ultimate_tensile_strength: Optional[Pressure] = Field(default=None, description="Ultimate tensile strength in Pa")

    def to_elmer(self) -> dict:
        d = {}
        density = _si(self.density, U.kg / U.m**3)
        if density is not None:
            d["Density"] = density
        youngs = _si(self.elastic_modulus, U.Pa)
        if youngs is not None:
            d["Youngs Modulus"] = youngs
        return d


class ThermalProperties(_PropertyModel):
    conductivity: Optional[ThermalConductivity] = Field(default=None, description="Thermal conductivity in W/(m·K)")
    specific_heat_capacity: Optional[SpecificHeat] = Field(default=None, description="Specific heat capacity in J/(kg·K)")
    convective_heat_transfer_coefficient: Optional[HeatTransferCoefficient] = Field(
        default=None, description="Convective heat transfer coefficient in W/(m²·K)"
    )
    glass_transition_temperature: Optional[Temperature] = Field(default=None, description="Glass transition temperature in K")

    def to_elmer(self) -> dict:
        d = {}
        k = _si(self.conductivity, U.W / (U.m * U.K))
        if k is not None:
            d["Heat Conductivity"] = k
        cp = _si(self.specific_heat_capacity, U.J / (U.kg * U.K))
        if cp is not None:
            d["Heat Capacity"] = cp
        return d


class MagneticProperties(_PropertyModel):
    rel_permeability: Optional[Dimensionless] = Field(default=None, description="μr: relative permeability (dimensionless)")
    remanence: Optional[FluxDensity] = Field(default=None, description="Bᵣ: remanence in Tesla (T)")
    coercivity: Optional[FieldStrength] = Field(default=None, description="Hc: coercivity in A/m")

    def to_elmer(self) -> dict:
        d = {}
        mu_r = self.rel_permeability
        if mu_r is not None:
            d["Relative Permeability"] = _si(mu_r, U.dimensionless)
        return d

    @property
    def magnetization_magnitude(self) -> Optional[float]:
        br = _si(self.remanence, U.T)
        if br is None:
            return None
        return br / MU0


class ElectricalProperties(_PropertyModel):
    conductivity: Optional[ElectricalConductivity] = Field(default=None, description="Electrical conductivity in S/m")
    resistivity: Optional[Resistivity] = Field(default=None, description="Electrical resistivity in Ω·m")
    permittivity: Optional[Permittivity] = Field(default=None, description="Permittivity in F/m")
    permeability: Optional[Permeability] = Field(default=None, description="Permeability in H/m")

    def to_elmer(self) -> dict:
        d = {}
        sigma = _si(self.conductivity, U.S / U.m)
        if sigma is not None:
            d["Electric Conductivity"] = sigma
        eps = _si(self.permittivity, U.F / U.m)
        if eps is not None:
            EPS0 = 8.8541878128e-12  # F/m
            d["Relative Permittivity"] = eps / EPS0
        return d


class MaterialProperties(_PropertyModel):
    name: str = ""
    tag: str = ""
    mechanical: MechanicalProperties = Field(default_factory=MechanicalProperties)
    thermal: ThermalProperties = Field(default_factory=ThermalProperties)
    magnetic: MagneticProperties = Field(default_factory=MagneticProperties)
    electrical: ElectricalProperties = Field(default_factory=ElectricalProperties)

    def to_elmer(self) -> dict:
        data: dict = {}
        data.update(self.mechanical.to_elmer())
        data.update(self.thermal.to_elmer())
        data.update(self.magnetic.to_elmer())
        data.update(self.electrical.to_elmer())
        return data

    @property
    def is_magnet(self) -> bool:
        return self.magnetic.magnetization_magnitude is not None

    def print_tree(self, tree: Tree | None = None):
        if tree is None:
            tree = Tree(COLORS.H1(self.name))
        else:
            tree = tree.add(COLORS.H1(self.name))
        for key in ("name", "tag", "mechanical", "thermal", "magnetic", "electrical"):
            value = getattr(self, key)
            if isinstance(value, (MechanicalProperties, ThermalProperties, MagneticProperties, ElectricalProperties)):
                subtree = tree.add(COLORS.H2(title(key)))
                for subkey, subvalue in value.__dict__.items():
                    prop = COLORS.Prop(title(subkey), f"{subvalue}")
                    subtree.add(prop)
            else:
                tree.add(COLORS.Prop(title(key), f"{value}"))
        return tree
