from __future__ import annotations

import json
from pathlib import Path
import numpy as np


def _inside_rectangle(points: np.ndarray, rectangle: dict, margin_m: float = 0.02) -> np.ndarray:
    xy = points[:, :2]
    u = np.asarray(rectangle['axis_u'], dtype=float)
    v = np.asarray(rectangle['axis_v'], dtype=float)
    u0, u1 = map(float, rectangle['u_bounds'])
    v0, v1 = map(float, rectangle['v_bounds'])
    pu = xy @ u
    pv = xy @ v
    return (
        (pu >= u0 + margin_m)
        & (pu <= u1 - margin_m)
        & (pv >= v0 + margin_m)
        & (pv <= v1 - margin_m)
    )


def structural_mask(
    points: np.ndarray,
    rectangle: dict,
    normals: np.ndarray | None = None,
    floor_clearance_m: float = 0.08,
    wall_clearance_m: float = 0.06,
    wall_normal_alignment: float = 0.85,
) -> np.ndarray:
    points = np.asarray(points, dtype=float)
    if len(points) == 0:
        return np.zeros(0, dtype=bool)

    structural = points[:, 2] <= floor_clearance_m
    xy = points[:, :2]
    u = np.asarray(rectangle['axis_u'], dtype=float)
    v = np.asarray(rectangle['axis_v'], dtype=float)
    u0, u1 = map(float, rectangle['u_bounds'])
    v0, v1 = map(float, rectangle['v_bounds'])
    pu = xy @ u
    pv = xy @ v

    inside_span = (
        (pu >= u0 - wall_clearance_m)
        & (pu <= u1 + wall_clearance_m)
        & (pv >= v0 - wall_clearance_m)
        & (pv <= v1 + wall_clearance_m)
    )
    near_u = (np.abs(pu - u0) <= wall_clearance_m) | (np.abs(pu - u1) <= wall_clearance_m)
    near_v = (np.abs(pv - v0) <= wall_clearance_m) | (np.abs(pv - v1) <= wall_clearance_m)

    if normals is None or len(normals) != len(points):
        wall_like = (near_u | near_v) & inside_span
    else:
        nxy = np.asarray(normals, dtype=float)[:, :2]
        nxy_norm = np.linalg.norm(nxy, axis=1)
        valid = nxy_norm > 1e-8
        nxy_unit = np.zeros_like(nxy)
        nxy_unit[valid] = nxy[valid] / nxy_norm[valid, None]
        align_u = np.abs(nxy_unit @ u) >= wall_normal_alignment
        align_v = np.abs(nxy_unit @ v) >= wall_normal_alignment
        wall_like = ((near_u & align_u) | (near_v & align_v)) & inside_span

    return structural | wall_like


def _candidate_features(points: np.ndarray) -> dict:
    center = np.median(points, axis=0)
    centered = points - center
    cov = np.cov(centered.T) if len(points) > 1 else np.eye(3) * 1e-9
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvals = np.maximum(eigvals[order], 0.0)
    axes = eigvecs[:, order]
    local = centered @ axes
    lo = np.quantile(local, 0.02, axis=0)
    hi = np.quantile(local, 0.98, axis=0)
    extents = hi - lo
    robust_center = center + ((lo + hi) * 0.5) @ axes.T
    total = float(eigvals.sum())
    ratios = (eigvals / total).tolist() if total > 0 else [0.0, 0.0, 0.0]
    sorted_extents = sorted((float(x) for x in extents), reverse=True)
    if sorted_extents[1] >= 0.10 and sorted_extents[2] < 0.10:
        shape = 'planar'
    elif sorted_extents[0] >= 0.10 and sorted_extents[1] < 0.10:
        shape = 'linear'
    elif sorted_extents[1] >= 0.10:
        shape = 'volumetric'
    else:
        shape = 'tiny'
    return {
        'center_m': robust_center.tolist(),
        'extents_m': extents.tolist(),
        'sorted_extents_m': sorted_extents,
        'shape': shape,
        'axes': axes.tolist(),
        'eigenvalues': eigvals.tolist(),
        'variance_ratios': ratios,
        'z_min_m': float(points[:, 2].min()),
        'z_max_m': float(points[:, 2].max()),
        'point_count': int(len(points)),
    }


def extract_object_candidates(
    room_pcd,
    room_report: dict,
    output_dir: str | Path,
    eps_m: float = 0.07,
    min_points: int = 6,
    min_cluster_points: int = 12,
    floor_clearance_m: float = 0.08,
    wall_clearance_m: float = 0.06,
    room_margin_m: float = 0.02,
    voxel_size_m: float = 0.02,
    min_two_axes_m: float = 0.10,
):
    import open3d as o3d

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    points = np.asarray(room_pcd.points)
    normals = np.asarray(room_pcd.normals) if room_pcd.has_normals() else None

    inside = _inside_rectangle(points, room_report['rectangle'], margin_m=room_margin_m)
    structural = structural_mask(
        points,
        room_report['rectangle'],
        normals=normals,
        floor_clearance_m=floor_clearance_m,
        wall_clearance_m=wall_clearance_m,
    )
    keep = inside & (~structural)
    object_idx = np.where(keep)[0]
    object_pcd_raw = room_pcd.select_by_index(object_idx.tolist())
    object_pcd = object_pcd_raw.voxel_down_sample(voxel_size_m) if len(object_pcd_raw.points) else object_pcd_raw

    object_path = output_dir / 'object_points.ply'
    o3d.io.write_point_cloud(str(object_path), object_pcd, write_ascii=False)

    if len(object_pcd.points) == 0:
        labels = np.empty(0, dtype=int)
    else:
        labels = np.asarray(
            object_pcd.cluster_dbscan(eps=eps_m, min_points=min_points, print_progress=False),
            dtype=int,
        )

    object_points = np.asarray(object_pcd.points)
    candidates = []
    rejected_tiny = 0
    for label in sorted(set(labels.tolist())):
        if label < 0:
            continue
        idx = np.where(labels == label)[0]
        if len(idx) < min_cluster_points:
            continue
        feat = _candidate_features(object_points[idx])
        if feat['sorted_extents_m'][1] < min_two_axes_m:
            rejected_tiny += 1
            continue
        feat['id'] = f'candidate_{len(candidates):03d}'
        feat['dbscan_label'] = int(label)
        feat['classification'] = {
            'class_id': 'unknown',
            'confidence': 0.0,
            'needs_user_confirmation': True,
        }
        candidates.append(feat)

    report = {
        'schema_version': '0.4',
        'method': 'room_crop+perimeter_structure_mask+voxel+dbscan+pca',
        'policy': {
            'keep_internal_planes': True,
            'human_confirmation_default': True,
            'tiny_filter': 'reject only when the second-largest robust extent is below threshold',
        },
        'parameters': {
            'room_margin_m': float(room_margin_m),
            'floor_clearance_m': float(floor_clearance_m),
            'wall_clearance_m': float(wall_clearance_m),
            'voxel_size_m': float(voxel_size_m),
            'dbscan_eps_m': float(eps_m),
            'dbscan_min_points': int(min_points),
            'min_cluster_points': int(min_cluster_points),
            'min_two_axes_m': float(min_two_axes_m),
        },
        'input_points': int(len(points)),
        'outside_room_points': int((~inside).sum()),
        'structural_points': int((inside & structural).sum()),
        'object_points_before_voxel': int(len(object_pcd_raw.points)),
        'object_points': int(len(object_pcd.points)),
        'dbscan_noise_points': int(np.sum(labels < 0)) if len(labels) else 0,
        'rejected_tiny_candidate_count': int(rejected_tiny),
        'candidate_count': len(candidates),
        'candidates': candidates,
        'object_pointcloud': str(object_path),
    }
    report_path = output_dir / 'object_candidates.json'
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report, object_pcd
