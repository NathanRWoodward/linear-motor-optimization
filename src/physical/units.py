import pint
from pint import Unit
from pint.delegates.formatter._spec_helpers import split_format
from pint.delegates.formatter.plain import DefaultFormatter
from pint.delegates.formatter._format_helpers import join_mu


__all__ = ["U", "Unit"]

_UNIT_STYLE = "bold cyan"


class RichEngineeringFormatter(DefaultFormatter):
    """Pint formatter that wraps unit strings in Rich markup."""

    default_format = ".5g~#P"

    def format_unit(self, unit, uspec="", sort_func=None, **babel_kwds) -> str:
        plain = super().format_unit(unit, uspec, sort_func, **babel_kwds)
        if not plain:
            return plain
        return f"[{_UNIT_STYLE}]{plain}[/{_UNIT_STYLE}]"

    def format_quantity(self, quantity, qspec="", sort_func=None, **babel_kwds) -> str:
        registry = self._registry
        mspec, uspec = split_format(qspec, registry.formatter.default_format, registry.separate_format_defaults)
        magnitude_str = self.format_magnitude(quantity.magnitude, mspec, **babel_kwds)
        unit_str = self.format_unit(quantity.unit_items(), uspec, sort_func, **babel_kwds)
        return join_mu("{} {}", magnitude_str, unit_str)


U = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
U.formatter = RichEngineeringFormatter(registry=U)
