import numpy as np

from scan2stage.room_geometry import convex_hull_2d


def test_convex_hull_rectangle():
    pts = np.array([
        [0, 0], [4, 0], [4, 3], [0, 3],
        [2, 1], [1, 2], [3, 2],
    ], dtype=float)
    hull = convex_hull_2d(pts)
    assert len(hull) == 4
    assert {tuple(p) for p in hull} == {(0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0)}


def test_convex_hull_deduplicates_points():
    pts = np.array([[0, 0], [0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
    hull = convex_hull_2d(pts)
    assert len(hull) == 4
