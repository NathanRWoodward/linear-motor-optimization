from common.vector import Vec3


def test_vec3_add():
    result = Vec3(1, 2, 3) + Vec3(4, 5, 6)
    assert result.x == 5 and result.y == 7 and result.z == 9


def test_vec3_sub():
    result = Vec3(5, 7, 9) - Vec3(1, 2, 3)
    assert result.x == 4 and result.y == 5 and result.z == 6


def test_vec3_mul():
    result = Vec3(1, 2, 3) * 3
    assert result.x == 3 and result.y == 6 and result.z == 9


def test_vec3_truediv():
    result = Vec3(6, 9, 12) / 3
    assert result.x == 2 and result.y == 3 and result.z == 4


def test_vec3_magnitude():
    # 1^2 + 2^2 + 2^2 = 9, sqrt = 3
    assert abs(Vec3(1, 2, 2).magnitude() - 3.0) < 1e-9


def test_vec3_magnitude_unit():
    assert abs(Vec3(1, 0, 0).magnitude() - 1.0) < 1e-9


def test_vec3_magnitude_zero():
    assert Vec3(0, 0, 0).magnitude() == 0.0


def test_vec3_magnitude_3_4_0():
    assert abs(Vec3(3, 4, 0).magnitude() - 5.0) < 1e-9
