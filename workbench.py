# ruff: noqa: F401, F841
from ocp_vscode import show
from build123d import *
from rich.tree import Tree
from common.vector import Vec3
from geometry.config import DualHalbachConfig
from geometry.magnet import create_dual_halbach
from meshing.config import EntityTag, MeshingConfig
from meshing.generator import Mesher
from physical.conditions import Magnetization
from physical.materials.air import Air
from physical.materials.neodymium import N52
from physical.units import U
from physical.materials.pcb import FR4
from common.utils import COLORS
from rich import print


def main():

    to_display = []

    config = DualHalbachConfig()
    config.debug_labels = False

    #  2 *N + 1 to ensure we start and end with opposite horizontal poles
    config.count = 2 * 2 + 1

    config.length = (1 * U.inch).to(U.mm).magnitude
    config.width = (1 / 4 * U.inch).to(U.mm).magnitude
    config.thickness = (1 / 4 * U.inch).to(U.mm).magnitude

    config.width = 5
    config.thickness = 5

    config.gap = 5

    halbach = create_dual_halbach(config)
    to_display.append(halbach)

    scene = Compound(children=to_display)
    step_filename = "data/pcb_coil.step"
    show(scene, progress="", deviation=99)
    # return

    export_step(scene, step_filename)

    mesh_config = MeshingConfig()
    mesh_config.STEP = step_filename

    mesh_config.materials.append(N52())

    # Magnetization direction per Halbach slot. Only the *direction* is
    # per-region; the magnitude |M| = Br/mu0 comes from the N52 material.
    Magnets = {
        "Mag_N": Vec3(0, 1, 0),
        "Mag_E": Vec3(1, 0, 0),
        "Mag_S": Vec3(0, -1, 0),
        "Mag_W": Vec3(-1, 0, 0),
    }

    for name, direction in Magnets.items():
        tag = EntityTag(tag=name, conditions=[Magnetization(direction=direction)])
        mesh_config.tags.append(tag)

    mesh_gen = Mesher(mesh_config)
    # mesh_gen.print_tree()

    # generate_mesh(step_filename)
