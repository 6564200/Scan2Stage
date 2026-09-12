from __future__ import annotations

import numpy as np
import open3d as o3d


def point_cloud_stats(pcd: o3d.geometry.PointCloud) -> dict:
    pts = np.asarray(pcd.points)
    if pts.size == 0:
        return {"point_count": 0}

    mins = pts.min(axis=0)
    maxs = pts.max(axis=0)
    size = maxs - mins

    return {
        "point_count": int(len(pts)),
        "has_colors": bool(pcd.has_colors()),
        "has_normals": bool(pcd.has_normals()),
        "bounds_min": mins.tolist(),
        "bounds_max": maxs.tolist(),
        "extent": size.tolist(),
    }
