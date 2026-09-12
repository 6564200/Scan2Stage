from __future__ import annotations

import numpy as np


def sample_mesh_surface(vertices, triangles, count, rng, triangle_uvs=None, texture=None, flip_v=True):
    vertices = np.asarray(vertices, dtype=np.float64)
    triangles = np.asarray(triangles, dtype=np.int64)
    tri_v = vertices[triangles]
    cross = np.cross(tri_v[:, 1] - tri_v[:, 0], tri_v[:, 2] - tri_v[:, 0])
    area2 = np.linalg.norm(cross, axis=1)
    total = area2.sum()
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Mesh has zero usable surface area")
    tri_ids = rng.choice(len(triangles), size=count, p=area2 / total)
    r1 = np.sqrt(rng.random(count))
    r2 = rng.random(count)
    weights = np.column_stack((1.0-r1, r1*(1.0-r2), r1*r2))
    points = np.einsum("ni,nij->nj", weights, tri_v[tri_ids])
    normals = cross[tri_ids]
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    colors = None
    if triangle_uvs is not None and texture is not None:
        uv = np.einsum("ni,nij->nj", weights, np.asarray(triangle_uvs)[tri_ids])
        uv = np.clip(uv, 0.0, 1.0)
        image = np.asarray(texture)
        if image.ndim == 2:
            image = np.repeat(image[..., None], 3, axis=2)
        image = image[:, :, :3]
        h, w = image.shape[:2]
        x = np.rint(uv[:, 0] * (w - 1)).astype(np.int64)
        v = 1.0 - uv[:, 1] if flip_v else uv[:, 1]
        y = np.rint(v * (h - 1)).astype(np.int64)
        colors = image[y, x]
        if np.issubdtype(colors.dtype, np.floating):
            colors = colors * (255.0 if np.nanmax(colors) <= 1.0 else 1.0)
        colors = np.clip(colors, 0, 255).astype(np.uint8)
    return points, normals, colors
