# Scan2Stage

Scan2Stage converts textured UGScan meshes (plus legacy point clouds) into a structured practical-shooting stage representation and, in later milestones, clean Blender scenes.

## Current state

The repository contains the ingestion/normalization foundation plus an active structural-first detector:

- UGScan ZIP and GLB/glTF ingestion with texture-aware surface sampling;
- legacy FBX/OBJ and point-cloud input paths;
- conversion to meters and canonical Z-up coordinates;
- floor detection, working-volume clipping and rectangular room fitting;
- conservative M4 DBSCAN/PCA candidates retained for compatibility;
- multi-height top-view rasterization (occupancy, density and height layers);
- structural components (walls/partitions/large and compact structures);
- red floor Fault Line proposals;
- shooting-direction prior derived from room geometry and rear structural support;
- generic IPSC Metric Target hypotheses using local 3D planarity, size, orientation and partial-observation tolerance;
- rear-zone metal-target proposals;
- JSON diagnostics plus compressed top-view layers for later visualization.

The detector is intentionally recall-oriented. Structural geometry is treated as context/evidence, not a destructive mask: a target may overlap a wall, partition, bullet trap or decoration in the scan.

## Domain rules encoded as priors

- Targets face the athlete / firing side.
- Poppers and steel are expected close to the rear bullet trap.
- Cardboard targets may be at different distances.
- Cardboard targets can appear between low wall/wheel-cover protrusions.
- Fault Lines are low, elongated red floor features that bound the shooting area.

## Mesh outputs

sampled_colored.ply, room_normalized.ply, room_geometry.json, object_candidates.json, topview_layers.npz, structural_scene.json and report.json.

## Local install

~~~bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
~~~

## CLI

~~~bash
scan2stage scan.zip --output-dir outputs/scan --samples 300000 --source-up y
~~~

## Architecture

~~~text
textured mesh
  -> surface sampling
  -> meters / Z-up
  -> floor + room normalization
  -> multi-height top-view
  -> structural scene understanding
  -> shooting-direction/context priors
  -> soft target hypotheses
  -> local 3D verification
  -> scene graph / review
  -> clean asset replacement / Blender
~~~

See ROADMAP.md, docs/STRUCTURAL_DETECTOR.md, docs/SCENE_SCHEMA.md, docs/ENGINEERING_PLAN.md and docs/NEWCOMER_GUIDE.md.

## Production principle

Notebooks remain orchestration/test surfaces only. Any logic that changes a result belongs under src/scan2stage and must be testable outside Colab.
