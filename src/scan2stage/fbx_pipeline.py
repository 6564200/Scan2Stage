from __future__ import annotations

import json
from pathlib import Path
import numpy as np

from .fbx_io import load_fbx
from .geometry import apply_transform, bounds, canonical_transform
from .sampling import sample_mesh_surface


def process_fbx(input_path, output_dir, sample_count=300000, source_up="y", seed=42):
    import open3d as o3d

    scene = load_fbx(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    transform = canonical_transform(source_up)
    rng = np.random.default_rng(seed)

    all_source = np.concatenate([part.vertices for part in scene.parts], axis=0)
    all_canonical = apply_transform(all_source, transform)
    tri_counts = np.array([len(p.triangles) for p in scene.parts], dtype=float)
    if tri_counts.sum() <= 0:
        raise ValueError("FBX contains no triangles")
    allocations = np.maximum(1, np.rint(sample_count * tri_counts / tri_counts.sum()).astype(int))

    sampled_points, sampled_normals, sampled_colors = [], [], []
    all_have_color = True
    part_reports = []

    for part, count in zip(scene.parts, allocations):
        points, normals, colors = sample_mesh_surface(
            part.vertices, part.triangles, int(count), rng,
            triangle_uvs=part.triangle_uvs, texture=part.texture,
        )
        sampled_points.append(apply_transform(points, transform))
        sampled_normals.append(normals @ transform[:3, :3].T)
        if colors is None:
            all_have_color = False
        else:
            sampled_colors.append(colors)
        texture_size = None
        if part.texture is not None:
            texture_size = [int(part.texture.shape[1]), int(part.texture.shape[0])]
        part_reports.append({
            "name": part.name,
            "vertices": int(len(part.vertices)),
            "triangles": int(len(part.triangles)),
            "has_uv": part.triangle_uvs is not None,
            "has_albedo_texture": part.texture is not None,
            "texture_size": texture_size,
        })

    points = np.concatenate(sampled_points, axis=0)
    normals = np.concatenate(sampled_normals, axis=0)
    colors = np.concatenate(sampled_colors, axis=0) if all_have_color and sampled_colors else None

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    pcd.normals = o3d.utility.Vector3dVector(normals)
    if colors is not None:
        pcd.colors = o3d.utility.Vector3dVector(colors.astype(float) / 255.0)

    pointcloud_path = output_dir / "sampled_colored.ply"
    if not o3d.io.write_point_cloud(str(pointcloud_path), pcd, write_ascii=False):
        raise RuntimeError(f"Failed to write {pointcloud_path}")

    report = {
        "schema_version": "0.2",
        "input": str(scene.path),
        "format": "fbx",
        "source_up": source_up,
        "canonical_up": "z",
        "transform_source_to_canonical": transform.tolist(),
        "mesh_count": len(scene.parts),
        "material_count": scene.material_count,
        "vertices_total": int(sum(len(p.vertices) for p in scene.parts)),
        "triangles_total": int(sum(len(p.triangles) for p in scene.parts)),
        "bounds_source": bounds(all_source),
        "bounds_canonical": bounds(all_canonical),
        "sample_count": int(len(points)),
        "sample_has_color": colors is not None,
        "pointcloud": str(pointcloud_path),
        "parts": part_reports,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
