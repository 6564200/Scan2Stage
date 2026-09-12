import numpy as np
import open3d as o3d

from scan2stage.models import PreprocessConfig
from scan2stage.preprocess import preprocess_point_cloud
from scan2stage.stats import point_cloud_stats


def test_preprocess_synthetic_cloud():
    rng = np.random.default_rng(42)
    xyz = rng.uniform([0.0, 0.0, 0.0], [2.0, 3.0, 1.0], size=(5000, 3))
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz))

    cfg = PreprocessConfig(voxel_size_m=0.05, outlier_nb_neighbors=8, normal_max_nn=10)
    result = preprocess_point_cloud(pcd, cfg)
    stats = point_cloud_stats(result)

    assert 0 < stats["point_count"] <= 5000
    assert stats["has_normals"] is True
