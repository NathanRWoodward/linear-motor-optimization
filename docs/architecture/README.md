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
| [05-property-functions.md](05-property-functions.md) | Plan: properties as pint-aware callables (static / calibration / closed-form) | **Planned, not implemented** |
| [06-typing-and-schema.md](06-typing-and-schema.md) | Plan: Pydantic+Protocol typing backbone, pint schema, de-duplication. The spine. | **Implemented (Phase 0)** |
| [07-run-lifecycle.md](07-run-lifecycle.md) | Plan: provenance (RunManifest), typed Result, mesh convergence, caching seam | **Planned, not implemented** |
| [08-optimization-seam.md](08-optimization-seam.md) | Plan: Parameterization/Objective seam + naive grid search + Study tracking | **Planned, not implemented** |

> **Read order for implementers:** [06](06