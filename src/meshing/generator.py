import gmsh
from rich import print
from rich.tree import Tree
from common.utils import COLORS, title
from meshing.config import MeshingConfig
from meshing.mesh_entity import MeshEntity
from itertools import groupby


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

        # Group entities by material
        self.Entities.sort(key=lambda e: e.material.name if e.material else "")

        self.EntitiesByMaterial = {material: list(group) for material, group in groupby(self.Entities, key=lambda e: e.material)}

        if None in self.EntitiesByMaterial.keys():
            print(f"[red]Error: {len(self.EntitiesByMaterial[None])} entities do not have an associated material.[/red]")
            for entity in self.EntitiesByMaterial[None]:
                print(f" - Entity Tag: {entity.tag}, Name: {entity.name_raw}")

            raise Exception("All entities must have an associated material. Please check the error messages above.")

        for material, entities in self.EntitiesByMaterial.items():
            print(f"Material: {material.name}, Entity Count: {len(entities)}")

            # Further group entities by tags within each material
            entities.sort(key=lambda e: tuple(tag.tag for tag in e.config.tags if tag in e.entity_tags))

            entities_by_tags = {
                tags: list(group) for tags, group in groupby(entities, key=lambda e: tuple(tag.tag for tag in e.config.tags if tag in e.entity_tags))
            }
            for tags, tagged_entities in entities_by_tags.items():
                # Make a compount name for this group of materal + tags, which will be used for the physical group in gmsh
                group_name = "_".join(filter(None, [material.tag] + list(tags))).replace(" ", "_").upper()
                print(f"  Tags: {tags}, Entity Count: {len(tagged_entities)} -> Group Name: {group_name}")

                mesh_material = gmsh.model.addPhysicalGroup(3, [entity.tag for entity in tagged_entities], name=group_name)
                gmsh.model.setPhysicalName(3, mesh_material, group_name)

    def print_tree(self):
        tree = Tree(COLORS.H1(title(self.name)))

        for entity in self.Entities:
            entity.print_tree(tree)

        print(tree)
