# Structural-first detector v2.3

## Why structural-first

Large gallery scans contain occlusion, incomplete mesh surfaces, texture noise and decorations. Searching the full mesh directly for a small target produces too many false positives and misses partially reconstructed targets.

The v2 pipeline treats the stage as a structured scene:

~~~text
mesh
 -> floor / room
 -> top-view structural layers
 -> structural components
 -> shooting direction + rear side
 -> candidate zones / soft hypotheses
 -> local 3D verification
 -> semantic scene graph
~~~

A recognized structure is not removed from the source evidence. A cardboard target can be geometrically merged with a trap, wall or decoration.

## Coordinate convention

Runtime geometry is normalized to meters and Z-up. Top view is the XY plane and every object height is measured relative to the detected floor.

## Top-view layers

Default coarse grid resolution: 5 cm/cell.

Height slices:
- 0.00–0.15 m
- 0.15–0.40 m
- 0.40–0.80 m
- 0.80–1.20 m
- 1.20–1.60 m
- 1.60–2.20 m

The implementation stores density, min/max height, height range and occupancy per slice. A future fine pass should use 1–2 cm/cell only around candidate zones.

## Structural objects

Current footprint classes are deliberately broad:
- partition_or_wall
- large_structure
- compact_structure
- unknown_structure

Planned semantic classes:
- bullet trap (three measured variants)
- partition
- barrel
- decoration
- wall protrusion / wheel cover

### Wall protrusions

Wheel-cover boxes should be detected as depth-profile bumps of a wall. They often merge into the wall connected component, so isolated-component search is unreliable.

Planned algorithm:
1. fit wall centerline;
2. transform points into wall-local coordinates u (along) and v (normal);
3. estimate stable wall depth baseline;
4. find local outward depth bumps;
5. use bump height to classify low wheel covers;
6. mask only the bump footprint, never the whole wall strip;
7. keep gaps between bumps available for target hypotheses.

## Shooting-direction prior

Practical-shooting targets face the athlete. In an indoor gallery the long room axis plus tall support at one end is used to estimate the rear direction. This is a reported confidence prior, not a hard fact.

For a planar target with horizontal normal n and shooting direction d:

orientation_score = abs(dot(n, d))

A high value is expected for a target facing the firing side.

## Metric Targets

The clean Metric target face is approximately 0.414 m wide and 0.535 m high. Generic Metric Target detection happens before B/S classification.

Evidence:
- local plane / planarity;
- approximate width and visible height;
- thinness;
- orientation toward the firing side;
- installation/context;
- support/stand geometry (planned refinement);
- texture only as a weak feature.

Partial observations are valid. Early proposal generation intentionally favors recall; a target hidden by decoration must remain a hypothesis.

B/S subtype should use installation height and context, not cardboard silhouette alone.

## Metal targets

Poppers and steel are expected close to the rear bullet trap. Rear proximity, height, thin vertical geometry and orientation are primary evidence. Blue texture is useful but should not be mandatory.

Planned subtypes:
- IPSC Popper
- IPSC Mini Popper
- IPSC Plates / Plates quad

## Fault Lines

Fault Lines are floor semantics:
- close to floor;
- red-dominant color;
- elongated footprint;
- ultimately reconstructed as connected polylines/polygons.

They are useful both as output geometry and as context for the usable shooting area.

## Confidence policy

Proposal generation is recall-oriented.

Suggested workflow states:
- CONFIRMED: score >= 0.80
- LIKELY: 0.55–0.80
- UNRESOLVED: 0.35–0.55

These are workflow thresholds, not calibrated probabilities. Real thresholds must be calibrated on labeled scans.

## Performance model

The intended execution model is parallel:

~~~text
preprocess once
  |-- Fault Line worker
  |-- structural/top-view worker
  |-- texture/color worker

structural result
  |-- Metric candidate workers
  |-- Popper/metal worker
  |-- decor/template workers
~~~

Spatial tiling and local candidate verification are naturally parallel. A 16-core CPU and 64 GB RAM are a practical workstation target; GPU becomes more important when image detectors or segmentation are introduced.
