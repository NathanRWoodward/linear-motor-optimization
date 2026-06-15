# 03 — Solver validation: catch errors before ElmerSolver does

**Status: planned, not implemented.** Addresses [00-assessment.md](00-assessment.md) #3. **Sequencing:** pulled early in the [roadmap](04-roadmap.md) (Phase 3). Once the typed/Pydantic config from [06-typing-and-schema.md](06-typing-and-schema.md) exists, much of this is nearly free — field-level validation happens at construction, and this doc covers the cross-object checks Pydantic can't see (material ↔ solver requirements). Wire it into `uv run pytest` so misconfig is caught in CI, not at solve time.

## Problem

`SOLVER_LIBRARY` / `PHYSICS_PRESETS` in `elmer/sim.py` are raw dicts. Maximum flexibility, zero safety: a typo'd keyword, a body whose material is missing a required property, or an unstripped unit only surfaces when ElmerSolver fails — often with an opaque message, and expensively if it happens deep inside an optimization loop.

## Goal

Add a lightweight, opt-in validation pass that runs when the Elmer `Generator` is constructed, so misconfigurations fail fast with a clear Python error pointing at the offending region/material/keyword.

This is intentionally *not* a full Elmer keyword schema (that would be a large, brittle undertaking). It targets the few error classes that actually bite.

## What to validate

1. **Required material properties per physics.** Each preset declares the material keywords its solvers need on every body:

   ```python
   PHYSICS_REQUIREMENTS = {
       "magnetostatics": {"Relative Permeability"},
       "thermal":        {"Heat Conductivity"},
       "electrostatics": {"Relative Permittivity"},
   }
   ```

   On build, for each body, assert its material's `to_elmer()` output contains the required keys; otherwise raise `f"Body {group.name}: material {mat.name} missing {missing} required by physics {physics}"`.

2. **Magnets have a direction.** For magnetostatics, every body whose material `is_magnet` must resolve a magnetization direction (a `Magnetization` condition once doc 02 lands; the tag today). Today this silently emits a `! Magnetization = MISSING DIRECTION TAG` comment — promote it to an error (or an explicit opt-in warning) so a zero-field magnet can't slip through.

3. **Numeric sanity / unit stripping.** All material and condition values handed to pyelmer must be plain numbers or strings, never pint quantities. A quantity leaking through means a `to_elmer()` forgot to strip units. Assert `isinstance(v, (int, float, str))` for every emitted value.

4. **Body/boundary coverage (once doc 01 lands).** Warn if a boundary group that adjacency produced has no condition attached under the active physics and is not the air-box far field — usually a sign a BC was forgotten.

5. **Keyword allow-list (optional, low priority).** Maintain a per-solver set of known keywords and warn (not error) on anything outside it, to catch typos like `Magnetisation` vs `Magnetization`. Kept as a warning because Elmer has many valid keywords and the list will never be complete.

## Where it lives

A `validate()` method on `elmer.sim.Generator`, called at the end of `__init__` behind a `validate: bool = True` flag so it can be turned off for experiments:

```python
def __init__(self, config, physical_groups=None, physics="magnetostatics", validate=True):
    ...
    self._build_bodies()
    if validate:
        self.validate()

def validate(self) -> None:
    problems: list[str] = []
    required = PHYSICS_REQUIREMENTS.get(self.physics, set())
    for group in self.physical_groups:
        emitted = group.material.to_elmer()
        missing = required - emitted.keys()
        if missing:
            problems.append(f"Body {group.name}: material {group.material.name} "
                            f"missing {sorted(missing)} for physics '{self.physics}'")
        for k, v in emitted.items():
            if not isinstance(v, (int, float, str)):
                problems.append(f"Material {group.material.name}: '{k}' is {type(v).__name__}, "
                                f"expected stripped number (unit not converted?)")
    if problems:
        raise ValueError("Solver configuration invalid:\n  - " + "\n  - ".join(problems))
```

## Non-goals

- Full Elmer `.sif` schema validation.
- Validating solver *numerics* (tolerances, iteration counts) — those are tuning, not correctness.
- Replacing actually running a quick ElmerSolver smoke job, which remains the ground truth.

## Handoff checklist

- [ ] Add `PHYSICS_REQUIREMENTS` next to `PHYSICS_PRESETS`.
- [ ] Add `Generator.validate()` covering checks 1–3 (the high-value ones).
- [ ] Promote the "magnet missing direction" comment to a validation error.
- [ ] Add checks 4–5 after [01-boundaries.md](01-boundaries.md) lands.
- [ ] Tests: a config missing `Relative Permeability` raises; a pint quantity leaking into `to_elmer()` raises; a valid config passes silently.
