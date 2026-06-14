# 04 — Roadmap

Phased sequencing for the restructure. Each phase is independently committable,
ships with its tests (pytest is already wired via `uv run pytest`), and leaves
the pipeline working.

This roadmap was revised to reflect: **typing/schema as the backbone, property
functions, and validation pulled early** (request sets from the second planning
round).

## Dependency graph

```
Phase 0: Typing backbone + de-dup        (doc 06)  ── foundation for everything
   │
   ├─► Phase 1: Property functions       (doc 05)
   │
   ├─► Phase 2: Magnetization condition  (doc 02, body half)
   │
   ├─► Phase 3: Solver validation        (doc 03)   ← pulled earlier, runs in CI
   │
   └─► Phase 4: BoundaryGroup emission   (doc 01)
                    │
                    └─► Phase 5: thermal/electrostatics BCs (docs 02+01)
```

Phase 0 is new and comes first because the typed/pint-aware `quantity_type` and
the de-duplication underpin the property functions, the conditions, and the
validation. Validation (Phase 3) is deliberately early — once the typed config
exists it is cheap and guards every later phase.

---

## Phase 0 — Typing backbone & de-duplication (foundation)

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

**Doc:** [05-property-functions.md](05-property-functions.md). **Needs:** Phase 0.

- Add the `PropertyFunction` Protocol, `BasePropertyFunction`, typed errors.
- Implement `Static`; migrate N52 end-to-end as proof.
- Implement `Calibration` (1-D) and `ClosedForm` (Callable form).
- Switch `*.to_elmer()` to evaluate at an `at` operating point.

**Done when:** a material property can be a constant, a set of calibration
points, or a formula — all behind one typed call site — and `to_elmer(at=...)`
yields the right SI float for each. Tests in `tests/physical/` pass.

---

## Phase 2 — Magnetization as a condition

**Doc:** [02-conditions-refactor.md](02-conditions-refactor.md) (body half).
**Needs:** Phase 0. **Why here:** self-contained, removes the
`magnetic_coercivity`-as-direction hack, establishes the `Condition.to_elmer()`
pattern boundaries will reuse.

- `Condition` base + `Magnetization` (Pydantic, typed direction).
- `EntityTag.conditions`; deprecate the scalar shim fields.
- `_wire_magnet_body` consumes a `Magnetization` condition.

**Done when:** the dual-Halbach smoke sif is equivalent (cleaner direction
source) and nothing reads `magnetic_coercivity` as a direction.

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

- N-D calibration interpolation; string-expression closed form; emitting Elmer's
  native tabular temperature dependency from a `PropertyFunction` (doc 05).
- Explicit build123d face labels / bbox overrides for surfaces adjacency can't
  name (doc 01 escape hatch).
- Transient / harmonic magnetics presets.
- Full Elmer keyword schema validation (doc 03 non-goal).
- Coupled magneto-thermal multiphysics (own design pass after Phase 5).
