import numpy as np

from scan2stage.structural_scene import (
    build_topview_layers,
    detect_fault_lines,
    estimate_shooting_direction,
    metric_target_hypothesis,
)


def test_topview_builds_height_slices():
    pts = np.array([
        [0.0, 0.0, 0.02],
        [0.0, 0.0, 0.50],
        [0.0, 0.0, 1.10],
        [0.5, 0.0, 0.05],
    ])
    tv = build_topview_layers(pts, resolution_m=0.1)
    assert tv["density"].sum() == 4
    assert len(tv["height_slices"]) == 6
    assert sum(int(x.sum()) for x in tv["height_slices"]) == 4


def test_fault_line_requires_red_low_elongated_component():
    x = np.linspace(0.0, 1.0, 40)
    pts = np.column_stack([x, np.zeros_like(x), np.full_like(x, 0.03)])
    colors = np.tile([0.9, 0.08, 0.06], (len(pts), 1))
    tv = build_topview_layers(pts, colors=colors, resolution_m=0.05)
    lines = detect_fault_lines(tv)
    assert lines
    assert lines[0]["class_id"] == "fault_line"
    assert lines[0]["extent_major_m"] >= 0.35


def test_metric_target_hypothesis_prefers_plane_facing_shooting_direction():
    rng = np.random.default_rng(4)
    pts = np.column_stack([
        rng.uniform(-0.207, 0.207, 1200),
        rng.normal(0.0, 0.006, 1200),
        rng.uniform(0.80, 1.335, 1200),
    ])
    good = metric_target_hypothesis(pts, np.array([0.0, 1.0]))
    side = metric_target_hypothesis(pts, np.array([1.0, 0.0]))
    assert good["score"] > side["score"]
    assert good["orientation_score"] > 0.85
    assert 0.30 < good["width_m"] < 0.55


def test_shooting_direction_uses_tall_support_at_rear_end():
    rng = np.random.default_rng(3)
    floor = np.column_stack([
        rng.uniform(-2, 2, 1000),
        rng.uniform(-8, 8, 1000),
        rng.uniform(0.0, 0.05, 1000),
    ])
    rear = np.column_stack([
        rng.uniform(-2, 2, 500),
        rng.uniform(7.5, 8.0, 500),
        rng.uniform(0.5, 2.0, 500),
    ])
    pts = np.vstack([floor, rear])
    rect = {
        "axis_u": [1.0, 0.0],
        "axis_v": [0.0, 1.0],
        "u_bounds": [-2.0, 2.0],
        "v_bounds": [-8.0, 8.0],
    }
    result = estimate_shooting_direction(pts, rect)
    assert result["direction_xy"][1] > 0
    assert result["support_high"] > result["support_low"]
