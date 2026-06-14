# Kickoff prompt — Phase 2 implementation

Phase 0 (typing backbone) and Phase 1 (property functions) are **complete** —
**134 tests pass** under `uv run pytest`. Paste the block below to start the next
session, which begins **Phase 2** (the body half of the conditions refactor:
the `Magnetization` condition).

---

We're continuing the restructure planned in `docs/architecture/`. **Phases 0 and
1 are done.** Phase 0 gave us the typing backbone (doc 06): materials are
Pydantic models with unit-validated pint quantities, a `Physics` enum, a single
material registry, and JSON-schema export. Phase 1 (doc 05) made every material
property a pint-aware callable (`Static` / `Calibration` / `ClosedForm`) behind
one typed `PropertyFunction` protocol, with typed errors and
`to_elmer(*, at: Mapping[str, Quantity])` evaluating at an operating point. Read
these first, in order: `docs/architecture/README.md` (status table),
`02-conditions-refactor.md` (this phase), `04-roadmap.md` (sequencing, esp.
Phase 2), and the top-level `README.md` (coding conventions — follow them). Skim
`06-typing-and-schema.md` (Pydantic-for-data / Protocol-for-callables split,
enums not magic strings) and `05-property-functions.md` (the `to_elmer(at=...)`
and `magnetization_magnitude(at=...)` shapes you'll call into). The plan is
approved; don't re-litigate the design — if something is genuinely
underspecified, ask before improvising.

Implement **Phase 2 — Magnetization as a condition** (doc 02, **body half
only**). Deliver it as one cohesive change with passing tests under
`uv run pytest`. Concretely:

1. **New module `src/physical/conditions.py`.** Add a `Condition` Pydantic base
   carrying `physics: Physics` (reuse `elmer.physics.Physics`, not a string) and
   a `target` that is an enum/`Literal["body","boundary"]` (no magic words), plus
   a `to_elmer(...)` method. Implement `Magnetization(Condition)` (target=body,
   physics=magnetostatics) with a typed `direction: Vec3Field` and
   `to_elmer(magnitude: float) -> dict` that scales the **normalized** direction
   by `magnitude` into `{"Magnetization 1/2/3": ...}` (use `Vec3.normalized()` /
   the existing vector ops, not open-coded math). Also add the thermal data
   carriers `FixedTemperature`, `HeatFlux`, `Convection` (target=boundary) with
   their `to_elmer()` — as **classes + round-trip tests only**; do **not** wire a
   boundary loop yet (that needs the Phase 4 `BoundaryGroup`s — see "Defer").
2. **Discriminated union for round-trip + schema.** A region will hold
   `conditions: list[Condition]`. For `model_dump()` → `model_validate()` to round
   trip and for clean JSON-schema export, give each subclass a discriminator
   (e.g. `kind: Literal["magnetization"]`) and use a Pydantic discriminated union.
   Get this right — it's the schema-as-deliverable requirement applied to the
   polymorphic list.
3. **`EntityTag.conditions: list[Condition]`** in `meshing/config.py`. Keep the
   existing scalar fields as **deprecated shims** so current configs/tests keep
   working: `magnetization_direction` should synthesize an equivalent
   `Magnetization` condition (this is the field to migrate — see the correction
   below). Provide a small helper to resolve "the conditions of (physics, target)
   that apply to a region" from `conditions` plus the shimmed scalars, living next
   to `first_tag_value` / `EntityTag.overrides()` rather than open-coded at the
   call site.
4. **Migrate `_wire_magnet_body` (`elmer/sim.py`)** to consume a `Magnetization`
   condition instead of reading `magnetization_direction` directly. The magnitude
   still comes from the material: `group.material.magnetic.magnetization_magnitude(at=self.operating_point)`
   (Phase 1 signature). Preserve the "magnet material but no direction" behaviour
   (the commented `! Magnetization: MISSING DIRECTION TAG` marker). This should
   let you delete the bespoke `_magnetization_direction` helper in favour of the
   uniform condition lookup.

**Important correction to doc 02:** that doc was written before Phase 0 and still
describes `magnetic_coercivity` being abused as the direction carrier. **That hack
is already gone** — Phase 0 introduced a clean interim `magnetization_direction:
Vec3Field` on `EntityTag` as the stepping stone. Phase 2 replaces **that interim
field** with the composable `Magnetization` condition. Don't go hunting for
`magnetic_coercivity`.

**Watch the ripple (important):** `tests/elmer/test_sif_smoke.py` builds
`EntityTag(tag="Mag_N", magnetization_direction=Vec3(0, 1, 0))` and asserts
`Magnetization 2 ≈ Br/μ₀` for the N-pointing magnet. That must stay green —
either through the deprecation shim or by migrating the test to
`conditions=[Magnetization(direction=Vec3(0, 1, 0))]` (do both: keep the shim
working AND add a condition-path test). Also touched: `_magnetization_direction`
and `first_tag_value(group.tags, "magnetization_direction")` in `elmer/sim.py`,
and `EntityTag.overrides()` / `_OVERRIDE_FIELDS` / `print_tree` (they enumerate
the scalar fields). Keep all 134 existing tests green.

Tests (add under `tests/physical/` for the condition logic, mirror the existing
layout): round-trip each condition's `to_elmer()`; `Magnetization.to_elmer(M)`
scales a non-unit direction correctly (normalizes first); `model_validate(
model_dump())` round-trips a `list[Condition]` via the discriminator; the smoke
sif emits the same `Magnetization 1/2/3` values through the condition path; the
missing-direction marker is preserved; and the `magnetization_direction` shim
yields an equivalent `Magnetization` condition.

Constraints / conventions to honour (from the plan, the project owner, and the
top-level `README.md`):
- **Pydantic for the condition data carriers** (doc 06); `Physics` enum + an
  enum/`Literal` for `target` — discoverable by autocomplete, checked statically.
- Each condition's Elmer mapping lives **with the condition** (mirrors materials'
  `to_elmer()`); the generator's job becomes a uniform filter-by-(physics,target)
  loop, not bespoke `_wire_*` methods.
- ~100% type hints on parameters, returns, and locals (incl. dict/list
  accumulators); reuse `Vec3` methods and the tag-lookup helpers rather than
  copy-pasting.
- Keep Phase 2 tests pure-logic (no gmsh / build123d imports) so they run in the
  Linux sandbox as well as on Windows.
- **Placement / import hygiene:** `elmer.physics` is import-light (no gmsh), so
  `physical/conditions.py` importing `from elmer.physics import Physics` is
  cycle-free. `meshing.config` and `elmer.sim` import the conditions; the
  conditions module must **not** import `meshing.config` or `elmer.sim`.

**Defer (parking lot — note in `04-roadmap.md` if you touch it):** the *boundary*
half — the condition-driven `elmer.Boundary` loop and deleting the
`_wire_thermal_body` stub — depends on the Phase 4 `BoundaryGroup`s and waits for
Phase 5. The thermal condition classes land now (data + tests) but are not yet
emitted. Also note that the `Convection` condition carries an external
temperature the current `convection_coefficient` scalar shim lacks, so that
thermal shim is best-effort until boundaries are wired.

When Phase 2 is green, stop and report what changed, then: regenerate and commit
`docs/schema/*.json` (the `EntityTag` shape changes — run `PYTHONPATH=src uv run
python -m schemas --out docs/schema`); update the **Status** column in
`docs/architecture/README.md` (mark doc 02 as body-half implemented) and the
Phase 2 section of `04-roadmap.md`. We'll pick the next phase after that.

---

## Environment notes (carried over)

- `uv run pytest` is the harness (`pytest` + `pythonpath=["src"]` already wired).
  **134 tests currently pass.**
- The committed `docs/schema/*.json` is generated by `python -m schemas --out
  docs/schema` — **note it needs `src` on the path**, so run it as `PYTHONPATH=src
  uv run python -m schemas --out docs/schema`. Regenerate and commit it when a
  model's shape changes (Phase 2 changes `EntityTag`). `.gitattributes` normalizes
  to LF; `Path.write_text` emits CRLF on Windows, so the working copy may show the
  three schema files as modified with only CRLF churn — `git checkout -- docs/schema`
  if the content is genuinely unchanged.
- The renamed pipeline classes are `meshing.Mesher` and `elmer.sim.SifWriter`.
- Phase 1 lives in `src/physical/property_functions.py`; material property fields
  use the coercing `property_function_type` (a bare quantity is auto-wrapped in a
  `Static`, so authoring like `air.thermal.conductivity = 0.0257 * U.W/(U.m*U.K)`
  still works). The `SifWriter` evaluates properties at
  `DEFAULT_OPERATING_POINT = {"temperature": 300 K}` (per-preset `operating_point`).

## After Phase 2

Subsequent phases, each its own session/PR (see `04-roadmap.md` for full detail
and the dependency graph):

- **Phase 3** — solver validation in CI (doc 03). Cheap now that the typed config
  exists; "magnet missing direction" becomes a typed error and is even cleaner
  once magnetization is a `Condition`. Guards every later phase.
- **Phase 4** — `BoundaryGroup` emission via adjacency (doc 01); reuses the
  relocated bbox/CoM helper in `meshing/geometry_utils.py`. Unblocks the boundary
  half of doc 02.
- **Phase 5** — thermal/electrostatics boundary conditions end-to-end (docs 02+01):
  finishes the deferred boundary loop and deletes the thermal stub.
- **Phase 6** — run lifecycle: `RunManifest` provenance + typed `Result` + run
  bundles + convergence/caching seam (doc 07). Only needs Phase 0, so it can jump
  ahead of 4–5 if the optimization track is the priority.
- **Phase 7** — optimization seam + naive grid search + `Study` tracking (doc 08).

Two tracks once Phase 3 lands: the **physics track** (4→5) and the
**optimization track** (6→7) are independent given Phase 0. If the near-term goal
is parameter sweeps on the already-working magnetostatics path, do 6→7 first.
