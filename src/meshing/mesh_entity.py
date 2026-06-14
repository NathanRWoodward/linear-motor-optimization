import gmsh
from rich.tree import Tree

KNOWN_MATERIALS = ["N52", "FR4", "Copper", "Air"]
IGNORE_PARTS = ["=>", "Solid", "Shape", "Assembly"]


class MeshEntity:
    def __init__(self, dim: int, tag: int):
        self.dim = dim
        self.tag = tag

        self.name_raw = gmsh.model.getEntityName(dim, tag)
        self.name_parts = _split_name(self.name_raw)

        self.material = _extract_material(self.name_parts)

        self.name = " ".join(self.name_parts)

    def print_tree(self, tree: Tree):
        report = tree.add(_prop("Tag", str(self.tag), "bold red"))
        report.add(_prop("Name", self.name))
        report.add(_prop("Name (Raw)", self.name_raw))
        report.add(_prop("Name (Parts)", self.name_parts))

        report.add(_prop("Dim", str(self.dim)))
        if self.material:
            report.add(_prop("Material", self.material))


def _split_name(name_raw: str) -> list[str]:
    parts = name_raw.split("/")

    # Remove extra info from build123d STEP exports
    parts = [part for part in parts if not _should_ignore_part(part)]

    return parts


def _prop(title: str, content: str = "", color: str = "bold cyan") -> Tree:
    if content == "":
        return Tree(f"[{color}]{title}[/{color}]")

    return f"[{color}]{title}[/{color}]: {content}"


def _tuple_fmt(t: tuple[float, ...], fmt: str = "5.2f") -> str:
    return f"({', '.join(f'{x:{fmt}}' for x in t)})"


def _should_ignore_part(part_name: str) -> bool:
    return any(ignore.casefold() in part_name.casefold() for ignore in IGNORE_PARTS)


def _extract_material(name_parts: list[str]) -> str:
    """Extract material from the name parts, removing it from the list if found"""
    for material in KNOWN_MATERIALS:
        for i, part in enumerate(name_parts):
            if material.casefold() in part.casefold():
                name_parts.pop(i)
                return material
    return None
