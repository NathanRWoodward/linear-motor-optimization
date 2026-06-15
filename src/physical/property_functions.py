"""
Material properties as pint-aware callables (doc 05).

A material property is not always a constant: remanence, conductivity, elastic modulus etc. can depend on temperature (and sometimes other quantities).
Every property is therefore modelled as a **callable taking zero or more named pint quantities and returning a pint quantity**, with three concrete kinds of increasing richness:

* :class:`Static`      – 0 parameters, a constant value.
* :class:`Calibration` – interpolation from sample points (1-D for now).
* :class:`ClosedForm`  – an explicit Python callable (pint-in / pint-out).

All three satisfy the :class:`PropertyFunction` protocol, so a property's *call site* never cares which kind it is.
The ``parameters`` mapping (name -> dimensionality string) *is* the schema: it tells a caller exactly what to pass and in what units, with no magic words (doc 06).

Why a Protocol *and* Pydantic models: the call contract is hot-path behaviour, expressed as a ``typing.Protocol``; the concrete carriers hold validated config data (a constant, calibration points, a formula) and so are Pydantic models with a shared validation base.
This mirrors the doc 06 split.
"""

from __future__ import annotations

from typing import Annotated, Any, Callable, Literal, Mapping, Protocol, runtime_checkable

import numpy as np
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic_core import core_schema

from physical.units import U, Quantity, dimensionality_matches

__all__ = [
    "PropertyFunction",
    "BasePropertyFunction",
    "Static",
    "CalibrationPoint",
    "Calibration",
    "ClosedForm",
    "PropertyError",
    "PropertyParameterError",
    "PropertyDimensionError",
    "PropertyRangeError",
    "property_function_type",
]


# ---------------------------------------------------------------------------
# Typed errors (doc 05 "request 4"): dedicated types, not bare ValueError, so callers can catch precisely and messages are actionable.
# ---------------------------------------------------------------------------


class PropertyError(Exception):
    """Base class for every property-function error."""


class PropertyParameterError(PropertyError):
    """A required parameter was not supplied when evaluating a property."""

    def __init__(self, fn: "PropertyFunction", missing: set[str]) -> None:
        self.fn: PropertyFunction = fn
        self.missing: set[str] = set(missing)
        wanted: str = ", ".join(f"{name}=<{dim or 'dimensionless'}>" for name, dim in fn.parameters.items())
        names: str = ", ".join(sorted(self.missing))
        super().__init__(f"{type(fn).__name__} requires [{wanted}]; not supplied: {names}.")


class PropertyDimensionError(PropertyError):
    """A supplied parameter had the wrong dimensionality."""

    def __init__(self, fn: "PropertyFunction", name: str, expected: str, got: Any) -> None:
        self.fn: PropertyFunction = fn
        self.name: str = name
        self.expected: str = expected
        self.got: Any = got
        super().__init__(f"{type(fn).__name__} parameter {name!r} expected {expected or 'dimensionless'}, got {got}.")


class PropertyRangeError(PropertyError):
    """A parameter fell outside the calibrated range and extrapolation is off."""

    def __init__(self, fn: "PropertyFunction", name: str, value: Any, low: Any, high: Any) -> None:
        self.fn: PropertyFunction = fn
        self.name: str = name
        super().__init__(f"{type(fn).__name__} parameter {name!r}={value} is outside the calibrated range [{low}, {high}]; set extrapolate=True to allow.")


# ---------------------------------------------------------------------------
# The callable contract.
# ---------------------------------------------------------------------------


@runtime_checkable
class PropertyFunction(Protocol):
    """
    A material property as a function of zero or more pint quantities.

    Calling it with the required parameters returns a pint Quantity in the property's own units.
    Parameters are passed by name and are themselves pint quantities, so callers cannot mix up argument order or units.
    """

    @property
    def parameters(self) -> Mapping[str, str]:
        """
        Required parameter name -> expected dimensionality (pint string).

        Empty for a :class:`Static` property. This IS the schema: it tells a caller exactly what to pass and in what units.
        """
        ...

    @property
    def result_dimensionality(self) -> str:
        """Dimensionality of the returned quantity, e.g. ``'[power]/[length]/[temperature]'``."""
        ...

    def __call__(self, **kwargs: Quantity) -> Quantity:
        """Evaluate. Raises a typed error if a required parameter is missing or has the wrong dimensionality."""
        ...


class BasePropertyFunction(BaseModel):
    """
    Pydantic base that implements parameter checking once.

    Subclasses declare ``parameters`` / ``result_dimensionality`` and implement ``_evaluate``; the shared ``__call__`` validates the supplied quantities against ``parameters`` (raising the typed errors above) and then delegates.
    Extra keyword arguments are ignored, so an operating point carrying more quantities than a given property needs (e.g. ``temperature`` passed to a Static property) is harmless.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def parameters(self) -> Mapping[str, str]:
        raise NotImplementedError

    @property
    def result_dimensionality(self) -> str:
        raise NotImplementedError

    def _check(self, kwargs: dict[str, Quantity]) -> None:
        missing: set[str] = set(self.parameters) - kwargs.keys()
        if missing:
            raise PropertyParameterError(self, missing=missing)
        for name, dim in self.parameters.items():
            q: Quantity = kwargs[name]
            if not isinstance(q, U.Quantity) or not q.check(dim):
                got: Any = q.dimensionality if isinstance(q, U.Quantity) else f"{type(q).__name__} (not a quantity)"
                raise PropertyDimensionError(self, name, expected=dim, got=got)

    def __call__(self, **kwargs: Quantity) -> Quantity:
        self._check(kwargs)
        return self._evaluate(**kwargs)

    def _evaluate(self, **kwargs: Quantity) -> Quantity:  # subclass fills in
        raise NotImplementedError

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.result_dimensionality or 'dimensionless'})"


def _as_quantity(v: Any) -> Quantity:
    """Coerce a value (Quantity / string / number) into a pint Quantity."""
    return v if isinstance(v, U.Quantity) else U.Quantity(v)


# ---------------------------------------------------------------------------
# 1) Static – the 0-parameter baseline.
# ---------------------------------------------------------------------------


class Static(BasePropertyFunction):
    """
    A constant property: zero parameters, always returns ``value``.

    This is the migration target for every current scalar property (``Static(value="8.7 W/(m*K)")``). It ignores any operating-point arguments.
    """

    value: Quantity

    @field_validator("value", mode="before")
    @classmethod
    def _coerce_value(cls, v: Any) -> Quantity:
        return _as_quantity(v)

    @property
    def parameters(self) -> Mapping[str, str]:
        return {}

    @property
    def result_dimensionality(self) -> str:
        return str(self.value.dimensionality)

    def _evaluate(self, **kwargs: Quantity) -> Quantity:
        return self.value

    def __str__(self) -> str:
        return f"{self.value}"


# ---------------------------------------------------------------------------
# 2) Calibration – interpolation from sample points (1-D for now).
# ---------------------------------------------------------------------------


class CalibrationPoint(BaseModel):
    """One measured sample: input quantities by name and the resulting output."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    inputs: dict[str, Quantity]
    output: Quantity

    @field_validator("inputs", mode="before")
    @classmethod
    def _coerce_inputs(cls, v: Any) -> dict[str, Quantity]:
        if not isinstance(v, Mapping):
            raise TypeError("CalibrationPoint inputs must be a mapping of name -> quantity")
        return {name: _as_quantity(value) for name, value in v.items()}

    @field_validator("output", mode="before")
    @classmethod
    def _coerce_output(cls, v: Any) -> Quantity:
        return _as_quantity(v)


def _interpolate_1d(x: float, xs: list[float], ys: list[float], method: str, fn: "Calibration", name: str, extrapolate: bool) -> float:
    """
    Interpolate ``ys`` at ``x`` over sorted-by-``xs`` samples.

    Shared numeric core so the unit handling in ``Calibration._evaluate`` stays separate from the interpolation maths. ``xs`` need not be pre-sorted.
    """
    order: list[int] = sorted(range(len(xs)), key=lambda i: xs[i])
    xs_sorted: list[float] = [xs[i] for i in order]
    ys_sorted: list[float] = [ys[i] for i in order]
    if not extrapolate and (x < xs_sorted[0] or x > xs_sorted[-1]):
        raise PropertyRangeError(fn, name, value=x, low=xs_sorted[0], high=xs_sorted[-1])
    if method == "linear":
        # np.interp clamps to the endpoints outside the range, which is exactly the desired behaviour once extrapolate=True has let us through.
        return float(np.interp(x, xs_sorted, ys_sorted))
    if method == "nearest":
        idx: int = min(range(len(xs_sorted)), key=lambda i: abs(xs_sorted[i] - x))
        return ys_sorted[idx]
    # "cubic" needs scipy and is parked (doc 04 parking lot) along with N-D.
    raise NotImplementedError(f"interpolation method {method!r} is not implemented yet (parked: see docs/architecture/04-roadmap.md)")


class Calibration(BasePropertyFunction):
    """
    A property defined by sample points and interpolated between them.

    1-D only for now (a single parameter, e.g. temperature); the signature already admits N-D so the call site does not change when N-D lands.
    Each point's inputs are validated against ``param_dims`` (by name and dimensionality) at construction, so a typo or unit mistake fails immediately rather than deep inside a solve.
    Out-of-range behaviour is explicit via ``extrapolate``.
    """

    param_dims: dict[str, str]
    points: list[CalibrationPoint]
    method: Literal["linear", "nearest", "cubic"] = "linear"
    extrapolate: bool = False

    @model_validator(mode="after")
    def _validate_points(self) -> "Calibration":
        # N-D calibration is parked (doc 04); enforce the 1-D limit up front.
        if len(self.param_dims) != 1:
            raise ValueError(f"Calibration is 1-D for now; got {len(self.param_dims)} parameters {sorted(self.param_dims)} (N-D is parked: docs/architecture/04-roadmap.md).")
        if not self.points:
            raise ValueError("Calibration needs at least one point.")
        output_dim: Any = self.points[0].output.dimensionality
        for point in self.points:
            if set(point.inputs) != set(self.param_dims):
                raise ValueError(f"calibration point inputs {sorted(point.inputs)} do not match declared parameters {sorted(self.param_dims)}.")
            for name, dim in self.param_dims.items():
                q: Quantity = point.inputs[name]
                if not q.check(dim):
                    raise PropertyDimensionError(self, name, expected=dim, got=q.dimensionality)
            if point.output.dimensionality != output_dim:
                raise ValueError(f"calibration point outputs have inconsistent dimensionality ({point.output.dimensionality} vs {output_dim}).")
        return self

    @property
    def parameters(self) -> Mapping[str, str]:
        return dict(self.param_dims)

    @property
    def result_dimensionality(self) -> str:
        return str(self.points[0].output.dimensionality)

    def _evaluate(self, **kwargs: Quantity) -> Quantity:
        (name, _dim), = self.param_dims.items()  # 1-D: exactly one parameter
        sample_x: Quantity = self.points[0].inputs[name]
        sample_y: Quantity = self.points[0].output
        x_unit: Any = sample_x.units
        out_unit: Any = sample_y.units
        xs: list[float] = [float(p.inputs[name].to(x_unit).magnitude) for p in self.points]
        ys: list[float] = [float(p.output.to(out_unit).magnitude) for p in self.points]
        x: float = float(kwargs[name].to(x_unit).magnitude)
        result: float = _interpolate_1d(x, xs, ys, self.method, self, name, self.extrapolate)
        return result * out_unit


# ---------------------------------------------------------------------------
# 3) ClosedForm – explicit Python callable (locked v1; doc 05).
# ---------------------------------------------------------------------------


class ClosedForm(BasePropertyFunction):
    """
    A property defined by an explicit Python callable, pint-in / pint-out.

    ``expression`` receives exactly the declared parameters by name and returns a pint Quantity, e.g. ``Br(T) = Br0 * (1 + alpha * (T - T0))``.
    The callable is code, not JSON-serializable — an accepted v1 trade-off (doc 05). A string/expression mini-language is parked (doc 04).
    """

    param_dims: dict[str, str]
    result_dim: str
    expression: Callable[..., Quantity]

    @property
    def parameters(self) -> Mapping[str, str]:
        return dict(self.param_dims)

    @property
    def result_dimensionality(self) -> str:
        return self.result_dim

    def _evaluate(self, **kwargs: Quantity) -> Quantity:
        args: dict[str, Quantity] = {name: kwargs[name] for name in self.param_dims}
        result: Quantity = self.expression(**args)
        if not isinstance(result, U.Quantity) or not result.check(self.result_dim):
            got: Any = result.dimensionality if isinstance(result, U.Quantity) else f"{type(result).__name__} (not a quantity)"
            raise PropertyDimensionError(self, "<result>", expected=self.result_dim, got=got)
        return result


# ---------------------------------------------------------------------------
# Pydantic field type: a property of a declared dimensionality.
#
# Mirrors physical.units.quantity_type, but the *value* is a PropertyFunction.
# A bare quantity / unit-string is coerced into a Static so the authoring style `thermal.conductivity = 8.7 * U.W/(U.m*U.K)` keeps working; a Static / Calibration / ClosedForm is accepted as-is.
# In every case the function's result dimensionality is validated against the field's declared dimensionality at construction (a wrong-dimensionality property fails here, not at solve time).
# ---------------------------------------------------------------------------


def _serialize_property_function(fn: PropertyFunction) -> Any:
    """
    Serialize a property-function field. Static round-trips through its unit string (matching quantity_type's format); richer kinds are returned as-is for in-session (python-mode) round-trips — JSON serialization of code-bearing forms is deferred (doc 05).
    """
    if isinstance(fn, Static):
        q: Quantity = fn.value
        return f"{q.magnitude} {q.units:~}"
    return fn


def property_function_type(dimensionality: str):
    """
    A :class:`PropertyFunction` constrained to ``dimensionality``, usable as a Pydantic field.
    Coerces bare quantities/strings into :class:`Static`, validates the function's result dimensionality, and exports the same unit-annotated JSON schema as ``quantity_type``.
    """

    class _PF:
        @classmethod
        def __get_pydantic_core_schema__(cls, source: Any, handler: Any) -> Any:
            def validate(v: Any) -> PropertyFunction:
                fn: PropertyFunction = v if isinstance(v, BasePropertyFunction) else Static(value=_as_quantity(v))
                if not dimensionality_matches(dimensionality, fn.result_dimensionality):
                    raise ValueError(f"expected property of dimensionality {dimensionality or 'dimensionless'}, got {fn.result_dimensionality}")
                return fn

            return core_schema.no_info_plain_validator_function(
                validate,
                serialization=core_schema.plain_serializer_function_ser_schema(_serialize_property_function),
            )

        @classmethod
        def __get_pydantic_json_schema__(cls, core: Any, handler: Any) -> dict:
            return {
                "type": "string",
                "x-unit-dimensionality": dimensionality,
                "description": f"pint quantity with dimensionality {dimensionality}",
            }

    return Annotated[Any, _PF]
