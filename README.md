# Scan2Stage

Scan2Stage converts iPhone/LiDAR point clouds into structured shooting-stage data and, in later milestones, Blender scenes.

## Current milestone

Pilot M1 implements:

- PLY/Open3D loading and validation;
- statistical outlier removal;
- voxel downsampling;
- normal estimation;
- JSON processing report;
- CLI entry point;
- pytest smoke tests;
- Colab pilot notebook;
- Docker boundary for later production deployment.

## Local install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## CLI

```bash
scan2stage data/input.ply \
  --output outputs/processed.ply \
  --stats outputs/stats.json \
  --voxel 0.02
```

## Colab pilot

Open `notebooks/01_colab_pilot.ipynb` in Google Colab. The notebook clones this repository, installs the package, accepts a PLY upload, executes the CLI and runs tests.

For repeatable datasets, use a GCS bucket and copy files in/out from notebook cells. GCP access remains orchestration-only; core algorithms do not depend on Google APIs.

## Production migration principle

Do not put processing logic into notebooks. Everything that affects a result belongs under `src/scan2stage` and is exercised by tests. Colab only invokes the same CLI that will later run on a production workstation/server/container.

See `docs/PILOT_ARCHITECTURE.md` and `ROADMAP.md`.
