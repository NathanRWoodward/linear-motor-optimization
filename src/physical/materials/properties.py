from typing import Any, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field
from rich.tree import Tree

from common.utils import COLORS, title
from physical.property_functions import PropertyFunction, property_function_type
from physical.units import (
    U,
    DIM_DENSITY,
    DIM_DIMENSIONLESS,
    DIM_ELECTRICAL_CONDUCTIVITY,
    DIM_FIELD_STRENGTH,
    DIM_FLUX_DENSITY,
    DIM_HEAT_TRANSFER_COEFFICIENT,
    DIM_PERMEABILITY,
    DIM_PERMITTIVITY,
    DIM_PRESSURE,
    DIM_RESISTIVITY,
    DIM_SPECIFIC_HEAT,
    DIM_TEMPERATURE,
    DIM_THERMAL_CONDUCTIVITY,
    Quantity,
)

MU0 = 1.25663706212e-6  # H/m (N/A^2)

# Property-field types: each material property is a PropertyFunction (static
# value, calibration points, or closed form) of a declared dimensionality. A
# bare quantity assigned to one of these fields is coerced into a Static (doc 05);
# the dimensionality is validated at construction either way. The dimensionality
# strings come from the single vocabulary in physical.units (no re-spelling).
_DensityPF = property_function_type(DIM_DENSITY)
_PressurePF = property_function_type(DIM_PRESSURE)
_ThermalConductivityPF = property_function_type(DIM_THERMAL_CONDUCTIVITY)
_SpecificHeatPF = property_function_type(DIM_SPECIFIC_HEAT)
_HeatTransferCoefficientPF = property_function_type(DIM_HEAT_TRANSFER_COEFFICIENT)
_TemperaturePF = property_function_type(DIM_TEMPERATURE)
_DimensionlessPF = property_function_type(DIM_DIMENSIONLESS)
_FluxDensityPF = property_function_type(DIM_FLUX_DENSITY)
_FieldStrengthPF = property_function_type(DIM_FIELD_STRENGTH)
_ElectricalConductivityPF = property_function_type(DIM_ELECTRICAL_CONDUCTIVITY)
_ResistivityPF = property_function_type(DIM_RESISTIVITY)
_PermittivityPF = property_function_type(DIM_PERMITTIVITY)
_PermeabilityPF = property_function_type(DIM_PERMEABILITY)


def _si(prop: Optional[PropertyFunction], unit: Any, at: Mapping[str, Quantity]) -> Optional[float]:
    """Evaluate a property function at operating point ``at`` and strip to a bare
    SI float in ``unit``.

    ``prop`` is a PropertyFunction or None; ``unit`` is the target pint unit;
    ``at`` is the operating point (e.g. ``{"temperature": 300 * U.K}``). Static
    properties ignore ``at``; Calibration / ClosedForm consume it. Typed as
    ``Any`` for the pint unit because pint's Quantity / Unit aren't generic and
    over-specifying here adds noise without safety.
    """
    if prop is None:
        return None
    return float(prop(**at).to(unit).magnitude)


class _PropertyModel(BaseModel):
    """Base for per-domain property models. Holds real pint quantities and
    validates on assignment so the material-definition authoring style stays
    honest (a wrong-dimensionality value raises at the point of assignment)."""

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)


class MechanicalProperties(_PropertyModel):
    density: Optional[_DensityPF] = Field(default=None, description="kg/m³")
    elastic_modulus: Optional[_PressurePF] = Field(default=None, description="Elastic (Young's) modulus in Pa")
    yield_strength: Optional[_PressurePF] = Field(default=None, description="Yield strength in Pa")
    ultimate_tensile_strength: Optional[_PressurePF] = Field(default=None, description="Ultimate tensile strength in Pa")

    def to_elmer(self, *, at: Mapping[str, Quantity]) -> dict:
        d: dict = {}
        density: Optional[float] = _si(self.density, U.kg / U.m**3, at)
        if density is not None:
            d["Density"] = density
        youngs: Optional[float] = _si(self.elastic_modulus, U.Pa, at)
        if youngs is not None:
            d["Youngs Modulus"] = youngs
        return d


class ThermalProperties(_PropertyModel):
    conductivity: Optional[_ThermalConductivityPF] = Field(default=None, description="Thermal conductivity in W/(m·K)")
    specific_heat_capacity: Optional[_SpecificHeatPF] = Field(default=None, description="Specific heat capacity in J/(kg·K)")
    convective_heat_transfer_coefficient: Optional[_HeatTransferCoefficientPF] = Field(
        default=None, description="Convective heat transfer coefficient in W/(m²·K)"
    )
    glass_transition_temperature: Optional[_TemperaturePF] = Field(default=None, description="Glass transition temperature in K")

    def to_elmer(self, *, at: Mapping[str, Quantity]) -> dict:
        d: dict = {}
        k: Optional[float] = _si(self.conductivity, U.W / (U.m * U.K), at)
        if k is not None:
            d["Heat Conductivity"] = k
        cp: Optional[float] = _si(self.specific_heat_capacity, U.J / (U.kg * U.K), at)
        if cp is not None:
            d["Heat Capacity"] = cp
        return d


class MagneticProperties(_PropertyModel):
    rel_permeability: Optional[_DimensionlessPF] = Field(default=None, description="μr: relative permeability (dimensionless)")
    remanence: Optional[_FluxDensityPF] = Field(default=None, description="Bᵣ: remanence in Tesla (T)")
    coercivity: Optional[_FieldStrengthPF] = Field(default=None, description="Hc: coercivity in A/m")

    def to_elmer(self, *, at: Mapping[str, Quantity]) -> dict:
        d: dict = {}
        mu_r: Optional[float] = _si(self.rel_permeability, U.dimensionless, at)
        if mu_r is not None:
            d["Relative Permeability"] = mu_r
        return d

    def magnetization_magnitude(self, *, at: Mapping[str, Quantity]) -> Optional[float]:
        """|M| = Bᵣ/μ₀ in A/m, evaluating the remanence at operating point ``at``.

        Returns None for a non-magnet (no remanence). Temperature-dependent
        remanence is honoured here because ``at`` flows into the property
        function — a Calibration/ClosedForm remanence yields a temperature-correct
        magnitude; a Static one ignores ``at``."""
        br: Optional[float] = _si(self.remanence, U.T, at)
        if br is None:
            return None
        return br / MU0


class ElectricalProperties(_PropertyModel):
    conductivity: Optional[_ElectricalConductivityPF] = Field(default=None, description="Electrical conductivity in S/m")
    resistivity: Optional[_ResistivityPF] = Field(default=None, description="Electrical resistivity in Ω·m")
    permittivity: Optional[_PermittivityPF] = Field(default=None, description="Permittivity in F/m")
    permeability: Optional[_PermeabilityPF] = Field(default=None, description="Permeability in H/m")

    def to_elmer(self, *, at: Mapping[str, Quantity]) -> dict:
        d: dict = {}
        sigma: Optional[float] = _si(self.conductivity, U.S / U.m, at)
        if sigma is not None:
            d["Electric Conductivity"] = sigma
        eps: Optional[float] = _si(self.permittivity, U.F / U.m, at)
        if eps is not None:
            EPS0: float = 8.8541878128e-12  # F/m
            d["Relative Permittivity"] = eps / EPS0
        return d


class MaterialProperties(_PropertyModel):
    name: str = ""
    tag: str = ""
    mechanical: MechanicalProperties = Field(default_factory=MechanicalProperties)
    thermal: ThermalProperties = Field(default_factory=ThermalProperties)
    magnetic: MagneticProperties = Field(default_factory=MagneticProperties)
    electrical: ElectricalProperties = Field(default_factory=ElectricalProperties)

    def to_elmer(self, *, at: Mapping[str, Quantity]) -> dict:
        data: dict = {}
        data.update(self.mechanical.to_elmer(at=at))
        data.update(self.thermal.to_elmer(at=at))
        data.update(self.magnetic.to_elmer(at=at))
        data.update(self.electrical.to_elmer(at=at))
        return data

    @property
    def is_magnet(self) -> bool:
        # A magnet is a material with a remanence; |M| itself depends on the
        # operating point, so presence (not magnitude) is the kind test here.
        return self.magnetic.remanence is not None

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
