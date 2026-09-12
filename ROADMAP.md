# Scan2Stage roadmap

> The milestone list below describes product direction. The audited, ordered
> engineering backlog—with risks and acceptance criteria—is maintained in
> [`docs/ENGINEERING_PLAN.md`](docs/ENGINEERING_PLAN.md).

## Pilot foundation — Colab/GCP + GitHub

- GitHub is the source of truth.
- Colab is only an interactive orchestration/test layer.
- GCS is optional persistent storage for raw scans and outputs.
- Core processing remains a normal Python package and CLI.
- Dockerfile defines the production hand-off boundary.
- GitHub Actions runs smoke tests on every push/PR.

### Pilot acceptance criteria

1. Fresh Colab runtime can clone `main` and install `.[dev]`.
2. A real Polycam PLY can be processed with one CLI command.
3. `processed.ply` and `stats.json` are produced.
4. Point count decreases after preprocessing on a normal dense scan.
5. RGB survives when present in the source cloud.
6. Normals exist in the processed cloud.
7. `pytest -q` passes in Colab and GitHub Actions.
8. The same CLI can run inside Docker without notebook code.

## M1 — Import and preprocessing

- PLY loading and validation.
- Statistical outlier removal.
- Voxel downsampling.
- Normal estimation.
- Processing statistics.

## M2 — Coordinate normalization

- Detect dominant floor candidate with RANSAC.
- Resolve floor vs ceiling using geometry/support heuristics.
- Rotate cloud to canonical Z-up.
- Translate floor to Z=0.
- Persist the 4x4 source-to-stage transform.

## M3 — Room reconstruction

- Detect/classify wall planes.
- Produce floor footprint / wall graph.
- Keep structural planes separate from object candidates.

## M4 — Object candidates

- Candidate extraction with geometry, color and connectivity.
- DBSCAN as one signal rather than the only segmentation method.
- Candidate feature records and debug exports.

## M5 — Classification and pose

- Closed-world catalog of stage props.
- PCA/OBB initial pose.
- Template registration and ICP refinement where useful.
- Front/back disambiguation.
- Confidence scoring.

## M6 — Scene contract and review

- Versioned `scene_config.json`.
- Top-view/debug preview.
- Manual correction path for uncertain detections.

## M7 — Blender generation

- Asset/template `.blend`.
- `bpy` scene generator.
- Deterministic placement from scene config.
- Headless save to result `.blend`.

## M8 — Hybrid/ML only if metrics require it

- RGB-assisted detection and 3D association first.
- Learned 3D detection only after a useful labeled dataset exists.
