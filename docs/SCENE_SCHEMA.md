# Scan2Stage scene/object schema

## Recognition policy

Candidates are not automatically deleted because they are planar. Internal gallery partitions, mesh walls, port walls, targets and decorations may all be planar.

Initial operation is human-in-the-loop:

1. detect candidate;
2. compare with known catalog/recognition exemplars;
3. assign confidence;
4. ask user when confidence is insufficient;
5. store the confirmed label as a future recognition exemplar.

## Clean asset library

Recognition exemplars and output assets are separate datasets.

Recommended layout:

```text
assets/
  <class_id>/
    <asset_id>.blend
    <asset_id>.glb
    metadata.json
```

Asset convention:

- units: meters;
- Z up;
- +Y front;
- origin: installation anchor;
- `.blend` is the editable master;
- `.glb` is the portable clean asset.

Example metadata:

```json
{
  "asset_id": "popper_standard_v1",
  "class_id": "popper",
  "blend": "popper_standard_v1.blend",
  "glb": "popper_standard_v1.glb",
  "front_axis": "+Y",
  "up_axis": "+Z",
  "origin": "bottom_center",
  "allow_uniform_scale": false
}
```

## Scene object

```json
{
  "object_id": "obj_001",
  "class_id": "bullet_trap",
  "variant_id": "bullet_trap_size_a",
  "asset_id": "bullet_trap_size_a_clean",
  "confidence": 0.92,
  "user_confirmed": true,
  "transform": {
    "position_m": [1.0, 4.0, 0.0],
    "rotation_quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
    "scale": [1.0, 1.0, 1.0]
  },
  "children": []
}
```

## Bullet trap and targets

Targets are modeled as children of a recognized bullet trap, not as expected standalone scene objects.

```json
{
  "object_id": "trap_003",
  "class_id": "bullet_trap",
  "variant_id": "bullet_trap_size_b",
  "asset_id": "bullet_trap_size_b_clean",
  "transform": {
    "position_m": [0.5, 8.2, 0.0],
    "rotation_quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
    "scale": [1.0, 1.0, 1.0]
  },
  "children": [
    {
      "object_id": "target_003_01",
      "class_id": "cardboard_target",
      "asset_id": "cardboard_target_clean",
      "parent_id": "trap_003",
      "local_position_m": [-0.22, 0.0, 0.25],
      "local_rotation_deg": 0.0,
      "confidence": 0.84,
      "user_confirmed": false
    }
  ]
}
```

This allows target type, count and arrangement to vary independently from the three large bullet-trap variants.

## Size filtering

Do not reject a candidate just because one dimension is below 0.10 m. Thin targets and panels are valid.

Current safe filter: reject only when the second-largest robust extent is below 0.10 m. This preserves planar and linear-looking structures for later grouping/recognition.
