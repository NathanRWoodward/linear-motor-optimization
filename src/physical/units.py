import re

import pint
from pint import Unit
from pint.delegates.formatter import Formatter
from pint.delegates.formatter._spec_helpers import split_format
from common.utils import COLORS

_SCI_RE = re.compile(r"^(-?)(\d+\.?\d*)[eE][+]?(-?\d+)$")
_SUP_TABLE = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")

__all__ = ["U", "Unit"]


class RichEngineeringFormatter(Formatter):
    """Pint formatter that wraps quantity parts in Rich markup.

    Class-level style attributes control rendering:

        magnitude_style  Rich style for the numeric magnitude.
        unit_style       Rich style for each unit segment between '/' separators.
        slash_style      Rich style for the '/' division separators.

    Set any attribute to '' to leave that part unstyled.
    """

    default_format = ".5g~#P"

    # magnitude_style: str = "#FFB86C "
    # unit_style: str = "#8BE9FD"
    # slash_style: str = "#8BE9FD dim"
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
        return f"[{x}, {y}, {z}]"

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
