# Scan2Stage engineering plan

This plan reflects the structural-first prototype now present on main.

## Current processing baseline

~~~text
UGScan ZIP/GLB
 -> sampled colored point cloud
 -> meters / Z-up
 -> floor + rectangular room
 -> legacy conservative object candidates
 -> multi-height top-view
 -> structural components + Fault Lines
 -> shooting-direction prior
 -> Metric/metal soft hypotheses
 -> JSON/NPZ diagnostics
~~~

The central policy is explicit: structural understanding must not destroy target evidence.

## P0 — correctness before classifier sophistication

### 1. Full floor rotation

The current room path translates detected floor height but still needs a complete rotation that maps the fitted floor normal to +Z.

Acceptance:
- synthetic tilted rooms normalize floor normal within 1 degree;
- source-to-room transform includes rotation plus translation;
- colors and normals survive.

### 2. Wall protrusion depth profiles

Implement wall-local depth profiles for wheel-cover boxes. Component segmentation alone is insufficient because protrusions merge with walls.

Acceptance:
- low attached bumps are classified as wall_protrusion;
- height is reported;
- only bump footprint is excluded from target hypotheses;
- gaps between bumps remain searchable.

### 3. Local Metric plane/silhouette verifier

The current local scorer is deliberately permissive. Add explicit plane RANSAC and partial template projection using the clean 0.414 x 0.535 m target face.

Acceptance:
- partially occluded target remains detectable with at least 35-45% visible face;
- wall/decor patches with wrong orientation are rejected;
- B/S classification is performed only after generic target detection.

### 4. Bullet-trap variants

Measure and encode all three trap variants. Recover front plane/local frame and identify the rear trap.

Acceptance:
- each measured variant recognized on validation scans;
- metal search ROI generated from rear trap front;
- trap-facing direction agrees with stage shooting direction.

## P1 — Fault Lines and stage topology

Upgrade red floor components to linked polylines and, where possible, a shooting-area polygon.

Acceptance:
- red features above the floor band are rejected;
- disconnected noise is not promoted;
- line segments preserve corners and topology.

## P1 — target subtypes

Metal:
- Popper vs Mini Popper;
- Plates / Plates quad;
- combine rear proximity, height, silhouette, orientation and blue color.

Cardboard:
- generic IPSC Metric Target first;
- B/S via installation height and context.

## P1 — ingestion/reproducibility work retained from the earlier audit

- bounded/streamed ZIP resolver;
- choose default units after inner mesh format is resolved;
- allocate surface samples by triangle area, not triangle count;
- transactional outputs;
- deterministic seeds/parameters in run manifest;
- explicit room-fit quality gates.

## P2 — semantic contracts

Replace untyped scene object dictionaries with typed Pydantic models for transform, evidence scores, confidence/review state, support/context links, polylines and object variants.

Add validation for config/object_catalog.json including unique IDs and reference integrity.

## P2 — validation dataset

Before learned detection:
- label representative large maps;
- record all real targets, including occluded targets;
- record hard negatives: decor, wall protrusions, wall ends and blue non-targets;
- measure proposal recall and final precision separately.

Initial goals:
- Metric Target recall > 90%;
- Popper/metal recall > 95%.

## P3 — performance

Keep the coarse-to-fine strategy:
- 4-5 cm top-view structural pass;
- 1-2 cm refinement only around hypotheses;
- spatial tiling;
- parallel local-patch verification;
- independent Fault Line, texture and structural branches.

CPU/RAM are the current priority. GPU acceleration is reserved for image segmentation/detection or learned models where profiling shows a benefit.

## P4 — clean assets and Blender

Once semantic outputs are stable:
- asset registry with anchor/front/up metadata;
- deterministic asset replacement;
- preview GLB/top-view;
- headless Blender scene generator;
- correction UI as a client of the same scene schema.
