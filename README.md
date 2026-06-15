# linear-motor-optimization

A CAD → mesh → solver pipeline for optimizing a linear motor:

```
build123d CAD ──► STEP ──► gmsh (meshing.Mesher) ──► Elmer (elmer.sim.SifWriter) ──► ElmerSolver
```

A single `MeshingConfig` (materials + tags + mesh settings) drives both the mesher and the solver-input writer.
See [`docs/architecture/`](docs/architecture/) for the design docs and phased roadmap.

## Project status

**Phases 0–3 are complete** — 150 tests pass via `uv run pytest`.
On the Phase 0 typing backbone (Pydantic + unit-validated pint quantities, a `Physics` enum, a single material registry, JSON-schema export), every material property is a pint-aware callable (Phase 1): `Static` (constant), `Calibration` (1-D interpolation), or `ClosedForm` (Python formula), all behind one typed `PropertyFunction` call site; `to_elmer(at=...)` evaluates each at an operating point and strips to SI.
Region physics is authored as composable `Condition` objects (Phase 2, body half — `Magnetization` today), and `SifWriter` validates the material ↔ solver coupling at construction (Phase 3), so a misconfigured solve fails fast with a region-pointing error instead of opaquely at ElmerSolver runtime.
See `docs/architecture/04-roadmap.md` for the full phased sequence.

## Running tests

```
uv run pytest
```

Pure-logic tests (typing, `to_elmer()`, schema export, sif generation via a fake physical group) run anywhere.
gmsh / build123d integration tests are gated so the suite passes without the Windows CAD stack.

## Repository hygiene

Enable the truncation/corruption guard once per clone:

```
git config core.hooksPath .githooks
```

The pre-commit hook runs `scripts/check_truncation.py`, which fails the commit if a staged text file contains NUL bytes or shrank sharply versus `HEAD` (the signal that a file was silently truncated — e.g. an editor saving back a stale, partial copy).
Run it manually any time with `python scripts/check_truncation.py --all`; acknowledge an intentional large deletion with `--allow-shrink <path>`.
`.md` and other docs aren't covered by the test suite, so this check is their safety net.

`.gitattributes` normalizes line endings to LF, which keeps `git diff` free of whole-file CRLF churn so a real change (like a file shrinking) stands out.

## Coding conventions

These are project preferences. New code (and reviews) should hold to them.

- **Type hints on ~100% of variables.**
  Annotate function parameters, return types, and locals — including `dict`/`list` accumulators and loop-derived values — unless there's a very good reason not to (e.g. a third-party type that isn't generic, where `Any` plus a short comment is clearer than a wrong hint).
  Good types carry the documentation.

- **Put vector math on `Vec3`, not inline.**
  Use `vec.magnitude()` and `vec.normalized()` rather than open-coding `(x**2 + y**2 + z**2) ** 0.5` or manual component division.
  If a vector operation is missing, add it to the `Vec3` class so every call site shares one implementation.

- **Factor out repeated patterns into utilities.**
  Don't copy-paste a filter-the-tags loop across call sites.
  Resolving which conditions a region carries lives in `meshing.config.conditions_for(tags, physics, target)`; reuse it instead of re-deriving the per-(physics, target) filter.

- **No magic words.**
  Fixed vocabularies are `Enum`/`Literal` (e.g. `elmer.physics.Physics`), discoverable by autocomplete and checked statically — never bare strings chosen from an unwritten set.

- **Pydantic for config/data; `typing.Protocol` for hot-path callables.**
  Validated, schema-exporting models for the authoring surface; lightweight typed contracts (`common.protocols`) where behaviour is evaluated.
  Don't turn behaviour classes (the generators) into Pydantic models.

- **No maximum line length in `.md` files.**
  Don't hard-wrap Markdown prose to some narrow column; markdown viewers reflow soft-wrapped text fine, and mid-sentence breaks in the source make editing painful.
  Within reason, keep a paragraph on a single line and start a new line only where a genuinely new thought begins (a new point, a paragraph break) — never in the middle of a sentence.

- **Target a maximum line length of 150 for comments in code.**
  The formatter holds code to 150, so comments should match that width rather than wrapping at some narrower column.
  Only move to a new line when it helps formatting or clarity, or when the sentence would otherwise run past 150.

- **Never split a single sentence across more than one line.**
  This applies to both code comments and `.md` files; barring a very good reason, a sentence lives on one line.
  Order of operations: try to fit the sentence on the current line → if it doesn't fit, move the whole sentence to start on a new line → if it still doesn't fit even on its own line, reword it to be shorter.

- **Multi-line docstrings put both `"""` on their own lines.**
  The opening `"""` sits alone, the summary starts on the next line, and the closing `"""` is alone, so every prose line is left-aligned with the block instead of the first line sitting indented past the quotes.
  Single-line docstrings stay on one line (`"""Summary."""`).
