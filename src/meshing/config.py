from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field
from rich.tree import Tree

from common.utils import COLORS
from elmer.physics import Physics
from physical.conditions import Condition, ConditionTarget, ConditionUnion
from physical.materials.properties import MaterialProperties


def conditions_for(tags: Iterable["EntityTag"], physics: Physics, target: ConditionTarget) -> list[Condition]:
    """
    Resolve the conditions of a given (physics, target) that apply to a region.

    Gathers every tag's ``conditions`` and keeps only those matching ``physics`` and ``target``.
    This is the uniform "find the conditions a region carries" lookup the sif writer's per-physics wiring uses, so the filter lives in one place rather than being re-derived at each call site.
    """
    matching: list[Condition] = []
    for tag in tags:
        for condition in tag.conditions:
            if condition.physics == physics and condition.target == target:
                matching.append(condition)
    return matching


class EntityTag(BaseModel):
    """
    A per-region override matched to a mesh entity by name.

    Carries information that is not a material property but still needs to reach the solver for a specific region, as a list of composable, self-describing `conditions` (doc 02): a `Magnetization` body force for a magnet block, a `FixedTemperature` boundary, etc.
    Each condition knows its physics, its body/boundary target, and how to emit its own Elmer keywords — so a region carries only the conditions it actually has, with no flat bag of optional scalars.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    tag: str = ""

    conditions: list[ConditionUnion] = Field(
        default_factory=list,
        description="Composable, self-describing conditions (body forces / boundary conditions) this region carries.",
    )

    def print_tree(self, tree: Tree) -> None:
        report: Tree = tree.add(COLORS.H2(f"Tag: {self.tag}"))
        for condition in self.conditions:
            report.add(COLORS.Prop(type(condition).__name__, f"{condition}"))


class MeshingConfig(BaseModel):
    """The single config that drives both the mesher and the sif writer."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    materials: list[MaterialProperties] = Field(default_factory=list)
    tags: list[EntityTag] = Field(default_factory=list)
    STEP: str = "data/geometry.step"
    global_mesh_size: float = Field(default=1.0, description="Global mesh size in meters")
