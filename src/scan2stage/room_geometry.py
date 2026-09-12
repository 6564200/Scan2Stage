from __future__ import annotations

import json
from pathlib import Path
import math
import numpy as np

WORKING_HEIGHT_M = 2.5


def _plane_z(model: np.ndarray) -> float:
    a, b, c, d = model
    if abs(c) < 1e-8:
        raise ValueError("Plane is not horizontal")
    return float(-d / c)


def detect_floor(pcd, distance_threshold=0.025, ransac_n=3, num_iterations=1500):
    pts = np.asarray(pcd.points)
    if len(pts) < 100:
        raise ValueError("Not enough points for floor detection")
    z = pts[:, 2]
    cutoff = np.quantile(z, 0.30)
    idx = np.where(z <= cutoff)[0]
    low = pcd.select_by_index(idx.tolist())
    model, inliers = low.segment_plane(distance_threshold, ransac_n, num_iterations)
    model = np.asarray(model, dtype=float)
    n = model[:3]
    n /= np.linalg.norm(n)
    if abs(n[2]) < 0.85:
        raise RuntimeError(f"Lowest dominant plane is not horizontal: normal={n.tolist()}")
    if n[2] < 0:
        model *= -1
    return model, _plane_z(model), len(inliers)


def detect_walls(pcd, max_walls=20, distance_threshold=0.035, min_inliers=1200):
    work = pcd
    walls = []
    for _ in range(max_walls * 4):
        if len(work.points) < min_inliers:
            break
        model, inliers = work.segment_plane(distance_threshold, 3, 1200)
        if len(inliers) < min_inliers:
            break
        m = np.asarray(model, dtype=float)
        norm = np.linalg.norm(m[:3])
        if norm == 0:
            break
        m /= norm
        n = m[:3]
        if abs(n[2]) < 0.20:
            walls.append({"plane": m.tolist(), "normal": n.tolist(), "inliers": int(len(inliers))})
            if len(walls) >= max_walls:
                break
        work = work.select_by_index(inliers, invert=True)
    return walls


def _dominant_rect_axes(walls: list[dict]) -> tuple[np.ndarray, np.ndarray, float]:
    if not walls:
        return np.array([1.0, 0.0]), np.array([0.0, 1.0]), 0.0
    angles = []
    weights = []
    for w in walls:
        n = np.asarray(w["normal"][:2], dtype=float)
        if np.linalg.norm(n) < 1e-8:
            continue
        n /= np.linalg.norm(n)
        angles.append(math.atan2(n[1], n[0]))
        weights.append(float(w["inliers"]))
    a = np.asarray(angles)
    w = np.asarray(weights)
    phi = 0.25 * math.atan2(float(np.sum(w * np.sin(4 * a))), float(np.sum(w * np.cos(4 * a))))
    u = np.array([math.cos(phi), math.sin(phi)])
    v = np.array([-u[1], u[0]])
    return u, v, math.degrees(phi)


def _cluster_offsets(values, weights, tolerance=0.30):
    order = np.argsort(values)
    clusters = []
    for i in order:
        x = float(values[i]); wt = float(weights[i])
        if not clusters or abs(x - clusters[-1]["center"]) > tolerance:
            clusters.append({"center": x, "weight": wt, "members": 1})
        else:
            c = clusters[-1]
            total = c["weight"] + wt
            c["center"] = (c["center"] * c["weight"] + x * wt) / total
            c["weight"] = total
            c["members"] += 1
    return clusters


def _axis_boundaries(walls, axis, projections, trim=0.04):
    offsets = []
    weights = []
    for w in walls:
        plane = np.asarray(w["plane"], dtype=float)
        nxy = plane[:2]
        dot = float(np.dot(nxy, axis))
        if abs(dot) < 0.80:
            continue
        offsets.append(float(-plane[3] / dot))
        weights.append(float(w["inliers"]))
    fallback = np.quantile(projections, [trim, 1.0 - trim]).astype(float)
    if len(offsets) < 2:
        return float(fallback[0]), float(fallback[1]), [], "trimmed_quantile"
    clusters = _cluster_offsets(np.asarray(offsets), np.asarray(weights))
    candidates = sorted(clusters, key=lambda c: c["weight"], reverse=True)[:6]
    if len(candidates) < 2:
        return float(fallback[0]), float(fallback[1]), clusters, "trimmed_quantile"
    best = None
    span_ref = max(0.5, float(fallback[1] - fallback[0]))
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            a, b = sorted([candidates[i]["center"], candidates[j]["center"]])
            sep = b - a
            if sep < 0.25 * span_ref or sep > 1.35 * span_ref:
                continue
            score = candidates[i]["weight"] + candidates[j]["weight"]
            if best is None or score > best[0]:
                best = (score, a, b)
    if best is None:
        return float(fallback[0]), float(fallback[1]), clusters, "trimmed_quantile"
    return float(best[1]), float(best[2]), clusters, "wall_support"


def fit_rectangular_footprint(points_xy: np.ndarray, walls: list[dict], trim=0.04):
    u, v, angle_deg = _dominant_rect_axes(walls)
    pu = points_xy @ u
    pv = points_xy @ v
    u0, u1, uc, um = _axis_boundaries(walls, u, pu, trim)
    v0, v1, vc, vm = _axis_boundaries(walls, v, pv, trim)
    corners_local = np.array([[u0, v0], [u1, v0], [u1, v1], [u0, v1]], dtype=float)
    basis = np.column_stack([u, v])
    corners_xy = corners_local @ basis.T
    inside = (pu >= u0) & (pu <= u1) & (pv >= v0) & (pv <= v1)
    return {
        "corners_xy_m": corners_xy.tolist(),
        "width_m": float(u1 - u0),
        "length_m": float(v1 - v0),
        "orientation_deg": float(angle_deg),
        "axis_u": u.tolist(),
        "axis_v": v.tolist(),
        "u_bounds": [u0, u1],
        "v_bounds": [v0, v1],
        "u_method": um,
        "v_method": vm,
        "u_wall_clusters": uc,
        "v_wall_clusters": vc,
        "inside_fraction": float(np.mean(inside)),
        "outlier_fraction": float(1.0 - np.mean(inside)),
    }


def normalize_room(pcd, output_dir: str | Path, source_to_meters: np.ndarray, working_height_m: float = WORKING_HEIGHT_M):
    import open3d as o3d
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    floor_model, floor_z, floor_inliers = detect_floor(pcd)
    aligned = o3d.geometry.PointCloud(pcd)
    aligned.translate((0.0, 0.0, -floor_z))

    aligned_pts = np.asarray(aligned.points)
    z_all = aligned_pts[:, 2]
    keep_idx = np.where((z_all >= -0.05) & (z_all <= working_height_m))[0]
    room_pcd = aligned.select_by_index(keep_idx.tolist())
    pts = np.asarray(room_pcd.points)
    z = pts[:, 2]

    wall_idx = np.where((z > 0.15) & (z < working_height_m - 0.05))[0]
    walls = detect_walls(room_pcd.select_by_index(wall_idx.tolist()))
    rect = fit_rectangular_footprint(pts[:, :2], walls, trim=0.04)

    t_floor = np.eye(4)
    t_floor[2, 3] = -floor_z
    source_to_room = t_floor @ source_to_meters

    normalized_path = output_dir / "room_normalized.ply"
    o3d.io.write_point_cloud(str(normalized_path), room_pcd, write_ascii=False)
    report = {
        "schema_version": "0.5",
        "coordinate_system": {"units": "meters", "up": "z", "floor_z": 0.0},
        "working_volume": {"min_z_m": 0.0, "max_z_m": float(working_height_m)},
        "floor": {"plane_before_translation": floor_model.tolist(), "z_m": float(floor_z), "inliers": int(floor_inliers)},
        "points_before_height_clip": int(len(aligned.points)),
        "points_after_height_clip": int(len(room_pcd.points)),
        "removed_above_working_height": int(np.sum(z_all > working_height_m)),
        "wall_candidates": walls,
        "room_model": "rectangle",
        "rectangle": rect,
        "footprint_xy_m": rect["corners_xy_m"],
        "source_to_room": source_to_room.tolist(),
        "normalized_pointcloud": str(normalized_path),
    }
    (output_dir / "room_geometry.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report, room_pcd
