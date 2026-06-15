"""
Discoverable vocabularies for the Elmer stage.

No magic words (doc 06): the set of supported physics is an enum, not a free string.
Autocomplete shows the legal values and a typo is a static error rather than a runtime ``KeyError`` deep inside the sif writer.
"""

from __future__ import annotations

from enum import StrEnum


class Physics(StrEnum):
    """
    Which physics preset the sif writer wires.

    The string values match the keys of ``PHYSICS_PRESETS`` in ``elmer.sim`` and the historical ``physics="magnetostatics"`` spelling, so existing configs and serialized data keep working — but callers now pass ``Physics.MAGNETOSTATICS`` and get IDE completion + validation.
    """

    MAGNETOSTATICS = "magnetostatics"
    THERMAL = "thermal"
    ELECTROSTATICS = "electrostatics"
    LINEAR_ELASTICITY = "linear_elasticity"  # mechanical / structural (planned)
