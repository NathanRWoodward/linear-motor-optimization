from build123d import *
from ocp_vscode import show, show_clear, show_object
from functools import singledispatch
from optimize.cad.config import MagnetConfig, HalbachConfig, DualHalbachConfig
import copy

from optimize.cad.utils import *


def create_magnet(config: MagnetConfig) -> Part:
    result: Part
    with BuildPart(mode=Mode.PRIVATE) as part:
        with BuildSketch(Plane.YX):
            Rectangle(config.length, config.width, align=(Align.MIN, Align.MIN))

        extrude(amount=config.thickness, dir=Axis.Z.direction)
    result = part.part
    result.color = (0.5, 0.5, 0.5)
    result.label = "Magnet Body"
    result.material = "Neodymium"

    if config.debug_labels:
        result.color = (0.5, 0.5, 0.5, 0.0)
        all_parts = []

        # Split the magnet in half and color the two halves differently for easier visualization of the orientation
        bottom_half, top_half = split(
            result, bisect_by=Plane.YX.offset(-config.thickness / 2), keep=Keep.BOTH
        )
        top_half.color = (0.6, 0.1, 0.1)
        bottom_half.color = (0.1, 0.1, 0.6)
        all_parts += [top_half, bottom_half]

        # extrude text on each of the 4 faces for easier debugging
        faces: ShapeList[Face] = part.faces()
        labels = [
            {"label": "N", "color": (1, 0, 0), "face": faces[5]},
            {"label": "E", "color": (0, 1, 0), "face": faces[3]},
            {"label": "S", "color": (0, 0, 1), "face": faces[4]},
            {"label": "W", "color": (1, 1, 0), "face": faces[1]},
            {"label": "↓", "color": (1, 1, 1), "face": faces[2]},
            {"label": "↑", "color": (1, 1, 1), "face": faces[0]},
        ]
        labels = labels[-2:]

        font_size = min(config.thickness, config.width)

        for label in labels:
            face: Face = label["face"]
            with BuildPart(mode=Mode.PRIVATE) as label_part:
                with BuildSketch(face.offset(0.07), mode=Mode.PRIVATE) as label_sketch:
                    Text(
                        label["label"],
                        font_size=font_size,
                        font_style=FontStyle.REGULAR,
                        align=(Align.CENTER, Align.CENTER),
                        font="Consolas",
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
    clockwise: bool = True,
    material: str = "N52",
) -> Compound:
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0)]
    labels = ["N", "E", "S", "W"]

    locs = [
        Location(),  # North
        Location((0, 0, config.width), (0, 90, 0)),  # East
        Location((config.width, 0, config.thickness), (0, 180, 0)),  # South
        Location((config.thickness, 0, 0), (0, 270, 0)),  # West
    ]

    magnets: list[Part] = []

    template: Part = create_magnet(config)

    loc = Location()

    x_pos = 0
    i = start_offset
    for _ in range(config.count):

        magnet = template.located(Location((x_pos, 0, 0)) * locs[i])

        pole_pair = (i) // 4
        magnet.label = f"{labels[i]}_{pole_pair +1}|{material}"

        if not config.debug_labels:
            # only color the magnets if not debugging, otherwise the labels will show the magnet type
            magnet.color = colors[i]

        magnets.append(magnet)

        if i % 2 == 0:
            x_step = config.width
        else:
            x_step = config.thickness

        x_pos += x_step

        if clockwise:
            i = (i + 1) % 4
        else:
            i = (i - 1) % 4

    return Compound(children=magnets, label="Halbach Array")


def create_dual_halbach(config: DualHalbachConfig) -> Compound:

    array_1 = create_halbach(config, 3, True)
    array_1.move(
        Location(
            (
                0,
                config.gap / 2,
                config.length,
            ),
            (-90, 0, 0),
        )
    )
    array_1.label = "Side A"

    array_2 = create_halbach(config, 1, False)

    array_2.move(
        Location(
            (
                0,
                -config.thickness - config.gap / 2,
                config.length,
            ),
            (-90, 0, 0),
        )
    )
    array_2.label = "Side B"

    return Compound(children=[array_1, array_2], label="Halbach")


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
