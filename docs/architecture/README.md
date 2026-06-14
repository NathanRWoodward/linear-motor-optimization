# Architecture & Restructure Plans

This folder holds design documents and implementation plans for evolving the
CAD → mesh → solver pipeline. They are written to be committed and used as a
reference / handoff across work sessions.

## The pipeline

```
build123d CAD ──► STEP ──► gmsh (meshing.Generator) ──► Elmer (elmer.sim.Generator) ──► ElmerSolver
                              │                              │
                              └──── one MeshingConfig drives both ────┘
```

A single `MeshingConfig` (materials + tags + mesh settings) drives both the
mesher and the solver-input generator. Regions are matched to materials/tags by
parsing the build123d part names that survive into the STEP file. The mesher
emits gmsh *physical groups*; the Elmer generator builds a matching `Body` per
group, referencing the same integer id and reusing the same name.

## Documents

| Doc | Purpose | Status |
|-----|---------|--------|
| [00-assessment.md](00-assessment.md) | Current-state architecture assessment: what flexes, what fights us | Reference |
| [01-boundaries.md](01-boundaries.md) | Plan: emit 2D (surface) physical groups via body adjacency; the biggest gap | **Planned, not implemented** |
| [02-conditions-refactor.md](02-conditions-refactor.md) | Plan: replace the overloaded `EntityTag` with composable condition objects | **Planned, not implemented** |
| [03-solver-validation.md](03-solver-validation.md) | Plan: validate solver presets against required material/BC properties | **Planned, not implemented** |
| [04-roadmap.md](04-roadmap.md) | Phased sequencing, dependencies, and per-phase handoff notes | Reference |

## How to use this folder

Each plan doc is self-contained and ends with a **Handoff checklist** an
implementer (human or agent) can follow. The roadmap ([04-roadmap.md](04-roadmap.md))
gives the order and what unblocks what. Update the **Status** column above as
phases land.

## Key decisions already made

- **Boundary identification: implicit from body adjacency.** Surface groups are
  derived from topology (external faces of the air box → far field; shared faces
  between two named bodies → interfaces) rather than from explicit CAD face
  labels or bounding-box rules. See [01-boundaries.md](01-boundaries.md) for the
  rationale and the escape hatch for cases adjacency can't resolve.
