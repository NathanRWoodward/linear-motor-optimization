import gmsh
from numpy.char import title
from rich import print
from rich.tree import Tree


class MeshEntity:
    def __init__(self, dim: int, tag: int):
        self.dim = dim
        self.tag = tag


class MeshGenerator:
    def __init__(self, filename: str):
        self.filename = filename

        self.ignore_parts = ["=>", "Solid", "Shape", "Assembly"]
        self.known_materials = ["N52", "FR4", "Copper", "Air"]

    def generate(self):
        generate_mesh(self.filename, self.show_gui, self.debug)


def generate_mesh(filename: str, show_gui: bool = False, debug: bool = True):

    def prop(title: str, content: str = "", color: str = "bold cyan") -> Tree:
        if content == "":
            return Tree(f"[{color}]{title}[/{color}]")

        return f"[{color}]{title}[/{color}]: {content}"

    def tuple_fmt(t: tuple[float, ...]) -> str:
        return f"({', '.join(f'{x:5.2f}' for x in t)})"

    def name_parts(name: str) -> str:
        parts = name.split("/")
        # Remove extra info from build123d STEP exports

        parts = [
            part
            for part in parts
            if not any(ignore.casefold() in part.casefold() for ignore in ignore_parts)
        ]

        return parts

    def extract_material(name: str) -> str:
        for material in known_materials:
            if material.casefold() in name.casefold():
                return material
        return None

    # Match the input STEP file name but with .msh extension for the output mesh
    filename_without_extension = filename.rsplit(".", 1)[0]
    filename_only = filename_without_extension.rsplit("/", 1)[-1]
    mesh_filename = f"{filename_without_extension}.msh"

    # Interruptible does not work in a background thread (like when triggered by watchdog), so we set it to False to avoid warnings
    gmsh.initialize(interruptible=False)

    # Enable importing labels from the STEP file, which can be used to identify different parts in the mesh
    gmsh.option.setNumber("Geometry.OCCImportLabels", 1)

    # Suppress terminal output for cleaner logs, especially when running in batch mode
    gmsh.option.setNumber("General.Terminal", 0)

    gmsh.model.occ.importShapes(filename)
    gmsh.model.occ.synchronize()

    entities = gmsh.model.getEntities(dim=3)

    tree = Tree(filename_only)

    # Gather metadata
    for dim, tag in entities:
        report = tree.add(f"[bold red]{tag}")

        nameRaw = gmsh.model.getEntityName(dim, tag)
        name = name_parts(nameRaw)

        # Get color data, RGBA
        color = gmsh.model.getColor(dim, tag)

        bounding_box = gmsh.model.getBoundingBox(dim, tag)

        volume = gmsh.model.occ.getMass(dim, tag)

        center_of_mass = gmsh.model.occ.getCenterOfMass(dim, tag)

        # asdf = gmsh.model.occ.get
        # report.add(prop("Attributes", ", ".join(asdf)))

        report.add(prop("Name", name))
        report.add(prop("Raw Name", nameRaw))
        report.add(prop("Dim", f"{dim}D"))

        bb = report.add(prop("Bounding Box"))
        bb.add(prop("Min", tuple_fmt(bounding_box[:3])))
        bb.add(prop("Max", tuple_fmt(bounding_box[3:])))

        report.add(prop("Volume", f"{volume:.2f}"))
        report.add(prop("Center of Mass", tuple_fmt(center_of_mass)))

    if debug:
        print(tree)

    gmsh.model.mesh.generate(3)

    gmsh.write(mesh_filename)

    if show_gui:
        gmsh.fltk.run()

    gmsh.finalize()
