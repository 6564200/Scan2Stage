from __future__ import annotations

import json
from pathlib import Path
import numpy as np


def convex_hull_2d(points: np.ndarray) -> np.ndarray:
    pts = np.unique(np.asarray(points, dtype=float), axis=0)
    if len(pts) <= 2:
        return pts
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.asarray(lower[:-1] + upper[:-1], dtype=float)


def _plane_z(model: np.ndarray) -> float:
    a, b, c, d = model
    if abs(c) < 1e-8:
        raise ValueError("Plane is not horizontal")
    return float(-d / c)


def detect_floor(pcd, distance_threshold=0.025, ransac_n=3, num_iterations=1500):
    import open3d as o3d
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
        n *= -1
    floor_z = _plane_z(model)
    return model, floor_z, len(inliers)


def detect_walls(pcd, max_walls=12, distance_threshold=0.035, min_inliers=1500):
    import open3d as o3d
    work = pcd
    walls = []
    for _ in range(max_walls * 3):
        if len(work.points) < min_inliers:
            break
        model, inliers = work.segment_plane(distance_threshold, 3, 1200)
        if len(inliers) < min_inliers:
            break
        m = np.asarray(model, dtype=float)
        n = m[:3]
        norm = np.linalg.norm(n)
        if norm == 0:
            break
        m /= norm
        n = m[:3]
        if abs(n[2]) < 0.25:
            walls.append({"plane": m.tolist(), "normal": n.tolist(), "inliers": int(len(inliers))})
            if len(walls) >= max_walls:
                break
        work = work.select_by_index(inliers, invert=True)
    return walls


def normalize_room(pcd, output_dir: str | Path, source_to_meters: np.ndarray):
    import open3d as o3d
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    floor_model, floor_z, floor_inliers = detect_floor(pcd)
    room_pcd = o3d.geometry.PointCloud(pcd)
    room_pcd.translate((0.0, 0.0, -floor_z))

    pts = np.asarray(room_pcd.points)
    z = pts[:, 2]
    height = float(np.quantile(z, 0.99) - np.quantile(z, 0.01))
    wall_idx = np.where((z > 0.10) & (z < max(0.30, height - 0.10)))[0]
    walls = detect_walls(room_pcd.select_by_index(wall_idx.tolist()))

    xy = pts[:, :2]
    lo = np.quantile(xy, 0.01, axis=0)
    hi = np.quantile(xy, 0.99, axis=0)
    clipped = xy[(xy[:, 0] >= lo[0]) & (xy[:, 0] <= hi[0]) & (xy[:, 1] >= lo[1]) & (xy[:, 1] <= hi[1])]
    if len(clipped) > 20000:
        clipped = clipped[:: max(1, len(clipped)//20000)]
    footprint = convex_hull_2d(clipped)

    t_floor = np.eye(4)
    t_floor[2, 3] = -floor_z
    source_to_room = t_floor @ source_to_meters

    normalized_path = output_dir / "room_normalized.ply"
    o3d.io.write_point_cloud(str(normalized_path), room_pcd, write_ascii=False)
    report = {
        "schema_version": "0.3",
        "coordinate_system": {"units": "meters", "up": "z", "floor_z": 0.0},
        "floor": {"plane_before_translation": floor_model.tolist(), "z_m": float(floor_z), "inliers": int(floor_inliers)},
        "estimated_room_height_m": height,
        "walls": walls,
        "footprint_xy_m": footprint.tolist(),
        "source_to_room": source_to_room.tolist(),
        "normalized_pointcloud": str(normalized_path),
    }
    path = output_dir / "room_geometry.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report, room_pcd
