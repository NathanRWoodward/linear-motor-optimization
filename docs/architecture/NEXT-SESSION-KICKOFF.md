# Kickoff prompt — Phase 3 implementation

Phase 0 (typing backbone), Phase 1 (property functions), and Phase 2 (the body
half of the conditions refactor — the `Magnetization` condition) are **complete**
— **143 tests pass** under `uv run pytest`. Paste the block below to start the
next session, which begins **Phase 3** (solver validation, pulled early so
misconfig fails in CI instead of at ElmerSolver runtime).

---

We're continuing the restructure planned in `docs/architecture/`. **Phases 0–2
are done.** Phase 0 gave us the typing backbone (doc 06): materials are Pydantic
models with unit-validated pint quantities, a `Physics` enum, a single material
registry, and JSON-schema export. Phase 1 (doc 05) made every material property a
pint-aware callable behind one typed `PropertyFunction` protocol, evaluated at an
operating point via `to_elmer(*, at: Mapping[str, Quantity])`. Phase 2 (doc 02,
body half) introduced composable `Condition` objects: `EntityTag` now carries
**only** `tag` + `conditions: list[Condition]` (a Pydantic discriminated union
keyed by `kind`), the old scalar shim fields are gone, and `_wire_magnet_body`
consumes a `Magnetization` condition resolved via
`meshing.config.conditions_for(tags, physics, target)`.

Read these first, in order: `docs/architecture/README.md` (status table),
`03-solver-validation.md` (this phase), `04-roadmap.md` (sequencing, esp. Phase
3), and the top-level `README.md` (coding conventions — follow them). Skim
`06-typing-and-schema.md` (Pydantic-for-data / Protocol-for-callables split,
enums not magic strings) and `02-conditions-refactor.md` (the `conditions_for`
lookup and `Magnetization` you'll validate against). The plan is approved; don't
re-litigate the design — if something is genuinely underspecified, ask before
improvising.

Implement **Phase 3 — solver validation** (doc 03). Deliver it as one cohesive
change with passing tests under `uv run pytest`. Concretely:

1. **`PHYSICS_REQUIREMENTS` next to `PHYSICS_PRESETS` in `elmer/sim.py`.** Map
   each physics to the set of material `to_elmer()` keys its solvers need on
   every body. **Key it by the `Physics` enum, not strings** (no magic words):
   `{Physics.MAGNETOSTATICS: {"Relative Permeability"}, Physics.THERMAL:
   {"Heat Conductivity"}, Physics.ELECTROSTATICS: {"Relative Permittivity"}}`.
   (Verify the exact emitted keys against `physical/materials/properties.py` —
   thermal emits `"Heat Conductivity"`, electrical emits `"Relative Permittivity"`.)

2. **`SifWriter.validate()` covering checks 1–3 from doc 03 (the high-value ones).**
   Add a `validate: bool = True` parameter to `SifWriter.__init__` and call
   `self.validate()` at the end of `__init__` (after `_build_bodies`). Accumulate
   all problems into a list and raise a single `ValueError` listing every one, so
   a broken config fails fast at construction with a clear, region-pointing
   message. Cover:
   - **Required material properties.** For each group, evaluate
     `group.material.to_elmer(at=self.operating_point)` (Phase 1 signature — note
     the `at=`, doc 03's example predates it) and assert the required keys are
     present; else report `Body {group.name}: material {mat.name} missing
     {sorted(missing)} for physics '{self.physics.value}'`.
   - **Numeric sanity / unit stripping.** Every emitted material value must be
     `isinstance(v, (int, float, str))` — a leaked pint `Quantity` means a
     `to_elmer()` forgot to strip units. Report the offending key/material.
   - **Magnets have a direction.** For magnetostatics, every body whose material
     `is_magnet` must resolve a usable `Magnetization` (via
     `conditions_for(group.tags, Physics.MAGNETOSTATICS, ConditionTarget.BODY)`,
     a non-zero `direction`). This is exactly the
     `! Magnetization: MISSING DIRECTION TAG` case in `_wire_magnet_body` today —
     **promote it to a validation error** so a zero-field magnet can't slip
     through. (Leave the comment marker in the wiring for when `validate=False`.)

3. **Wire validation into the test suite.** Add the validation run to pytest so
   misconfig is caught in CI (doc 03 §"Goal"). Use the existing standalone
   fake-`PhysicalGroup` pattern (see `tests/elmer/test_sif_smoke.py`) so the
   tests stay pure-logic and run in the Linux sandbox.

**Corrections to doc 03 (written before Phases 0–2):**
- The class is **`elmer.sim.SifWriter`**, not `Generator`.
- `to_elmer()` is now **`to_elmer(*, at=...)`**; call it with
  `at=self.operating_point`. The doc's `group.material.to_elmer()` example omits
  this — don't copy it verbatim.
- "Magnet missing direction" is now a **`Magnetization` condition** resolved via
  `conditions_for`, not a scalar tag field. Reuse that helper; don't re-derive
  the lookup.
- `PHYSICS_REQUIREMENTS` is keyed by the **`Physics` enum** (the doc shows string
  keys).

**Defer (checks 4–5, doc 03):** body/boundary coverage warnings and the
per-solver keyword allow-list both need the Phase 4 `BoundaryGroup`s and/or are
explicitly low-priority warnings — leave them to Phase 5. Note this in
`04-roadmap.md` if you touch it.

Tests (add under `tests/elmer/`, mirror the existing layout): a magnetostatics
config whose material lacks `Relative Permeability` raises at `SifWriter(...)`
construction; a `to_elmer()` that leaks a pint quantity raises; a magnet body
with no `Magnetization` condition raises (and `validate=False` suppresses it,
falling back to the comment marker); a valid config passes silently. Keep all 143
existing tests green — note that `tests/elmer/test_sif_smoke.py` builds magnet
groups **with** a `Magnetization` condition, so they stay valid; the
`test_magnet_without_direction_emits_missing_marker` test must now pass
`validate=False` (or be updated to assert the new error).

Constraints / conventions to honour (from the plan, the project owner, and the
top-level `README.md`):
- ~100% type hints on parameters, returns, and locals (incl. the `problems` list
  and loop-derived values).
- **No magic words:** `PHYSICS_REQUIREMENTS` keyed by `Physics`; reuse
  `ConditionTarget` and `conditions_for` rather than open-coding tag iteration.
- Keep Phase 3 tests pure-logic (no gmsh / build123d) so they run in the Linux
  sandbox as well as on Windows.
- Phase 3 does **not** change any Pydantic model shape, so `docs/schema/*.json`
  should be unchanged — don't regenerate it unless a model actually changes.

**Done when:** a deliberately broken config raises a clear Python error at
`SifWriter(...)` construction, exercised by a pytest, and the existing smoke sif
still generates. When Phase 3 is green, stop and report what changed, then update
the **Status** column in `docs/architecture/README.md` (mark doc 03 implemented)
and the Phase 3 section of `04-roadmap.md`. We'll pick the next phase after that.

---

## Environment notes (carried over)

- `uv run pytest` is the harness (`pytest` + `pythonpath=["src"]` already wired).
  **143 tests currently pass.**
- The committed `docs/schema/*.json` is generated by `python -m schemas --out
  docs/schema` — it needs `src` on the path, so run it as `PYTHONPATH=src uv run
  python -m schemas --out docs/schema`. Regenerate and commit it **only** when a
  model's shape changes (Phase 3 does not). `.gitattributes` normalizes to LF;
  `Path.write_text` emits CRLF on Windows, so the working copy may show schema
  files as modified with only CRLF churn — `git checkout -- docs/schema/<file>`
  if the content is genuinely unchanged.
- The renamed pipeline classes are `meshing.Mesher` and `elmer.sim.SifWriter`.
- The `SifWriter` evaluates properties at
  `DEFAULT_OPERATING_POINT = {"temperature": 300 K}` (per-preset `operating_point`).
- Conditions live in `src/physical/conditions.py` (`Condition`, `Magnetization`,
  `FixedTemperature`, `HeatFlux`, `Convection`, `ConditionTarget`,
  `ConditionUnion`). The thermal carriers are data-only until Phase 5 wires the
  boundary loop.

## After Phase 3

Subsequent phases, each its own session/PR (see `04-roadmap.md` for full detail
and the dependency graph). **Two tracks open up once Phase 3 lands** — they are
independent given Phase 0, so pick by priority:

- **Physics track:** **Phase 4** — `BoundaryGroup` emission via adjacency
  (doc 01); reuses the relocated bbox/CoM helper in
  `meshing/geometry_utils.py`. Unblocks **Phase 5** — thermal/electrostatics
  boundary conditions end-to-end (docs 02+01): finishes the deferred boundary
  loop and deletes the `_wire_thermal_body` no-op stub.
- **Optimization track:** **Phase 6** — run lifecycle: `RunManifest` provenance +
  typed `Result` + run bundles + convergence/caching seam (doc 07). Only needs
  Phase 0, so it can jump ahead of 4–5 if parameter sweeps on the already-working
  magnetostatics path are the priority. Unblocks **Phase 7** — optimization seam
  + naive grid search + `Study` tracking (doc 08).
