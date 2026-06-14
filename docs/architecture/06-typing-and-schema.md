# 06 — Typing, schema, and structural de-duplication

**Status: implemented (Phase 0).** New direction (request set 4 + clarified
2). This doc is the spine the others lean on.

## Principles (the brief, restated)

- **Good typing replaces documentation.** The types should tell a user how to use
  the system. If you have to read prose to know what to pass, the type failed.
- **No magic words.** String keys chosen from an unwritten vocabulary are out.
  Where a fixed set of choices exists, it is an `Enum` or `Literal`, discoverable
  by autocomplete and checked statically.
- **Enforce correct usage gracefully.** Wrong input fails at construction with a
  clear, typed error — not at ElmerSolver runtime, not silently.
- **Schema is a deliverable.** Config objects can emit a JSON schema describing
  exactly how to construct them ("this is how you can use me").
- **One structure, reused.** Avoid parallel near-identical definitions across the
  CAD / mesh / Elmer stages (clarified request 2).

## Backbone: Pydantic for config, Protocol for callables

Decided. Two complementary tools:

| Surface | Tool | Why |
|---------|------|-----|
| Config & data objects (materials, conditions, tags, presets) | **Pydantic v2** (already a dep, v2.13) | Runtime validation at construction, JSON-schema export, great errors, IDE-discoverable fields |
| Hot-path callables (property functions, stage emitters) | **`typing.Protocol`** | The *signature* is the contract; no per-call validation overhead; structural typing = no forced inheritance |

This keeps validated/schema'd surfaces where authoring happens, and lightweight
typed contracts where evaluation happens.

## The pint ↔ Pydantic keystone

Plain pint `Quantity` fields validate and serialize in Pydantic but **break JSON
schema export** unless they declare a schema. We provide one annotated type that
does all three (verified working against pydantic 2.13 + pint):

```python
# physical/units.py  (extends the existing module)
from typing import Annotated
from pydantic_core import core_schema

def quantity_type(dimensionality: str):
    """A pint Quantity constrained to a dimensionality, usable as a Pydantic
    field. Validates dimensionality, serializes to a unit string, and exports a
    JSON schema annotated with the expected unit."""
    class _Q:
        @classmethod
        def __get_pydantic_core_schema__(cls, source, handler):
            def validate(v):
                q = v if isinstance(v, U.Quantity) else U.Quantity(v)
                if not q.check(dimensionality):
                    raise ValueError(f"expected {dimensionality}, got {q.dimensionality}")
                return q
            return core_schema.no_info_plain_validator_function(
                validate,
                serialization=core_schema.plain_serializer_function_ser_schema(
                    lambda q: f"{q:~P}"))
        @classmethod
        def __get_pydantic_json_schema__(cls, core, handler):
            return {"type": "string",
                    "x-unit-dimensionality": dimensionality,
                    "description": f"pint quantity with dimensionality {dimensionality}"}
    return Annotated[U.Quantity, _Q]

# convenience aliases so field declarations read like documentation
Temperature   = quantity_type("[temperature]")
Conductivity  = quantity_type("[power]/[length]/[temperature]")
Density       = quantity_type("[mass]/[length]**3")
FluxDensity   = quantity_type("[mass]/[current]/[time]**2")   # Tesla
Quantity      = U.Quantity                                     # unconstrained alias
```

Result, proven in a spike:
- `ThermalProps(conductivity="8.7 W/(m*K)")` validates and stores a real pint
  quantity.
- `ThermalProps(conductivity="5 kg")` raises a clear dimensionality error at
  construction.
- `ThermalProps.model_json_schema()` emits the unit in the schema.

So a material field declared `conductivity: Conductivity` is self-documenting:
the type name, the dimensionality, and the schema all say what belongs there.

## No magic words: enums/literals everywhere a vocabulary exists

Replace stringly-typed choices with discoverable types:

- Physics selection: `class Physics(StrEnum): MAGNETOSTATICS = "magnetostatics"; ...`
  instead of `physics="magnetostatics"`.
- Condition target: `Literal["body", "boundary"]` (or an enum).
- Interpolation method: `Literal["linear", "nearest", "cubic"]`.
- Solver/preset *names* stay strings only where they are genuinely open-ended,
  and even then are validated against the registered set at construction.

Autocomplete now shows the legal values; a typo is a static error.

## De-duplication: one structure reused across stages (clarified request 2)

There are currently **two parallel config worlds** plus a dead third:

- `geometry/config.py` — `MagnetConfig`/`HalbachConfig`/`DualHalbachConfig` (CAD
  dimensions).
- `meshing/config.py` — `MeshingConfig`/`EntityTag` (materials, tags, mesh+sim).
- `geometry/mesh.py` — a superseded prototype with a hardcoded
  `known_materials = ["N52","FR4","Copper","Air"]` that re-implements, badly,
  what `meshing` does properly.

The goal is **not** to force one mega-object. It is to have a single source of
truth for each concept and let stages *reference* it, not redefine it:

1. **Delete `geometry/mesh.py`** (dead duplication). Its only useful bit — the
   per-entity bounding-box/center-of-mass extraction — moves to a helper the
   adjacency code ([01-boundaries.md](01-boundaries.md)) can reuse.

2. **One material registry.** Materials (`N52`, `Air`, `FR4`) are defined once as
   Pydantic models and referenced by both the CAD stage (for labels/colors) and
   the mesh/sim stage (for properties). No second `known_materials` list.

3. **`PhysicalGroup` / `BoundaryGroup` already are the reuse mechanism** between
   mesh and Elmer — they carry the shared identity so the Elmer side references
   rather than re-declares. Keep extending that pattern; don't add a parallel
   Elmer-side region list.

4. **Stage emission via Protocols, not parallel classes.** Rather than a
   `MagnetCadConfig` + `MagnetMeshEntity` + `MagnetElmerBody` trio, a concept
   implements whichever stage protocols apply:

   ```python
   @runtime_checkable
   class ElmerEmitter(Protocol):
       def to_elmer(self, **ctx) -> dict: ...

   @runtime_checkable
   class MeshGroupSource(Protocol):
       """Something that resolves to one or more gmsh physical groups."""
       def physical_group_name(self) -> str: ...
   ```

   Objects gain a facet by implementing a protocol, not by spawning a parallel
   class hierarchy. This is the "reuse the structure of each, shared between
   them" you asked for, without a god object. **Caveat (your own):** if a given
   unification makes things *less* maintainable, don't force it — the test is
   "does this remove duplication without coupling unrelated stages?" If CAD
   dimensions and Elmer keywords have nothing real in common for a concept, leave
   them in separate models and let a thin builder relate them.

## Schema as a deliverable

Every Pydantic config model gets JSON-schema export for free. We expose a small
entry point so a user (or a tool) can ask the system how to configure it:

```python
# e.g. a `schemas` CLI / function
MeshingConfig.model_json_schema()      # full config schema, units annotated
MaterialProperties.model_json_schema() # what a material looks like
```

Optionally dump these to `docs/schema/*.json` in CI so the committed schema
tracks the code. Decide during implementation whether that's worth the wiring.

## Migration / compatibility

- Pydantic models can keep `model_config = ConfigDict(arbitrary_types_allowed=True)`
  for the pint fields and any build123d objects held by reference.
- Convert leaf data classes (`MaterialProperties` and sub-objects, `EntityTag`,
  the new conditions) to Pydantic first; they have the most to gain and the least
  coupling.
- Generators (`meshing.Generator`, `elmer.sim.Generator`) stay plain classes —
  they're behaviour, not data — but consume the now-validated models.

## Testing (request 3)

- A field given the wrong dimensionality raises at construction (typed).
- `model_json_schema()` includes the unit annotation for a quantity field.
- An enum/literal field rejects an out-of-vocabulary string statically (covered
  by the type checker) and at runtime.
- Round-trip: `model_dump()` → `model_validate()` preserves quantities.

## Handoff checklist

- [x] Add `quantity_type` + named aliases to `physical/units.py` (keystone).
- [x] Convert `MaterialProperties` + sub-objects to Pydantic using the aliases.
- [x] Introduce `Physics` enum + `Literal`s; purge magic strings from `elmer/sim.py`.
- [x] Delete `geometry/mesh.py`; relocate its bbox/CoM helper.
- [x] Establish the single material registry; remove `known_materials`.
- [x] Add `ElmerEmitter` / mesh-source Protocols; adopt where they remove a
      parallel class (and only there).
- [x] Wire `model_json_schema()` access; optionally dump to `docs/schema/`.
- [x] Tests above under `uv run pytest`.
