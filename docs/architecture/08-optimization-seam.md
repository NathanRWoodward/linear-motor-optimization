# 08 — Optimization seam

**Status: planned, not implemented.** New direction (optimization round). Sits on
top of the pipeline ([06](06-typing-and-schema.md)) and the run lifecycle
([07-run-lifecycle.md](07-run-lifecycle.md)). Built last; it's the consumer, not
the foundation.

## Goal

Provide the thin layer that turns "free parameters → an objective number" into a
sequence of tracked pipeline runs — **without the pipeline knowing anything about
optimization**. The first consumer is deliberately a dumb grid search: it proves
the seam by exercising it end to end, with zero optimizer cleverness.

## The two interfaces

Keep the framework optimization-ignorant. The seam is just two typed contracts +
a driver call.

```python
# illustrative
class Parameterization(BaseModel):
    """The free variables and their ranges. Maps a point in parameter space to a
    concrete MeshingConfig. This is the ONLY thing that knows which knobs vary."""
    # e.g. fields like gap, magnet_thickness, pole_count, each a typed quantity/range
    def to_config(self, point: dict[str, float]) -> MeshingConfig: ...
    def space(self) -> dict[str, ParamSpec]: ...   # name -> bounds/choices (the schema)


class Objective(Protocol):
    """Result -> scalar to optimize. Pure, typed, trivially testable. Knows the
    physics goal (maximize force, minimize ripple, ...); knows nothing about how
    the Result was produced."""
    def __call__(self, result: Result) -> float: ...
```

`Parameterization` is Pydantic (it's config/data and benefits from schema +
validation); `Objective` is a `Protocol` (it's a pure callable). This mirrors the
"Pydantic for config, Protocol for callables" rule from
[06](06-typing-and-schema.md) — consistency, not new machinery.

The evaluation of one point is just:

```
point ─► Parameterization.to_config ─► driver (mesh+sif+solve, doc 07) ─► Result ─► Objective ─► scalar
```

The driver from [07](07-run-lifecycle.md) already returns a typed `Result` and
writes a `RunManifest`, so the optimizer inherits provenance for free.

## First consumer: naive grid search

No surrogate, no gradients, no Bayesian anything. Walk a grid, evaluate each
point through the pipeline, record everything. Its entire job is to **interact
with the pipeline, read the results, and efficiently track input/output/quantities
for later analysis.**

```python
class GridSearch(BaseModel):
    parameterization: Parameterization
    grid: dict[str, list[float]]        # name -> values to sweep
    objective: ...                      # an Objective

    def run(self, driver) -> "Study":
        study = Study(...)
        for point in itertools.product(*self.grid.values()):
            cfg = self.parameterization.to_config(point)
            result = driver.evaluate(cfg)      # writes its own run bundle (doc 07)
            study.record(point, result, self.objective(result))
        return study
```

Deliberately missing (and that's correct for v1): early stopping, adaptive
sampling, parallelism beyond "loop and maybe submit jobs," any optimizer. Those
slot in later behind the same `Objective`/driver seam without touching the
pipeline.

## The Study: tracked records for later analysis

The point of v1 is the **record**, not the search. A `Study` is the queryable
log of (inputs, outputs, quantities) across runs — the thing you actually analyze
afterward.

```python
class StudyRecord(BaseModel):
    point: dict[str, float]             # the parameter-space coordinate
    run_id: str                         # link to the full run bundle (doc 07)
    objective: float
    result: Result                      # typed quantities, units intact

class Study(BaseModel):
    records: list[StudyRecord]
    def to_dataframe(self): ...          # pandas/polars for analysis & plotting
    def best(self): ...                  # argmax/argmin objective
```

Because each record carries `run_id`, the study is a thin index over the
content-addressed run bundles — no data duplication, full traceability from a dot
on a plot back to the exact sif/mesh/geometry that produced it. `to_dataframe()`
is the bridge to whatever analysis/plotting you do (the units get stripped there,
at the boundary, per [06](06-typing-and-schema.md)).

## What stays out (anti-over-engineering)

- **No optimizer abstraction yet.** One concrete `GridSearch`. A generic
  `Optimizer` base appears only when a *second* strategy (random, Bayesian, CMA-ES
  via Optuna/Ax) actually exists to justify it — premature generality is how these
  frameworks rot.
- **No distributed-execution framework.** The driver call is a function; if you
  later want parallel/cluster execution, wrap that one call (joblib, a job queue),
  don't redesign the seam.
- **No DSL / config-file-driven studies.** Define studies in Python. Revisit only
  if non-coders need to launch sweeps.

## Testing (request 3)

- `Parameterization.to_config(point)` produces a valid `MeshingConfig` for grid
  corners; `space()` schema matches the grid keys.
- An `Objective` against a synthetic `Result` returns the expected scalar.
- `GridSearch.run` with a **fake driver** (returns canned `Result`s, no solve)
  produces a `Study` with one record per grid point and a correct `best()`.
- `Study.to_dataframe()` shape/columns; `run_id` links resolve.

The fake-driver test is the important one: it proves the whole seam (params →
config → result → objective → record) with zero gmsh/Elmer, runnable anywhere.

## Handoff checklist

- [ ] `Parameterization` (Pydantic) for the motor's free variables → `MeshingConfig`.
- [ ] `Objective` Protocol + one concrete objective (e.g. maximize net force).
- [ ] `Study` / `StudyRecord` + `to_dataframe()` + `best()`.
- [ ] `GridSearch` consuming the [07](07-run-lifecycle.md) driver.
- [ ] Fake-driver test for the full seam; objective/parameterization unit tests.
- [ ] Parking lot: real optimizers, parallel execution, study-as-config.
