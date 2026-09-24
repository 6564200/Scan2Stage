# Local application architecture

## Product boundary

Scan2Stage is a local-first Windows application. The browser is only the UI; geometry processing, database, files and worker processes remain on the same workstation.

Chosen stack:

- FastAPI — local HTTP application/API;
- Jinja2 + server-rendered HTML — simple multi-page UI without a frontend build chain;
- vanilla CSS/HTML — no external CDN dependency;
- SQLite — galleries, scans, runs and artifact metadata;
- filesystem storage — large scans and generated artifacts;
- separate Python worker process — Open3D/NumPy processing cannot block the web request thread.

This is intentionally more durable than Streamlit/Gradio for a multi-page application with persistent projects, logs, settings, job history and future manual scene editing.

## Domain model

~~~text
Gallery
  ├─ Scan 1
  ├─ Scan 2
  ├─ Scan N
  └─ Run
      ├─ selected Scan IDs
      ├─ immutable settings snapshot
      ├─ progress/status
      ├─ log
      └─ Artifacts
~~~

A Gallery represents one physical gallery/stage dataset.

A Scan is immutable source material. Uploading a second capture creates another Scan; it never overwrites the first.

A Run is reproducible processing history. It stores the exact settings used and selected Scan IDs.

An Artifact is a generated file such as PNG, JSON, NPZ, PLY, and later final GLB/FBX.

## Multi-scan policy

Storage and run selection already support multiple scans per Gallery.

The current worker processes selected scans independently. This is deliberate: multi-scan fusion must not be implemented by simply concatenating coordinate systems.

Planned multi-scan stages:

1. determine whether scans already share a stable coordinate system;
2. estimate coarse alignment from room/bullet-trap structures;
3. refine with ICP/features only after a valid coarse transform;
4. preserve each scan transform and provenance;
5. fuse evidence at semantic level before destructive geometry merge;
6. retain per-scan confidence so one bad scan cannot corrupt a good one.

## Storage

SQLite stores metadata only. Large binary files stay on disk.

Benefits:

- database remains small;
- scans can be copied/backed up normally;
- generated runs can be pruned independently;
- no multi-gigabyte BLOB transactions;
- Blender and external tools can consume normal files.

## Worker isolation

The web process launches a worker using the same virtual environment:

~~~text
python -m scan2stage.worker <run-id>
~~~

The worker writes progress to SQLite and append-only text logs.

Future improvements:

- explicit cancel flag;
- job queue with enforced concurrency;
- per-stage timings;
- process CPU/RAM monitoring;
- resume/retry from cached intermediate stages.

## Artifact policy

Current valid result artifacts include:

- semantic map PNG;
- reports/scene JSON;
- top-view NPZ;
- sampled and normalized PLY.

Final result.glb and result.fbx are only exposed if a real exporter generated them. Source scan files must never be mislabeled as final results.

## Recommended future additions

1. Manual review/editor state stored separately from automatic detections.
2. Dataset versioning: confirmed corrections become labeled validation examples.
3. Cache keys from scan checksum + processing settings.
4. Run comparison to compare two parameter sets on the same Gallery.
5. Backup/export package containing Gallery metadata, source hashes, scene config and selected artifacts.
6. Health diagnostics page: Python/Open3D/Blender versions, free disk, RAM, CPU.
7. Storage retention controls for deleting derived heavy PLY/NPZ while retaining source and final scene.
8. Multi-scan registration review before fusion.
9. Asset-library manager for clean target/decor models.
10. Manual semantic correction UI directly on the top-view map.
