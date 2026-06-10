from build123d import *
from ocp_vscode import show, show_clear
from functools import singledispatch
from optimize.cad.config import MagnetConfig, HalbachConfig, DualHalbachConfig


def create_magnet(config: MagnetConfig, debug_labels: bool = True) -> Part:
    with BuildPart() as part:
        with BuildSketch(Plane.YX):
            Rectangle(config.length, config.width, align=(Align.MIN, Align.MIN))

        extrude(amount=config.thickness, dir=Axis.Z.direction)

        if debug_labels:
            # extrude text on each of the 4 faces for easier debugging
            labels = ["N", "E", "S", "W"]
            face_indexes = [5, 3, 4, 1]
            all_faces = part.faces()
            faces = [all_faces[i] for i in face_indexes]
            for i in range(4):
                face = faces[i]
                with BuildSketch(face):
                    Text(labels[i], font_size=3, align=(Align.CENTER, Align.CENTER))
                extrude(
                    amount=-0.01, dir=face.normal_at().to_tuple(), mode=Mode.SUBTRACT
                )
    return part.part


def create_halbach(
    config: HalbachConfig,
    start_offset: int = 0,
) -> Compound:
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0)]
    labels = ["N", "E", "S", "W"]
    magnets = []

    magnet: Part = create_magnet(config)
    magnet.color = colors[0 + start_offset]
    magnet.label = f"{labels[0 + start_offset]}_1"
    magnets.append(magnet)

    pos = config.width
    rot = 0
    for i in range(1, config.count):

        axis = Axis((pos, 0, 0), (0, 1, 0))
        loc = Location()
        magnet = magnet.moved(loc)
        magnet = magnet.rotate(axis, 90)
        # magnet.move(Location((pos, 0, 0)))

        mag_type = (i + start_offset) % 4
        magnet.color = colors[mag_type]

        pole_pair = (i) // 4
        magnet.label = f"{labels[mag_type]}_{pole_pair +1}"
        magnets.append(magnet)

        if i % 2 == 0:
            pos += config.width
        else:
            pos += config.thickness
        rot += 90

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
