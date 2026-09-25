import numpy as np

from scan2stage.structural_scene import (
    apply_rear_zone_semantics,
    build_topview_layers,
    detect_structural_components,
    detect_fault_lines,
    detect_rear_bullet_trap,
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


def test_structural_component_keeps_actual_raster_footprint():
    # L-shaped tall structure: an axis-only representation would lose the corner.
    pts = []
    for x in np.arange(0.0, 1.05, 0.05):
        for z in (0.0, 0.7, 1.4):
            pts.append([x, 0.0, z])
    for y in np.arange(0.0, 0.85, 0.05):
        for z in (0.0, 0.7, 1.4):
            pts.append([1.0, y, z])
    tv = build_topview_layers(np.asarray(pts), resolution_m=0.05)
    structures = detect_structural_components(tv)
    assert structures
    boundary = structures[0]["boundary_segments_xy_m"]
    assert len(boundary) >= 4
    # Boundary must contain both horizontal-ish and vertical-ish segments.
    dx = [abs(s[1][0] - s[0][0]) for s in boundary]
    dy = [abs(s[1][1] - s[0][1]) for s in boundary]
    assert max(dx) > 0.5
    assert max(dy) > 0.4


def test_rear_zone_partition_is_not_left_as_decorative_partition():
    rng = np.random.default_rng(12)
    points = np.column_stack([
        rng.uniform(-2.0, 2.0, 2000),
        rng.uniform(-8.0, 8.0, 2000),
        rng.uniform(0.0, 0.15, 2000),
    ])
    # Strong tall rear support establishes +Y as rear.
    rear = np.column_stack([
        rng.uniform(-2.0, 2.0, 800),
        rng.uniform(7.7, 8.0, 800),
        rng.uniform(0.5, 2.0, 800),
    ])
    points = np.vstack([points, rear])
    shooting = {"direction_xy": [0.0, 1.0]}
    structures = [{
        "id": "struct_001",
        "class_id": "partition_or_wall",
        "center_xy_m": [0.0, 7.1],
        "extent_major_m": 1.6,
        "extent_minor_m": 0.35,
        "height_m": 1.2,
    }]
    metal = [{"center_m": [0.3, 7.35, 0.7]}]
    out = apply_rear_zone_semantics(structures, points, shooting, metal)
    assert out[0]["class_id"] == "metal_shield"
    assert out[0]["context_zone"] == "rear/popper"


def test_detect_rear_bullet_trap_finds_wide_tall_rear_face():
    rng = np.random.default_rng(33)
    floor = np.column_stack([
        rng.uniform(-2.0, 2.0, 2500),
        rng.uniform(-8.0, 8.0, 2500),
        rng.uniform(0.0, 0.05, 2500),
    ])
    trap = np.column_stack([
        rng.uniform(-1.8, 1.8, 1800),
        rng.normal(7.55, 0.035, 1800),
        rng.uniform(0.25, 2.0, 1800),
    ])
    pts = np.vstack([floor, trap])
    shooting = {"direction_xy": [0.0, 1.0]}
    result = detect_rear_bullet_trap(pts, shooting)
    assert result is not None
    assert result["class_id"] == "bullet_trap"
    assert result["width_m"] > 3.0
    assert result["height_m"] > 1.4
    assert result["front_projection_m"] > 7.3
