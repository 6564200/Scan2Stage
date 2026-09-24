# Scan2Stage engineering plan

## Current baseline

~~~text
local web UI
 -> Gallery / Scan storage
 -> Run + settings snapshot
 -> worker process
 -> textured mesh sampling
 -> room normalization
 -> structural-first detector
 -> semantic PNG + diagnostics
~~~

The current engineering priority is reliability and reproducibility on a Windows workstation.

## P0 — local application correctness

### Job lifecycle

- enforce max parallel runs;
- add cancel/retry;
- detect stale/crashed workers;
- keep append-only logs;
- record per-stage timings.

### Storage safety

- SHA-256 every source scan;
- never overwrite sources;
- atomic artifact publication;
- archive/delete UI with confirmation;
- free-disk guard before a run.

### Environment diagnostics

Expose Python, Open3D, Blender, CPU, RAM and disk status in the UI.

## P0 — geometry correctness

### Floor rotation

Map the fitted floor normal to +Z, not only its offset.

### Wall protrusions

Detect wheel-cover boxes as local wall depth-profile bumps and keep gaps available for targets.

### Local Metric verifier

Add explicit plane fitting and partial template projection. Generic Metric detection precedes B/S subtype.

### Bullet traps

Measure all three variants and recover front plane/local frame.

## P1 — multi-scan

1. source checksums and metadata;
2. detect shared coordinate frames;
3. structure-based coarse alignment;
4. alignment review UI;
5. refinement;
6. semantic evidence fusion;
7. canonical Gallery frame.

Do not merge geometry before transforms are validated.

## P1 — manual review

Automatic detector output and human corrections must be separate layers. A confirmed correction should be reusable as validation/training data without destroying original evidence.

## P2 — clean scene export

- typed scene graph;
- clean asset registry;
- deterministic Blender build;
- result.glb and result.fbx;
- optional .blend;
- expose all final artifacts through Results page.

## P2 — performance

- coarse 4–5 cm whole scene;
- fine 1–2 cm ROIs;
- spatial tiling;
- parallel local candidate verification;
- cache by source hash + settings;
- CPU/RAM profiling first.

## Metrics

Initial labeled-set goals:

- Metric Target proposal recall > 90%;
- Popper/metal recall > 95%.

Precision is evaluated separately after proposal generation.
