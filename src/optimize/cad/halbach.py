from build123d import *
from ocp_vscode import show, show_clear, show_object
from functools import singledispatch
from optimize.cad.config import MagnetConfig, HalbachConfig, DualHalbachConfig
import copy

from optimize.cad.utils import *


def create_magnet(config: MagnetConfig) -> Part:
    result: Part
    with BuildPart() as part:
        with BuildSketch(Plane.YX):
            Rectangle(config.length, config.width, align=(Align.MIN, Align.MIN))

        extrude(amount=config.thickness, dir=Axis.Z.direction)
    result = part.part
    result.color = (0.5, 0.5, 0.5)
    result.label = "Magnet Body"
    result.material = "Neodymium"

    if config.debug_labels:
        result.color = (0.5, 0.5, 0.5, 0.0)
        result._DisplayNode
        all_parts = [result]

        # Split the magnet in half and color the two halves differently for easier visualization of the orientation
        top_half, bottom_half = split(
            result, bisect_by=Plane.YX.offset(-config.thickness / 2), keep=Keep.BOTH
        )
        top_half.color = (0.4, 0, 0)
        bottom_half.color = (0, 0, 0.4)
        all_parts += [top_half, bottom_half]

        # extrude text on each of the 4 faces for easier debugging
        faces: ShapeList[Face] = part.faces()
        labels = [
            {"label": "N", "color": (1, 0, 0), "face": faces[5]},
            {"label": "E", "color": (0, 1, 0), "face": faces[3]},
            {"label": "S", "color": (0, 0, 1), "face": faces[4]},
            {"label": "W", "color": (1, 1, 0), "face": faces[1]},
            {"label": "↓↓", "color": (1, 1, 1), "face": faces[2]},
            {"label": "↑↑", "color": (1, 1, 1), "face": faces[0]},
        ]

        for label in labels:
            face: Face = label["face"]
            with BuildPart() as label_part:
                with BuildSketch(face.offset(0.05)) as label_sketch:
                    Text(
                        label["label"], font_size=3, align=(Align.CENTER, Align.CENTER)
                    )
                # extrude(amount=0.01, dir=face.normal_at().to_tuple())
                sketch = label_sketch.sketch
                sketch.color = label["color"]
                sketch.label = label["label"]
                all_parts.append(sketch)

        result = Compound(children=all_parts, label="Magnet")

    return result


def create_halbach(
    config: HalbachConfig,
    start_offset: int = 0,
) -> Compound:
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0)]
    labels = ["N", "E", "S", "W"]
    magnets = []

    template: Part = create_magnet(config)

    loc = Location()

    x_pos = 0

    for i in range(config.count):

        magnet = template.located(loc)

        mag_type = (i + start_offset) % 4
        pole_pair = (i) // 4
        magnet.label = f"{labels[mag_type]}_{pole_pair +1}"

        if not config.debug_labels:
            # only color the magnets if not debugging, otherwise the labels will show the magnet type
            magnet.color = colors[mag_type]

        magnets.append(magnet)

        if i % 2 == 0:
            x_step = config.width
        else:
            x_step = config.thickness

        x_pos += x_step

        axis = Axis((x_pos, 0, 0), (0, 1, 0))
        loc = rotate_around_axis(loc, axis, 90)
        # magnets.append(create_debug_arrow(axis))
        # magnets.append(Compound.make_triad(axes_scale=5).locate(loc))

    return Compound(children=magnets, label="Halbach Array")


def create_dual_halbach(config: DualHalbachConfig) -> Compound:

    array_1 = create_halbach(config, 0)
    array_1.move(Location((0, (config.gap / 2) + config.thickness, 0), (90, 0, 0)))
    array_1.label = "Halbach Array 1"

    array_2 = create_halbach(config, 2)

    array_2.move(Location((0, -config.gap / 2, 0), (90, 0, 0)))
    array_2.label = "Halbach Array 2"

    return Compound(children=[array_1, array_2], label="Dual Halbach Array")


if __name__ == "__main__":
    show_clear()

    assembly = create_dual_halbach(
        DualHalbachConfig(
            length=25.4,
            width=6.35,
            thickness=6.35,
            count=2 * 4,
            gap=5,
        )
    )

    show(assembly)
    # export_step(assembly, "halbach_array.step")
