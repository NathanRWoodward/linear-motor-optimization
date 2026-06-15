"""
Structural typing contracts shared across pipeline stages (doc 06).

Per doc 06's "stage emission via Protocols, not parallel classes": a concept gains a stage facet by *implementing a protocol*, not by spawning a parallel class hierarchy (no ``MagnetCadConfig`` + ``MagnetMeshEntity`` + ``MagnetElmerBody`` trio).
These are ``runtime_checkable`` so a stage can ``isinstance``-check what a config object can do.

Caveat (doc 06): only adopt a protocol where it removes real duplication without coupling unrelated stages.
If CAD dimensions and Elmer keywords have nothing in common for a concept, leave them in separate models and relate them with a thin builder instead.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ElmerEmitter(Protocol):
    """
    Something that knows how to emit its own Elmer sif keywords.

    This is the ``to_elmer()`` pattern (doc 00 guiding principle #2) expressed as a contract: materials, and later conditions/boundaries, all satisfy it, so the sif writer can consume any of them uniformly.
    """

    def to_elmer(self, **ctx) -> dict: ...


@runtime_checkable
class MeshGroupSource(Protocol):
    """
    Something that resolves to one or more gmsh physical groups.

    The shared identity (a stable group name) is what lets the Elmer side *reference* a region rather than re-declare it.
    """

    def physical_group_name(self) -> str: ...
