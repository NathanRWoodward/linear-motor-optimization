"""
Composable, self-describing conditions attached to a region (doc 02).

`EntityTag` was becoming a god object: a flat bag of optional scalars (`magnetization_direction`, `fixed_temperature`, `fixed_heat_flux`, …) most of which are `None` for any given region, with the link between a field and the solver that consumes it left implicit.
This module replaces that grab-bag with small condition objects. Each condition knows:

* which physics/solver it belongs to (`physics`, a :class:`elmer.physics.Physics`
  enum member — no magic strings),
* whether it applies to a body or a boundary (`target`, a
  :class:`ConditionTarget` enum), and
* how to emit its own Elmer sif keywords (``to_elmer``), mirroring the
  ``to_elmer()`` pattern that already works for materials.

A region then carries only the conditions it actually has, and the sif writer's job becomes a uniform *filter by (physics, target)* loop rather than a set of bespoke ``_wire_*`` methods.

Each subclass also carries a ``kind`` discriminator (``Literal[...]``) so a ``list[Condition]`` round-trips through ``model_dump()`` / ``model_validate()`` and exports clean JSON schema via a Pydantic discriminated union (:data:`ConditionUnion`).

This is Phase 2 (the *body* half of doc 02): only :class:`Magnetization` is wired into the generator.
The thermal carriers (:class:`FixedTemperature`, :class:`HeatFlux`, :class:`Convection`) land as data + round-trip tests; their boundary loop waits for the Phase 4 ``BoundaryGroup`` work.

Import hygiene (doc, "Placement"): this module imports only the import-light ``elmer.physics`` enum, ``common.vector`` and ``physical.units``.
It must NOT import ``meshing.config`` or ``elmer.sim`` — those import *it*.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from common.vector import Vec3, Vec3Field
from elmer.physics import Physics
from physical.units import (
    HeatFlux as HeatFluxQuantity,
    HeatTransferCoefficient,
    Quantity,
    Temperature,
    U,
)

__all__ = [
    "ConditionTarget",
    "Condition",
    "Magnetization",
    "FixedTemperature",
    "HeatFlux",
    "Convection",
    "ConditionUnion",
]


class ConditionTarget(StrEnum):
    """
    Whether a condition attaches to a 3D body or a 2D boundary.

    A fixed vocabulary, so it is an enum rather than a bare ``"body"`` / ``"boundary"`` string (doc 06, "no magic words"): autocomplete shows the legal values and a typo is a static error.
    """

    BODY = "body"
    BOUNDARY = "boundary"


def _si(quantity: Quantity, unit: Any) -> float:
    """
    Strip ``quantity`` to a bare SI float in ``unit`` for Elmer.

    Mirrors the unit-stripping the material ``to_elmer()`` methods do: Elmer's sif keywords are plain numbers, so a condition converts its pint quantity to the documented SI unit and hands over the magnitude.
    """
    return float(quantity.to(unit).magnitude)


class Condition(BaseModel):
    """
    Base: a self-describing piece of physics attached to a region.

    Subclasses pin ``physics`` / ``target`` to fixed defaults and implement ``to_elmer``.
    The base is never instantiated directly (it has no ``kind`` discriminator); construct one of the concrete subclasses instead.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    physics: Physics
    target: ConditionTarget

    def to_elmer(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Return this condition's exact Elmer sif keyword dict.

        Signatures vary by subclass (``Magnetization`` needs the material-derived magnitude; the thermal carriers take no arguments), so the generator dispatches on the concrete type.
        """
        raise NotImplementedError


class Magnetization(Condition):
    """
    Permanent-magnet body force (magnetostatics, body target).

    The *direction* is per-region (in a Halbach array the same N52 block points N/E/S/W depending on its slot) and lives here; the *magnitude* ``|M| = Bᵣ/μ₀`` is a material property and is passed into ``to_elmer`` by the generator.
    ``direction`` need not be a unit vector — ``to_elmer`` normalizes it (via :meth:`Vec3.normalized`) before scaling, so authoring an axis-aligned ``Vec3(0, 1, 0)`` or a raw ``Vec3(0, 2, 0)`` gives the same result.
    """

    kind: Literal["magnetization"] = "magnetization"
    physics: Physics = Physics.MAGNETOSTATICS
    target: ConditionTarget = ConditionTarget.BODY

    direction: Vec3Field = Field(description="Magnetization direction (normalized before use); magnitude comes from the material.")

    def to_elmer(self, magnitude: float) -> dict[str, str]:
        """
        Scale the normalized direction by ``magnitude`` (A/m) into the three ``Magnetization`` components. Formatted with ``.6g`` to match the sif the generator emitted before this refactor.
        """
        m: Vec3 = self.direction.normalized() * magnitude
        return {
            "Magnetization 1": f"{m.x:.6g}",
            "Magnetization 2": f"{m.y:.6g}",
            "Magnetization 3": f"{m.z:.6g}",
        }


class FixedTemperature(Condition):
    """Dirichlet temperature boundary condition (thermal, boundary target)."""

    kind: Literal["fixed_temperature"] = "fixed_temperature"
    physics: Physics = Physics.THERMAL
    target: ConditionTarget = ConditionTarget.BOUNDARY

    value: Temperature = Field(description="Fixed temperature (K) imposed on the boundary.")

    def to_elmer(self) -> dict[str, float]:
        return {"Temperature": _si(self.value, U.K)}


class HeatFlux(Condition):
    """Prescribed heat flux boundary condition (thermal, boundary target)."""

    kind: Literal["heat_flux"] = "heat_flux"
    physics: Physics = Physics.THERMAL
    target: ConditionTarget = ConditionTarget.BOUNDARY

    value: HeatFluxQuantity = Field(description="Heat flux (W/m^2) through the boundary.")

    def to_elmer(self) -> dict[str, float]:
        return {"Heat Flux": _si(self.value, U.W / U.m**2)}


class Convection(Condition):
    """
    Convective (Newton-cooling) boundary condition (thermal, boundary target).

    Carries both the heat-transfer coefficient *and* the external temperature it exchanges with — together they fully specify the boundary, which a lone coefficient could not.
    """

    kind: Literal["convection"] = "convection"
    physics: Physics = Physics.THERMAL
    target: ConditionTarget = ConditionTarget.BOUNDARY

    coefficient: HeatTransferCoefficient = Field(description="Convective heat-transfer coefficient (W/m^2/K).")
    ext_temperature: Temperature = Field(description="External (ambient) temperature (K) the boundary exchanges with.")

    def to_elmer(self) -> dict[str, float]:
        return {
            "Heat Transfer Coefficient": _si(self.coefficient, U.W / (U.m**2 * U.K)),
            "External Temperature": _si(self.ext_temperature, U.K),
        }


# A region holds a polymorphic ``list[Condition]``. Tagging each subclass with a distinct ``kind`` lets Pydantic build a discriminated union so the list round-trips through model_dump()/model_validate() and exports clean JSON schema (schema-as-a-deliverable, doc 06) instead of an ambiguous anyOf.
ConditionUnion = Annotated[
    Union[Magnetization, FixedTemperature, HeatFlux, Convection],
    Field(discriminator="kind"),
]
