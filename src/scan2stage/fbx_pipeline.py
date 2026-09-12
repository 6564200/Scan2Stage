from __future__ import annotations

import json
from pathlib import Path
import numpy as np

from .scene_io import load_scene
from .geometry import apply_transform, bounds, canonical_transform
from .room_geometry import normalize_room
from .object_candidates import extract_object_candidates
from .sampling import sample_mesh_surface


def process_mesh(input_path, output_dir, sample_count=300000, source_up='y', seed=42, unit_scale=1.0, room_normalize=True):
    import open3d as o3d

    scene = load_scene(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    axis_transform = canonical_transform(source_up)
    scale_transform = np.diag([unit_scale, unit_scale, unit_scale, 1.0])
    source_to_meters = scale_transform @ axis_transform
    rotation = axis_transform[:3, :3]
    rng = np.random.default_rng(seed)

    all_source = np.concatenate([part.vertices for part in scene.parts], axis=0)
    all_meters = apply_transform(all_source, source_to_meters)
    tri_counts = np.array([len(p.triangles) for p in scene.parts], dtype=float)
    if tri_counts.sum() <= 0:
        raise ValueError('Mesh contains no triangles')
    allocations = np.maximum(1, np.rint(sample_count * tri_counts / tri_counts.sum()).astype(int))

    sampled_points, sampled_normals, sampled_colors = [], [], []
    all_have_color = True
    part_reports = []

    for part, count in zip(scene.parts, allocations):
        points, normals, colors = sample_mesh_surface(part.vertices, part.triangles, int(count), rng, triangle_uvs=part.triangle_uvs, texture=part.texture)
        sampled_points.append(apply_transform(points, source_to_meters))
        sampled_normals.append(normals @ rotation.T)
        if colors is None:
            all_have_color = False
        else:
            sampled_colors.append(colors)
        texture_size = [int(part.texture.shape[1]), int(part.texture.shape[0])] if part.texture is not None else None
        part_reports.append({'name': part.name, 'vertices': int(len(part.vertices)), 'triangles': int(len(part.triangles)), 'has_uv': part.triangle_uvs is not None, 'has_albedo_texture': part.texture is not None, 'texture_size': texture_size})

    points = np.concatenate(sampled_points, axis=0)
    normals = np.concatenate(sampled_normals, axis=0)
    colors = np.concatenate(sampled_colors, axis=0) if all_have_color and sampled_colors else None

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    pcd.normals = o3d.utility.Vector3dVector(normals)
    if colors is not None:
        pcd.colors = o3d.utility.Vector3dVector(colors.astype(float) / 255.0)

    pointcloud_path = output_dir / 'sampled_colored.ply'
    if not o3d.io.write_point_cloud(str(pointcloud_path), pcd, write_ascii=False):
        raise RuntimeError(f'Failed to write {pointcloud_path}')

    report = {
        'schema_version': '0.7',
        'input': str(scene.source_container),
        'resolved_mesh': str(scene.path),
        'format': scene.format,
        'source_up': source_up,
        'canonical_up': 'z',
        'source_unit_scale_to_meters': float(unit_scale),
        'transform_source_to_meters': source_to_meters.tolist(),
        'mesh_count': len(scene.parts),
        'material_count': scene.material_count,
        'vertices_total': int(sum(len(p.vertices) for p in scene.parts)),
        'triangles_total': int(sum(len(p.triangles) for p in scene.parts)),
        'bounds_source': bounds(all_source),
        'bounds_meters': bounds(all_meters),
        'sample_count': int(len(points)),
        'sample_has_color': colors is not None,
        'pointcloud': str(pointcloud_path),
        'parts': part_reports,
    }
    if room_normalize:
        room_report, room_pcd = normalize_room(pcd, output_dir, source_to_meters)
        report['room_geometry'] = room_report
        object_report, _ = extract_object_candidates(room_pcd, room_report, output_dir)
        report['object_candidates'] = object_report
    (output_dir / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def process_fbx(input_path, output_dir, sample_count=300000, source_up='y', seed=42, unit_scale=0.01, room_normalize=True):
    return process_mesh(input_path, output_dir, sample_count, source_up, seed, unit_scale, room_normalize)
