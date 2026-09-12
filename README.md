# Scan2Stage

Scan2Stage converts UGScan textured meshes (or legacy point clouds) into structured
shooting-stage data and, in later milestones, clean Blender scenes.

## Current milestone

The repository currently contains the M1/M2 ingestion foundation, an M3 room
normalization prototype, and active M4 object-candidate extraction:

- UGScan ZIP and GLB/glTF ingestion, including texture-aware surface sampling;
- legacy FBX/OBJ and point-cloud input paths;
- conversion to meters and canonical Z-up coordinates;
- floor detection, working-height clipping, and rectangular room fitting;
- conservative candidate extraction that keeps internal planar structures;
- JSON diagnostics, pytest coverage, Colab notebooks, and a Docker boundary.

The pipeline is intentionally conservative: an unknown candidate is preferable to
silently deleting a real target, partition, mesh wall, or frame.

## Local install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## CLI

For the production mesh path:

```bash
scan2stage scan.zip \
  --output-dir outputs/scan \
  --samples 300000 \
  --source-up y
```

The legacy point-cloud path remains available:

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

## Where to start

New contributors should read [`docs/NEWCOMER_GUIDE.md`](docs/NEWCOMER_GUIDE.md)
for the end-to-end data flow, module map, invariants, and a suggested reading
order. See also `docs/PILOT_ARCHITECTURE.md`, `docs/SCENE_SCHEMA.md`, and
`ROADMAP.md`.
