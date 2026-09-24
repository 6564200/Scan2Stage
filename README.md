# Scan2Stage

Scan2Stage is a local-first Windows application that converts textured 3D scans of a practical-shooting gallery into a structured semantic stage representation and, in later milestones, a clean GLB/FBX/Blender scene.

## Current direction

The primary runtime is now a local Windows 10 workstation:

~~~text
browser UI
  -> FastAPI local server
  -> SQLite project metadata
  -> immutable source scan storage
  -> worker process
  -> structural-first detector
  -> semantic map / reports
  -> future clean-scene GLB/FBX exporter
~~~

Colab notebooks are no longer part of the supported workflow.

## Local UI

Install on Windows 10 using:

~~~bat
scripts\setup_windows.bat
~~~

Start:

~~~bat
scripts\start_windows.bat
~~~

Then open:

~~~text
http://127.0.0.1:8765
~~~

Full setup instructions: WINDOWS_LOCAL_SETUP.md.

## UI pages

- Инструкция — short workflow and storage location;
- Загрузка — create a Gallery and upload one or multiple scans;
- Gallery — select scans and start processing;
- Ход выполнения — progress and status history;
- Результаты — semantic PNG and generated artifacts;
- Логи — worker output and errors;
- Настройки — processing parameters with explanations.

## Persistent data model

One Gallery can contain multiple scans. Every processing Run records a settings snapshot and selected Scan IDs. Source files are immutable and results are versioned per Run.

Default local data root:

~~~text
%USERPROFILE%\Scan2StageData
~~~

See docs/LOCAL_ARCHITECTURE.md.

## Current detector

The structural-first pipeline currently includes:

- UGScan ZIP and GLB/glTF ingestion;
- legacy FBX/OBJ ingestion;
- texture-aware surface sampling;
- conversion to meters and canonical Z-up;
- floor/room normalization;
- conservative candidate extraction;
- multi-height top-view;
- structural components;
- Fault Line proposals from low red geometry;
- shooting-direction prior;
- generic IPSC Metric Target proposals with partial-observation tolerance;
- rear-zone metal proposals;
- semantic top-view PNG renderer.

Structural geometry is context/evidence, not a destructive mask.

## Multi-scan

The application can already store several scans for one Gallery and include several scans in one Run. They are currently processed independently.

Automatic registration/fusion is not yet implemented. It will use explicit transforms and provenance instead of blindly merging point clouds.

## Outputs

Per processed scan:

~~~text
sampled_colored.ply
room_normalized.ply
room_geometry.json
object_candidates.json
structural_scene.json
topview_layers.npz
semantic_topview.png
report.json
run_manifest.json
~~~

result.glb and result.fbx will appear only when the clean-scene exporter is implemented.

## Development

~~~bat
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest -q
~~~

CLI remains available:

~~~bat
.venv\Scripts\scan2stage.exe scan.glb --output-dir outputs\test --samples 300000 --source-up y
~~~

Architecture and roadmap:

- docs/LOCAL_ARCHITECTURE.md
- docs/STRUCTURAL_DETECTOR.md
- docs/SCENE_SCHEMA.md
- ROADMAP.md
