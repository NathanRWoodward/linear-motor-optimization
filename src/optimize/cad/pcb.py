from build123d import *
from ocp_vscode import show, show_clear


def pcb_base(length: float, width: float, thickness: float) -> Part:
    with BuildPart() as part:
        with BuildSketch(Plane.XZ):
            Rectangle(length, width, align=(Align.MIN, Align.MIN))

        extrude(amount=thickness, dir=Axis.Y.direction)
    part.part.color = (0.5, 0.8, 0.5)
    return part.part


if __name__ == "__main__":
    show_clear()

    base = pcb_base(
        length=25.4 * 4,
        width=35.0,
        thickness=1.6,
    )
    show(base)
