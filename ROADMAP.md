# Scan2Stage roadmap

The immediate product goal is reliable reconstruction of a practical-shooting stage from a textured mobile scan. Recognition is structural-first: recover the stage layout, then classify targets and props in context.

## Implemented foundation

### M1 — Import and preprocessing
- PLY loading and validation.
- UGScan ZIP / GLB / glTF ingestion.
- Legacy FBX / OBJ path.
- Texture-aware surface sampling.
- Voxel/outlier/normal preprocessing for point-cloud input.

### M2 — Coordinate normalization
- Source-axis conversion to canonical Z-up.
- Unit conversion to meters.
- Floor detection and floor-relative heights.
- Source-to-room transform reporting.

### M3 — Room reconstruction
- Wall-plane candidates.
- Rectangular room footprint.
- Conservative structural handling.
- Internal planar structures are not automatically discarded.

### M4 — Candidate extraction
- Existing DBSCAN/PCA candidates remain available.
- Conservative unknown-first policy.
- Thin/planar geometry retained for later semantic analysis.

### M4.5 — Structural-first detector (current)
- Multi-height XY top-view at configurable resolution.
- Density/min/max/height-range layers.
- Structural connected components and footprint descriptors.
- Fault Line proposals from red, low, elongated floor evidence.
- Shooting-direction prior from long room axis plus rear tall support.
- Generic IPSC Metric Target local-patch scoring.
- Partial target observations allowed.
- B/S subtype deliberately deferred until generic detection.
- Rear-zone metal target proposals.
- Structural evidence is never destructively removed before target analysis.

## Next: v2.4 structural semantics

1. Wall protrusion / wheel-cover profiles:
   - detect protrusions as depth changes of a parent wall, not independent connected components;
   - use measured height to reject them as target candidates;
   - preserve gaps between protrusions as target-valid zones.

2. Bullet-trap recognition:
   - encode the three known trap size variants once dimensions are measured;
   - recover front plane, local frame and working side;
   - classify rear trap vs intermediate traps.

3. Metric Target verification:
   - refine local plane extraction;
   - compare projected partial silhouette against clean target template;
   - use support/stand evidence;
   - classify IPSC Metric Target B vs S from installation height/context.

4. Metal branch:
   - distinguish Popper / Mini Popper / Plates;
   - combine rear proximity, silhouette, height, orientation and blue texture;
   - exploit repeated plate layouts.

5. Fault Lines:
   - reconstruct connected polylines, not only isolated components;
   - derive shooting-area polygons when topology is sufficient.

## M5 — Semantic scene graph and confidence
- Typed scene objects and relationships.
- support/context links.
- Per-evidence confidence: geometry, top-view, orientation, color, context.
- CONFIRMED / LIKELY / UNRESOLVED review states.
- Preserve unresolved hypotheses instead of deleting them.

Initial validation targets:
- Metric Target recall > 90%.
- Popper/metal recall > 95%.
- Precision reported separately; recall has priority during proposal generation.

## M6 — Review and validation
- Versioned scene_config.json.
- Top-view/debug preview with all hypotheses.
- Manual correction workflow.
- Regression fixtures from real failure cases.
- Hard-negative library: decor, wall protrusions, partial structures, blue non-targets.

## M7 — Asset replacement and Blender
- Clean asset registry.
- Deterministic placement from scene graph.
- Headless Blender generation.
- Preserve measured pose while replacing noisy scanned geometry.

## M8 — Performance
- Coarse 4–5 cm structural pass.
- Fine 1–2 cm local refinement only in candidate zones.
- Spatial tiling.
- Parallel local candidate verification.
- Independent Fault Line / structure / texture branches.
- GPU acceleration only where it materially helps image/ML stages.

## M9 — Hybrid ML only if metrics require it
- 2D RGB detector plus 3D association before learned 3D detection.
- Learned models only after the labeled dataset is large enough to measure generalization and hard negatives.
