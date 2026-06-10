import os

os.environ["NATIVE_TESSELLATOR"] = "1"
from build123d import *
from optimize.cad.config import DualHalbachConfig
from optimize.cad.pcb import oval_coil_trace, CoilType
from optimize.cad.halbach import create_dual_halbach, create_magnet, create_halbach
from ocp_vscode import (
    Camera,
    Render,
    set_defaults,
    set_port,
    show,
    ignore_camera_warnings,
    show_all,
)
from optimize.constants import *


def main():

    length = 25.4 * 4
    height = 35.0

    to_display = []

    halbach_config = DualHalbachConfig()
    halbach_config.debug_labels = True

    halbach_config.count = 4 * 4  # 2 pole pairs

    halbach_config.length = IN_TO_MM * 1.0
    halbach_config.width = IN_TO_MM * (1 / 4)
    halbach_config.thickness = IN_TO_MM * (1 / 4)

    # magnet = create_magnet(halbach_config, debug_labels=True)
    # to_display.append(magnet)

    single = create_halbach(halbach_config)

    to_display.append(single)

    # halbach = create_dual_halbach(halbach_config)
    # to_display.append(halbach)

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
    # export_step(scene, step_filename)

    show(to_display, progress="", deviation=99)
