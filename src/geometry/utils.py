from build123d import *

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


# def axis_angle_to_euler(axis, angle_rad, order="ZYX"):
#     """
#     Convert axis-angle to Euler angles (radians).

#     axis  : (x, y, z) rotation axis (need not be normalized)
#     angle : rotation magnitude in radians
#     order : intrinsic Euler order. "ZYX" returns (yaw, pitch, roll).

#     Returns a tuple of three angles in the requested order.
#     """
#     x, y, z = axis
#     n = math.sqrt(x * x + y * y + z * z)
#     if n < 1e-12:
#         return (0.0, 0.0, 0.0)  # no rotation
#     x, y, z = x / n, y / n, z / n

#     c = math.cos(angle_rad)
#     s = math.sin(angle_rad)
#     t = 1.0 - c

#     # Rodrigues rotation matrix
#     r00 = t * x * x + c
#     # r01 = t * x * y - s * z
#     # r02 = t * x * z + s * y
#     r10 = t * x * y + s * z
#     r11 = t * y * y + c
#     r12 = t * y * z - s * x
#     r20 = t * x * z - s * y
#     r21 = t * y * z + s * x
#     r22 = t * z * z + c

#     if order == "ZYX":
#         # yaw (Z), pitch (Y), roll (X)
#         sy = -r20
#         if sy > 1.0:
#             sy = 1.0
#         elif sy < -1.0:
#             sy = -1.0
#         pitch = math.asin(sy)

#         if abs(sy) < 1.0 - 1e-9:  # not at gimbal lock
#             roll = math.atan2(r21, r22)
#             yaw = math.atan2(r10, r00)
#         else:  # gimbal lock: pitch = ±90°
#             roll = math.atan2(-r12, r11)
#             yaw = 0.0
#         return (yaw, pitch, roll)

#     raise ValueError(f"Unsupported order: {order}")


# def axis_angle_to_rotation(axis, angle_rad) -> Rotation:
#     yaw, pitch, roll = axis_angle_to_euler(axis, angle_rad)
#     return Rotation((math.degrees(roll), math.degrees(pitch), math.degrees(yaw)))


# def rotate_position_around_axis(position: VectorLike, axis: Axis, angle: float) -> Vector:
#     # Create a rotation around the specified axis
#     axis_rotation = axis_angle_to_rotation(axis.direction, math.radians(angle))

#     # Move the position to the origin, apply the rotation, and move it back
#     rotated_position = (Location(-axis.position) * axis_rotation * Location(axis.position)) * Vector(position)

#     return rotated_position


# def extract_matrix_rotation(matrix: Matrix) -> Rotation:
#     # Extract the upper-left 3x3 rotation part of the matrix

#     # Calculate Euler angles from the rotation matrix
#     if abs(matrix[2, 0]) < 1.0:
#         pitch = math.asin(-matrix[2, 0])
#         roll = math.atan2(matrix[2, 1] / math.cos(pitch), matrix[2, 2] / math.cos(pitch))
#         yaw = math.atan2(matrix[1, 0] / math.cos(pitch), matrix[0, 0] / math.cos(pitch))
#     else:  # Gimbal lock case
#         pitch = math.pi / 2 if matrix[2, 0] <= -1.0 else -math.pi / 2
#         roll = math.atan2(-matrix[1, 2], matrix[1, 1])
#         yaw = 0.0

#     return Rotation((math.degrees(roll), math.degrees(pitch), math.degrees(yaw)))


# def rotate_around_axis(location: Location, axis: Axis, angle_deg: float) -> Location:

#     angle_rad = math.radians(angle_deg)

#     # Calculate the axis relative to the location's current position
#     axis.position -= location.position

#     matrix = Matrix()
#     matrix.rotate(axis, angle_rad)

#     orientation_rotation = extract_matrix_rotation(matrix)

#     # Extract the rotated XYZ position
#     position = matrix.multiply(Vector())

#     # Add back the original location's position to get the final rotated position
#     position = position + location.position

#     result = Location(position) * Rotation(location.orientation) * orientation_rotation

#     return result
