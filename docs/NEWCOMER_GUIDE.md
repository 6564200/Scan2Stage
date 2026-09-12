# Scan2Stage newcomer guide

## What the project is building

Scan2Stage turns a noisy 3D scan of an indoor shooting gallery into a semantic
scene. The intended flow is:

```text
UGScan ZIP / GLB -> textured mesh import -> colored surface samples
  -> coordinate and room normalization -> object candidates
  -> recognition + human confirmation -> scene_config.json
  -> clean asset placement -> Blender scene
```

The scan is evidence, not the final visual asset. The final scene should contain a
rectangular room and clean reference models at confirmed poses, rather than copied
pieces of the scan mesh.

## Repository map

| Area | Responsibility |
| --- | --- |
| `src/scan2stage/cli.py` | Selects the mesh or legacy point-cloud path and exposes the `scan2stage` command. |
| `src/scan2stage/scene_io.py` | Safely resolves ZIP input and imports GLB/glTF/FBX/OBJ parts, UVs, and textures. |
| `src/scan2stage/sampling.py` | Samples mesh triangles and transfers normals, UVs, and albedo into a controlled point cloud. |
| `src/scan2stage/geometry.py` | Applies unit scaling and source-up to canonical Z-up transforms. |
| `src/scan2stage/fbx_pipeline.py` | Orchestrates mesh ingestion, sampling, normalization, candidate extraction, and output reports. The historical name remains although it handles all mesh formats. |
| `src/scan2stage/room_geometry.py` | Finds the floor and wall candidates, clips the working height, and fits the rectangular gallery footprint. |
| `src/scan2stage/object_candidates.py` | Crops to the room, removes only structural boundaries, voxelizes, clusters primitives, and computes PCA/OBB features. |
| `src/scan2stage/models.py` | Holds the small Pydantic contracts currently used by preprocessing and scene output. |
| `config/object_catalog.json` | Defines semantic classes and their priors; it is not a store of scanned examples or clean assets. |
| `docs/SCENE_SCHEMA.md` | Describes confirmed semantic objects, transforms, clean assets, and bullet-trap child targets. |
| `notebooks/` | Colab orchestration and visualization only; production algorithms belong in the package. |
| `tests/` | Executable examples for transforms, ZIP safety, room fitting, candidate retention, and schemas. |

## Follow one input through the code

1. `cli.main()` chooses the mesh pipeline for ZIP, GLB, glTF, FBX, or OBJ.
2. `scene_io.load_scene()` validates an archive, selects exactly one mesh, and
   produces a `MeshScene` containing one or more material-aware `MeshPart`s.
3. Surface sampling converts those parts into a density-controlled colored point
   cloud. This common representation supports RANSAC, DBSCAN, PCA, OBB, and later
   registration regardless of the original mesh format.
4. Coordinate conversion scales to meters and converts the source up-axis to Z.
   For UGScan/glTF the expected source is Y-up and meter-scale; legacy FBX often
   needs a `0.01` scale.
5. Room normalization estimates the floor, moves it to `Z=0`, clips the working
   volume to `0..2.5 m`, finds vertical wall candidates, and fits exactly one
   rectangle.
6. Candidate extraction discards points outside that rectangle, removes the floor
   and supported perimeter surfaces, voxelizes the remainder, and uses DBSCAN to
   create **primitive candidates**.
7. Candidate features and diagnostics are written for later recognition and
   review. Classification, clean-asset replacement, and Blender generation remain
   later milestones.

## Invariants that should guide every change

### The gallery footprint is rectangular

Corridors, neighboring galleries, open doorways, and geometry above partitions
must not enlarge the fitted room. Do not replace the rectangle fit with a convex
hull of all observed points.

### Z is up and dimensions are meters

The internal convention is meters, Z-up, with +Y reserved as canonical front.
Absolute front is not yet reliably recoverable from room geometry alone and will
eventually need a semantic reference such as the start position.

### Preserve uncertain interior geometry

Only a confidently identified floor and perimeter boundaries should be removed
automatically. Large internal planes may be port walls, mesh panels, partitions,
decorations, targets, or parts of composite frames. False `unknown` is safer than
false deletion.

### A cluster is not necessarily an object

DBSCAN is a primitive segmentation tool. One physical frame may split into several
clusters, while touching props may merge. The next architectural layer should
relate planar, linear, and volumetric primitives into composite hypotheses.

### Thin does not mean noise

A target can be wide and tall but only centimeters thick. The current safe size
rule considers the second-largest robust extent, preserving thin planar candidates
and long linear frame elements.

### Keep the three data stores separate

1. The **class catalog** defines available classes and dimension/shape priors.
2. The **recognition library** will hold noisy, labeled scan exemplars.
3. The **clean asset library** will hold canonical `.blend` masters and portable
   `.glb` assets used in final scenes.

Mixing recognition scans with output assets makes both matching and deterministic
scene generation harder.

## Outputs to inspect while debugging

The mesh pipeline writes these main artifacts under `--output-dir`:

- `sampled_colored.ply` and `report.json` for ingestion/sampling;
- `room_normalized.ply` and `room_geometry.json` for M3;
- `object_points.ply` and `object_candidates.json` for M4.

For room failures, inspect floor Z, bounds, rectangle axes and dimensions,
wall-candidate support, and inside/outlier fractions. For candidate failures,
inspect outside-room counts, points before and after voxelization, DBSCAN noise,
candidate extents, and shape labels.

## Suggested reading and first changes

1. Start with `tests/test_scene_io.py` and `scene_io.py` to understand safe input
   handling and the `MeshScene` boundary.
2. Read `tests/test_room_geometry.py` beside `room_geometry.py`; synthetic tests
   make the rectangular-room assumptions easier to see than a real scan.
3. Read `tests/test_object_candidates.py` beside `object_candidates.py`, paying
   special attention to internal-plane preservation and the tiny-candidate rule.
4. Read `docs/SCENE_SCHEMA.md` and `config/object_catalog.json` before adding any
   recognition or asset feature.
5. Use `notebooks/02_room_normalization.ipynb` only to run and visualize the same
   package pipeline; do not put result-affecting logic in notebook cells.

A safe first contribution is usually a synthetic regression test for one domain
invariant, followed by the smallest implementation change that makes it pass.

## Development loop

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
scan2stage --help
```

To exercise the mesh path:

```bash
scan2stage scan.zip \
  --output-dir outputs/test \
  --samples 300000 \
  --source-up y
```

Do not commit real UGScan samples unless their redistribution rights have been
confirmed. Export metadata may impose restrictions that require a separate legal
check before commercial use.
