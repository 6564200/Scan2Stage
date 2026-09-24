# Scan2Stage scene/object schema

## Recognition policy

The scene model separates observation, hypothesis, and clean output asset. Structural geometry is evidence and is never deleted merely because it matches a wall, partition, or trap.

Initial operation remains human-in-the-loop:

1. generate hypotheses with high recall;
2. accumulate geometry, top-view, orientation, color and context evidence;
3. classify when evidence is sufficient;
4. retain uncertain hypotheses for review;
5. store confirmed labels as future validation/training examples.

## Coordinate convention

- units: meters;
- runtime scene: Z up;
- top view: XY;
- clean assets: +Y front unless metadata overrides it;
- transforms explicitly state quaternion order.

## Scene graph example

~~~json
{
  "object_id": "target_014",
  "class_id": "ipsc_metric_target_b",
  "state": "LIKELY",
  "confidence": 0.77,
  "transform": {
    "position_m": [1.2, 8.4, 1.15],
    "rotation_quaternion_xyzw": [0, 0, 0, 1],
    "scale": [1, 1, 1]
  },
  "context": {
    "faces_shooter": true,
    "support_object_id": "trap_003",
    "shooting_zone_id": "zone_01"
  },
  "evidence": {
    "geometry": 0.84,
    "topview": 0.65,
    "orientation": 0.94,
    "color": 0.30,
    "context": 0.88,
    "partial_observation": true
  }
}
~~~

## Key semantic classes

Structural:
- bullet_trap
- partition
- barrel
- decoration
- wall_protrusion
- unknown_structure

Targets:
- ipsc_metric_target (generic proposal)
- ipsc_metric_target_b
- ipsc_metric_target_s
- popper
- mini_popper
- plates_quad
- metal_target (generic proposal)

Floor semantics:
- fault_line

## Domain constraints

Constraints contribute to confidence; they must not silently erase evidence.

- All targets face the athlete / firing side.
- Poppers and steel are expected adjacent to the rear bullet trap.
- Cardboard targets can be installed at different distances.
- Cardboard targets may appear between low wall/wheel-cover protrusions.
- Fault Lines lie close to the floor and define shooting-area boundaries.

## Clean asset library

Recognition exemplars and output assets are separate datasets.

~~~text
assets/
  <class_id>/
    <asset_id>.blend
    <asset_id>.glb
    metadata.json
~~~

## Fault Lines

Fault Lines should ultimately be represented as polylines rather than boxes.

~~~json
{
  "object_id": "fault_line_01",
  "class_id": "fault_line",
  "polyline_xy_m": [[-1.2, 2.0], [0.5, 2.0], [1.1, 2.8]],
  "width_m": 0.05,
  "confidence": 0.91
}
~~~

## Bullet traps and target relations

Targets can reference a recognized bullet trap through context.support_object_id, but cardboard targets are not globally required to be children of a bullet trap. They may be installed at different distances in the stage.

The rear bullet trap remains a strong context anchor for metal targets.
