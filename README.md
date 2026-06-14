# linear-motor-optimization

A CAD → mesh → solver pipeline for optimizing a linear motor:

```
build123d CAD ──► STEP ──► gmsh (meshing.Mesher) ──► Elmer (elmer.sim.SifWriter) ──► ElmerSolver
```

A single `MeshingConfig` (materials + tags + mesh settings) drives both the
mesher and the solver-input writer. See [`docs/architecture/`](docs/architecture/)
for the design docs and phased roadmap.

## Project status

**Phase 0 (typing backbone & de-duplication) is complete** — 117 tests pass
via `uv run pytest`. The config/material surface is now Pydantic with
unit-validated pint quantities, a `Physics` enum (incl. a linear-elasticity
scaffold), a single material registry, and JSON-schema export
(`docs/schema/`). See `docs/architecture/NEXT-SESSION-KICKOFF.md` for the next
phase and `docs/architecture/04-roadmap.md` for the full sequence.

## Running tests

```
uv run pytest
```

Pure-logic tests (typing, `to_elmer()`, schema export, sif generation via a fake
physical group) run anywhere. gmsh / build123d integration tests are gated so the
suite passes without the Windows CAD stack.

## Repository hygiene

Enable the truncation/corruption guard once per clone:

```
git config core.hooksPath .githooks
```

The pre-commit hook runs `scripts/check_truncation.py`, which fails the commit if
a staged text file contains NUL bytes or shrank sharply versus `HEAD` (the signal
that a file was silently truncated — e.g. an editor saving back a stale, partial
copy). Run it manually any time with `python scripts/check_truncation.py --all`;
acknowledge an intentional large deletion with `--allow-shrink <path>`. `.md` and
other docs aren't covered by the test suite, so this check is their safety net.

`.gitattributes` normalizes line endings to LF, which keeps `git diff` free of
whole-file CRLF churn so a real change (like a file shrinking) stands out.

## Coding conventions

These are project preferences. New code (and reviews) should hold to them.

- **Type hints on ~100% of variables.** Annotate function parameters, return
  types, and locals — including `dict`/`list` accumulators and loop-derived
  values — unless there's a very good reason not to (e.g. a third-party type
  that isn't generic, where `Any` plus a short comment is clearer than a wrong
  hint). Good types carry the documentation.

- **Put vector math on `Vec3`, not inline.** Use `vec.magnitude()` and
  `vec.normalized()` rather than open-coding `(x**2 + y**2 + z**2) ** 0.5` or
  manual component division. If a vector operation is missing, add it to the
  `Vec3` class so every call site shares one implementation.

- **Factor out repeated patterns into utilities.** Don't copy-paste logic like
  `if getattr(tag, "field", None) is not None: ...` across call sites. The
  per-region override lookup lives in `meshing.config.first_tag_value(tags,
  field)` (and `EntityTag.overrides()` for iterating set values); reuse those
  instead of re-deriving the pattern.

- **No magic words.** Fixed vocabularies are `Enum`/`Literal` (e.g.
  `elmer.physics.Physics`), discoverable by autocomplete and checked statically —
  never bare strings chosen from an unwritten set.

- **Pydantic for config/data; `typing.Protocol` for hot-path callables.**
  Validated, schema-exporting models for the authoring surface; lightweight typed
  contracts (`common.protocols`) where behaviour is evaluated. Don't turn
  behaviour classes (the generators) into Pydantic models.
