"""
The single material registry (doc 06 de-dup step 2).

Materials are defined once (as the Pydantic ``MaterialProperties`` subclasses in this package) and referenced by both pipeline stages: the CAD/mesh stage matches STEP region names against ``tag``; the sif writer reads the same objects' Elmer keywords.
There is deliberately no second ``known_materials = ["N52", ...]`` list (that lived in the now-deleted ``geometry/mesh.py``) — this registry is the one source of truth, keyed by each material's ``tag``.
"""

from __future__ import annotations

from physical.materials.air import Air
from physical.materials.neodymium import N52
from physical.materials.pcb import FR4
from physical.materials.properties import MaterialProperties

# Each value is a zero-arg factory so callers get a fresh, independent instance (materials are mutable Pydantic models; sharing one instance across configs would let an edit in one place leak into another).
_FACTORIES: dict[str, type[MaterialProperties]] = {
    "N52": N52,
    "Air": Air,
    "FR4": FR4,
}


def available_materials() -> list[str]:
    """The tags of every registered material (replaces the old hardcoded list)."""
    return list(_FACTORIES)


def material(tag: str) -> MaterialProperties:
    """Construct a fresh registered material by its tag (e.g. ``"N52"``)."""
    try:
        return _FACTORIES[tag]()
    except KeyError:
        raise KeyError(f"unknown material tag {tag!r}; registered: {available_materials()}") from None


def all_materials() -> list[MaterialProperties]:
    """A fresh instance of every registered material."""
    return [factory() for factory in _FACTORIES.values()]


def register_material(tag: str, factory: type[MaterialProperties]) -> None:
    """Add (or replace) a material in the registry. Lets downstream code extend the vocabulary without editing this module."""
    _FACTORIES[tag] = factory
