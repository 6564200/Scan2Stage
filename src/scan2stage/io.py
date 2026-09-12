from __future__ import annotations

from pathlib import Path
import open3d as o3d


def load_point_cloud(path: str | Path) -> o3d.geometry.PointCloud:
    """Load a point cloud and perform basic validation.

    PLY is the preferred MVP input format. Other formats supported by Open3D
    may also work, but are not part of the initial compatibility contract.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    pcd = o3d.io.read_point_cloud(str(path))
    if pcd.is_empty():
        raise ValueError(f"Point cloud is empty or unreadable: {path}")

    if not pcd.has_points():
        raise ValueError("Point cloud does not contain XYZ points")

    return pcd
