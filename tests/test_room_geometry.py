import numpy as np

from scan2stage.room_geometry import fit_rectangular_footprint


def _wall(nx, ny, d, inliers):
    return {"plane": [nx, ny, 0.0, d], "normal": [nx, ny, 0.0], "inliers": inliers}


def test_rectangular_footprint_ignores_corridor_outliers():
    rng = np.random.default_rng(7)
    interior = np.column_stack([
        rng.uniform(-5.0, 5.0, 20000),
        rng.uniform(-12.5, 12.5, 20000),
    ])
    corridor_outliers = np.column_stack([
        rng.uniform(5.5, 8.0, 1500),
        rng.uniform(-12.5, 12.5, 1500),
    ])
    pts = np.vstack([interior, corridor_outliers])
    walls = [
        _wall(1.0, 0.0, 5.0, 9000),
        _wall(1.0, 0.0, -5.0, 8500),
        _wall(0.0, 1.0, 12.5, 10000),
        _wall(0.0, 1.0, -12.5, 9800),
    ]
    rect = fit_rectangular_footprint(pts, walls)
    dims = sorted([rect["width_m"], rect["length_m"]])
    assert np.allclose(dims, [10.0, 25.0], atol=0.2)
    assert len(rect["corners_xy_m"]) == 4
    assert rect["outlier_fraction"] > 0.02


def test_rectangular_footprint_falls_back_without_walls():
    rng = np.random.default_rng(3)
    pts = np.column_stack([rng.uniform(-2, 2, 5000), rng.uniform(-4, 4, 5000)])
    rect = fit_rectangular_footprint(pts, [])
    assert len(rect["corners_xy_m"]) == 4
    assert rect["u_method"] == "trimmed_quantile"
    assert rect["v_method"] == "trimmed_quantile"
