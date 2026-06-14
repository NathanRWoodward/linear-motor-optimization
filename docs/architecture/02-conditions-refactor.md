# 02 — Conditions: replace the overloaded `EntityTag`

**Status: planned, not implemented.** Addresses [00-assessment.md](00-assessment.md) #2.
**Builds on:** the typing backbone in [06-typing-and-schema.md](06-typing-and-schema.md)
— `Condition` subclasses are Pydantic models with typed, schema-exporting fields,
and `physics`/`target` are an enum/`Literal`, not magic strings.

## Problem

`EntityTag` (in `meshing/config.py`) is becoming a god object. Today:

```python
class EntityTag:
    tag: str
    fixed_temperature: float        # thermal BC
    fixed_heat_flux: float          # thermal BC
    magnetic_coercivity: Vec3       # currently (ab)used as magnetization DIRECTION
```

Issues:

- Most fields are `None` for any given region.
- The link between a field and the solver that consumes it is implicit.
- `magnetic_coercivity` is doing double duty as the magnetization-direction
  carrier — a semantic hack introduced to get magnetostatics working.
- Adding a solver means adding more rarely-used fields (current density,
  emissivity, contact conductance, …), worsening the grab-bag.

## Goal

Make a region's conditions **composable, self-describing, and solver-scoped**,
reusing the `to_elmer()` pattern that already works for materials — applied now
to body forces, initial conditions, and boundary conditions.

## Design: condition objects

Replace the flat fields with a list of small condition objects. Each condition
knows (a) which solver/physics it belongs to, (b) whether it applies to a body or
a boundary, and (c) how to emit its own Elmer keywords.

```python
# illustrative, not final
class Condition:
    """Base: a self-describing piece of physics attached to a region."""
    physics: str            # "magnetostatics" | "thermal" | "electrostatics"
    target: str             # "body" | "boundary"
    def to_elmer(self) -> dict: ...      # exact sif keyword dict


class Magnetization(Condition):
    physics = "magnetostatics"; target = "body"
    direction: Vec3                       # unit vector; magnitude from material
    def to_elmer(self, magnitude: float) -> dict:
        d = self.direction.normalized() * magnitude
        return {"Magnetization 1": d.x, "Magnetization 2": d.y, "Magnetization 3": d.z}


class FixedTemperature(Condition):
    physics = "thermal"; target = "boundary"
    value: float                          # K
    def to_elmer(self) -> dict:
        return {"Temperature": self.value}


class HeatFlux(Condition):
    physics = "thermal"; target = "boundary"
    value: float                          # W/m^2
    def to_elmer(self) -> dict:
        return {"Heat Flux": self.value}


class Convection(Condition):
    physics = "thermal"; target = "boundary"
    coefficient: float; ext_temperature: float
    def to_elmer(self) -> dict:
        return {"Heat Transfer Coefficient": self.coefficient,
                "External Temperature": self.ext_temperature}
```

### How a region declares conditions

A tag becomes a *named bundle of conditions* rather than a bag of optional
scalars:

```python
tag_mag_n = EntityTag("Mag_N", conditions=[Magnetization(direction=Vec3(0,0,1))])
tag_hot   = EntityTag("HotFace", conditions=[FixedTemperature(value=350)])
```

`EntityTag` keeps its `tag` string (still parsed from build123d names) and gains
`conditions: list[Condition]`. The legacy scalar fields can remain as deprecated
shims that construct the equivalent condition, so nothing breaks during
migration.

### How the generators consume conditions

- **Mesher** is unchanged in spirit — it still resolves which `EntityTag`s apply
  to each region by name parsing. It now also reports them on the `PhysicalGroup`
  (already does) and `BoundaryGroup`.
- **Elmer generator** filters by `physics` and `target`:

```python
# body forces / body data
for cond in [c for c in group.conditions if c.physics == self.physics and c.target == "body"]:
    if isinstance(cond, Magnetization):
        M = group.material.magnetic.magnetization_magnitude
        body.body_force = elmer.BodyForce(sim, f"{group.name}_mag", cond.to_elmer(M))

# boundary conditions (on BoundaryGroups from doc 01)
for bg in mesh.boundary_groups:
    for cond in [c for c in bg.conditions if c.physics == self.physics and c.target == "boundary"]:
        elmer.Boundary(sim, f"{bg.name}_{type(cond).__name__}", [bg.id]).data.update(cond.to_elmer())
```

This deletes the `_wire_thermal_body` / `_wire_magnet_body` special-casing in
favor of a uniform loop driven by condition type.

## Benefits

- A region carries only the conditions it actually has (no `None` soup).
- Each condition's Elmer mapping lives with the condition (mirrors materials).
- Adding a new BC type = adding one small class, no edits to the generator's
  core loop.
- Resolves the `magnetic_coercivity`-as-direction hack: `Magnetization.direction`
  is explicit and correctly named.

## Migration path (non-breaking)

1. Introduce `Condition` + subclasses alongside the existing fields.
2. Add `EntityTag.conditions`; make the old scalar fields construct conditions
   on access (deprecation shim) so current configs keep working.
3. Switch `elmer/sim.py` to the condition-driven loop; keep the old wiring behind
   a fallback until parity is confirmed by tests.
4. Update the project's material/tag configs to declare conditions directly.
5. Remove the deprecated scalar fields.

## Dependency

The *boundary* half of this is only useful once `BoundaryGroup`s exist
([01-boundaries.md](01-boundaries.md)). The *body* half (Magnetization) can land
independently and immediately removes the `magnetic_coercivity` hack — so this
doc can be partially implemented before doc 01.

## Handoff checklist

- [ ] Add `Condition` base + `Magnetization`, `FixedTemperature`, `HeatFlux`,
      `Convection` (start with these four).
- [ ] Add `conditions: list[Condition]` to `EntityTag`; keep scalar fields as
      deprecation shims.
- [ ] Migrate `_wire_magnet_body` to consume a `Magnetization` condition (drops
      the `magnetic_coercivity` reuse). Do this first — it is self-contained.
- [ ] Once `BoundaryGroup`s exist, add the boundary-condition loop and migrate
      the thermal stub.
- [ ] Tests: round-trip each condition's `to_elmer()`; assert the generator emits
      one Boundary per (boundary group × condition).
