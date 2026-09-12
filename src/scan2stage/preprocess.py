from __future__ import annotations

import open3d as o3d

from .models import PreprocessConfig


def preprocess_point_cloud(
    pcd: o3d.geometry.PointCloud,
    cfg: PreprocessConfig,
) -> o3d.geometry.PointCloud:
    """Clean and downsample an Open3D point cloud."""
    if pcd.is_empty():
        raise ValueError("Cannot preprocess an empty point cloud")

    cleaned, _ = pcd.remove_statistical_outlier(
        nb_neighbors=cfg.outlier_nb_neighbors,
        std_ratio=cfg.outlier_std_ratio,
    )

    down = cleaned.voxel_down_sample(voxel_size=cfg.voxel_size_m)

    if cfg.estimate_normals and not down.is_empty():
        down.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=cfg.normal_radius_m,
                max_nn=cfg.normal_max_nn,
            )
        )

    return down
