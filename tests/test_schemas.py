"""
Phase 0: schema-as-a-deliverable.
The committed docs/schema/*.json must stay in sync with the models (regenerate with `python -m schemas --out docs/schema`).
"""

import json
from pathlib import Path

import pytest

import schemas

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO_ROOT / "docs" / "schema"


def test_all_schemas_exports_every_model():
    out = schemas.all_schemas()
    assert set(out) == set(schemas.SCHEMA_MODELS)


@pytest.mark.parametrize("name", list(schemas.SCHEMA_MODELS))
def test_committed_schema_matches_code(name):
    committed = json.loads((SCHEMA_DIR / f"{name}.json").read_text())
    assert committed == schemas.model_schema(name), f"{name}.json is stale; run `python -m schemas --out docs/schema`"


def test_dump_schemas_writes_files(tmp_path):
    written = schemas.dump_schemas(tmp_path)
    assert {p.name for p in written} == {f"{n}.json" for n in schemas.SCHEMA_MODELS}
