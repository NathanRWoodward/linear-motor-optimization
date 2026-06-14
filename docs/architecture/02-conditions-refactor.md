# 02 — Conditions: replace the overloaded `EntityTag`

**Status: body half implemented (Phase 2); boundary half deferred to Phase 5.**
Addresses [00-assessment.md](00-assessment.md) #2. **Builds on:** the typing
backbone in [06-typing-and-schema.md](06-typing-and-schema.md) — `Condition`
subclasses are Pydantic models with typed, schema-exporting fields, and
`physics`/`target` are enums, not magic strings.

## Problem

`EntityTag` (in `meshing/config.py`) had become a god object: a flat bag of
optional scalars, one per solver knob, most of them `None` for any given region.

```python
class EntityTag:
    tag: str
    fixed_temperature: float        # thermal BC
    fixed_heat_flux: float          # thermal BC
    magnetic_coercivity: Vec3       # (ab)used as magnetization DIRECTION
```

Issues:

- Most fields are `None` for any given region.
- The link between a field and the solver that consumes it is implicit.
- `magnetic_coercivity` was doing double duty as the magnetization-direction
  carrier — a semantic hack (Phase 0 replaced it with an interim
  `magnetization_direction: Vec3` field; Phase 2 replaced *that* with a
  `Magnetization` condition).
- Adding a solver means adding more rarely-used fields (current density,
  emissivity, contact conductance, …), worsening the grab-bag.

## Goal

Make a region's conditions **composable, self-describing, and solver-scoped**,
reusing the `to_elmer()` pattern that already works for materials — applied now
to body forces, initial conditions, and boundary conditions.

## Design: condition objects (as implemented)

A region's physics is a list of small condition objects. Each condition knows
(a) which solver/physics it belongs to (`physics`, a `Physics` enum member),
(b) whether it applies to a body or a boundary (`target`, a `ConditionTarget`
enum), and (c) how to emit its own Elmer keywords (`to_elmer`). Each subclass
also carries a `kind` discriminator so a polymorphic `list[Condition]` round-trips
through `model_dump()` / `model_validate()` and exports clean JSON schema via a
Pydantic discriminated union (`ConditionUnion`).

```python
# src/physical/conditions.py (abridged)
class ConditionTarget(StrEnum):
    BODY = "body"
    BOUNDARY = "boundary"


class Condition(BaseModel):
    physics: Physics
    target: ConditionTarget
    def to_elmer(self, *args, **kwargs) -> dict: ...   # subclass-specific


class Magnetization(Condition):
    kind: Literal["magnetization"] = "magnetization"
    physics: Physics = Physics.MAGNETOSTATICS
    target: ConditionTarget = ConditionTarget.BODY
    direction: Vec3Field                               # normalized before use
    def to_elmer(self, magnitude: float) -> dict[str, str]:
        m = self.direction.normalized() * magnitude    # |M| from the material
        return {"Magnetization 1": f"{m.x:.6g}", "Magnetization 2": f"{m.y:.6g}",
                "Magnetization 3": f"{m.z:.6g}"}


class FixedTemperature(Condition):   # kind="fixed_temperature", thermal, boundary
    value: Temperature
    def to_elmer(self) -> dict[str, float]: return {"Temperature": _si(self.value, U.K)}

class HeatFlux(Condition):           # kind="heat_flux", thermal, boundary
    value: HeatFluxQuantity
    def to_elmer(self) -> dict[str, float]: return {"Heat Flux": _si(self.value, U.W / U.m**2)}

class Convection(Condition):         # kind="convection", thermal, boundary
    coefficient: HeatTransferCoefficient
    ext_temperature: Temperature
    def to_elmer(self) -> dict[str, float]: ...
```

### How a region declares conditions

`EntityTag` keeps its `tag` string (still parsed from build123d names) and
carries `conditions: list[ConditionUnion]` — **and nothing else**. There are no
flat scalar fields and no deprecation shims: a region's physics is authored one
way only.

```python
tag_mag_n = EntityTag(tag="Mag_N", conditions=[Magnetization(direction=Vec3(0, 1, 0))])
tag_hot   = EntityTag(tag="HotFace", conditions=[FixedTemperature(value="350 K")])
```

### How the generators consume conditions

- **Mesher** is unchanged in spirit — it still resolves which `EntityTag`s apply
  to each region by name parsing, and reports them on the `PhysicalGroup`.
- **Elmer generator** filters by `(physics, target)` via the
  `meshing.config.conditions_for(tags, physics, target)` helper:

```python
# body forces / body data — implemented for magnetostatics:
for cond in conditions_for(group.tags, Physics.MAGNETOSTATICS, ConditionTarget.BODY):
    if isinstance(cond, Magnetization):
        M = group.material.magnetic.magnetization_magnitude(at=self.operating_point)
        body.body_force = elmer.BodyForce(self.sim, f"{group.name}_magnetization", cond.to_elmer(M))

# boundary conditions (on BoundaryGroups from doc 01) — DEFERRED to Phase 5:
# for bg in mesh.boundary_groups:
#     for cond in conditions_for(bg.tags, self.physics, ConditionTarget.BOUNDARY):
#         elmer.Boundary(sim, f"{bg.name}_{cond.kind}", [bg.id]).data.update(cond.to_elmer())
```

This removed the bespoke `_magnetization_direction` helper. `_wire_thermal_body`
is now a documented no-op: thermal conditions are boundary-target, so they will
be emitted by the boundary loop (Phase 5), not the body loop.

## Benefits

- A region carries only the conditions it actually has (no `None` soup).
- Each condition's Elmer mapping lives with the condition (mirrors materials).
- Adding a new BC type = adding one small class, no edits to the generator's
  core loop.
- Resolves the `magnetic_coercivity`-as-direction hack: `Magnetization.direction`
  is explicit and correctly named.

## What landed in Phase 2 (body half)

1. ✅ `Condition` base + `Magnetization`, `FixedTemperature`, `HeatFlux`,
   `Convection` in `src/physical/conditions.py`.
2. ✅ `EntityTag.conditions: list[ConditionUnion]` (discriminated union for
   round-trip + schema). The interim scalar fields and their helpers
   (`first_tag_value`, `overrides()`/`_OVERRIDE_FIELDS`) were removed.
3. ✅ `_wire_magnet_body` consumes a `Magnetization` condition via
   `conditions_for`.

## Deferred to Phase 5 (boundary half)

The *boundary* half is only useful once `BoundaryGroup`s exist
([01-boundaries.md](01-boundaries.md)). The thermal condition classes
(`FixedTemperature`, `HeatFlux`, `Convection`) exist and have round-trip tests,
but are **not emitted** yet:

- [ ] Add the condition-driven boundary loop in `elmer/sim.py` and delete the
      `_wire_thermal_body` no-op stub.
- [ ] Tests: assert the generator emits one `Boundary` per (boundary group ×
      condition).

## Handoff checklist

- [x] Add `Condition` base + `Magnetization`, `FixedTemperature`, `HeatFlux`,
      `Convection`.
- [x] Add `conditions: list[Condition]` to `EntityTag` (discriminated union);
      remove the interim scalar fields outright (greenfield — no shims).
- [x] Migrate `_wire_magnet_body` to consume a `Magnetization` condition.
- [ ] Once `BoundaryGroup`s exist (Phase 4), add the boundary-condition loop and
      delete the thermal stub (Phase 5).
- [x] Tests: round-trip each condition's `to_elmer()`; round-trip a
      `list[Condition]` via the discriminator.
