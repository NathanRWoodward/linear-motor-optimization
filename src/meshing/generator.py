import gmsh
from rich import print
from rich.tree import Tree
from common.utils import COLORS, title
from meshing.config import MeshingConfig
from meshing.mesh_entity import MeshEntity


class Generator:
    def __init__(self, config: MeshingConfig):
        self.input_filename = config.STEP

        filename_without_extension = self.input_filename.rsplit(".", 1)[0]

        self.name = filename_without_extension.rsplit("/", 1)[-1]
        self.output_filename = f"{filename_without_extension}.msh"

        # Interruptible does not work in a background thread (like when triggered by watchdog), so we set it to False to avoid warnings
        if gmsh.isInitialized():
            gmsh.clear()  # Wipes the current model geometry, meshes, and options
        else:
            gmsh.initialize(interruptible=False)

        # Enable importing labels from the STEP file, which can be used to identify different parts in the mesh
        gmsh.option.setNumber("Geometry.OCCImportLabels", 1)

        # Suppress terminal output for cleaner logs, especially when running in batch mode
        gmsh.option.setNumber("General.Terminal", 0)

        gmsh.model.occ.importShapes(self.input_filename)
        gmsh.model.occ.synchronize()

        self.EntityCounts = len(gmsh.model.getEntities(dim=3))
        print(f"Found {self.EntityCounts} entities in the STEP file.")
        self.Entities = [MeshEntity(*entity, config) for entity in gmsh.model.getEntities(dim=3)]

    def print_tree(self):
        tree = Tree(COLORS.H1(title(self.name)))

        for entity in self.Entities:
            entity.print_tree(tree)

        print(tree)
