import numpy as np

from scan2stage.object_candidates import structural_mask, _candidate_features


def _rect():
    return {
        'axis_u': [1.0, 0.0],
        'axis_v': [0.0, 1.0],
        'u_bounds': [-5.0, 5.0],
        'v_bounds': [-12.5, 12.5],
    }


def test_structural_mask_removes_floor_and_wall_but_keeps_object():
    points = np.array([
        [0.0, 0.0, 0.02],
        [4.98, 0.0, 1.0],
        [0.0, 0.0, 1.0],
    ])
    normals = np.array([
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ])
    mask = structural_mask(points, _rect(), normals=normals)
    assert mask.tolist() == [True, True, False]


def test_candidate_features_return_robust_center_and_extents():
    rng = np.random.default_rng(11)
    pts = np.column_stack([
        rng.uniform(-0.20, 0.20, 1000),
        rng.uniform(-0.05, 0.05, 1000),
        rng.uniform(0.5, 1.5, 1000),
    ])
    feat = _candidate_features(pts)
    assert len(feat['center_m']) == 3
    assert len(feat['extents_m']) == 3
    assert feat['z_min_m'] >= 0.49
    assert feat['z_max_m'] <= 1.51
    assert feat['point_count'] == 1000
