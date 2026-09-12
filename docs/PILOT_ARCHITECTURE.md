# Pilot architecture: Colab + GitHub + GCP

## Source of truth

GitHub repository `6564200/Scan2Stage` is the source of truth for code, tests, notebooks and container definition.

## Pilot runtime

Google Colab is an interactive test runner only. The core pipeline lives in `src/scan2stage` and must not import Colab-specific modules.

Flow:

1. Colab clones GitHub.
2. Colab installs the package with `pip install -e .[dev]`.
3. A `.ply` is uploaded directly or copied from Google Cloud Storage.
4. `scan2stage` creates `processed.ply` and `stats.json`.
5. Tests run with `pytest`.
6. Results may be copied back to GCS.

## GCP storage convention

Recommended pilot layout:

```text
gs://<bucket>/scan2stage/
  raw/<scan-id>/input.ply
  processed/<scan-id>/processed.ply
  reports/<scan-id>/stats.json
```

No GCP SDK dependency is added to the core package. Colab/GCP orchestration uses `gcloud storage` or `gsutil` outside the core.

## Production portability

The production boundary is the CLI:

```bash
scan2stage INPUT.ply --output OUTPUT.ply --stats STATS.json --voxel 0.02
```

The same command can run in Colab, a GCP VM, Docker, or a dedicated workstation. Production migration therefore changes orchestration/storage, not point-cloud algorithms.
