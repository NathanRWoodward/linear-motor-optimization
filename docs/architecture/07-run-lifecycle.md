# 07 — Run lifecycle: provenance, results, convergence, caching

**Status: planned, not implemented.** New direction (run-lifecycle round). This
doc covers everything *around* a single solve. It exists because the repo's real
goal is **optimization** (see [08-optimization-seam.md](08-optimization-seam.md)),
and an optimization loop is only as trustworthy as its run bookkeeping.

## Guiding constraint: build the seam, not the cathedral

Every idea here is scoped to "the minimum that keeps the door open." A run
manifest is a Pydantic model + a directory convention, not a database. A
convergence check is a documented step, not an adaptive-remeshing engine. Caching
is a `cache_key` you compute now and *act on later*. The failure mode to avoid is
the project dying under its own infrastructure before it produces a single
optimized motor.

## 1. A run is an immutable, content-addressed artifact

Today a solve writes `case.sif` / `case.vtu` into a directory and forgets how it
got there. The moment you sweep parameters you need to answer "which inputs
produced this result?" — so every run becomes a self-describing bundle.

```python
# illustrative
class RunManifest(BaseModel):
    run_id: str                     # content hash of the inputs (see cache_key)
    created_at: datetime
    git_sha: str                    # code version that produced it
    elmer_version: str | None       # solver version (parse from log)
    config: MeshingConfig           # the FULL typed input — serializes for free (doc 06)
    physics: Physics
    mesh_stats: MeshStats           # element counts, sizes (see §3)
    status: Literal["ok", "diverged", "error"]
    notes: str = ""
```

Because the config is already Pydantic ([06](06-typing-and-schema.md)), the
manifest serializes to JSON with no extra work — that is a concrete payoff of the
typing backbone. Directory convention:

```
runs/
  <run_id>/
    manifest.json        # RunManifest
    case.sif
    geometry.step        # exact geometry used (or a hash + pointer)
    case.vtu             # results
    elmersolver.log
    result.json          # typed Result (see §2)
```

`run_id` is a hash of the *inputs that affect the result* (config + step +
physics + code version), giving content-addressing for free. Two identical
configs land in the same `run_id` → natural dedup hook for §4.

## 2. A typed result / post-processing layer (the return path)

The forward path (config → sif) is well-typed; the return path (vtu/log →
numbers) must be too, or a clean front end feeds a dirty back end. Replace
ad-hoc log-scraping (à la pyelmer's brittle `extract_results_logfile`) with one
module that parses Elmer outputs into validated objects.

```python
class Result(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    status: Literal["ok", "diverged", "error"]
    force: Vec3Quantity | None = None       # net force on the moving array (pint)
    torque: Vec3Quantity | None = None
    field_max: FluxDensity | None = None    # peak |B|, pint Tesla
    residual: float | None = None           # final linear/nonlinear residual
    wall_time_s: float | None = None
    raw: dict = {}                          # escape hatch for un-modelled scalars
```

Design notes:
- **Force/torque are the optimization quantities** for a motor; they come from the
  `MagnetoDynamicsCalcFields` "Calculate Nodal Forces" output. The parser owns the
  knowledge of *where* in the vtu/log/`.dat` they live — one place, tested.
- Prefer Elmer's `SaveScalars`/`SaveData` `.dat` outputs (structured) over log
  scraping where possible; fall back to log parsing only for what isn't exported.
- Results carry **pint quantities**, so downstream analysis keeps units to the
  boundary (strip to floats only in a hot inner loop — see [06](06-typing-and-schema.md)).
- `raw` keeps the layer from blocking progress when a new scalar appears before
  it's modelled.

## 3. Mesh convergence as a first-class concern

`MeshingConfig.global_mesh_size` is one number. For a Halbach motor the optimized
quantity (air-gap force) is most sensitive exactly where the mesh is easiest to
under-resolve (the gap). Optimizing against an unconverged mesh optimizes
discretization error.

Two cheap, high-value moves:

1. **Per-region mesh sizing.** Mesh refinement becomes a typed per-region concern
   reusing the existing tag machinery — e.g. an air-gap region carries a finer
   target size than the bulk. (`EntityTag`/condition already scopes per-region
   data; add an optional `mesh_size` there.)
2. **A convergence study as a documented step.** A helper that re-runs a single
   configuration at increasing refinement and reports when the quantity of
   interest (force) changes < tolerance between levels. Track `MeshStats`
   (element count, min/max size) per run so a sweep can later be audited for mesh
   consistency (coefficient-of-variation across runs is a known smell test).

```python
class MeshStats(BaseModel):
    element_count: int
    min_size: float
    max_size: float

class ConvergencePoint(BaseModel):
    refinement: float
    quantity: Quantity          # e.g. force magnitude
    delta_vs_previous: float | None
```

Not in scope: adaptive/error-driven remeshing. A manual refinement ladder + a
"have we converged?" check is enough to trust a number; build the fancy version
only if convergence ever becomes the bottleneck.

## 4. Caching / skip-work (plan the seam, act later)

Content-addressing (§1) gives the hook: if a run's `cache_key` already exists,
skip it. Bigger win — **mesh reuse**: when only material params or excitation
change, geometry didn't, so the mesh can be reused across solves. In a motor
sweep that's a large fraction of total cost.

```python
def cache_key(config, physics, code_sha) -> str: ...        # full-run identity
def mesh_key(geometry_step, mesh_settings) -> str: ...       # geometry-only identity
```

Compute both keys now and store them in the manifest. **Implement the skip/reuse
logic only when run counts make it hurt** — the keys are the cheap part, the
cache management is the part that can rot, so defer the latter.

## How this interacts with the rest

- The pipeline generators (`Mesher`, `SifWriter` — note the rename in
  [06](06-typing-and-schema.md)/§ naming) stay ignorant of runs; a thin **driver**
  assembles a run, invokes mesh + sif + ElmerSolver, parses the `Result`, writes
  the manifest. The framework stays reusable; the lifecycle lives above it.
- This driver is exactly what the optimization layer
  ([08](08-optimization-seam.md)) calls once per evaluation.

## Testing (request 3 — pytest via UV)

- `RunManifest` / `Result` round-trip (`model_dump` → `model_validate`) with pint
  quantities preserved.
- `cache_key` is stable for identical configs and differs when a result-affecting
  field changes (and *doesn't* change for a cosmetic field like `notes`).
- The result parser against a captured sample Elmer `.dat`/log fixture (commit a
  small real output) yields the expected force/residual — no live solver needed.
- `mesh_key` is invariant to non-geometry config changes.

## Handoff checklist

- [ ] `RunManifest`, `Result`, `MeshStats` Pydantic models (after Phase 0 typing).
- [ ] Result parser module: Elmer `.dat`/log → `Result`, with a committed fixture.
- [ ] `runs/<run_id>/` directory convention + a driver that writes the bundle.
- [ ] `cache_key` / `mesh_key` computed and stored (no skip logic yet).
- [ ] Optional per-region `mesh_size`; a convergence-ladder helper + `MeshStats`.
- [ ] Tests above under `uv run pytest`.
- [ ] Defer to parking lot: cache skip/reuse execution, adaptive remeshing.
