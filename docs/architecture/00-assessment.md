# 00 — Architecture Assessment

A candid assessment of the current pipeline's flexibility for supporting more
solver types and use cases. This is the "why" behind the plans in this folder.

## What the architecture does well

**One config drives both halves.** `MeshingConfig` (materials + tags + mesh
settings) is consumed by both `meshing.Generator` and `elmer.sim.Generator`.
Because both derive their structure from the same source, they cannot drift out
of sync. Adding a material or a tagged region is a *data* change, not a code
change. This is the hard thing to get right, and it is right.

**Region resolution is name-driven and uniform.** Regions are matched to
materials/tags by parsing build123d part names that survive into the STEP. The
same mechanism that names a body can name its conditions. This keeps the CAD as
the single source of truth for "what is this region."

**Properties are split by physical domain.** `MaterialProperties` delegates to
`MechanicalProperties` / `ThermalProperties` / `MagneticProperties` /
`ElectricalProperties`, each with its own `to_elmer()`. A new solver that needs a
new property reads from the domain that already owns it; the conversion
(pint quantity → bare SI float + exact Elmer keyword) lives in one place.

**The mesh↔sim contract is explicit.** `meshing.generator.PhysicalGroup` carries
`(id, name, material, tags, entity_tags)`. The Elmer generator targets bodies by
the same gmsh id and reuses the same name. This is the seam that lets the two
tools evolve independently.

**Solver/physics definitions are data.** `SOLVER_LIBRARY` / `SIMULATION_LIBRARY`
/ `PHYSICS_PRESETS` in `elmer/sim.py` are plain dicts in exact sif syntax. Adding
a *variant* of an existing physics (e.g. transient magnetics) or a new
body-only physics is mostly a new preset entry, and the body loop already
attaches one shared equation listing all active solvers — which is how Elmer
expects coupled multiphysics.

## Where the architecture fights us

### 1. The pipeline is volume-centric; boundaries have nowhere to live

The mesher emits only 3D (body) physical groups. But nearly every solver beyond
"magnetostatics with a far-field air box" needs *surface* conditions:

- thermal → fixed temperature, heat flux, convection (all boundary conditions)
- electrostatics → potential BCs
- magnetostatics → the far-field / infinity BC on the air box itself

`EntityTag` already declares `fixed_temperature` and `fixed_heat_flux`, but they
have nowhere to attach because there are no surface groups. `_wire_thermal_body`
in `elmer/sim.py` is stubbed for exactly this reason.

There is also a hard gmsh constraint that makes this non-optional once started:
**when any physical group is defined, only entities belonging to a physical group
survive to the mesh.** So the moment we emit one 2D group, every boundary Elmer
needs must be in a group. Half-measures don't work. → [01-boundaries.md](01-boundaries.md)

### 2. `EntityTag` is an overloaded "god object"

`EntityTag` accumulates unrelated fields (`fixed_temperature`,
`fixed_heat_flux`, `magnetic_coercivity`, and — currently as a semantic hack —
magnetization *direction* riding on `magnetic_coercivity`). Most are `None` for
any given region. As solvers are added this grows: current density, contact
conductance, emissivity, etc. The class becomes a grab-bag where the relationship
between a field and the solver that consumes it is implicit. → [02-conditions-refactor.md](02-conditions-refactor.md)

### 3. Solver presets are unvalidated raw dicts

The inline dicts are maximally flexible — any Elmer keyword works — but nothing
catches a typo'd keyword, a missing required material property, or a unit that
wasn't stripped, until ElmerSolver fails at runtime. Fine for a research tool run
by hand; risky inside an optimization loop that runs the pipeline hundreds of
times. → [03-solver-validation.md](03-solver-validation.md)

## Litmus test: "what does a new solver cost?"

| Scenario | Cost today | After plans land |
|----------|-----------|------------------|
| Variant of existing physics (transient magnetics) | Cheap — new preset | Cheap |
| New body-only physics | Cheap — new domain mapping + preset | Cheap |
| Anything needing boundary conditions | **Blocked** on the 2D-group gap | Cheap — define a condition on a region/interface |
| Coupled multiphysics (e.g. magneto-thermal) | Partial — bodies couple, boundaries don't | Cheap |

The architecture is flexible along the axis already exercised (bodies/materials)
and rigid along the axis not yet exercised (boundaries). That is normal and
expected — you build the seams you need first. These plans build the next seam.

## Guiding principle for the restructure

Keep the property of #1's strength — *config is the single source of truth, both
halves derive from it* — and extend it to boundaries and conditions. Every new
abstraction should:

1. Be declared once in the config (data, not code).
2. Know how to emit its own Elmer keywords (the `to_elmer()` pattern).
3. Be resolvable from the mesh by a stable id/name shared across both tools.
