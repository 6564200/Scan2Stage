from __future__ import annotations

import argparse
import json
from pathlib import Path

import open3d as o3d

from .fbx_pipeline import process_fbx
from .io import load_point_cloud
from .models import PreprocessConfig
from .preprocess import preprocess_point_cloud
from .stats import point_cloud_stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan2Stage 3D scan ingestion")
    parser.add_argument("input", type=Path, help="Input .fbx or point cloud")
    parser.add_argument("--output", type=Path, default=Path("outputs/processed.ply"))
    parser.add_argument("--stats", type=Path, default=Path("outputs/stats.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/fbx"))
    parser.add_argument("--voxel", type=float, default=0.02, help="Voxel size in meters for point clouds")
    parser.add_argument("--samples", type=int, default=300000, help="FBX surface sample count")
    parser.add_argument("--source-up", choices=["x", "y", "z"], default="y", help="FBX source up axis")
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
        raise RuntimeError("Preprocessing produced an empty point cloud")
    if not o3d.io.write_point_cloud(str(args.output), processed):
        raise RuntimeError(f"Failed to write point cloud: {args.output}")
    report = {
        "input": str(args.input),
        "output": str(args.output),
        "config": cfg.model_dump(),
        "before": before,
        "after": after,
    }
    args.stats.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    args = build_parser().parse_args()
    if args.input.suffix.lower() == ".fbx":
        report = process_fbx(args.input, args.output_dir, args.samples, args.source_up)
    else:
        report = _process_point_cloud(args)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
