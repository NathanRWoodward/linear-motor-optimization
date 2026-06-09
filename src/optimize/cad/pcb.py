from build123d import *
from ocp_vscode import show, show_clear


def pcb_base(length: float, height: float, thickness: float) -> Part:
    with BuildPart() as part:
        with BuildSketch(Plane.XZ):
            Rectangle(length, height, align=(Align.MIN, Align.MIN))

        extrude(amount=thickness, dir=Axis.Y.direction)
    part.part.color = (0.5, 0.8, 0.5)
    return part.part


def rotate_2d(point: tuple[float, float], angle: float) -> tuple[float, float]:
    """Rotate a 2D point by a given angle in degrees"""
    import math

    radians = math.radians(angle)
    cos_angle = math.cos(radians)
    sin_angle = math.sin(radians)

    x, y = point
    x_new = x * cos_angle - y * sin_angle
    y_new = x * sin_angle + y * cos_angle

    return (x_new, y_new)


class Vec2:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> "Vec2":
        return Vec2(self.x / scalar, self.y / scalar)

    def rotate(self, angle: float, center: "Vec2" = None) -> "Vec2":
        """Rotate the vector by a given angle in degrees around a center point"""
        import math

        if center is None:
            center = Vec2(0, 0)

        radians = math.radians(angle)
        cos_angle = math.cos(radians)
        sin_angle = math.sin(radians)

        # Translate the point to the origin
        translated_x = self.x - center.x
        translated_y = self.y - center.y

        # Rotate the point
        rotated_x = translated_x * cos_angle - translated_y * sin_angle
        rotated_y = translated_x * sin_angle + translated_y * cos_angle

        # Translate back to the original position
        final_x = rotated_x + center.x
        final_y = rotated_y + center.y

        return Vec2(final_x, final_y)


class Rect:
    def __init__(self, min: Vec2, max: Vec2):
        self.min = min
        self.max = max


class CoilCorner:
    def __init__(
        self,
        center: Vec2 = Vec2(0, 0),
        radius_outside: float = 0,
        start_angle: float = 0,
    ):
        self.center: Vec2 = center
        self.radius_outside: float = radius_outside

        angles = [start_angle, start_angle - 45, start_angle - 90]
        vector = Vec2(radius_outside, 0)
        self.vec_points = [
            vector.rotate(angle, Vec2(0, 0)) + center for angle in angles
        ]

        self.points = [(p.x, p.y) for p in self.vec_points]


class CoilTurn:

    def __init__(self, centers: Rect, outside_radius: float):
        self.top_left: CoilCorner = CoilCorner(
            center=Vec2(centers.min.x, centers.max.y),
            radius_outside=outside_radius,
            start_angle=180,
        )
        self.top_right: CoilCorner = CoilCorner(
            center=Vec2(centers.max.x, centers.max.y),
            radius_outside=outside_radius,
            start_angle=90,
        )
        self.bottom_right: CoilCorner = CoilCorner(
            center=Vec2(centers.max.x, centers.min.y),
            radius_outside=outside_radius,
            start_angle=0,
        )
        self.bottom_left: CoilCorner = CoilCorner(
            center=Vec2(centers.min.x, centers.min.y),
            radius_outside=outside_radius,
            start_angle=-90,
        )


def oval_coil_trace(
    width: float,
    height: float,
    thickness: float,
    trace_width: float,
    trace_space: float,
    min_bend_radius: float,
    min_inner_gap: float,
) -> Part:

    if min_inner_gap < 2 * min_bend_radius:
        min_inner_gap = 2 * min_bend_radius

    min_outside_radius = min_bend_radius + trace_width
    # Calculate the number of turns that can fit in the given width and height (take the smaller of the two)
    arc_center_top_left = min_inner_gap / 2
    num_turns = 0
    while True:
        arc_center_top_left += trace_width
        if arc_center_top_left >= width / 2 or arc_center_top_left >= height / 2:
            break
        arc_center_top_left += trace_space
        num_turns += 1

    print(f"Turns: {num_turns}")

    # Now that we know the max number of turns, calculate the radius of the outermost bend
    # distance_to_outer_bend = (
    #     trace_width / 2 + trace_space * turns + trace_width * (turns - 1) / 2
    # )
    # bend_radius_outside = distance_to_outer_bend + min_bend_radius

    inside_radii = [
        min_bend_radius + i * trace_width + (i - 1) * trace_space
        for i in range(1, num_turns + 1)
    ]
    # Sort outside to inside
    inside_radii = inside_radii[::-1]
    outside_radii = [r + trace_width for r in inside_radii]
    centerline_radii = [
        (in_r + out_r) / 2 for in_r, out_r in zip(inside_radii, outside_radii)
    ]

    # Draw the arcs of the upper left quadrant of the coil, starting from the outside
    parts = []

    turns = []

    for i in range(num_turns):
        if False:
            if outside_radii[0] * 2 > width or outside_radii[0] * 2 > height:
                raise ValueError(
                    f"Cannot fit the coil with the given parameters. The outermost bend radius ({outside_radii[0]:.2f} mm) is too large for the width ({width} mm) and height ({height} mm)."
                )

            arc_centers = Rect(
                min=Vec2(outside_radii[0], outside_radii[0]),
                max=Vec2(width - outside_radii[0], height - outside_radii[0]),
            )
            turn = CoilTurn(arc_centers, outside_radii[i])
            turns.append(turn)
        else:
            tmp = min_outside_radius + i * trace_width + i * trace_space
            arc_centers = Rect(
                min=Vec2(tmp, tmp),
                max=Vec2(width - tmp, height - tmp),
            )
            turn = CoilTurn(arc_centers, min_outside_radius)
            turns.append(turn)
        # R
    # turns = [CoilTurn(arc_centers, r) for r in outside_radii]

    for index, turn in enumerate(turns):
        with BuildPart() as arc_part:
            with BuildSketch(Plane.XZ) as sketch:
                with BuildLine() as line:

                    ThreePointArc(*turn.top_left.points)
                    Line(turn.top_left.points[-1], turn.top_right.points[0])
                    ThreePointArc(*turn.top_right.points)
                    Line(turn.top_right.points[-1], turn.bottom_right.points[0])
                    ThreePointArc(*turn.bottom_right.points)
                    Line(turn.bottom_right.points[-1], turn.bottom_left.points[0])
                    ThreePointArc(*turn.bottom_left.points)
                    Line(turn.bottom_left.points[-1], turn.top_left.points[0])

                make_face()

                offset(
                    amount=-trace_width,
                    side=Side.RIGHT,
                    kind=Kind.ARC,
                    mode=Mode.SUBTRACT,
                )

            extrude(amount=thickness, dir=-Axis.Y.direction)
        parts.append(arc_part.part)

    print(f"Inside Radii: {inside_radii}")
    print(f"Outside Radii: {outside_radii}")

    return Compound(children=parts, label="Coil Trace")


if __name__ == "__main__":
    show_clear()

    length = 25.4 * 4
    height = 35.0

    to_display = []

    base = pcb_base(
        length=length,
        height=height,
        thickness=1.6,
    )
    to_display.append(base)

    MILL_TO_MM = 25.4 * 0.001

    coil_1 = oval_coil_trace(
        width=12,
        height=height,
        thickness=0.5,
        trace_width=8 * MILL_TO_MM,
        trace_space=8 * MILL_TO_MM,
        min_bend_radius=16 * MILL_TO_MM,
        min_inner_gap=0 * MILL_TO_MM,
    )
    # to_display.append(coil_1)

    for i in range(5):
        coil = coil_1.moved(Location((i * 13, 0, 0)))
        to_display.append(coil)

    show(to_display)
