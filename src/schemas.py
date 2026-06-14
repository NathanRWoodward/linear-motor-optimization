"""Schema-as-a-deliverable (doc 06).

Every Pydantic config model can emit a JSON schema describing exactly how to
construct it ("this is how you can use me"). This module is the small entry point
doc 06 asks for: a function to get the schemas, a helper to dump them to
``docs/schema/*.json`` so the committed schema tracks the code, and a CLI:

    python -m schemas              # print all schemas to stdout
    python -m schemas MeshingConfig
    python -m schemas --out docs/schema   # write docs/schema/*.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from meshing.config import EntityTag, MeshingConfig
from physical.materials.properties import MaterialProperties

# The models worth advertising. Keyed by the name used for the JSON filename and
# the CLI selector.
SCHEMA_MODELS = {
    "MeshingConfig": MeshingConfig,
    "MaterialProperties": MaterialProperties,
    "EntityTag": EntityTag,
}


def model_schema(name: str) -> dict:
    """JSON schema for one registered model, by name."""
    try:
        return SCHEMA_MODELS[name].model_json_schema()
    except KeyError:
        raise KeyError(f"unknown schema {name!r}; available: {list(SCHEMA_MODELS)}") from None


def all_schemas() -> dict[str, dict]:
    """JSON schema for every registered model, keyed by name."""
    return {name: model.model_json_schema() for name, model in SCHEMA_MODELS.items()}


def dump_schemas(out_dir: str | Path) -> list[Path]:
    """Write one ``<Name>.json`` per registered model into ``out_dir``.

    Returns the paths written. Used to keep ``docs/schema/`` in sync with the
    code (optionally from CI).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, schema in all_schemas().items():
        path = out / f"{name}.json"
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export JSON schemas for the config/material models.")
    parser.add_argument("model", nargs="?", help="A single model name to print (default: all).")
    parser.add_argument("--out", metavar="DIR", help="Write <Name>.json for every model into DIR instead of printing.")
    args = parser.parse_args(argv)

    if args.out:
        paths = dump_schemas(args.out)
        for p in paths:
            print(f"wrote {p}")
        return 0

    if args.model:
        print(json.dumps(model_schema(args.model), indent=2))
    else:
        print(json.dumps(all_schemas(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
