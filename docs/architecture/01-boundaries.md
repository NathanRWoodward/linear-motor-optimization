# 01 — Boundaries: emit 2D physical groups from body adjacency

**Status: planned, not implemented.** This is the highest-priority structural
gap (see [00-assessment.md](00-assessment.md) #1).

## Goal

Give the pipeline a way to define, identify, and emit *surface* physical groups
so boundary conditions (fixed temperature, heat flux, far-field, interfaces) can
attach to real mesh entities — without requiring the CAD author to hand-label
every face.

## Decision: identify boundaries implicitly from body adjacency

Chosen over explicit build123d face labels and bounding-box rules. Rationale:

- **Lowest authoring burden.** The body groups already exist; the surfaces we
  care about are mostly derivable from how bodies touch each other and the
  outside world. No new work in the build123d code, no brittle coordinate rules.
- **Robust to geometry changes.** Topology (who is adjacent to whom) survives
  parametric changes that would break a hard-coded bounding box.
- **CAD-agnostic.** Doesn't depend on STEP preserving face-level labels, which is
  less reliable than the part/solid labels we already rely on.

### The two boundary kinds adjacency gives us

1. **External boundaries** — faces of a body that are not shared with any other
   body. For the air box, these are the domain's outer shell → the natural place
   for a far-field / infinity BC. For a solid exposed to air, its faces shared
   with the air box are its convective/exposed surfaces.

2. **Interface boundaries** — faces shared between two named bodies (e.g.
   magnet↔air, PCB↔air, magnet↔PCB). Useful for contact conditions, interface
   heat transfer, and simply for naming surfaces deterministically.

### Naming convention (the shared contract)

Mirror the body convention. A surface group name encodes the two bodies it lies
between (sorted for determinism), or the body + `EXT` for an external face:

```
<BODYA>__<BODYB>        e.g.  AIR__N52_MAG_N_1     (interface)
<BODY>__EXT             e.g.  AIR__EXT             (external shell)
```

Elmer references these by the integer physical-group id, exactly as bodies are
referenced today, so `boundaries.Boundary(... [group.id])` lines up automatically.

## Hard constraint to design around

Per ElmerGrid/gmsh: **once any physical group is defined, only entities belonging
to a physical group are written to the mesh.** Today only 3D groups exist, so all
volumes survive. The moment we add 2D groups, *every* surface Elmer needs must be
in a 2D group, or it won't exist in the mesh and `Target Boundaries` will point
at nothing.

**Implication:** boundary emission cannot be partial. The mesher must emit a 2D
group for *every* boundary face of the model (every face is either an interface
between two bodies or an external face of one body). Adjacency gives us exactly
this total partition for free — that is a second reason the implicit approach
fits. We can collapse uninteresting faces into a catch-all group (e.g.
`AIR__EXT`) so the count stays manageable.

## Proposed implementation shape

> Code below is illustrative pseudocode for the plan, not final.

### A. Extend `PhysicalGroup` / add `BoundaryGroup`

`meshing/generator.py` gains a sibling record for dim-2 groups:

```python
class BoundaryGroup:
    dim = 2
    id: int                 # gmsh physical-group id (Elmer boundary id)
    name: str               # AIR__N52_MAG_N_1 or AIR__EXT
    bodies: tuple[str, ...] # the 1 or 2 body group names it borders
    face_tags: list[int]    # gmsh surface entity tags in this group
```

### B. Compute adjacency after body groups are built

Using gmsh topology (each volume's bounding surfaces) and the already-built body
groups:

```python
# pseudocode
face_to_bodies: dict[int, set[str]] = defaultdict(set)
for body_group in self.physical_groups:           # the existing 3D groups
    for vol_tag in body_group.entity_tags:
        for face in gmsh.model.getBoundary([(3, vol_tag)], oriented=False):
            face_to_bodies[face.tag].add(body_group.name)

# partition every face into interface (2 bodies) or external (1 body)
groups: dict[str, list[int]] = defaultdict(list)
for face_tag, bodies in face_to_bodies.items():
    if len(bodies) == 2:
        name = "__".join(sorted(bodies))
    else:                                          # 1 body -> external
        name = f"{next(iter(bodies))}__EXT"
    groups[name].append(face_tag)

for name, face_tags in groups.items():
    gid = gmsh.model.addPhysicalGroup(2, face_tags, name=name)
    self.boundary_groups.append(BoundaryGroup(2, gid, name, ..., face_tags))
```

(`gmsh.model.getAdjacencies` / `getBoundary` provide the volume→face map. The old
`geometry/mesh.py` prototype already pulls bounding boxes and centers of mass per
entity, which is a useful fallback for disambiguating faces if needed.)

### C. Consume boundary groups in `elmer/sim.py`

The condition model (see [02-conditions-refactor.md](02-conditions-refactor.md))
resolves which boundary groups get which BC. For the magnetostatics far-field:

```python
for bg in mesh.boundary_groups:
    if bg.name == f"{air_group_name}__EXT":
        b = elmer.Boundary(sim, "FarField", [bg.id])
        b.data.update({"Infinity BC": "True"})   # WhitneyAVSolver far-field
```

### Escape hatch (when adjacency isn't enough)

Some surfaces can't be distinguished by adjacency alone (e.g. "the top face of
the air box specifically"). The design keeps a documented override path: an
optional bounding-box predicate or build123d face label in the config that can
*rename or split* an adjacency group. This stays optional so the common path
needs zero authoring. Defer building it until a concrete case needs it.

## Validation / testing

- Unit: a synthetic 2-box adjacency fixture (no gmsh) asserting the face→bodies
  partition yields the expected interface + external group names.
- Integration (needs gmsh): mesh the existing `data/pcb_coil.step` (or the
  dual-Halbach STEP) and assert (a) every body still survives, (b) the air-box
  external shell becomes one group, (c) interface counts are sane.
- End-to-end: thermal sif with a fixed-temperature BC on a real surface group;
  confirm `Target Boundaries(n)` points at the right id.

## Handoff checklist

- [ ] Add `BoundaryGroup` to `meshing/generator.py`.
- [ ] After 3D groups are built, compute face→bodies adjacency and emit 2D groups
      covering **all** boundary faces (respect the "all-or-nothing" gmsh rule).
- [ ] Store `self.boundary_groups` on the mesher, mirroring `physical_groups`.
- [ ] Decide the surface-group naming and document it next to the body naming.
- [ ] Wire the magnetostatics far-field BC onto the air-box `__EXT` group (this
      also tightens the currently-implicit far field).
- [ ] Add the synthetic adjacency unit test before the gmsh integration test.
- [ ] Cross-check with [02-conditions-refactor.md](02-conditions-refactor.md):
      the condition objects are what decide *which* BC lands on *which* group.

## Sources

- [Elmer Forum — how are physical surfaces numbered by ElmerGrid](https://www.elmerfem.org/forum/viewtopic.php?t=2769)
- [Elmer Forum — assigning BCs to many surfaces](http://www.elmerfem.org/forum/viewtopic.php?t=6654)
- [Gmsh physical vs elementary entities](https://bthierry.pages.math.cnrs.fr/tutorial/gmsh/basics/physical_vs_elementary/)
