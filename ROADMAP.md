# Scan2Stage roadmap

## Current milestone — local workstation application

Implemented / being established on main:

- Windows 10 + Python venv workflow;
- local FastAPI web UI;
- SQLite Gallery / Scan / Run / Artifact metadata;
- immutable source scan storage;
- multiple scans per Gallery;
- background worker process with progress and logs;
- settings snapshots per Run;
- semantic PNG result and downloadable diagnostic artifacts;
- structural-first detector v2.3.

Colab/notebook orchestration is retired.

## M1 — Local application hardening

- enforce configured parallel-run limit;
- cancel/retry controls;
- disk-space and environment diagnostics;
- safe deletion of completed Runs/results and uploaded Scan source bytes;\n- archive/delete whole Galleries;
- checksums for source scans;
- stage timings and resource metrics;
- transactional run output publication.

## M2 — Structural detector v2.4

- wall protrusion / wheel-cover depth profiles;
- generic rear bullet-trap hypothesis (implemented baseline);\n- classify three measured bullet-trap variants once dimensions are available;
- stronger local Metric plane/template verifier;
- Metric B/S classification from installation height/context;
- Popper vs Mini Popper vs Plates;
- Fault Line polyline reconstruction;
- improved semantic map symbols and confidence display.

Initial validation targets:

- Metric Target proposal recall > 90%;
- Popper/metal recall > 95%.

## M3 — Multi-scan registration and evidence fusion

- keep every source scan immutable;
- detect whether captures share coordinates;
- coarse room/structure alignment;
- transform review;
- registration refinement;
- per-scan provenance/confidence;
- fuse semantic evidence rather than blindly concatenate meshes;
- choose a canonical Gallery coordinate frame.

## M4 — Manual review UI

- click/select objects on semantic top-view;
- change class;
- move/rotate/delete/add object;
- confirm/reject target hypotheses;
- edit Fault Lines;
- save corrections as a versioned review layer;
- compare automatic vs corrected scene.

## M5 — Scene graph and clean asset library

- typed scene schema;
- support/context relations;
- clean asset registry with anchor/front/up metadata;
- asset-library manager;
- measured bullet-trap variants;
- confirmed object replacement.

## M6 — Blender / GLB / FBX generation

- configure blender.exe;
- deterministic clean-scene build;
- output result.glb;
- output result.fbx;
- optional .blend working scene;
- preserve Gallery coordinate frame;
- expose outputs in web Results page.

## M7 — Performance

- coarse 4–5 cm whole-scene pass;
- 1–2 cm refinement only in ROIs;
- spatial tiling;
- parallel local candidate verification;
- reusable intermediate cache keyed by source checksum + settings;
- profile CPU/RAM/I/O before adding GPU code.

## M8 — Dataset and regression system

- confirmed corrections become labeled examples;
- hard-negative library;
- representative large-scene benchmark;
- run-to-run metrics;
- regression dashboard.

## M9 — ML only where measured benefit exists

- RGB-assisted 2D detection + 3D association;
- segmentation where texture materially improves recall;
- learned 3D detection only after the labeled dataset is sufficient.
