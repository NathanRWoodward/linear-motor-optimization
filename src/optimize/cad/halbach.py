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

    if config.debug_labels:
        all_parts = [result]
        # extrude text on each of the 4 faces for easier debugging
        faces = part.faces()
        labels = [
            {"label": "N", "color": (1, 0, 0), "face": faces[5]},
            {"label": "E", "color": (0, 1, 0), "face": faces[3]},
            {"label": "S", "color": (0, 0, 1), "face": faces[4]},
            {"label": "W", "color": (1, 1, 0), "face": faces[1]},
            {"label": "↓↓↓↓", "color": (0, 0, 0), "face": faces[2]},
            {"label": "↑↑↑↑", "color": (0, 0, 0), "face": faces[0]},
        ]

        for label in labels:
            face = label["face"]
            with BuildPart() as label_part:
                with BuildSketch(face):
                    Text(
                        label["label"], font_size=3, align=(Align.CENTER, Align.CENTER)
                    )
                extrude(amount=0.01, dir=face.normal_at().to_tuple())
            label_part.part.color = label["color"]
            label_part.part.label = label["label"]
            all_parts.append(label_part.part)

        result = Compound(children=all_parts, label="Magnet")

    return result


# def create_halbach(
#     config: HalbachConfig,
#     start_offset: int = 0,
# ) -> Compound:
#     colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0)]
#     labels = ["N", "E", "S", "W"]
#     magnets = []

#     magnet: Part = create_magnet(config)
#     magnet.color = colors[0 + start_offset]
#     magnet.label = f"{labels[0 + start_offset]}_1"
#     magnets.append(magnet)

#     pos = config.width
#     rot = 0
#     for i in range(1, config.count):

#         axis = Axis((pos, 0, 0), (0, 1, 0))
#         loc = Location()
#         magnet = magnet.moved(loc)
#         magnet = magnet.rotate(axis, 90)
#         # magnet.move(Location((pos, 0, 0)))

#         mag_type = (i + start_offset) % 4

#         if not config.debug_labels:
#             # only color the magnets if not debugging, otherwise the labels will show the magnet type
#             magnet.color = colors[mag_type]

#         pole_pair = (i) // 4
#         magnet.label = f"{labels[mag_type]}_{pole_pair +1}"
#         magnets.append(magnet)

#         if i % 2 == 0:
#             pos += config.width
#         else:
#             pos += config.thickness
#         rot += 90

#     return Compound(children=magnets, label="Halbach Array")


def create_halbach(
    config: HalbachConfig,
    start_offset: int = 0,
) -> Compound:
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0)]
    labels = ["N", "E", "S", "W"]
    magnets = []

    template: Part = create_magnet(config)

    # magnet.color = colors[0 + start_offset]
    # magnet.label = f"{labels[0 + start_offset]}_1"
    # magnets.append(magnet)
    loc = Location()
    xform = Matrix()

    x_pos = 0

    pos = 0
    rot = 0
    for i in range(config.count):

        # magnet.move(Location((pos, 0, 0)))
        magnet = copy.deepcopy(template)

        mag_type = (i + start_offset) % 4

        if not config.debug_labels:
            # only color the magnets if not debugging, otherwise the labels will show the magnet type
            magnet.color = colors[mag_type]

        pole_pair = (i) // 4
        magnet.label = f"{labels[mag_type]}_{pole_pair +1}"
        magnet.locate(loc)
        magnets.append(Compound.make_triad(axes_scale=2).locate(loc))
        magnets.append(magnet)

        # axis = Axis((pos, 0, 0), (0, 1, 0))
        # loc = Location()
        # magnet = magnet.moved(loc)
        # magnet = magnet.rotate(axis, 90)

        if i % 2 == 0:
            x_step = config.width
            # pos += config.width
            # loc *= Location((config.width, 0, 0))
        else:
            x_step = config.thickness
            # pos += config.thickness
            # loc *= Location((config.thickness, 0, 0))

        x_pos += x_step
        # Rotate the current loc by 90 degrees around this axis for the next magnet
        # # loc.to_tuple
        # axis_origin: VectorLike = (x_pos, 0, 0)
        # axis_direction: VectorLike = (0, -1, 0)
        # angle: float = 90
        # test = Location(axis_origin, axis_direction, angle)

        # transform = (
        #     Location((x_pos, 0, 0)) * Rotation((0, 90, 0)) * Location((-x_pos, 0, 0))
        # )

        # magnets.append(Compound.make_triad(axes_scale=2).locate(test))
        axis = Axis((x_pos, 0, 0), (0, 1, 0))
        magnets.append(create_debug_arrow(axis))

        new_location = rotate_around_axis(loc, axis, 90)
        magnets.append(Compound.make_triad(axes_scale=5).locate(new_location))

        loc_tmp = copy.deepcopy(loc)

        origin = Location()
        rotated_origin = origin * Location((x_pos, 0, 0))
        rotated_origin *= Rotation((0, 90, 0))
        # magnets.append(Compound.make_triad(axes_scale=2).locate(rotated_origin))

        loc = copy.deepcopy(new_location)
        # loc *= Location((x_step, 0, 0))

        # rot += 90

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
