import gmsh
from rich import print
from rich.tree import Tree
from common.utils import COLORS, title
from meshing.config import EntityTag, MeshingConfig
from meshing.mesh_entity import MeshEntity
from physical.materials.properties import MaterialProperties
from itertools import groupby


class PhysicalGroup:
    """A single gmsh physical group, and the metadata needed to reconstruct the
    matching Elmer body.

    This is the shared contract between the gmsh mesher and the Elmer sif
    generator: both refer to a region by the same `name`, and Elmer references
    it in the mesh by the same integer `id` that gmsh assigned. Without keeping
    this id around, the Elmer `Target Bodies(...)` would have nothing to point
    at.
    """

    def __init__(self, dim: int, gmsh_id: int, name: str, material: MaterialProperties, tags: list[EntityTag], entity_tags: list[int]):
        self.dim = dim
        """Topological dimension of the group (3 = volume/body, 2 = surface/boundary)."""

        self.id = gmsh_id
        """The gmsh physical-group tag. This is the integer Elmer uses to target
        the region (ElmerGrid preserves physical-group ids as body/boundary ids)."""

        self.name = name
        """The compound MATERIAL_TAG1_TAG2 name, shared verbatim with Elmer."""

        self.material = material
        self.tags = tags
        """The EntityTag objects matched to this group (carry per-region overrides
        like fixed temperature, heat flux, and magnetization direction)."""

        self.entity_tags = entity_tags
        """The gmsh entity (volume) tags that make up this group."""

    def __repr__(self):
        return f"PhysicalGroup(id={self.id}, name={self.name!r}, material={self.material.name!r})"

    def physical_group_name(self) -> str:
        """Satisfies the `common.protocols.MeshGroupSource` protocol: the stable
        name both the mesher and the sif writer reference this region by."""
        return self.name


class Mesher:
    """Walk a STEP file, match each region to a material + tags, and create one
    gmsh physical group per (material, tags) combination.

    Formerly ``meshing.Generator``; renamed to ``Mesher`` (and the Elmer side to
    ``elmer.sim.SifWriter``) so the optimization driver can import both without a
    name clash.
    """

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

        # Shared mesh<->sim contract: every physical group we create here is
        # recorded so the Elmer sif generator can build a matching body that
        # targets the same gmsh id and reuses the same compound name.
        self.physical_groups: list[PhysicalGroup] = []

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

                entity_volume_tags = [entity.tag for entity in tagged_entities]
                mesh_material = gmsh.model.addPhysicalGroup(3, entity_volume_tags, name=group_name)
                gmsh.model.setPhysicalName(3, mesh_material, group_name)

                # Resolve the EntityTag objects (not just their string keys) so
                # the Elmer generator can read per-region overrides. All entities
                # in a group share the same tag set by construction.
                tag_objs = tagged_entities[0].entity_tags if tagged_entities else []
                self.physical_groups.append(
                    PhysicalGroup(
                        dim=3,
                        gmsh_id=mesh_material,
                        name=group_name,
                        material=material,
                        tags=tag_objs,
                        entity_tags=entity_volume_tags,
                    )
                )

    def print_tree(self):
        tree = Tree(COLORS.H1(title(self.name)))

        for entity in self.Entities:
            entity.print_tree(tree)

        print(tree)
