from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
import zipfile
import numpy as np

SUPPORTED_MESH_FORMATS = {'.glb', '.gltf', '.fbx', '.obj'}

@dataclass
class MeshPart:
    name: str
    vertices: np.ndarray
    triangles: np.ndarray
    triangle_uvs: np.ndarray | None
    texture: np.ndarray | None

@dataclass
class MeshScene:
    path: Path
    source_container: Path
    parts: list[MeshPart]
    material_count: int
    format: str
    temp_dir: tempfile.TemporaryDirectory | None = None

def _np(value):
    return value.numpy() if hasattr(value, 'numpy') else np.asarray(value)

def _image_np(image):
    return image.as_tensor().numpy() if hasattr(image, 'as_tensor') else np.asarray(image)

def _safe_extract_zip(path: Path) -> tuple[tempfile.TemporaryDirectory, Path]:
    td = tempfile.TemporaryDirectory(prefix='scan2stage_')
    root = Path(td.name).resolve()
    with zipfile.ZipFile(path) as zf:
        for member in zf.infolist():
            target = (root / member.filename).resolve()
            if root not in target.parents and target != root:
                td.cleanup()
                raise ValueError(f'Unsafe ZIP member: {member.filename}')
        zf.extractall(root)
    meshes = [p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in SUPPORTED_MESH_FORMATS]
    glbs = [p for p in meshes if p.suffix.lower() == '.glb']
    candidates = glbs or meshes
    if len(candidates) != 1:
        td.cleanup()
        raise ValueError(f'Expected exactly one mesh file in ZIP, found {len(candidates)}')
    return td, candidates[0]

def load_scene(path: str | Path) -> MeshScene:
    import open3d as o3d
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    td = None
    mesh_path = source
    if source.suffix.lower() == '.zip':
        td, mesh_path = _safe_extract_zip(source)
    if mesh_path.suffix.lower() not in SUPPORTED_MESH_FORMATS:
        if td:
            td.cleanup()
        raise ValueError(f'Unsupported mesh format: {mesh_path.suffix}')
    model = o3d.io.read_triangle_model(str(mesh_path))
    meshes = o3d.t.geometry.TriangleMesh.from_triangle_mesh_model(model)
    if not meshes:
        if td:
            td.cleanup()
        raise ValueError(f'No mesh geometry found in {mesh_path}')
    parts = []
    for name, mesh in meshes.items():
        triangle_uvs = None
        texture = None
        try:
            triangle_uvs = _np(mesh.triangle['texture_uvs'])
        except Exception:
            pass
        try:
            maps = mesh.material.texture_maps
            if 'albedo' in maps:
                texture = _image_np(maps['albedo'])
        except Exception:
            pass
        parts.append(MeshPart(name, _np(mesh.vertex.positions), _np(mesh.triangle.indices), triangle_uvs, texture))
    return MeshScene(mesh_path, source, parts, len(model.materials), mesh_path.suffix.lower().lstrip('.'), td)
