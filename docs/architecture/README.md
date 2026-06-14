# Architecture & Restructure Plans

This folder holds design documents and implementation plans for evolving the
CAD → mesh → solver pipeline. They are written to be committed and used as a
reference / handoff across work sessions.

## The pipeline

```
build123d CAD ──► STEP ──► gmsh (meshing.Mesher) ──► Elmer (elmer.sim.SifWriter) ──► ElmerSolver
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
| [05-property-functions.md](05-property-functions.md) | Plan: properties as pint-aware callables (static / calibration / closed-form) | **Implemented (Phase 1)** |
| [06-typing-and-schema.md](06-typing-and-schema.md) | Plan: Pydantic+Protocol typing backbone, pint schema, de-duplication. The spine. | **Implemented (Phase 0)** |
| [07-run-lifecycle.md](07-run-lifecycle.md) | Plan: provenance (RunManifest), typed Result, mesh convergence, caching seam | **Planned, not implemented** |
| [08-optimization-seam.md](08-optimization-seam.md) | Plan: Parameterization/Objective seam + naive grid search + Study tracking | **Planned, not implemented** |

> **Read order for implementers:** [06](06-typing-and-schema.md) (backbone) →
> [05](05-property-functions.md) → [02](02-conditions-refactor.md) →
> [03](03-solver-validation.md) → [01](01-boundaries.md) →
> [07](07-run-lifecycle.md) → [08](08-optimization-seam.md). The
> [roadmap](04-roadmap.md) sequences these as Phases 0–7.

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
- **Typing backbone: Pydantic for config, Protocol for callables.** Validated,
  schema-exporting Pydantic models for the authoring surface; lightweight typed
  `Protocol`s for hot-path callables (property functions, stage emitters). pint
  quantities are made Pydantic-native via a `quantity_type` annotation that also
  exports JSON schema. See [06-typing-and-schema.md](06-typing-and-schema.md).
- **No magic words.** Fixed vocabularies are enums/`Literal`s, discoverable by
  autocomplete and checked statically. Good types carry the documentation.
- **One structure, reused.** Each concept has a single source of truth; stages
  reference it rather than re-declaring parallel near-identical classes — applied
  only where it removes duplication without coupling unrelated stages.
- **Material properties are callable.** Every property is a function of zero or
  more pint quantities (static value, calibration points, or closed-form
  formula). See [05-property-functions.md](05-property-functions.md).
- **A run is a tracked artifact; optimization sits on top.** The repo's goal is
  optimizing a motor, so provenance (a `RunManifest` + content-addressed run
  bundles), a typed `Result` return path, and mesh-convergence awareness are
  designed in ([07](07-run-lifecycle.md)). The optimizer is a thin consumer over
  a `Parameterization`/`Objective` seam; the first one is a deliberately naive
  grid search whose job is tracking inputs/outputs for analysis
  ([08](08-optimization-seam.md)). The pipeline itself stays optimization-ignorant.
