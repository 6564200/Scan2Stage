from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np

DEFAULT_HEIGHT_SLICES = (
    (0.00, 0.15),
    (0.15, 0.40),
    (0.40, 0.80),
    (0.80, 1.20),
    (1.20, 1.60),
    (1.60, 2.20),
)


def _robust_span(values: np.ndarray, q: float = 0.02) -> tuple[float, float]:
    if len(values) == 0:
        return 0.0, 0.0
    lo, hi = np.quantile(values, [q, 1.0 - q])
    return float(lo), float(hi)


def build_topview_layers(
    points: np.ndarray,
    colors: np.ndarray | None = None,
    resolution_m: float = 0.05,
    height_slices: Iterable[tuple[float, float]] = DEFAULT_HEIGHT_SLICES,
) -> dict:
    """Rasterize a Z-up point cloud into XY structural layers.

    The returned arrays are intentionally geometry-first. They are used as a
    structural representation, not as a destructive mask over the source cloud.
    """
    points = np.asarray(points, dtype=float)
    if len(points) == 0:
        raise ValueError("Cannot rasterize an empty point cloud")
    if resolution_m <= 0:
        raise ValueError("resolution_m must be positive")

    x0, x1 = _robust_span(points[:, 0], q=0.005)
    y0, y1 = _robust_span(points[:, 1], q=0.005)
    nx = max(1, int(np.ceil((x1 - x0) / resolution_m)) + 1)
    ny = max(1, int(np.ceil((y1 - y0) / resolution_m)) + 1)

    ix = np.clip(((points[:, 0] - x0) / resolution_m).astype(int), 0, nx - 1)
    iy = np.clip(((points[:, 1] - y0) / resolution_m).astype(int), 0, ny - 1)

    density = np.zeros((ny, nx), dtype=np.int32)
    np.add.at(density, (iy, ix), 1)

    min_height = np.full((ny, nx), np.inf, dtype=np.float32)
    max_height = np.full((ny, nx), -np.inf, dtype=np.float32)
    np.minimum.at(min_height, (iy, ix), points[:, 2])
    np.maximum.at(max_height, (iy, ix), points[:, 2])
    empty = density == 0
    min_height[empty] = np.nan
    max_height[empty] = np.nan

    slices = []
    for low, high in height_slices:
        mask = (points[:, 2] >= low) & (points[:, 2] < high)
        layer = np.zeros((ny, nx), dtype=np.int32)
        np.add.at(layer, (iy[mask], ix[mask]), 1)
        slices.append(layer)

    color_mean = None
    if colors is not None and len(colors) == len(points):
        rgb = np.asarray(colors, dtype=float)
        if rgb.max(initial=0.0) > 1.5:
            rgb = rgb / 255.0
        sums = np.zeros((ny, nx, 3), dtype=np.float64)
        for channel in range(3):
            np.add.at(sums[..., channel], (iy, ix), rgb[:, channel])
        color_mean = np.zeros_like(sums, dtype=np.float32)
        valid = density > 0
        color_mean[valid] = (sums[valid] / density[valid, None]).astype(np.float32)

    return {
        "origin_xy_m": [x0, y0],
        "resolution_m": float(resolution_m),
        "shape_yx": [ny, nx],
        "density": density,
        "min_height": min_height,
        "max_height": max_height,
        "height_range": max_height - min_height,
        "height_slices": slices,
        "height_slice_ranges_m": [list(x) for x in height_slices],
        "color_mean": color_mean,
    }


def _neighbors(y: int, x: int, h: int, w: int):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w:
                yield yy, xx


def connected_components(mask: np.ndarray, min_cells: int = 1) -> list[np.ndarray]:
    mask = np.asarray(mask, dtype=bool)
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    for y, x in np.argwhere(mask):
        if seen[y, x]:
            continue
        stack = [(int(y), int(x))]
        seen[y, x] = True
        cells = []
        while stack:
            cy, cx = stack.pop()
            cells.append((cy, cx))
            for yy, xx in _neighbors(cy, cx, h, w):
                if mask[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True
                    stack.append((yy, xx))
        if len(cells) >= min_cells:
            out.append(np.asarray(cells, dtype=int))
    return out


def _component_boundary_segments(cells: np.ndarray, topview: dict) -> list[list[list[float]]]:
    """Return a compact rectilinear footprint boundary from occupied raster cells.

    Shared cell edges are removed and collinear boundary edges are merged. This
    preserves L/U/angled/stair-step partition geometry instead of reducing every
    structure to one PCA line.
    """
    res = float(topview["resolution_m"])
    x0, y0 = map(float, topview["origin_xy_m"])
    occupied = {(int(y), int(x)) for y, x in cells}

    horizontal: dict[int, list[tuple[int, int]]] = {}
    vertical: dict[int, list[tuple[int, int]]] = {}

    for y, x in occupied:
        if (y - 1, x) not in occupied:
            horizontal.setdefault(y, []).append((x, x + 1))
        if (y + 1, x) not in occupied:
            horizontal.setdefault(y + 1, []).append((x, x + 1))
        if (y, x - 1) not in occupied:
            vertical.setdefault(x, []).append((y, y + 1))
        if (y, x + 1) not in occupied:
            vertical.setdefault(x + 1, []).append((y, y + 1))

    def merge(intervals):
        intervals = sorted(intervals)
        if not intervals:
            return []
        out = []
        start, end = intervals[0]
        for a, b in intervals[1:]:
            if a <= end:
                end = max(end, b)
            else:
                out.append((start, end))
                start, end = a, b
        out.append((start, end))
        return out

    segments = []
    for gy, intervals in horizontal.items():
        wy = y0 + gy * res
        for a, b in merge(intervals):
            segments.append([
                [x0 + a * res, wy],
                [x0 + b * res, wy],
            ])
    for gx, intervals in vertical.items():
        wx = x0 + gx * res
        for a, b in merge(intervals):
            segments.append([
                [wx, y0 + a * res],
                [wx, y0 + b * res],
            ])
    return segments


def _component_geometry(cells: np.ndarray, topview: dict) -> dict:
    res = float(topview["resolution_m"])
    x0, y0 = map(float, topview["origin_xy_m"])
    xy = np.column_stack([
        x0 + (cells[:, 1] + 0.5) * res,
        y0 + (cells[:, 0] + 0.5) * res,
    ])
    center = xy.mean(axis=0)
    centered = xy - center
    cov = np.cov(centered.T) if len(xy) > 1 else np.eye(2) * 1e-9
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    axes = eigvecs[:, order]
    local = centered @ axes
    lo = local.min(axis=0)
    hi = local.max(axis=0)
    ext = hi - lo + res

    ys, xs = cells[:, 0], cells[:, 1]
    min_h = topview["min_height"][ys, xs]
    max_h = topview["max_height"][ys, xs]
    valid_min = min_h[np.isfinite(min_h)]
    valid_max = max_h[np.isfinite(max_h)]
    z_min = float(np.quantile(valid_min, 0.05)) if len(valid_min) else 0.0
    z_max = float(np.quantile(valid_max, 0.95)) if len(valid_max) else 0.0

    return {
        "center_xy_m": center.tolist(),
        "axes_xy": axes.tolist(),
        "extent_major_m": float(max(ext)),
        "extent_minor_m": float(min(ext)),
        "height_min_m": z_min,
        "height_max_m": z_max,
        "height_m": float(max(0.0, z_max - z_min)),
        "boundary_segments_xy_m": _component_boundary_segments(cells, topview),
        "cell_count": int(len(cells)),
    }


def detect_structural_components(topview: dict) -> list[dict]:
    """Find large/tall 2D footprints without deleting them from target evidence."""
    density = topview["density"]
    height_range = np.nan_to_num(topview["height_range"], nan=0.0)
    tall = (density >= 2) & (height_range >= 0.45)
    comps = connected_components(tall, min_cells=4)
    result = []
    for i, cells in enumerate(comps):
        feat = _component_geometry(cells, topview)
        major = feat["extent_major_m"]
        minor = feat["extent_minor_m"]
        aspect = major / max(minor, 1e-6)
        if major >= 1.0 and minor <= 0.40 and aspect >= 3.0:
            cls = "partition_or_wall"
        elif 0.35 <= major <= 1.2 and 0.30 <= minor <= 1.0 and aspect < 2.2:
            cls = "compact_structure"
        elif major >= 1.0:
            cls = "large_structure"
        else:
            cls = "unknown_structure"
        feat.update({
            "id": f"struct_{i:03d}",
            "class_id": cls,
            "aspect_ratio": float(aspect),
        })
        result.append(feat)
    return result


def _range_score(value: float, low: float, high: float, margin: float) -> float:
    if low <= value <= high:
        return 1.0
    if value < low:
        return max(0.0, 1.0 - (low - value) / margin)
    return max(0.0, 1.0 - (value - high) / margin)


def apply_rear_zone_semantics(
    structures: list[dict],
    points: np.ndarray,
    shooting: dict,
    metal_proposals: list[dict],
    rear_band_m: float = 1.35,
) -> list[dict]:
    """Apply shooting-gallery semantics to structures near the rear/popper zone.

    A normal decorative partition is not a valid interpretation inside the
    popper area immediately in front of the rear bullet trap. The known
    scan_metal_shield_001 exemplar has an observed profile around 1.5-1.7 m
    major span and about 1.2 m height; broad ranges are intentionally used here
    because scene scans are noisy and partially occluded.
    """
    pts = np.asarray(points, dtype=float)
    direction = np.asarray(shooting["direction_xy"], dtype=float)
    direction /= max(np.linalg.norm(direction), 1e-9)
    rear_edge = float(np.quantile(pts[:, :2] @ direction, 0.985))

    metal_xy = []
    for obj in metal_proposals:
        center = obj.get("center_m")
        if center and len(center) >= 2:
            metal_xy.append(np.asarray(center[:2], dtype=float))

    for obj in structures:
        center = np.asarray(obj["center_xy_m"], dtype=float)
        rear_distance = float(rear_edge - center @ direction)
        obj["rear_proximity_m"] = rear_distance

        if rear_distance < -0.10 or rear_distance > rear_band_m:
            continue

        # Very large geometry on the extreme rear boundary is more likely the
        # rear wall / bullet-trap envelope than a free-standing shield.
        major = float(obj.get("extent_major_m", 0.0))
        minor = float(obj.get("extent_minor_m", 0.0))
        height = float(obj.get("height_m", 0.0))
        if rear_distance <= 0.22 and major >= 2.0:
            obj["context_zone"] = "rear_boundary"
            continue

        nearest_metal = None
        if metal_xy:
            nearest_metal = min(float(np.linalg.norm(center - m)) for m in metal_xy)
        near_metal = nearest_metal is not None and nearest_metal <= 1.15

        if obj.get("class_id") not in {
            "partition_or_wall",
            "compact_structure",
            "unknown_structure",
        }:
            continue

        length_score = _range_score(major, 1.20, 2.05, 0.70)
        height_score = _range_score(height, 0.85, 1.50, 0.65)
        thickness_score = _range_score(minor, 0.12, 0.65, 0.45)
        rear_score = max(0.0, 1.0 - max(rear_distance - 0.20, 0.0) / rear_band_m)
        context_score = 1.0 if near_metal else 0.45
        shield_score = (
            0.30 * length_score
            + 0.30 * height_score
            + 0.15 * thickness_score
            + 0.15 * rear_score
            + 0.10 * context_score
        )

        # Domain rule: in the popper/rear target zone do not call an interior
        # structure a decorative partition. Use the shield hypothesis when its
        # geometry is compatible; otherwise keep it explicitly unresolved.
        if shield_score >= 0.52:
            obj["class_id"] = "metal_shield"
            obj["confidence"] = float(shield_score)
            obj["classification_reason"] = "rear/popper zone + metal-shield geometry"
        elif obj.get("class_id") == "partition_or_wall":
            obj["class_id"] = "rear_zone_structure"
            obj["confidence"] = float(shield_score)
            obj["classification_reason"] = "partition is invalid in rear/popper zone; needs review"

        obj["context_zone"] = "rear/popper"
        obj["nearest_metal_target_m"] = nearest_metal

    return structures


def _red_mask(rgb: np.ndarray) -> np.ndarray:
    rgb = np.asarray(rgb, dtype=float)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # Robust to lighting: red dominance + moderate saturation proxy.
    return (r >= 0.22) & (r >= g * 1.25) & (r >= b * 1.25) & ((r - np.minimum(g, b)) >= 0.08)


def detect_fault_lines(topview: dict, max_floor_height_m: float = 0.15) -> list[dict]:
    color = topview.get("color_mean")
    if color is None:
        return []
    low_layer = topview["height_slices"][0].copy()
    if topview["height_slice_ranges_m"][0][1] < max_floor_height_m and len(topview["height_slices"]) > 1:
        low_layer = low_layer + topview["height_slices"][1]
    mask = (low_layer > 0) & _red_mask(color)
    comps = connected_components(mask, min_cells=3)
    lines = []
    for cells in comps:
        feat = _component_geometry(cells, topview)
        major = feat["extent_major_m"]
        minor = feat["extent_minor_m"]
        aspect = major / max(minor, 1e-6)
        if major < 0.35 or aspect < 2.2:
            continue
        confidence = min(1.0, 0.45 + 0.15 * min(aspect, 4.0) + 0.08 * min(major, 2.0))
        feat.update({
            "id": f"fault_line_{len(lines):03d}",
            "class_id": "fault_line",
            "aspect_ratio": float(aspect),
            "confidence": float(confidence),
        })
        lines.append(feat)
    return lines


def estimate_shooting_direction(points: np.ndarray, rectangle: dict) -> dict:
    """Estimate stage direction along the room's long axis.

    Direction sign is chosen toward the end with stronger tall structural support,
    which is usually the rear bullet-trap side in an indoor range. This is a prior,
    not a hard fact, and is reported with confidence.
    """
    pts = np.asarray(points, dtype=float)
    u = np.asarray(rectangle["axis_u"], dtype=float)
    v = np.asarray(rectangle["axis_v"], dtype=float)
    u_span = float(rectangle["u_bounds"][1] - rectangle["u_bounds"][0])
    v_span = float(rectangle["v_bounds"][1] - rectangle["v_bounds"][0])
    axis = v if v_span >= u_span else u
    proj = pts[:, :2] @ axis
    lo, hi = np.quantile(proj, [0.03, 0.97])
    band = max(0.5, 0.08 * float(hi - lo))
    tall = pts[:, 2] >= 0.40
    low_support = int(np.sum(tall & (proj <= lo + band)))
    high_support = int(np.sum(tall & (proj >= hi - band)))
    sign = 1.0 if high_support >= low_support else -1.0
    rear = axis * sign
    total = low_support + high_support
    confidence = abs(high_support - low_support) / total if total else 0.0
    return {
        "direction_xy": rear.tolist(),
        "rear_side": "high" if sign > 0 else "low",
        "support_low": low_support,
        "support_high": high_support,
        "confidence": float(confidence),
        "method": "long_axis+tall_end_support",
    }


def _local_patch(points: np.ndarray, center_xy: np.ndarray, radius_m: float) -> np.ndarray:
    d = points[:, :2] - center_xy
    return points[np.einsum("ij,ij->i", d, d) <= radius_m * radius_m]


def metric_target_hypothesis(
    patch_points: np.ndarray,
    shooting_direction_xy: np.ndarray,
    expected_width_m: float = 0.414,
    expected_height_m: float = 0.535,
) -> dict:
    """Score a local patch as a generic IPSC Metric Target.

    This intentionally accepts partial observations. B/S subtype is deferred until
    a generic target has been found.
    """
    pts = np.asarray(patch_points, dtype=float)
    if len(pts) < 12:
        return {"score": 0.0, "reason": "insufficient_points"}

    z_lo, z_hi = np.quantile(pts[:, 2], [0.05, 0.95])
    height = float(z_hi - z_lo)
    center = np.median(pts, axis=0)
    centered = pts - center
    cov = np.cov(centered.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvecs = eigvecs[:, order]
    local = centered @ eigvecs
    ext = np.quantile(local, 0.95, axis=0) - np.quantile(local, 0.05, axis=0)
    ext_sorted = np.sort(ext)[::-1]
    thickness = float(ext_sorted[-1])

    normal = eigvecs[:, -1]
    nxy = normal[:2]
    nxy_norm = np.linalg.norm(nxy)
    d = np.asarray(shooting_direction_xy, dtype=float)
    d /= max(np.linalg.norm(d), 1e-9)
    orientation = float(abs(np.dot(nxy / nxy_norm, d))) if nxy_norm > 1e-8 else 0.0

    # Width estimate is the strongest horizontal in-plane span.
    horiz = pts[:, :2] - np.median(pts[:, :2], axis=0)
    hc = np.cov(horiz.T) if len(horiz) > 1 else np.eye(2)
    hv, ha = np.linalg.eigh(hc)
    width_axis = ha[:, int(np.argmax(hv))]
    hp = horiz @ width_axis
    width = float(np.quantile(hp, 0.95) - np.quantile(hp, 0.05))

    def closeness(value, target, tolerance):
        return max(0.0, 1.0 - abs(value - target) / tolerance)

    width_score = closeness(width, expected_width_m, 0.28)
    # Partial targets may expose only 35-45% of their face; do not require full height.
    height_score = max(
        closeness(height, expected_height_m, 0.38),
        0.65 if 0.22 <= height <= 0.85 else 0.0,
    )
    thin_score = max(0.0, 1.0 - thickness / 0.18)
    planarity = float(1.0 - min(1.0, eigvals[0] / max(eigvals.sum(), 1e-9)))
    score = (
        0.25 * width_score
        + 0.20 * height_score
        + 0.20 * orientation
        + 0.15 * thin_score
        + 0.20 * planarity
    )
    return {
        "score": float(score),
        "center_m": center.tolist(),
        "width_m": width,
        "height_m": height,
        "thickness_m": thickness,
        "orientation_score": orientation,
        "planarity_score": planarity,
        "partial_observation_allowed": True,
    }


def generate_target_proposals(
    points: np.ndarray,
    topview: dict,
    shooting_direction_xy: np.ndarray,
    min_score: float = 0.42,
) -> list[dict]:
    """Generate soft hypotheses from vertical occupancy; structural points are retained."""
    slices = topview["height_slices"]
    if len(slices) < 4:
        return []
    vertical_votes = sum((layer > 0).astype(np.uint8) for layer in slices[1:5])
    mask = vertical_votes >= 2
    comps = connected_components(mask, min_cells=2)
    proposals = []
    for cells in comps:
        feat = _component_geometry(cells, topview)
        if feat["extent_major_m"] > 1.2:
            continue
        center = np.asarray(feat["center_xy_m"], dtype=float)
        patch = _local_patch(points, center, radius_m=0.42)
        hyp = metric_target_hypothesis(patch, shooting_direction_xy)
        if hyp["score"] < min_score:
            continue
        hyp.update({
            "id": f"metric_proposal_{len(proposals):03d}",
            "class_id": "ipsc_metric_target",
            "footprint": feat,
            "needs_subtype_classification": True,
            "possible_subtypes": ["ipsc_metric_target_b", "ipsc_metric_target_s"],
        })
        proposals.append(hyp)
    return proposals


def detect_rear_metal_proposals(
    points: np.ndarray,
    rectangle: dict,
    shooting: dict,
    rear_band_m: float = 1.0,
) -> list[dict]:
    pts = np.asarray(points, dtype=float)
    direction = np.asarray(shooting["direction_xy"], dtype=float)
    proj = pts[:, :2] @ direction
    rear_edge = float(np.quantile(proj, 0.985))
    mask = (
        (proj >= rear_edge - rear_band_m)
        & (pts[:, 2] >= 0.12)
        & (pts[:, 2] <= 1.45)
    )
    rear = pts[mask]
    if len(rear) < 20:
        return []
    # Coarse XY bins create candidate groups without making blue color mandatory.
    res = 0.08
    origin = rear[:, :2].min(axis=0)
    ij = np.floor((rear[:, :2] - origin) / res).astype(int)
    unique, counts = np.unique(ij, axis=0, return_counts=True)
    active = unique[counts >= 2]
    if len(active) == 0:
        return []
    amin = active.min(axis=0)
    shifted = active - amin
    grid = np.zeros((shifted[:, 1].max() + 1, shifted[:, 0].max() + 1), dtype=bool)
    grid[shifted[:, 1], shifted[:, 0]] = True
    comps = connected_components(grid, min_cells=2)
    out = []
    for comp in comps:
        cells_xy = np.column_stack([comp[:, 1], comp[:, 0]]) + amin
        center_xy = origin + (cells_xy.mean(axis=0) + 0.5) * res
        patch = _local_patch(rear, center_xy, 0.35)
        if len(patch) < 8:
            continue
        z0, z1 = np.quantile(patch[:, 2], [0.03, 0.97])
        height = float(z1 - z0)
        if height < 0.35:
            continue
        out.append({
            "id": f"rear_metal_{len(out):03d}",
            "class_id": "metal_target",
            "center_m": [float(center_xy[0]), float(center_xy[1]), float(np.median(patch[:, 2]))],
            "height_m": height,
            "rear_proximity_m": float(rear_edge - np.median(patch[:, :2] @ direction)),
            "context": "near_rear_bullet_trap",
            "confidence": float(min(0.95, 0.45 + 0.25 * min(height, 1.0))),
        })
    return out


def analyze_structural_scene(
    room_pcd,
    room_report: dict,
    output_dir: str | Path,
    resolution_m: float = 0.05,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    points = np.asarray(room_pcd.points, dtype=float)
    colors = np.asarray(room_pcd.colors, dtype=float) if room_pcd.has_colors() else None

    topview = build_topview_layers(points, colors=colors, resolution_m=resolution_m)
    structures = detect_structural_components(topview)
    fault_lines = detect_fault_lines(topview)
    shooting = estimate_shooting_direction(points, room_report["rectangle"])
    metric = generate_target_proposals(points, topview, np.asarray(shooting["direction_xy"]))
    metal = detect_rear_metal_proposals(points, room_report["rectangle"], shooting)
    structures = apply_rear_zone_semantics(structures, points, shooting, metal)

    npz_path = output_dir / "topview_layers.npz"
    np.savez_compressed(
        npz_path,
        density=topview["density"],
        min_height=topview["min_height"],
        max_height=topview["max_height"],
        height_range=topview["height_range"],
        **{f"slice_{i}": x for i, x in enumerate(topview["height_slices"])},
    )

    report = {
        "schema_version": "0.9",
        "method": "structural-first multi-height top-view + local 3D verification",
        "coordinate_system": {"units": "meters", "up": "z", "top_view_plane": "xy"},
        "policy": {
            "structural_geometry_is_evidence_not_a_destructive_mask": True,
            "prefer_recall_over_early_false-positive_rejection": True,
            "partial_target_observations_allowed": True,
            "metric_subtype_after_generic_detection": True,
            "metal_expected_near_rear_bullet_trap": True,
            "targets_expected_to_face_shooter": True,\n            "decorative_partitions_invalid_in_rear_popper_zone": True,
        },
        "topview": {
            "origin_xy_m": topview["origin_xy_m"],
            "resolution_m": topview["resolution_m"],
            "shape_yx": topview["shape_yx"],
            "height_slice_ranges_m": topview["height_slice_ranges_m"],
            "artifact": str(npz_path),
        },
        "shooting_direction": shooting,
        "structural_components": structures,
        "fault_lines": fault_lines,
        "metric_target_proposals": metric,
        "rear_metal_proposals": metal,
        "counts": {
            "structural_components": len(structures),
            "fault_lines": len(fault_lines),
            "metric_target_proposals": len(metric),
            "rear_metal_proposals": len(metal),
        },
    }
    path = output_dir / "structural_scene.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
