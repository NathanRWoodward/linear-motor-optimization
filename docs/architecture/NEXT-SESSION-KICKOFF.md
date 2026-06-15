# Kickoff prompt — next phase (post Phase 3)

Phase 0 (typing backbone), Phase 1 (property functions), Phase 2 (conditions refactor — body half / `Magnetization`), and Phase 3 (solver validation) are **complete** — **150 tests pass** under `uv run pytest`, working tree clean. All `docs/architecture/` status lines, the README status table, the roadmap, and the top-level `README.md` were audited and are current as of this handoff.

**You are at a fork.** Two tracks are independent given Phase 0; pick by priority (see `04-roadmap.md` dependency graph):

- **Optimization track — Phase 6 (recommended).** Run lifecycle: `RunManifest` provenance + typed `Result` + run bundles + convergence/caching seam (doc 07). Only needs Phase 0, so it can jump ahead of the boundary work. This is the repo's stated north star (optimizing a motor), and it wraps the *already-working* magnetostatics path, so it delivers value without waiting on Phases 4–5. Unblocks **Phase 7** (optimization seam + naive grid search + `Study`, doc 08).
- **Physics track — Phase 4 (alternative).** `BoundaryGroup` emission via body adjacency (doc 01); reuses the relocated bbox/CoM helper in `meshing/geometry_utils.py`. Unblocks **Phase 5** — thermal/electrostatics boundary conditions end-to-end (docs 02 boundary half + 01), which finishes the deferred boundary loop and deletes the `_wire_thermal_body` no-op stub. Pick this if usable thermal/electrostatics runs matter more than parameter sweeps.

Paste the block below to start **Phase 6**. If you'd rather do the physics track, say so and read `01-boundaries.md` + the Phase 4 section of `04-roadmap.md` instead.

---

We're continuing the restructure planned in `docs/architecture/`. **Phases 0–3 are done** (150 tests pass under `uv run pytest`). Phase 0 gave the typing backbone (doc 06): materials are Pydantic models with unit-validated pint quantities, a `Physics` enum, a single material registry, JSON-schema export. Phase 1 (doc 05) made every material property a pint-aware callable behind one typed `PropertyFunction`, evaluated via `to_elmer(*, at: Mapping[str, Quantity])`. Phase 2 (doc 02, body half) introduced composable `Condition` objects (`EntityTag` carries `tag` + `conditions: list[Condition]`, a discriminated union; `_wire_magnet_body` consumes a `Magnetization` resolved via `meshing.config.conditions_for`). Phase 3 (doc 03) added `SifWriter.validate()` — cross-object material↔solver checks at construction.

Read these first, in order: `docs/architecture/README.md` (status table), `07-run-lifecycle.md` (this phase), `04-roadmap.md` (sequencing, esp. Phase 6 — note it only needs Phase 0 and wraps the working magnetostatics path), and the top-level `README.md` (coding conventions — follow them). Skim `06-typing-and-schema.md` (Pydantic-for-data / Protocol-for-callables split, enums not magic strings; the `quantity_type`/`Vec3Quantity` annotations the manifest and `Result` reuse) and `08-optimization-seam.md` (the consumer that will call your driver, so design the driver signature with it in mind). The plan is approved; don't re-litigate the design — if something is genuinely underspecified, ask before improvising.

Implement **Phase 6 — run lifecycle** (doc 07). Deliver it as one cohesive change with passing tests under `uv run pytest`. Keep all 150 existing tests green. Concretely (doc 07 §§1–4 + handoff checklist):

1. **`RunManifest`, `Result`, `MeshStats` Pydantic models** (doc 07 §1–3). Reuse the Phase 0 pint annotations (`quantity_type` / `Vec3Quantity` / the flux-density alias) so the manifest and result serialize for free. `RunManifest` embeds the full typed `MeshingConfig` + `Physics`. `Result` carries pint force/torque/field-max plus `residual`/`wall_time_s` and a `raw: dict` escape hatch.
2. **A result parser module: Elmer `.dat`/log → typed `Result`** (doc 07 §2). Prefer structured `SaveScalars`/`SaveData` `.dat` output over log scraping; fall back to log parsing only for what isn't exported. **Commit a small real Elmer output fixture** and test the parser against it — no live solver needed.
3. **`runs/<run_id>/` bundle convention + a thin driver** (doc 07 §1, §"How this interacts"). The driver assembles a run (mesh + sif + solve → parse `Result` → write `manifest.json` + `result.json`); the `Mesher`/`SifWriter` stay run-ignorant. This driver is exactly the unit the Phase 7 optimizer calls once per evaluation — design its signature accordingly.
4. **`cache_key` / `mesh_key` computed and stored** in the manifest (doc 07 §4). **Keys only — no skip/reuse execution** (deferred to the parking lot). `cache_key` = hash of result-affecting inputs (config + step + physics + code sha); `mesh_key` = geometry-only identity, invariant to non-geometry config changes.
5. **Optional per-region `mesh_size` + a convergence-ladder helper** (doc 07 §3). Add an optional `mesh_size` on the existing per-region tag machinery; a helper that re-runs one config at increasing refinement and reports when the quantity of interest (force) changes < tolerance, tracking `MeshStats` per run.

**Tests** (doc 07 §"Testing", pure-logic so they run in the Linux sandbox): `RunManifest`/`Result` round-trip (`model_dump` → `model_validate`) with pint quantities preserved; `cache_key` stable for identical configs, differs on a result-affecting field, *unchanged* by a cosmetic field like `notes`; the parser against the committed fixture yields the expected force/residual; `mesh_key` invariant to non-geometry changes. Keep the standalone fake-`PhysicalGroup` pattern (see `tests/elmer/test_sif_smoke.py`) for anything touching the generators.

**Constraints / conventions** (from the plan, the owner, and the top-level `README.md`):
- ~100% type hints on parameters, returns, and locals.
- **No magic words:** statuses are `Literal`s/enums; reuse `Physics`, the pint annotations, and existing tag machinery rather than re-deriving.
- **Build the seam, not the cathedral** (doc 07 §"Guiding constraint"): manifest = Pydantic model + directory convention, not a database; caching = keys now, skip/reuse logic later; convergence = a documented ladder, not adaptive remeshing.
- Keep tests pure-logic (no gmsh / build123d / live ElmerSolver) so they run in the sandbox.
- This phase **adds** Pydantic models (`RunManifest`/`Result`/`MeshStats`) and may add an optional `mesh_size` field — so `docs/schema/*.json` **will** change. Regenerate with `PYTHONPATH=src uv run python -m schemas --out docs/schema` and commit it. (`.gitattributes` normalizes to LF; `Path.write_text` emits CRLF on Windows, so `git checkout -- docs/schema/<file>` any file whose only diff is CRLF churn.)

**Defer to the parking lot** (doc 07 §4 + roadmap "Out of scope"): cache skip/reuse *execution*, mesh-reuse-across-solves, adaptive/error-driven remeshing. Compute the keys; don't act on them.

**Done when:** one solve (or a fixture-driven dry run) produces a self-describing `runs/<run_id>/` bundle with a typed, unit-carrying `Result` and a `RunManifest`, the parser is covered by a committed fixture test, and all keys are stored. When Phase 6 is green, stop and report what changed, then update the **Status** column in `docs/architecture/README.md` (mark doc 07 implemented), the Phase 6 section of `04-roadmap.md`, the top-level `README.md` status block, and **replace this kickoff doc** to stage **Phase 7** (doc 08).

---

## Environment notes (carried over)

- `uv run pytest` is the harness (`pytest` + `pythonpath=["src"]` already wired). **150 tests currently pass.**
- The committed `docs/schema/*.json` is generated by `python -m schemas --out docs/schema`; it needs `src` on the path, so run `PYTHONPATH=src uv run python -m schemas --out docs/schema`. Regenerate and commit **only** when a model's shape changes — **Phase 6 does change model shapes**, so regenerate it. CRLF caveat above.
- Pipeline classes are `meshing.Mesher` and `elmer.sim.SifWriter`. The `SifWriter` evaluates properties at `DEFAULT_OPERATING_POINT = {"temperature": 300 K}` (per-preset `operating_point`).
- Conditions live in `src/physical/conditions.py` (`Condition`, `Magnetization`, `FixedTemperature`, `HeatFlux`, `Convection`, `ConditionTarget`, `ConditionUnion`). The thermal carriers are data-only until Phase 5 wires the boundary loop.
- Phase 0 relocated a bbox/center-of-mass helper into `meshing/geometry_utils.py` for Phase 4 adjacency — not needed for Phase 6, noted for the alternative track.

## After Phase 6

- **Phase 7** — optimization seam + naive grid search + `Study` tracking (doc 08): `Parameterization` (point → `MeshingConfig`), an `Objective` Protocol + one concrete objective (maximize net force), `Study`/`StudyRecord` + `to_dataframe()`/`best()`, and a `GridSearch` walking the grid via the Phase 6 driver. Proven by a fake-driver test (no solve). **Needs Phase 6.**
- **Phases 4–5** (physics track) remain open and independent if usable thermal/electrostatics runs become the priority — see `04-roadmap.md`.
