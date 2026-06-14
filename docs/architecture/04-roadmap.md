# 04 — Roadmap

Phased sequencing for the restructure. Each phase is independently committable
and leaves the pipeline working. Ordered so that early phases unblock later ones
and deliver value before the largest piece (boundaries).

## Dependency graph

```
Phase 1: Magnetization condition  ──┐         (doc 02, body half)
                                    ├──► Phase 4: thermal/electrostatics BCs
Phase 2: Solver validation        ──┤              (docs 02+03 boundary half)
                                    │
Phase 3: BoundaryGroup emission   ──┘         (doc 01)
```

Phases 1 and 2 have no dependency on the boundary work and can land first. Phase
3 is the big structural change. Phase 4 is where thermal/electrostatics actually
become usable, and it needs 1+3.

---

## Phase 1 — Magnetization as a condition (small, high value)

**Doc:** [02-conditions-refactor.md](02-conditions-refactor.md) (body half only).
**Why first:** self-contained, removes the `magnetic_coercivity`-as-direction
hack immediately, and establishes the `Condition.to_elmer()` pattern the rest
builds on. No mesh changes.

- Add `Condition` base + `Magnetization`.
- Add `EntityTag.conditions`; deprecate the scalar shim fields.
- Switch `_wire_magnet_body` to consume a `Magnetization` condition.
- Tests: magnetization round-trips; existing magnetostatics smoke test still
  passes (update the test's tag setup to use `Magnetization`).

**Done when:** the dual-Halbach smoke sif is byte-comparable (modulo the cleaner
direction source) and no code reads `magnetic_coercivity` as a direction.

---

## Phase 2 — Solver validation (small, high value)

**Doc:** [03-solver-validation.md](03-solver-validation.md) (checks 1–3).
**Why early:** cheap, independent, and makes every later phase fail loudly
instead of silently. No mesh changes.

- Add `PHYSICS_REQUIREMENTS` + `Generator.validate()`.
- Promote "magnet missing direction" to an error.
- Tests for the three failure classes + a passing config.

**Done when:** a deliberately broken config raises a clear Python error at
`Generator(...)` construction.

---

## Phase 3 — BoundaryGroup emission via adjacency (large, structural)

**Doc:** [01-boundaries.md](01-boundaries.md).
**Why third:** biggest change; benefits from the condition + validation patterns
already in place. Respects the gmsh "all-or-nothing physical group" rule.

- Add `BoundaryGroup` to `meshing/generator.py`.
- Compute face→bodies adjacency; emit 2D groups covering **all** boundary faces.
- Store `self.boundary_groups`; document surface naming.
- Wire the magnetostatics far-field BC onto the air-box `__EXT` group (tightens
  the currently-implicit far field — a concrete, testable win for this phase).
- Tests: synthetic adjacency unit test; gmsh integration on a real STEP.

**Done when:** meshing a real STEP yields body groups (all volumes preserved) +
a complete set of surface groups, and the magnetostatic far-field BC targets a
real surface id.

---

## Phase 4 — Thermal & electrostatics become usable (medium)

**Docs:** [02](02-conditions-refactor.md) (boundary half) + [01](01-boundaries.md).
**Why last:** needs both conditions and boundary groups.

- Add `FixedTemperature`, `HeatFlux`, `Convection` conditions.
- Add the condition-driven boundary loop to `elmer/sim.py`; delete the thermal
  stub.
- Add validation checks 4–5 (boundary coverage, keyword allow-list warning).
- Tests + an end-to-end thermal sif on a real surface group.

**Done when:** a thermal run can be generated end-to-end with a fixed-temperature
and a convection BC on adjacency-derived surfaces, validated, and confirmed by a
short ElmerSolver smoke run.

---

## Cross-cutting: testing strategy

The Linux sandbox can't run the Windows gmsh build or the full CAD stack, so:

- **Pure-logic tests** (property/condition `to_elmer()`, adjacency partition,
  validation) use synthetic fixtures and run anywhere. Prioritize these.
- **gmsh integration tests** run where gmsh is available; gate them so the suite
  passes without it.
- Keep the standalone `smoke_test_sif.py` pattern (fake `PhysicalGroup`s) — it's
  the cheapest way to exercise the Elmer generator without a mesh.

## Status tracking

Update [README.md](README.md)'s status table as each phase merges. Suggested
commit granularity: one phase per PR, each with its tests.

## Out of scope (parking lot)

- Explicit build123d face labels / bbox overrides (escape hatch in doc 01) —
  build only when a real case needs a surface adjacency can't name.
- Transient / harmonic magnetics presets — cheap to add later; not blocked by
  this restructure.
- Full Elmer keyword schema validation — deliberately avoided (doc 03 non-goals).
- Coupled magneto-thermal multiphysics — unblocked after Phase 4, own design pass.
