from ocp_vscode import show
from build123d import *
from rich.tree import Tree
from common.vector import Vec3
from geometry.config import DualHalbachConfig
from geometry.magnet import create_dual_halbach
from meshing.config import EntityTag, MeshingConfig
from meshing.generator import Generator
from physical.materials.air import Air
from physical.materials.neodymium import N52
from physical.units import U
from physical.materials.pcb import FR4
from common.utils import COLORS
from rich import print


def main():

    to_display = []

    config = DualHalbachConfig()
    config.debug_labels = True

    #  2 *N + 1 to ensure we start and end with opposite horizontal poles
    config.count = 2 * 2 + 1

    config.length = (1 * U.inch).to(U.mm).magnitude
    config.width = (1 / 4 * U.inch).to(U.mm).magnitude
    config.thickness = (1 / 4 * U.inch).to(U.mm).magnitude

    config.width = 5
    config.thickness = 5

    config.gap = 5

    # all_materials = {
    #     "FasdfsaefdR4": FR4(),
    #     "N5dd2": N52(),
    #     "Air": Air(),
    # }
    # matTree = Tree(COLORS.H1("Materials"))
    # for mat in all_materials.values():
    #     mat.print_tree(matTree)

    # print(matTree)

    # magnet = create_magnet(config, debug_labels=True)
    # to_display.append(magnet)

    # single = create_halbach(config, 0, clockwise=False)
    # # single.move(Location((0, 0, config.length), (-90, 0, 0)))
    # single.move(
    #     Location(
    #         (
    #             0,
    #             config.gap / 2,
    #             config.length,
    #         ),
    #         (-90, 0, 0),
    #     )
    # )
    # single.move(
    #     Location(
    #         (
    #             0,
    #             -config.thickness - config.gap / 2,
    #             config.length,
    #         ),
    #         (-90, 0, 0),
    #     )
    # )
    # to_display.append(single)

    #

    halbach = create_dual_halbach(config)
    to_display.append(halbach)

    # coil_1 = oval_coil_trace(
    #     width=12,
    #     height=height,
    #     thickness=CU_OZ_TO_MM * 20,
    #     trace_width=MILL_TO_MM * 16,
    #     trace_space=MILL_TO_MM * 8,
    #     min_bend_radius=MILL_TO_MM * 8 * 3,
    #     min_inner_gap=MILL_TO_MM * 100,
    #     coil_type=CoilType.OVAL,
    # )

    # for i in range(1):
    #     coil = coil_1.moved(Location((i * 13, 0, 0)))
    #     to_display.append(coil)

    scene = Compound(children=to_display)
    step_filename = "data/pcb_coil.step"
    show(scene, progress="", deviation=99)
    # return

    export_step(scene, step_filename)

    mesh_config = MeshingConfig()
    mesh_config.STEP = step_filename

    mesh_config.materials.append(N52())

    mag_strength = 800000 * (U.amp / U.meter)  # A/m, example value for N52 magnet
    Magnets = {
        "Mag_N": Vec3(0, 1, 0),
        "Mag_E": Vec3(1, 0, 0),
        "Mag_S": Vec3(0, -1, 0),
        "Mag_W": Vec3(-1, 0, 0),
    }

    for name, coercivity in Magnets.items():
        tag = EntityTag(tag=name)
        tag.magnetic_coercivity = U.Quantity(coercivity * mag_strength.magnitude, mag_strength.units)
        mesh_config.tags.append(tag)

    mesh_gen = Generator(mesh_config)
    mesh_gen.print_tree()

    print(f"{mag_strength}")
    print(f"{U.Quantity(Magnets['Mag_E'] * mag_strength.magnitude, mag_strength.units)}")
    # generate_mesh(step_filename)
