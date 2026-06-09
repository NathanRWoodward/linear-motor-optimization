from build123d import *
from ocp_vscode import show, show_clear


def create_magnet(length: float, width: float, thickness: float) -> Part:
    with BuildPart() as part:
        with BuildSketch(Plane.YX):
            Rectangle(length, width, align=(Align.MIN, Align.MIN))

        extrude(amount=thickness, dir=Axis.Z.direction)
    return part.part


def halback_array(
    length: float,
    width: float,
    thickness: float,
    count: int,
    start_offset: int = 0,
) -> Compound:
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0)]
    labels = ["N", "E", "S", "W"]
    magnets = []

    magnet: Part = create_magnet(length, width, thickness)
    magnet.color = colors[0 + start_offset]
    magnet.label = f"{labels[0 + start_offset]}_1"
    magnets.append(magnet)

    pos = width
    rot = 0
    for i in range(1, count):

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
            pos += width
        else:
            pos += thickness
        rot += 90

    return Compound(children=magnets, label="Halbach Array")


def dual_halbach_array(
    length: float,
    width: float,
    thickness: float,
    count: int,
    gap: float,
) -> Compound:

    array_1 = halback_array(length, width, thickness, count, 0)
    array_1.move(Location((0, (gap / 2) + thickness, 0), (90, 0, 0)))
    array_1.label = "Halbach Array 1"

    array_2 = halback_array(length, width, thickness, count, 2)
    array_2.move(Location((0, -gap / 2, 0), (90, 0, 0)))
    array_2.label = "Halbach Array 2"

    return Compound(children=[array_1, array_2], label="Dual Halbach Array")


if __name__ == "__main__":
    show_clear()

    assembly = dual_halbach_array(
        length=25.4,
        width=6.35,
        thickness=6.35,
        count=2 * 4,
        gap=5,
    )
    show(assembly)
    # export_step(assembly, "halbach_array.step")
