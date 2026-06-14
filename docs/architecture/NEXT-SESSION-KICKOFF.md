# Kickoff prompt — Phase 0 implementation

Paste the block below to start the next session. It begins **Phase 0** (the
typing backbone), which everything else depends on.

---

We're implementing the restructure planned in `docs/architecture/`. Read these
first, in order: `README.md`, `06-typing-and-schema.md`, `04-roadmap.md`. Then
skim `00-assessment.md` for context. (The full set is docs 00–08 covering typing,
property functions, conditions, validation, boundaries, run lifecycle/provenance,
and the optimization seam — but Phase 0 below only needs 06 + the roadmap.) The
plan is approved; don't re-litigate the design — if you hit something genuinely
underspecified, ask before improvising.

Start with **Phase 0 — Typing backbone & de-duplication** (doc 06). Deliver it as
one cohesive change with passing tests under `uv run pytest`. Concretely:

1. Add `quantity_type(dimensionality)` plus named unit aliases (`Temperature`,
   `Conductivity`, `Density`, `FluxDensity`, an unconstrained `Quantity`, and any
   others the materials need) to `src/physical/units.py`. It must: validate
   dimensionality at construction, serialize to a unit string, and export JSON
   schema with the unit annotated. The approach is proven against pydantic 2.13 —
   see the code block in doc 06; reuse it.
2. Convert `MaterialProperties` and its sub-classes (`MechanicalProperties`,
   `ThermalProperties`, `MagneticProperties`, `ElectricalProperties`) to Pydantic
   v2 models using those aliases, so each field is self-documenting and a
   wrong-dimensionality value raises at construction. Keep the existing
   `to_elmer()` behaviour working (still emits bare SI floats). Update the three
   material definitions (`neodymium.py`, `air.py`, `pcb.py`) to the new shape.
3. Replace magic strings with discoverable types: a `Physics` enum and any
   `Literal`s, and purge the `physics="magnetostatics"` string handling in
   `src/elmer/sim.py` in favour of the enum.
4. De-duplicate: delete the dead `src/geometry/mesh.py`, relocating its
   per-entity bounding-box / center-of-mass extraction into a small reusable
   helper (it'll be reused by the Phase 4 adjacency code). Remove the hardcoded
   `known_materials` list; there should be a single material registry referenced
   by both stages. While here, resolve the `Generator` name collision
   (`meshing.Generator` vs `elmer.sim.Generator`) — rename to `Mesher` /
   `SifWriter` or namespace them, since the optimization driver will import both.
5. Expose `model_json_schema()` access for the config/material models (a small
   function or CLI entry is fine).

Tests (add under `tests/`, mirror the existing layout; pytest already works via
UV): wrong-dimensionality raises at construction; `model_json_schema()` includes
the unit annotation; an enum field rejects out-of-vocabulary input; a
`model_dump()` → `model_validate()` round-trip preserves quantities; and the
existing magnetostatics sif still generates correctly (port the standalone
`smoke_test_sif.py` pattern into a real pytest if it isn't already).

Constraints / preferences to honour (from the plan and the project owner):
- Strong, discoverable typing is a hard requirement — good types should make docs
  largely unnecessary, and incorrect usage should fail gracefully with a clear,
  typed error. No magic words where an enum/Literal will do.
- Pydantic for config/data; `typing.Protocol` for hot-path callables. Don't make
  the generators (behaviour) into Pydantic models.
- Don't force unification that reduces maintainability — dedupe only where it
  removes real duplication without coupling unrelated stages (doc 06's caveat).
- The Linux sandbox can't run the Windows gmsh build or the full CAD stack, so
  keep Phase 0 tests pure-logic (no gmsh/build123d imports) so they run anywhere.

When Phase 0 is green, stop and report what changed; we'll do Phase 1 (property
functions, doc 05) next. Update the Status column in `docs/architecture/README.md`
as you complete the phase.

---

## After Phase 0

Subsequent phases, each its own session/PR (see `04-roadmap.md` for full detail
and the dependency graph):

- **Phase 1** — property functions: `Static` → `Calibration` → `ClosedForm`
  (callable form; doc 05).
- **Phase 2** — `Magnetization` condition; remove the `magnetic_coercivity` hack (doc 02).
- **Phase 3** — solver validation in CI (doc 03).
- **Phase 4** — `BoundaryGroup` emission via adjacency (doc 01).
- **Phase 5** — thermal/electrostatics boundary conditions end-to-end (docs 02+01).
- **Phase 6** — run lifecycle: `RunManifest` provenance + typed `Result` + run
  bundles + convergence/caching seam (doc 07). Only needs Phase 0, so it can jump
  ahead of 4–5 if the optimization track is the priority.
- **Phase 7** — optimization seam + naive grid search + `Study` tracking (doc 08).

Note the two tracks after Phase 3: the **physics track** (4→5) and the
**optimization track** (6→7) are independent given Phase 0. If the near-term goal
is running parameter sweeps on the already-working magnetostatics path, do 6→7
before 4→5.
