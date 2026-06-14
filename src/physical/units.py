import pint
from pint import Unit
from pint.delegates.formatter import Formatter
from pint.delegates.formatter._spec_helpers import split_format
from common.utils import COLORS

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

    @staticmethod
    def _tag(text: str, style: str) -> str:
        if not style or not text:
            return text
        return "[" + style + "]" + text + "[/" + style + "]"

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
        magnitude_str = self._tag(
            sub_fmt.format_magnitude(obj.magnitude, mspec, **babel_kwds),
            self.magnitude_style,
        )
        unit_str = self._style_unit(sub_fmt.format_unit(obj.unit_items(), uspec, sort_func=self.default_sort_func, **babel_kwds))
        return f"{magnitude_str} {unit_str}".strip()


U = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
U.formatter = RichEngineeringFormatter(registry=U)
