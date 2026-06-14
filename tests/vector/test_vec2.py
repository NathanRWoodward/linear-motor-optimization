import pytest
from common.vector import Vec2


def test_vec2_rotation():
    v = Vec2(1, 0)
    rotated_90 = v.rotate(90, Vec2(0, 0))
    assert abs(rotated_90.x) < 1e-6 and abs(rotated_90.y - 1) < 1e-6

    rotated_180 = v.rotate(180, Vec2(0, 0))
    assert abs(rotated_180.x + 1) < 1e-6 and abs(rotated_180.y) < 1e-6

    rotated_270 = v.rotate(270, Vec2(0, 0))
    assert abs(rotated_270.x) < 1e-6 and abs(rotated_270.y + 1) < 1e-6


def test_vec2_rotation_around_point():
    v = Vec2(2, 0)
    center = Vec2(1, 0)
    rotated_90 = v.rotate(90, center)
    assert abs(rotated_90.x - 1) < 1e-6 and abs(rotated_90.y - 1) < 1e-6

    rotated_180 = v.rotate(180, center)
    assert abs(rotated_180.x - 0) < 1e-6 and abs(rotated_180.y - 0) < 1e-6

    rotated_270 = v.rotate(270, center)
    assert abs(rotated_270.x - 1) < 1e-6 and abs(rotated_270.y + 1) < 1e-6


def test_vec2_rotation_non_origin():
    v = Vec2(2, 1)
    center = Vec2(1, 0)
    rotated_90 = v.rotate(90, center)
    assert abs(rotated_90.x - 1) < 1e-6 and abs(rotated_90.y - 2) < 1e-6

    rotated_180 = v.rotate(180, center)
    assert abs(rotated_180.x - 0) < 1e-6 and abs(rotated_180.y - 1) < 1e-6

    rotated_270 = v.rotate(270, center)
    assert abs(rotated_270.x - 1) < 1e-6 and abs(rotated_270.y + 1) < 1e-6


def test_vec2_rotation_full_circle():
    v = Vec2(1, 0)
    rotated_360 = v.rotate(360, Vec2(0, 0))
    assert abs(rotated_360.x - 1) < 1e-6 and abs(rotated_360.y) < 1e-6


def test_vec2_rotation_negative_angle():
    v = Vec2(1, 0)
    rotated_neg_90 = v.rotate(-90, Vec2(0, 0))
    assert abs(rotated_neg_90.x) < 1e-6 and abs(rotated_neg_90.y + 1) < 1e-6
