from copy import deepcopy
import math

from build123d import *
import inspect

MATRIX_IDENTITY = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]


def create_debug_arrow(
    axis: Axis,
    length: float = 10,
    radius: float = 0.2,
    color: Color = Color("cyan"),
) -> Part:
    arrow_compound = Compound()

    proportion_body = 0.85
    proportion_head = 1 - proportion_body

    with BuildPart() as arrow:
        # Arrow stem
        Cylinder(
            radius=radius,
            height=length * proportion_body,
            align=[Align.CENTER, Align.CENTER, Align.MIN],
        )

        # Arrow head
        with Locations((0, 0, length * proportion_body)):
            Cone(
                bottom_radius=radius * 2.5,
                top_radius=0,
                height=length * proportion_head,
                align=[Align.CENTER, Align.CENTER, Align.MIN],
            )

    arrow_compound += arrow.part
    arrow_compound.color = color
    arrow_compound.label = "Debug Arrow"
    arrow_compound = arrow_compound.locate(axis.location)
    return arrow_compound


def axis_angle_to_euler(axis, angle_rad, order="ZYX"):
    """
    Convert axis-angle to Euler angles (radians).

    axis  : (x, y, z) rotation axis (need not be normalized)
    angle : rotation magnitude in radians
    order : intrinsic Euler order. "ZYX" returns (yaw, pitch, roll).

    Returns a tuple of three angles in the requested order.
    """
    x, y, z = axis
    n = math.sqrt(x * x + y * y + z * z)
    if n < 1e-12:
        return (0.0, 0.0, 0.0)  # no rotation
    x, y, z = x / n, y / n, z / n

    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    t = 1.0 - c

    # Rodrigues rotation matrix
    r00 = t * x * x + c
    r01 = t * x * y - s * z
    r02 = t * x * z + s * y
    r10 = t * x * y + s * z
    r11 = t * y * y + c
    r12 = t * y * z - s * x
    r20 = t * x * z - s * y
    r21 = t * y * z + s * x
    r22 = t * z * z + c

    if order == "ZYX":
        # yaw (Z), pitch (Y), roll (X)
        sy = -r20
        if sy > 1.0:
            sy = 1.0
        elif sy < -1.0:
            sy = -1.0
        pitch = math.asin(sy)

        if abs(sy) < 1.0 - 1e-9:  # not at gimbal lock
            roll = math.atan2(r21, r22)
            yaw = math.atan2(r10, r00)
        else:  # gimbal lock: pitch = ±90°
            roll = math.atan2(-r12, r11)
            yaw = 0.0
        return (yaw, pitch, roll)

    raise ValueError(f"Unsupported order: {order}")


def axis_angle_to_rotation(axis, angle_rad) -> Rotation:
    yaw, pitch, roll = axis_angle_to_euler(axis, angle_rad)
    return Rotation((math.degrees(roll), math.degrees(pitch), math.degrees(yaw)))


def rotate_position_around_axis(
    position: VectorLike, axis: Axis, angle: float
) -> Vector:
    # Create a rotation around the specified axis
    axis_rotation = axis_angle_to_rotation(axis.direction, math.radians(angle))

    # Move the position to the origin, apply the rotation, and move it back
    rotated_position = (
        Location(-axis.position) * axis_rotation * Location(axis.position)
    ) * Vector(position)

    return rotated_position


def rotate_around_axis(location: Location, axis: Axis, angle: float) -> Location:
    original = deepcopy(location)
    # Create a rotation around the specified axis
    # axis_origin = axis.position
    # axis_direction = axis.direction
    # axis_rotation = axis.location.orientation
    # # Convert the axis rotation to Euler angles
    # axis_rotation = axis_angle_to_rotation(axis_direction, math.radians(angle))
    # location_origin = original.position
    # axis_origin = Vector(1, 0, 0)
    angle = math.radians(angle)

    # Move the location to the origin, apply the rotation, and move it back

    matrix = Matrix()
    matrix.rotate(axis, angle)
    print(f"Rotation Matrix:\n{matrix}")

    delta_pos = axis.position - original.position

    position = Vector(original.position)
    # position = position + delta_pos

    position = matrix.multiply(position)

    orientation = original.orientation
    orientation = matrix.multiply(orientation)
    as_rot = axis_angle_to_rotation(axis.direction, angle)
    result = Location(position) * as_rot
    # position = position - delta_pos

    # origin = origin.rotate(axis, math.radians(angle))

    # origin = rotate_position_around_axis(og_pos, axis, angle)

    # axis_rotation = axis_angle_to_rotation(axis.direction, math.radians(angle))
    # origin *= Location(origin)

    # print(f"Original Position: {og_pos}")
    print(f"Rotated Position: {position}")

    # rotated_location = matrix * original

    # rotated_location = (
    #     location * Location(-axis_origin) * axis_rotation * Location(axis_origin)
    # )

    # report = f"""
    #             Original: {location}
    #             --------------
    #             Axis Origin: {axis.position.to_tuple()}
    #             Axis Direction: {axis.direction.to_tuple()}
    #             -------------
    #             Angle: {angle} degrees
    #             Resulting Rotation: {axis_rotation.to_tuple()}
    #             -------------
    #             Rotated Location: {rotated_location.to_tuple()}
    #         """
    # print(inspect.cleandoc(report))
    return result
