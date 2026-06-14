# 04 — Roadmap

Phased sequencing for the restructure. Each phase is independently committable,
ships with its tests (pytest is already wired via `uv run pytest`), and leaves
the pipeline working.

This roadmap was revised across three planning rounds: **typing/schema as the
backbone, property functions, validation pulled early**, then **run lifecycle
(provenance + typed results) and an optimization seam** — because the repo's real
goal is optimizing a motor, and that needs run bookkeeping designed in, not
bolted on.

## Dependency graph

```
Phase 0: Typing backbone + de-dup        (doc 06)  ── foundation for everything
   │
   ├─► Phase 1: Property functions       (doc 05)
   │
   ├─► Phase 2: Magnetization condition  (doc 02, body half)
   │
   ├─► Phase 3: Solver validation        (doc 03)   ← pulled early, runs in CI
   │
   ├─► Phase 4: BoundaryGroup emission   (doc 01)
   │        │
   │        └─► Phase 5: thermal/electrostatics BCs (docs 02+01)
   │
   └─► Phase 6: Run lifecycle            (doc 07)   ← provenance + typed Result
            │
            └─► Phase 7: Optimization seam + grid search (doc 08)
```

Phase 0 comes first because the typed/pint-aware `quantity_type` and the
de-duplication underpin everything. Validation (Phase 3) is deliberately early —
cheap once the typed config exists, and it guards every later phase. The run
lifecycle (Phase 6) only needs Phase 0 (it consumes the typed config + the
existing magnetostatics generator) so it can land before the boundary work if the
optimization track is the priority. The optimization seam (Phase 7) is the
consumer that sits on top of a working pipeline + lifecycle.

---

## Phase 0 — Typing backbone & de-duplication (foundation)

**Status: ✅ COMPLETE.** Landed with 117 passing tests. Also added a
`Physics.LINEAR_ELASTICITY` mechanical scaffold (StressSolver preset) and
`Vec3.normalized()` / `meshing.config.first_tag_value()` utilities (review
follow-ups); coding conventions captured in the top-level `README.md`.

**Doc:** [06-typing-and-schema.md](06-typing-and-schema.md).
**Why first:** the `quantity_type` keystone (pint + Pydantic + JSON schema) and
the single-source-of-truth cleanup are prerequisites for property functions,
conditions, and schema export.

- Add `quantity_type` + named unit aliases to `physical/units.py` (verified
  working against pydantic 2.13).
- Convert `MaterialProperties` + sub-property classes to Pydantic models using
  the aliases (fields become self-documenting).
- Introduce the `Physics` enum and `Literal`s; purge magic strings from
  `elmer/sim.py`.
- Delete the dead `geometry/mesh.py`; relocate its bbox/center-of-mass helper for
  later reuse by adjacency (Phase 4).
- Establish the single material registry; remove the duplicate `known_materials`.
- Expose `model_json_schema()` access.

**Done when:** materials are Pydantic models, a wrong-dimensionality value raises
at construction, `model_json_schema()` emits unit-annotated schema, and no magic
physics strings remain. Existing magnetostatics smoke sif still generates.

---

## Phase 1 — Property functions (static → calibration → closed-form)

**Status: ✅ COMPLETE.** Landed with 134 passing tests (117 prior + 17 new in
`tests/physical/test_property_functions.py`). The magnetostatics smoke sif is
byte-unchanged and `docs/schema/*.json` is unchanged (the property fields
serialize through the same unit-string form as before).

**Doc:** [05-property-functions.md](05-property-functions.md). **Needs:** Phase 0.

- Added the `PropertyFunction` Protocol, `BasePropertyFunction` (shared parameter
  checking), and typed errors `PropertyParameterError` / `PropertyDimensionError`
  / `PropertyRangeError` in `physical/property_functions.py`.
- Implemented `Static`; migrated **N52 end-to-end** (its scalars are now explicit
  `Static(value=...)`). Air / FR4 keep bare-quantity authoring, which the new
  `property_function_type` field coerces into a `Static` — so both styles work
  and the field still validates dimensionality at construction.
- Implemented `Calibration` (1-D linear/nearest interpolation; points validated
  against `param_dims` at construction; out-of-range raises unless
  `extrapolate=True`) and `ClosedForm` (the locked Python-callable form,
  pint-in / pint-out).
- Switched `*.to_elmer()` to `to_elmer(*, at: Mapping[str, Quantity])`; the
  `SifWriter` threads an operating point from the physics preset
  (`DEFAULT_OPERATING_POINT = {"temperature": 300 K}`). `magnetization_magnitude`
  is now `magnetization_magnitude(at=...)` so a temperature-dependent remanence
  flows through correctly.

**Parking lot (deferred, see "Out of scope" below):** N-D calibration (1-D only —
construction rejects >1 parameter), the `"cubic"` interpolation method (needs
scipy; raises `NotImplementedError`), the string-expression closed form, and
emitting Elmer's native tabular temperature-dependency syntax by sampling a
`PropertyFunction`.

**Done when:** a material property can be a constant, a set of calibration
points, or a formula — all behind one typed call site — and `to_elmer(at=...)`
yields the right SI float for each. Tests in `tests/physical/` pass.

---

## Phase 2 — Magnetization as a condition

**Status: ✅ COMPLETE (body half).** Landed with 143 passing tests. The
magnetostatics smoke sif is equivalent through the new condition path.

**Doc:** [02-conditions-refactor.md](02-conditions-refactor.md) (body half).
**Needs:** Phase 0. **Why here:** self-contained, removes the
`magnetic_coercivity`-as-direction hack, establishes the `Condition.to_elmer()`
pattern boundaries will reuse.

- Added `src/physical/conditions.py`: `Condition` Pydantic base carrying
  `physics: Physics` and `target: ConditionTarget` (an enum, no magic words),
  plus `Magnetization` (typed `direction: Vec3Field`, `to_elmer(magnitude)`
  normalizes via `Vec3.normalized()` then scales) and the thermal data carriers
  `FixedTemperature` / `HeatFlux` / `Convection` (data + round-trip tests only —
  not yet emitted; the boundary loop is Phase 5).
- Each subclass carries a `kind` discriminator and the polymorphic list is a
  Pydantic discriminated union (`ConditionUnion`), so `EntityTag.conditions`
  round-trips through `model_dump()`/`model_validate()` and exports clean JSON
  schema.
- `EntityTag` now carries **only** `tag` + `conditions: list[ConditionUnion]`.
  The interim Phase-0 scalar shim fields (`magnetization_direction`,
  `fixed_temperature`, `fixed_heat_flux`, `convection_coefficient`) and the
  helpers that served them (`first_tag_value`, `EntityTag.overrides()` /
  `_OVERRIDE_FIELDS`) were **removed outright** — greenfield, one way to author a
  region's physics. `conditions_for(tags, physics, target)` is the uniform lookup.
- `_wire_magnet_body` consumes a `Magnetization` condition via `conditions_for`;
  the bespoke `_magnetization_direction` helper is gone.

**Parking lot (deferred):** the *boundary* half — the condition-driven
`elmer.Boundary` loop and deleting the `_wire_thermal_body` stub (now a documented
no-op, since thermal conditions are boundary-target) — needs the Phase 4
`BoundaryGroup`s and lands in Phase 5. The thermal condition classes exist now
but are not emitted.

**Done when:** the dual-Halbach smoke sif is equivalent (cleaner direction
source) and nothing reads `magnetic_coercivity` as a direction. ✅

---

## Phase 3 — Solver validation (pulled early, runs in CI)

**Doc:** [03-solver-validation.md](03-solver-validation.md). **Needs:** Phase 0
(typed config makes the checks trivial). **Why early:** cheap once typing exists,
and it makes every later phase fail loudly instead of at ElmerSolver runtime.

- `PHYSICS_REQUIREMENTS` + `Generator.validate()` (required props, magnet
  direction, unit-stripping/numeric sanity).
- Promote "magnet missing direction" to a typed error.
- Add the validation run to the test suite so misconfig is caught in CI.

**Done when:** a deliberately broken config raises a clear Python error at
`Generator(...)` construction, exercised by a pytest.

---

## Phase 4 — BoundaryGroup emission via adjacency (structural)

**Doc:** [01-boundaries.md](01-boundaries.md). **Needs:** Phase 0 (reuses the
relocated bbox/CoM helper).

- `BoundaryGroup` in `meshing/generator.py`.
- Face→bodies adjacency; emit 2D groups covering **all** boundary faces (respect
  the gmsh all-or-nothing physical-group rule).
- Wire the magnetostatics far-field BC onto the air-box `__EXT` group.
- Synthetic adjacency unit test + gmsh integration test (gated on gmsh).

**Done when:** meshing a real STEP preserves all bodies and yields a complete set
of named surface groups, and the far-field BC targets a real surface id.

---

## Phase 5 — Thermal & electrostatics become usable

**Docs:** [02](02-conditions-refactor.md) (boundary half) + [01](01-boundaries.md).
**Needs:** Phases 1–4.

- `FixedTemperature`, `HeatFlux`, `Convection` conditions.
- Condition-driven boundary loop in `elmer/sim.py`; delete the thermal stub.
- Validation checks for boundary coverage + keyword allow-list warning.
- End-to-end thermal sif on adjacency-derived surfaces + ElmerSolver smoke run.

**Done when:** a thermal run generates end-to-end with fixed-temperature and
convection BCs, validated, confirmed by a short solve.

---

## Phase 6 — Run lifecycle: provenance & typed results

**Doc:** [07-run-lifecycle.md](07-run-lifecycle.md). **Needs:** Phase 0 (typed
config serializes into the manifest for free). **Independent of Phases 4–5** — it
wraps the already-working magnetostatics path, so it can be sequenced right after
the early phases if optimization is the priority.

- `RunManifest`, `Result`, `MeshStats` Pydantic models.
- Result parser: Elmer `.dat`/log → typed `Result` (commit a small real fixture).
- `runs/<run_id>/` bundle convention + a thin **driver** (mesh + sif + solve →
  Result + manifest). The driver is the unit the optimizer calls.
- `cache_key` / `mesh_key` computed and stored (no skip logic yet).
- Optional per-region `mesh_size` + a convergence-ladder helper.

**Done when:** one solve produces a self-describing run bundle with a typed,
unit-carrying `Result`, and the parser is covered by a fixture test (no live
solver needed).

---

## Phase 7 — Optimization seam + naive grid search

**Doc:** [08-optimization-seam.md](08-optimization-seam.md). **Needs:** Phase 6
(the driver + typed Result) and Phase 0. **The consumer, built last.**

- `Parameterization` (Pydantic) mapping a parameter point → `MeshingConfig`.
- `Objective` Protocol + one concrete objective (e.g. maximize net force).
- `Study` / `StudyRecord` + `to_dataframe()` + `best()`.
- `GridSearch` walking the grid via the Phase 6 driver, recording every point.

**Done when:** a grid search runs end-to-end, each point producing a tracked
`StudyRecord` linked to its run bundle, and `Study.to_dataframe()` gives an
analyzable table. The full seam is proven by a fake-driver test (no solve).

---

## Cross-cutting: testing strategy

`uv run pytest` is the harness; `tests/` already works. Sandbox/CI can't run the
Windows gmsh build or the full CAD stack, so:

- **Pure-logic tests** (property functions, `to_elmer()`, adjacency partition,
  validation, schema export) use synthetic fixtures and run anywhere. Prioritize.
- **gmsh integration tests** run where gmsh exists; gate them so the suite passes
  without it.
- Keep the standalone fake-`PhysicalGroup` smoke pattern for the Elmer generator.

## Status tracking

Update [README.md](README.md)'s status table as each phase merges. One phase per
PR, each with tests.

## Out of scope (parking lot)

- N-D calibration interpolation; the `"cubic"` interpolation method (needs scipy;
  `linear`/`nearest` ship in Phase 1); string-expression closed form (callable
  form is the locked v1); emitting Elmer's native tabular temperature dependency
  from a `PropertyFunction` (doc 05).
- Explicit build123d face labels / bbox overrides for surfaces adjacency can't
  name (doc 01 escape hatch).
- Transient / harmonic magnetics presets.
- Full Elmer keyword schema validation (doc 03 non-goal).
- Coupled magneto-thermal multiphysics (own design pass after Phase 5).
- Cache skip/reuse execution and mesh-reuse-across-solves (keys computed in
  Phase 6; acting on them deferred until run counts hurt — doc 07 §4).
- Adaptive / error-driven remeshing (manual convergence ladder is enough — doc 07 §3).
- Real optimizers (random / Bayesian / CMA-ES via Optuna/Ax), parallel/distributed
  execution, and config-file-driven studies (doc 08). Grid search is v1; a generic
  `Optimizer` abstraction appears only when a second strategy justifies it.
