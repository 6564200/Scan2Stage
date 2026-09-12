# Pilot architecture: Colab now, dedicated production machine later

## Source of truth

GitHub repository `6564200/Scan2Stage` is the source of truth for code, tests, notebooks and container definition.

## Environment strategy

Google Colab is the primary development and integration-test runtime during the
pilot. The intended production runtime is a dedicated machine. This is a planned
environment migration, not a pipeline rewrite.

The core pipeline lives in `src/scan2stage` and must not import `google.colab`,
depend on notebook state, or assume `/content` paths. Notebooks may handle upload,
download, visualization, and command orchestration, but they must call the same
package API or CLI used in production.

GitHub `main` is the hand-off boundary between sessions: a fresh Colab runtime
must be able to clone it and reproduce the current result.

## Current pilot flow

Flow:

1. Colab clones only `main` from GitHub.
2. `scripts/colab_bootstrap.sh` installs a compatible Open3D build and the package.
3. An UGScan `.zip` or `.glb` is uploaded directly or copied from durable storage.
4. The notebook invokes `scan2stage INPUT --output-dir OUTPUT --source-up y`.
5. The CLI writes ingestion, room, and object-candidate artifacts.
6. The notebook prints diagnostics and visualizes outputs without reimplementing
   algorithms.
7. `pytest -q` runs against the checked-out package.
8. Outputs and useful diagnostics may be copied to durable storage.

`notebooks/02_room_normalization.ipynb` is the current mesh-pipeline pilot.
`notebooks/01_colab_pilot.ipynb` is retained as a legacy PLY smoke test.

## GCP storage convention

Recommended pilot layout:

```text
gs://<bucket>/scan2stage/
  raw/<scan-id>/scan.zip
  runs/<scan-id>/<run-id>/report.json
  runs/<scan-id>/<run-id>/sampled_colored.ply
  runs/<scan-id>/<run-id>/room_geometry.json
  runs/<scan-id>/<run-id>/room_normalized.ply
  runs/<scan-id>/<run-id>/object_candidates.json
  runs/<scan-id>/<run-id>/object_points.ply
```

No GCP SDK dependency is added to the core package. Colab/GCP orchestration uses `gcloud storage` or `gsutil` outside the core.

## Portability contract

The production boundary is the package CLI and its versioned JSON/file artifacts:

```bash
scan2stage scan.zip \
  --output-dir outputs/scan \
  --samples 300000 \
  --source-up y
```

The same command and input must have the same coordinate conventions, defaults,
schemas, and deterministic parameters in Colab, CI, Docker, and the production
machine. Absolute artifact paths and performance timings may differ.

To preserve this contract:

- keep all result-affecting defaults in Python/CLI code, never only in a notebook;
- record explicit parameters, versions, seed, resolved input format, and transforms
  in the run report;
- use paths supplied by CLI arguments rather than Colab-specific constants;
- keep Blender, PySide6, cloud SDKs, and future GPU dependencies optional;
- maintain at least one small redistributable end-to-end fixture for CI and
  cross-environment comparison;
- compare output schemas and numeric tolerances across environments before a
  release, rather than requiring byte-identical PLY files.

## Production-machine migration checklist

Before moving the pilot to the production machine:

1. Pin and record the Python, Open3D, NumPy, SciPy, OpenCV, and package versions
   validated in Colab.
2. Build the same package revision in an isolated environment or container on the
   production machine.
3. Run unit tests and the redistributable end-to-end fixture in both environments.
4. Run a small representative scan set and compare room dimensions, transforms,
   retained candidate count/features, and rejection reasons within documented
   tolerances.
5. Configure production input/output storage outside the core package.
6. Benchmark sample count, memory, CPU/GPU use, and processing time; tune only
   explicit configuration values.
7. Add Blender and the manual-correction UI as separate optional runtime layers
   after the headless CLI contract is stable.

The production machine should not need any notebook to process a scan. Colab can
remain a reproducible research/debugging surface after production deployment.
