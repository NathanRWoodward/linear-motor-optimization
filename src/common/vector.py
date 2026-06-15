import math


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

    def magnitude(self) -> float:
        import math

        return math.sqrt(self.x**2 + self.y**2)

    def __repr__(self):
        return f"Vec2({self.x}, {self.y})"

    def __str__(self):
        return f"({self.x:.3f}, {self.y:.3f})"


class Rect:
    def __init__(self, min: Vec2, max: Vec2):
        self.min = min
        self.max = max

    @property
    def center(self) -> Vec2:
        return Vec2(
            (self.min.x + self.max.x) / 2,
            (self.min.y + self.max.y) / 2,
        )

    @center.setter
    def center(self, new_center: Vec2):
        current_center = self.center
        offset = new_center - current_center
        self.min += offset
        self.max += offset

    @property
    def size(self) -> Vec2:
        return Vec2(
            self.max.x - self.min.x,
            self.max.y - self.min.y,
        )

    @size.setter
    def size(self, new_size: Vec2):
        center = self.center
        self.min = Vec2(center.x - new_size.x / 2, center.y - new_size.y / 2)
        self.max = Vec2(center.x + new_size.x / 2, center.y + new_size.y / 2)


class Vec3:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vec3":
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> "Vec3":
        return Vec3(scalar * self.x, scalar * self.y, scalar * self.z)

    def __truediv__(self, scalar: float) -> "Vec3":
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)

    def magnitude(self) -> float:
        """Euclidean length |v| of the vector."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalized(self) -> "Vec3":
        """
        Return a unit vector in the same direction.

        Raises ``ValueError`` for a zero-length vector (which has no direction).
        Callers that want to tolerate zero should check ``magnitude()`` first.
        """
        mag: float = self.magnitude()
        if mag == 0:
            raise ValueError("cannot normalize a zero-length Vec3")
        return self / mag

    def __abs__(self) -> float:
        return self.magnitude()

    def __repr__(self) -> str:
        return f"Vec3({self.x}, {self.y}, {self.z})"

    def __str__(self):
        return repr(self)

    def __format__(self, format_spec):
        if format_spec.endswith("~"):
            format_spec = format_spec[:-1]
            return f"({format(self.x, format_spec)}, {format(self.y, format_spec)}, {format(self.z, format_spec)})"
        else:
            return f"({format(self.x, format_spec)}, {format(self.y, format_spec)}, {format(self.z, format_spec)})"

    def __rich__(self) -> str:
        return f"([red]{self.x:.3f}[/red], [green]{self.y:.3f}[/green], [blue]{self.z:.3f}[/blue])"


class Box:
    def __init__(self, min: Vec3, max: Vec3):
        self.min = min
        self.max = max

    @property
    def center(self) -> Vec3:
        return Vec3(
            (self.min.x + self.max.x) / 2,
            (self.min.y + self.max.y) / 2,
            (self.min.z + self.max.z) / 2,
        )

    @center.setter
    def center(self, new_center: Vec3):
        current_center = self.center
        offset = new_center - current_center
        self.min += offset
        self.max += offset

    @property
    def size(self) -> Vec3:
        return Vec3(
            self.max.x - self.min.x,
            self.max.y - self.min.y,
            self.max.z - self.min.z,
        )

    @size.setter
    def size(self, new_size: Vec3):
        center = self.center
        self.min = Vec3(center.x - new_size.x / 2, center.y - new_size.y / 2, center.z - new_size.z / 2)
        self.max = Vec3(center.x + new_size.x / 2, center.y + new_size.y / 2, center.z + new_size.z / 2)


class Quaternion:
    def __init__(self, w: float, x: float, y: float, z: float):
        self.w = w
        self.x = x
        self.y = y
        self.z = z

    def __mul__(self, other: "Quaternion") -> "Quaternion":
        """Hamilton product of two quaternions"""
        w1, x1, y1, z1 = self.w, self.x, self.y, self.z
        w2, x2, y2, z2 = other.w, other.x, other.y, other.z

        w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
        x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
        y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
        z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2

        return Quaternion(w, x, y, z)

    def conjugate(self) -> "Quaternion":
        """Conjugate of the quaternion"""
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def magnitude(self) -> float:
        import math

        return math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)

    def normalized(self) -> "Quaternion":
        mag = self.magnitude()
        if mag == 0:
            raise ValueError("Cannot normalize a zero-length quaternion")
        return Quaternion(self.w / mag, self.x / mag, self.y / mag, self.z / mag)

    def rotate_vector(self, vec: Vec3) -> Vec3:
        """Rotate a vector by this quaternion"""
        q_vec = Quaternion(0, vec.x, vec.y, vec.z)
        rotated_q = self * q_vec * self.conjugate()
        return Vec3(rotated_q.x, rotated_q.y, rotated_q.z)

    def to_rotation_matrix(self) -> list[list[float]]:
        """Convert the quaternion to a 3x3 rotation matrix"""
        w, x, y, z = self.w, self.x, self.y, self.z

        return [
            [1 - 2 * (y**2 + z**2), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x**2 + z**2), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x**2 + y**2)],
        ]

    def to_euler_angles(self) -> tuple[float, float, float]:
        """Convert the quaternion to Euler angles (yaw, pitch, roll) in degrees"""
        w, x, y, z = self.w, self.x, self.y, self.z

        # Yaw (Z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y**2 + z**2)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        # Pitch (Y-axis rotation)
        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)  # use 90 degrees if out of range
        else:
            pitch = math.asin(sinp)

        # Roll (X-axis rotation)
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x**2 + y**2)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        return (math.degrees(yaw), math.degrees(pitch), math.degrees(roll))

    @staticmethod
    def from_euler_angles(yaw: float, pitch: float, roll: float):
        """Create a quaternion from Euler angles (yaw, pitch, roll) in degrees"""
        yaw_rad = math.radians(yaw)
        pitch_rad = math.radians(pitch)
        roll_rad = math.radians(roll)

        cy = math.cos(yaw_rad * 0.5)
        sy = math.sin(yaw_rad * 0.5)
        cp = math.cos(pitch_rad * 0.5)
        sp = math.sin(pitch_rad * 0.5)
        cr = math.cos(roll_rad * 0.5)
        sr = math.sin(roll_rad * 0.5)

        return Quaternion(
            w=cy * cp * cr + sy * sp * sr,
            x=cy * cp * sr - sy * sp * cr,
            y=cy * sp * cr + sy * cp * sr,
            z=sy * cp * cr - cy * sp * sr,
        ).normalized()

    @staticmethod
    def from_axis_angle(axis: Vec3, angle_degrees: float) -> "Quaternion":
        """Create a quaternion from an axis and angle in degrees"""
        angle_rad = math.radians(angle_degrees)
        half_angle = angle_rad / 2
        sin_half_angle = math.sin(half_angle)

        return Quaternion(
            w=math.cos(half_angle),
            x=axis.x * sin_half_angle,
            y=axis.y * sin_half_angle,
            z=axis.z * sin_half_angle,
        ).normalized()

    @staticmethod
    def slerp(q1: "Quaternion", q2: "Quaternion", t: float) -> "Quaternion":
        """Spherical linear interpolation between two quaternions"""
        q1 = q1.normalized()
        q2 = q2.normalized()

        dot = q1.w * q2.w + q1.x * q2.x + q1.y * q2.y + q1.z * q2.z

        if dot < 0.0:
            q2 = Quaternion(-q2.w, -q2.x, -q2.y, -q2.z)
            dot = -dot

        if dot > 0.9995:
            # If the quaternions are very close, use linear interpolation
            result = Quaternion(
                w=q1.w + t * (q2.w - q1.w),
                x=q1.x + t * (q2.x - q1.x),
                y=q1.y + t * (q2.y - q1.y),
                z=q1.z + t * (q2.z - q1.z),
            ).normalized()
            return result

        theta_0 = math.acos(dot)
        theta = theta_0 * t

        sin_theta_0 = math.sin(theta_0)
        sin_theta = math.sin(theta)

        s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
        s1 = sin_theta / sin_theta_0

        return Quaternion(
            w=(s0 * q1.w) + (s1 * q2.w),
            x=(s0 * q1.x) + (s1 * q2.x),
            y=(s0 * q1.y) + (s1 * q2.y),
            z=(s0 * q1.z) + (s1 * q2.z),
        ).normalized()

    def __repr__(self):
        return f"Quaternion(w={self.w}, x={self.x}, y={self.y}, z={self.z})"

    def __str__(self):
        return f"({self.w:.3f}, {self.x:.3f}, {self.y:.3f}, {self.z:.3f})"


class CoordinateFrame:
    def __init__(self, origin: Vec3, orientation: Quaternion):
        self.origin = origin
        self.orientation = orientation

    def transform_position(self, position: Vec3) -> Vec3:
        """Transform a position from local to global coordinates"""
        rotated_position = self.orientation.rotate_vector(position)
        return self.origin + rotated_position

    def inverse_transform_position(self, position: Vec3) -> Vec3:
        """Transform a position from global to local coordinates"""
        translated_position = position - self.origin
        inverse_orientation = self.orientation.conjugate()
        return inverse_orientation.rotate_vector(translated_position)

    def transform_direction(self, direction: Vec3) -> Vec3:
        """Transform a direction vector (ignoring translation) from local to global coordinates"""
        return self.orientation.rotate_vector(direction)

    def inverse_transform_direction(self, direction: Vec3) -> Vec3:
        """Transform a direction vector (ignoring translation) from global to local coordinates"""
        inverse_orientation = self.orientation.conjugate()
        return inverse_orientation.rotate_vector(direction)

    def __mul__(self, other: "CoordinateFrame") -> "CoordinateFrame":
        """Combine two coordinate frames by applying this transformation followed by the other"""
        new_origin = self.transform_position(other.origin)
        new_orientation = self.orientation * other.orientation
        return CoordinateFrame(new_origin, new_orientation)

    def __rmul__(self, other: "CoordinateFrame") -> "CoordinateFrame":
        """Allow left multiplication to combine coordinate frames"""
        return self.__mul__(other)

    def __imul__(self, other: "CoordinateFrame") -> "CoordinateFrame":
        """In-place combination of coordinate frames"""
        combined = self * other
        self.origin = combined.origin
        self.orientation = combined.orientation
        return self

    def __str__(self):
        return f"CoordinateFrame(origin={self.origin}, orientation={self.orientation})"

    def __repr__(self):
        return f"CoordinateFrame(origin={self.origin}, orientation={self.orientation})"


def _vec3_pydantic_schema():
    from typing import Annotated
    from pydantic_core import core_schema

    class _V:
        @classmethod
        def __get_pydantic_core_schema__(cls, source, handler):
            def validate(v):
                if isinstance(v, Vec3):
                    return v
                if isinstance(v, dict):
                    return Vec3(v["x"], v["y"], v["z"])
                if isinstance(v, (list, tuple)) and len(v) == 3:
                    return Vec3(v[0], v[1], v[2])
                raise ValueError("expected a Vec3, a 3-element [x, y, z], or {x, y, z}")

            return core_schema.no_info_plain_validator_function(
                validate,
                serialization=core_schema.plain_serializer_function_ser_schema(lambda v: {"x": v.x, "y": v.y, "z": v.z}),
            )

        @classmethod
        def __get_pydantic_json_schema__(cls, core, handler):
            num = {"type": "number"}
            return {
                "type": "object",
                "properties": {"x": num, "y": num, "z": num},
                "required": ["x", "y", "z"],
                "description": "3D vector {x, y, z}",
            }

    return Annotated[Vec3, _V]


try:
    Vec3Field = _vec3_pydantic_schema()
except Exception:
    Vec3Field = Vec3
