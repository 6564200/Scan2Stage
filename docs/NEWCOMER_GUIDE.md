# Scan2Stage newcomer guide

## What the project is building

Scan2Stage turns one or more textured 3D scans of an indoor practical-shooting gallery into a persistent semantic Gallery and, later, a clean GLB/FBX/Blender scene.

The supported workflow is local Windows 10. Colab notebooks are retired.

## Runtime architecture

~~~text
Browser
  -> FastAPI local UI
  -> SQLite metadata
  -> filesystem source scans
  -> worker process
  -> geometry pipeline
  -> versioned Run artifacts
~~~

Main concepts:

- Gallery — one physical gallery/stage dataset;
- Scan — immutable source capture;
- Run — one processing attempt with a settings snapshot;
- Artifact — generated PNG/JSON/NPZ/PLY and later GLB/FBX.

## Repository map

| Area | Responsibility |
| --- | --- |
| src/scan2stage/web.py | Local web application and pages. |
| src/scan2stage/storage.py | SQLite metadata and local filesystem layout. |
| src/scan2stage/worker.py | Background processing process. |
| src/scan2stage/local_config.py | Persistent local settings. |
| src/scan2stage/fbx_pipeline.py | Mesh ingestion and detector orchestration. |
| src/scan2stage/room_geometry.py | Floor/wall/room normalization. |
| src/scan2stage/structural_scene.py | Multi-height top-view, structures, targets and Fault Lines. |
| src/scan2stage/visualize.py | Semantic top-view renderer. |
| config/object_catalog.json | Semantic object catalog/priors. |
| tests/ | Regression and architecture tests. |

## Important invariants

### Source scans are immutable

Never overwrite an uploaded Scan. Corrections and reprocessing create a new Run or review layer.

### Results are versioned

Every Run has its own directory and exact settings snapshot.

### Structural geometry is evidence

Walls, partitions and bullet traps must not be destructively removed before target hypotheses are evaluated.

### Multi-scan does not mean concatenate

Several scans can belong to the same Gallery, but their coordinates must be registered explicitly before fusion.

### Meters and Z-up internally

Geometry processing uses meters and canonical Z-up after normalization.

### Unknown is valid

An unresolved candidate is preferable to silently deleting a real object.

## Development loop on Windows

~~~bat
scripts\setup_windows.bat
.venv\Scripts\python.exe -m pytest -q
scripts\start_windows.bat
~~~

See WINDOWS_LOCAL_SETUP.md and docs/LOCAL_ARCHITECTURE.md before changing application boundaries.
