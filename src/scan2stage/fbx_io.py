from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np

@dataclass
class MeshPart:
    name: str
    vertices: np.ndarray
    triangles: np.ndarray
    triangle_uvs: np.ndarray | None
    texture: np.ndarray | None

@dataclass
class FbxScene:
    path: Path
    parts: list[MeshPart]
    material_count: int

def _np(value):
    return value.numpy() if hasattr(value, "numpy") else np.asarray(value)

def _image_np(image):
    return image.as_tensor().numpy() if hasattr(image, "as_tensor") else np.asarray(image)

def load_fbx(path: str | Path) -> FbxScene:
    import open3d as o3d
    path = Path(path)
    if path.suffix.lower() != ".fbx":
        raise ValueError(f"Expected .fbx input, got {path.suffix}")
    if not path.is_file():
        raise FileNotFoundError(path)
    model = o3d.io.read_triangle_model(str(path))
    meshes = o3d.t.geometry.TriangleMesh.from_triangle_mesh_model(model)
    if not meshes:
        raise ValueError(f"No mesh geometry found in {path}")
    parts = []
    for name, mesh in meshes.items():
        triangle_uvs = None
        texture = None
        try:
            triangle_uvs = _np(mesh.triangle["texture_uvs"])
        except Exception:
            pass
        try:
            maps = mesh.material.texture_maps
            if "albedo" in maps:
                texture = _image_np(maps["albedo"])
        except Exception:
            pass
        parts.append(MeshPart(name, _np(mesh.vertex.positions), _np(mesh.triangle.indices), triangle_uvs, texture))
    return FbxScene(path, parts, len(model.materials))
