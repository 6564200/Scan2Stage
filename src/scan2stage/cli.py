from __future__ import annotations

import argparse
import json
from pathlib import Path

import open3d as o3d

from .fbx_pipeline import process_mesh
from .io import load_point_cloud
from .models import PreprocessConfig
from .preprocess import preprocess_point_cloud
from .stats import point_cloud_stats

MESH_EXTENSIONS = {'.zip', '.glb', '.gltf', '.fbx', '.obj'}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Scan2Stage 3D scan ingestion')
    parser.add_argument('input', type=Path, help='Input UGScan .zip, .glb/.gltf, .fbx/.obj, or point cloud')
    parser.add_argument('--output', type=Path, default=Path('outputs/processed.ply'))
    parser.add_argument('--stats', type=Path, default=Path('outputs/stats.json'))
    parser.add_argument('--output-dir', type=Path, default=Path('outputs/mesh'))
    parser.add_argument('--voxel', type=float, default=0.02, help='Voxel size in meters for point clouds')
    parser.add_argument('--samples', type=int, default=300000, help='Mesh surface sample count')
    parser.add_argument('--source-up', choices=['x', 'y', 'z'], default='y', help='Source up axis')
    parser.add_argument('--unit-scale', type=float, default=None, help='Multiply source coordinates by this factor to get meters; defaults to 1.0 except FBX=0.01')
    parser.add_argument('--topview-resolution', type=float, default=0.05, help='Structural top-view cell size in meters')
    parser.add_argument('--skip-room', action='store_true', help='Skip floor/wall/footprint normalization')
    return parser


def _process_point_cloud(args) -> dict:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.stats.parent.mkdir(parents=True, exist_ok=True)
    pcd = load_point_cloud(args.input)
    before = point_cloud_stats(pcd)
    cfg = PreprocessConfig(voxel_size_m=args.voxel)
    processed = preprocess_point_cloud(pcd, cfg)
    after = point_cloud_stats(processed)
    if processed.is_empty():
        raise RuntimeError('Preprocessing produced an empty point cloud')
    if not o3d.io.write_point_cloud(str(args.output), processed):
        raise RuntimeError(f'Failed to write point cloud: {args.output}')
    report = {'input': str(args.input), 'output': str(args.output), 'config': cfg.model_dump(), 'before': before, 'after': after}
    args.stats.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main() -> None:
    args = build_parser().parse_args()
    suffix = args.input.suffix.lower()
    if suffix in MESH_EXTENSIONS:
        default_scale = 0.01 if suffix == '.fbx' else 1.0
        unit_scale = default_scale if args.unit_scale is None else args.unit_scale
        report = process_mesh(
            args.input,
            args.output_dir,
            sample_count=args.samples,
            source_up=args.source_up,
            unit_scale=unit_scale,
            room_normalize=not args.skip_room,
            topview_resolution_m=args.topview_resolution,
        )
    else:
        report = _process_point_cloud(args)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
