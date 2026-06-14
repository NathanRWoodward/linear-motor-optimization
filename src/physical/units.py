import re
from typing import Annotated

import pint
from pint import Unit
from pint.delegates.formatter import Formatter
from pint.delegates.formatter._spec_helpers import split_format
from pydantic_core import core_schema
from common.utils import COLORS

_SCI_RE = re.compile(r"^(-?)(\d+\.?\d*)[eE][+]?(-?\d+)$")
_SUP_TABLE = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")

__all__ = [
    "U",
    "Unit",
    "quantity_type",
    "Temperature",
    "Conductivity",
    "ThermalConductivity",
    "SpecificHeat",
    "Density",
    "FluxDensity",
    "FieldStrength",
    "Pressure",
    "HeatFlux",
    "HeatTransferCoefficient",
    "ElectricalConductivity",
    "Resistivity",
    "Permittivity",
    "Permeability",
    "Dimensionless",
    "Quantity",
]


class RichEngineeringFormatter(Formatter):
    """Pint formatter that wraps quantity parts in Rich markup."""

    default_format = ".5g~#P"

    magnitude_style: str = COLORS.MAGNITUDE
    unit_style: str = COLORS.UNITS + " bold"
    slash_style: str = COLORS.UNITS + " "
    x_style: str = "#FC7B7B"
    y_style: str = "#7EF19B"
    z_style: str = "#58C2DA"

    @staticmethod
    def _tag(text: str, style: str) -> str:
        if not style or not text:
            return text
        return "[" + style + "]" + text + "[/" + style + "]"

    @staticmethod
    def _pretty_sci(s: str) -> str:
        """Ensure scientific notation uses unicode superscripts (fixes pint's negative-value gap)."""
        m = _SCI_RE.match(s.strip())
        if not m:
            return s
        sign, coef, exp = m.groups()
        exp_pretty = str(int(exp)).translate(_SUP_TABLE)
        return f"{sign}{coef}×10{exp_pretty}"

    def _format_vec3_magnitude(self, vec3, mspec: str, sub_fmt, **babel_kwds) -> str:
        def fmt(val):
            return self._pretty_sci(sub_fmt.format_magnitude(val, mspec, **babel_kwds))

        x = self._tag(fmt(vec3.x), self.x_style)
        y = self._tag(fmt(vec3.y), self.y_style)
        z = self._tag(fmt(vec3.z), self.z_style)
        return f"<{x}, {y}, {z}>"

    def _style_unit(self, unit_str: str) -> str:
        if not unit_str:
            return unit_str
        slash = self._tag("/", self.slash_style)
        segments = unit_str.split("/")
        return slash.join(self._tag(seg, self.unit_style) for seg in segments)

    def format_quantity(self, quantity, spec: str = "", **babel_kwds) -> str:
        spec = spec or self.default_format
        if "#" in spec:
            spec = spec.replace("#", "")
            mag = quantity.magnitude
            if hasattr(mag, "x") and hasattr(mag, "y") and hasattr(mag, "z"):
                try:
                    scalar_proxy = self._registry.Quantity(abs(mag), quantity.units)
                    obj = quantity.to(scalar_proxy.to_compact().units)
                except Exception:
                    obj = quantity
            else:
                try:
                    obj = quantity.to_compact()
                except Exception:
                    obj = quantity
        else:
            obj = quantity
        sub_fmt = self.get_formatter(spec)
        mspec, uspec = split_format(spec, self.default_format, self._registry.separate_format_defaults)
        mag = obj.magnitude
        if hasattr(mag, "x") and hasattr(mag, "y") and hasattr(mag, "z"):
            magnitude_str = self._format_vec3_magnitude(mag, mspec, sub_fmt, **babel_kwds)
        else:
            magnitude_str = self._tag(
                sub_fmt.format_magnitude(mag, mspec, **babel_kwds),
                self.magnitude_style,
            )
        unit_str = self._style_unit(sub_fmt.format_unit(obj.unit_items(), uspec, sort_func=self.default_sort_func, **babel_kwds))
        return f"{magnitude_str} {unit_str}".strip()


U = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
U.formatter = RichEngineeringFormatter(registry=U)


def quantity_type(dimensionality: str):
    """A pint Quantity constrained to a dimensionality, usable as a Pydantic field."""

    class _Q:
        @classmethod
        def __get_pydantic_core_schema__(cls, source, handler):
            def validate(v):
                q = v if isinstance(v, U.Quantity) else U.Quantity(v)
                if not q.check(dimensionality):
                    raise ValueError(f"expected dimensionality {dimensionality}, got {q.dimensionality}")
                return q

            return core_schema.no_info_plain_validator_function(
                validate,
                serialization=core_schema.plain_serializer_function_ser_schema(lambda q: f"{q.magnitude} {q.units:~}"),
            )

        @classmethod
        def __get_pydantic_json_schema__(cls, core, handler):
            return {
                "type": "string",
                "x-unit-dimensionality": dimensionality,
                "description": f"pint quantity with dimensionality {dimensionality}",
            }

    return Annotated[U.Quantity, _Q]


Temperature = quantity_type("[temperature]")
ThermalConductivity = quantity_type("[power]/[length]/[temperature]")
Conductivity = ThermalConductivity
SpecificHeat = quantity_type("[energy]/[mass]/[temperature]")
Density = quantity_type("[mass]/[length]**3")
FluxDensity = quantity_type("[mass]/[current]/[time]**2")
FieldStrength = quantity_type("[current]/[length]")
Pressure = quantity_type("[pressure]")
HeatFlux = quantity_type("[power]/[length]**2")
HeatTransferCoefficient = quantity_type("[power]/[length]**2/[temperature]")
ElectricalConductivity = quantity_type("[current]**2*[time]**3/[mass]/[length]**3")
Resistivity = quantity_type("[mass]*[length]**3/[current]**2/[time]**3")
Permittivity = quantity_type("[current]**2*[time]**4/[mass]/[length]**3")
Permeability = quantity_type("[mass]*[length]/[current]**2/[time]**2")
Dimensionless = quantity_type("")
Quantity = U.Quantity
