# 05 — Property functions: properties as pint-aware callables

**Status: implemented (Phase 1).** New direction (request set 2). Depends on
the typing backbone in [06-typing-and-schema.md](06-typing-and-schema.md). Lives
in `physical/property_functions.py`; the material fields use the coercing
`property_function_type` so bare quantities still authorable as before.

## Goal

A material property is not always a constant. Thermal conductivity, remanence,
elastic modulus etc. depend on temperature (and sometimes other quantities). We
want every material property to be a **callable that takes zero or more named
pint quantities and returns a pint quantity**, with three concrete
implementations of increasing richness:

1. **Static** — 0 parameters, a constant value (the starting point; what we have
   today, lifted into the new shape).
2. **Calibration** — N parameters, defined by sample/interpolation points.
3. **ClosedForm** — N parameters, defined by an explicit formula.

All three share one typed interface, so a property's *call site* never cares
which kind it is.

## The callable contract (Protocol)

Property functions are on the hot path and don't need Pydantic; they need a
discoverable, typed signature. We express the contract as a `Protocol`
([06-typing-and-schema.md](06-typing-and-schema.md) explains why Protocol here
and Pydantic for config).

```python
# illustrative
from typing import Protocol, runtime_checkable, Mapping
from physical.units import Quantity   # pint Quantity alias (see doc 06)

@runtime_checkable
class PropertyFunction(Protocol):
    """A material property as a function of zero or more pint quantities.

    Calling it with the required parameters returns a pint Quantity in the
    property's own units. Parameters are passed by name and are themselves pint
    quantities, so callers cannot mix up argument order or units.
    """
    @property
    def parameters(self) -> Mapping[str, str]:
        """Required parameter name -> expected dimensionality (pint string).
        Empty for a Static property. This IS the schema: it tells a user exactly
        what to pass and in what units."""
        ...

    @property
    def result_dimensionality(self) -> str:
        """Dimensionality of the returned quantity, e.g. '[power]/[length]/[temperature]'."""
        ...

    def __call__(self, **kwargs: Quantity) -> Quantity:
        """Evaluate. Raises a typed error if a required parameter is missing or
        has the wrong dimensionality."""
        ...
```

Because `parameters` advertises name→dimensionality, the object is
self-documenting: an IDE/inspection (or a generated JSON schema) shows the user
"call me with `temperature=<[temperature]>`" without external docs. This is the
"schema tells the user how to use me" requirement applied to the dynamic part of
the system.

### Shared validation base

A small base class implements the parameter-checking once so the three concrete
types only implement evaluation:

```python
class BasePropertyFunction(BaseModel):     # pydantic model -> validated + schema
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _check(self, kwargs: dict[str, Quantity]) -> None:
        missing = set(self.parameters) - kwargs.keys()
        if missing:
            raise PropertyParameterError(self, missing=missing)
        for name, dim in self.parameters.items():
            q = kwargs[name]
            if not q.check(dim):
                raise PropertyDimensionError(self, name, expected=dim, got=q.dimensionality)

    def __call__(self, **kwargs: Quantity) -> Quantity:
        self._check(kwargs)
        return self._evaluate(**kwargs)

    def _evaluate(self, **kwargs: Quantity) -> Quantity:   # subclass fills in
        raise NotImplementedError
```

## 1) Static — the 0-parameter baseline

```python
class Static(BasePropertyFunction):
    value: Quantity                       # validated pint quantity (doc 06)
    @property
    def parameters(self): return {}
    @property
    def result_dimensionality(self): return str(self.value.dimensionality)
    def _evaluate(self, **kwargs) -> Quantity:
        return self.value

# usage: thermal.conductivity = Static(value="8.7 W/(m*K)")
# value()  ->  8.7 W/(m*K)
```

This is the migration target for every current scalar property. `to_elmer()`
calls the property with no args (or with a reference temperature) and strips to
SI — see "Integration" below.

## 2) Calibration — interpolation from sample points

For data like "conductivity measured at 20°C, 60°C, 100°C". One or more
parameters; points carry their own pint units.

```python
class Calibration(BasePropertyFunction):
    # parameter name -> dimensionality, declared up front (the schema)
    param_dims: dict[str, str]                  # e.g. {"temperature": "[temperature]"}
    points: list[CalibrationPoint]              # each: inputs={name: Quantity}, output: Quantity
    method: Literal["linear", "nearest", "cubic"] = "linear"

    @property
    def parameters(self): return self.param_dims
    def _evaluate(self, **kwargs) -> Quantity:
        # convert kwargs + points to a common unit, interpolate (1-D now;
        # N-D via scipy.interpolate.griddata later), return Quantity in output unit.
        ...
```

Design notes:
- **1-D first** (single parameter, e.g. temperature) using numpy interp; the type
  signature already allows N-D so the closed form of the API doesn't change when
  N-D lands.
- Points validate at construction: every point's inputs must match `param_dims`
  by name and dimensionality (Pydantic validator) — a typo is caught immediately,
  not at evaluation deep in a solve.
- Out-of-range behaviour is an explicit field (`extrapolate: bool` /
  `clamp`), not a silent default.

## 3) ClosedForm — explicit formula

For properties with a known analytic temperature dependence (e.g. linear
remanence falloff `Br(T) = Br0 * (1 + alpha*(T - T0))`).

```python
class ClosedForm(BasePropertyFunction):
    param_dims: dict[str, str]
    result_dim: str
    expression: Callable[..., Quantity]     # python callable, pint-in/pint-out
    # OR a safe string expression evaluated against the params (see below)

    @property
    def parameters(self): return self.param_dims
    @property
    def result_dimensionality(self): return self.result_dim
    def _evaluate(self, **kwargs) -> Quantity:
        return self.expression(**kwargs)
```

**Decision (locked):** `expression` is a **Python callable** (pint-in / pint-out).
Simplest, fully pint-aware, good for in-code material definitions. It is not
JSON-serializable (it's code) — that's an accepted trade-off for now. A
string/expression mini-language for config-file-defined formulas is explicitly
**deferred** to the parking lot ([04-roadmap.md](04-roadmap.md)) until a concrete
material-database / config-file use case demands it.

## Integration with `to_elmer()` and the rest

`MaterialProperties` sub-objects hold `PropertyFunction`s instead of raw
quantities. `to_elmer()` evaluates them at a reference operating point and strips
to SI:

```python
class ThermalProperties(BaseModel):
    conductivity: PropertyFunction | None = None
    def to_elmer(self, *, at: Mapping[str, Quantity]) -> dict:
        d = {}
        if self.conductivity is not None:
            q = self.conductivity(**self._args_for(self.conductivity, at))
            d["Heat Conductivity"] = float(q.to("W/(m*K)").magnitude)
        return d
```

Key points:
- `at` is the operating point (e.g. `{"temperature": 300*U.K}`) supplied by the
  Elmer generator / physics preset. Static properties ignore it; Calibration and
  ClosedForm consume it.
- For genuinely temperature-*dependent* Elmer runs, a later enhancement can emit
  Elmer's own tabular dependency syntax (`Heat Conductivity = Variable Temperature; Real ...`)
  by sampling the `PropertyFunction` across a range — the calibration points map
  almost directly onto Elmer's `Real` interpolation tables. Note this future path
  in the roadmap; first pass just evaluates at a fixed `at`.

## Errors (typed, graceful — request 4)

Dedicated exception types, not bare `ValueError`, so callers can catch precisely
and messages are actionable:

- `PropertyParameterError(fn, missing)` — "Calibration property needs
  `temperature` ([temperature]); not supplied."
- `PropertyDimensionError(fn, name, expected, got)` — "`temperature` expected
  [temperature], got [length]."

## Testing (lands with the feature — request 3)

In `tests/physical/` (pytest already wired via UV):
- `Static` returns its value; ignores extra kwargs or rejects them (decide).
- `Calibration` interpolates a known 2-point line exactly at endpoints and
  midpoint; rejects a point whose units mismatch `param_dims`.
- `ClosedForm` evaluates `Br(T)` and round-trips units.
- Missing/!wrong-dimension parameter raises the typed errors above.
- `to_elmer(at=...)` produces the right SI float for each kind.

## Handoff checklist

- [x] Land the typing backbone (doc 06: `Quantity` alias + `quantity_type`) first.
- [x] Add `PropertyFunction` Protocol + `BasePropertyFunction` + typed errors.
- [x] Implement `Static`; migrate one material (N52) end-to-end as proof.
- [x] Implement `Calibration` (1-D) + `ClosedForm` (Callable form).
- [x] Switch `*.to_elmer()` to evaluate at an `at` operating point.
- [x] Tests above, all passing under `uv run pytest`.
- [x] (Defer) N-D calibration, string-expression closed form, Elmer tabular
      dependency emission — noted as parking-lot in [04-roadmap.md](04-roadmap.md).
