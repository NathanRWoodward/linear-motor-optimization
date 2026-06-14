import re

import gmsh
from rich.tree import Tree

from common.utils import COLORS
from meshing.config import EntityTag, MeshingConfig
from physical.materials.properties import MaterialProperties


IGNORE_PARTS = ["=>", "Solid", "Shape", "Assembly"]


class MeshEntity:
    def __init__(self, dim: int, tag: int, config: MeshingConfig):
        self.dim = dim
        self.tag = tag
        self.config = config

        self.name_raw = gmsh.model.getEntityName(dim, tag)
        self.material = self._extract_material(self.name_parts)
        self.name = " ".join(self.name_parts)

    def print_tree(self, tree: Tree):

        report = tree.add(COLORS.H1(self.name))
        report.add(COLORS.Prop("Tag", f"{self.tag}"))

        report.add(COLORS.Prop("Name (Raw)", self.name_raw))
        report.add(COLORS.Prop("Name (Parts)", ", ".join(self.name_parts)))

        report.add(COLORS.Prop("Dim", str(self.dim)))

        if self.material:
            report.add(COLORS.Prop("Material", self.material.name))

        for tag in self.entity_tags:
            tag.print_tree(report)

    @property
    def name_parts(self) -> list[str]:
        parts = re.split(r"[/|]", self.name_raw)

        # Remove extra info from build123d STEP exports
        parts = [part for part in parts if not self._should_ignore_part(part)]

        return parts

    def _should_ignore_part(self, part_name: str) -> bool:
        return any(ignore.casefold() in part_name.casefold() for ignore in IGNORE_PARTS)

    def _extract_material(self, name_parts: list[str]) -> MaterialProperties | None:
        """Extract material from the name parts, removing it from the list if found"""
        for material in self.config.materials:
            for i, part in enumerate(name_parts):
                if material.tag.casefold() in part.casefold():
                    name_parts.pop(i)
                    return material
        return None

    @property
    def entity_tags(self) -> list[EntityTag]:
        """Extract entity tags from the name parts, removing them from the list if found"""
        tags = []
        for tag in self.config.tags:
            for i, part in enumerate(self.name_parts):
                if tag.tag.casefold() in part.casefold():
                    self.name_parts.pop(i)
                    tags.append(tag)
        return tags
