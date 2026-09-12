# Scan2Stage engineering plan

This document converts the product manifest into an implementation order. It is
based on the current repository rather than the intended final architecture.

## Current baseline

The strongest part of the prototype is the straight-through geometry path:

```text
ZIP / mesh -> material-aware import -> surface sampling -> Z-up/meters
  -> floor and rectangle -> conservative structural mask
  -> voxelized DBSCAN primitives -> JSON diagnostics
```

The project already has useful boundaries between ingestion, sampling, room
geometry, and candidate extraction. It also encodes two important safety policies:
the room is a rectangle and internal planes are not stripped merely because they
are large.

This is not yet a V1 semantic-scene pipeline. There is no validated catalog API,
recognition library, confirmation workflow, asset registry, complete scene model,
or Blender generator. The immediate goal should therefore be to make geometry
outputs reliable and versioned before adding recognition.

## Audit findings

### P0: correctness and data-loss risks

1. **Floor tilt is not corrected.** Floor detection validates a plane, but room
   normalization only translates its height. A tilted capture leaves walls
   non-vertical and makes height clipping, rectangle fitting, and object poses
   systematically wrong.
2. **The documented linear-object policy and implementation disagree.** Candidate
   feature extraction can label a primitive `linear`, but the subsequent
   second-largest-extent filter rejects every sufficiently thin linear primitive.
   Fault lines, frame members, and stands can therefore disappear.
3. **The floor mask can erase floor-mounted semantics.** Every point below the
   clearance is structural, regardless of local geometry or color. This is risky
   for fault lines and low bases and should be made explicit in diagnostics before
   it is made more selective.
4. **Room fallback can silently fit the wrong space.** When supported opposing
   walls are unavailable, global trimmed quantiles become room boundaries. A large
   corridor or neighboring gallery can then determine the result without a clear
   quality gate.

### P1: ingestion and reproducibility risks

1. ZIP paths are checked, but the implementation extracts the entire archive and
   has no member-count, uncompressed-size, or compression-ratio limits.
2. Default scale is selected from the outer CLI suffix. A ZIP containing a legacy
   FBX receives the ZIP default (`1.0`) rather than the FBX default (`0.01`).
3. Samples are allocated between mesh parts by triangle count. Parts containing a
   few large triangles are undersampled relative to parts containing many small
   triangles; allocation should follow surface area.
4. Output writes are not consistently checked. A failed room or candidate PLY
   write can still leave JSON that appears successful.
5. Randomness is seeded for surface sampling, but RANSAC and DBSCAN reproducibility
   is not defined or reported.

### P1: contract and testing gaps

1. `SceneConfig` currently validates little beyond coordinate literals and an
   untyped object list. It does not represent the documented room, transforms,
   confidence, confirmation state, variants, or child targets.
2. `object_catalog.json` is data without a loader or Pydantic validation. Duplicate
   IDs, invalid dimensions, and unknown child classes are not rejected.
3. ZIP tests cover the happy path only; traversal, absolute paths, multiple meshes,
   archive limits, and deterministic selection need tests.
4. Candidate tests exercise helpers, not the full extraction report. There are no
   regression fixtures for linear preservation, internal composite structures, or
   floor-mounted objects.
5. There is no small, redistributable integration fixture that runs ingestion
   through candidate extraction without proprietary UGScan data.

## Recommended execution order

### Phase 1 — establish trustworthy geometry

#### 1.1 Align the floor, not only its offset

Compute a stable rotation that maps the detected floor normal to `+Z`, apply it
before height clipping and wall detection, and compose it into `source_to_room`.
Resolve the antiparallel case and reject implausible tilt rather than guessing.

**Acceptance criteria**

- synthetic rooms tilted around two axes normalize to a floor normal within 1° of
  `+Z`;
- recovered wall positions stay within 30–50 mm on synthetic fixtures;
- `source_to_room` maps original source points to the persisted cloud;
- colors and normals survive the transform.

#### 1.2 Make candidate retention policy internally consistent

Separate shape labeling from retention. Preserve meaningful linear primitives
using length, point support, and optionally floor-contact rules instead of applying
the planar two-axis threshold to all shapes. Add reason codes and counts for every
rejection.

**Acceptance criteria**

- `2.0 x 0.05 x 0.05 m` frame/fault-line fixtures survive;
- `0.08 x 0.06 x 0.03 m` noise fixtures are rejected;
- thin `0.60 x 0.45 x 0.01 m` targets survive;
- JSON reports distinguish size, support, structural, and outside-room rejection.

#### 1.3 Add room-fit quality gates

Report support per boundary, fallback use, plausible dimension ranges, and an
overall quality/confidence state. Low-quality fits should stop semantic extraction
or require review instead of silently cropping possible objects.

**Acceptance criteria**

- corridor-heavy and missing-wall fixtures produce an explicit `review` result;
- four well-supported walls produce `accepted`;
- object extraction refuses an invalid rectangle unless an explicit override is
  supplied.

### Phase 2 — harden ingestion and outputs

#### 2.1 Stream and limit ZIP ingestion

Inspect central-directory metadata, reject unsafe or ambiguous archives, enforce
configurable member/size/ratio limits, and extract only the selected mesh plus any
external resources required by glTF. Prefer the canonical UGScan GLB name when it
is present, while keeping deterministic ambiguity errors.

**Acceptance criteria**

- tests cover traversal, absolute paths, symlink-like entries, too many members,
  oversized content, suspicious compression ratios, and multiple GLBs;
- a normal single-GLB UGScan archive remains a one-command input;
- rejected archives write no partial output.

#### 2.2 Resolve format before choosing defaults

Move unit-scale selection after container resolution. Preserve explicit
`--unit-scale` as the highest-priority override and record both the selected rule
and resolved format in `report.json`.

#### 2.3 Allocate surface samples by area

Calculate each part's triangle area after unit conversion and allocate the global
budget proportionally, with a documented minimum for non-empty parts. Test
determinism and exact/near-exact budget handling.

#### 2.4 Make outputs transactional

Check every serializer return value, write to a temporary run directory, and
publish the completed run atomically. Include pipeline version, parameters, seed,
timings, and artifact-relative paths in one manifest.

### Phase 3 — define semantic contracts before recognition

#### 3.1 Implement catalog models and loader

Add typed models for classes, variants, dimension ranges, placement, anchors,
allowed children, and recognition priority. Validate uniqueness and references.
Keep exact bullet-trap dimensions nullable until measured; do not invent them.

#### 3.2 Implement a real scene schema

Replace `list[dict]` with typed room, transform, object, child-target, confidence,
and confirmation models. Choose one naming/casing convention for coordinate axes
and one quaternion order, then add round-trip and schema-version tests.

#### 3.3 Add a CLI confirmation artifact

Before building a GUI, support a review JSON workflow:

```text
object_candidates.json -> review template -> user edits/confirmation
  -> validated recognized_objects.json -> scene_config.json
```

Never overwrite raw candidate evidence. Store label provenance, timestamp, source
candidate IDs, and whether a transform was edited.

### Phase 4 — recognition without premature ML

1. Match candidates to catalog priors by robust dimensions, shape, placement, and
   floor contact; always retain an `unknown` option.
2. Add a recognition-exemplar metadata schema and immutable dataset layout. Do not
   place clean assets in this store.
3. Implement primitive relationship graphs (distance, coplanarity, parallelism,
   contact, shared bounding rectangle) and composite hypotheses for mesh walls,
   frames, and stands.
4. Recognize the three bullet-trap variants once measured dimensions are available;
   estimate their front plane and local coordinate system.
5. Only then add RGB/texture target detection inside the trap's front ROI and map
   detections back to trap-local 3D coordinates.

Confidence thresholds should be calibrated from labeled validation scans, not
hard-coded as meaningful probabilities before a dataset exists.

### Phase 5 — clean assets and Blender

1. Validate an asset registry mapping `class_id`/`variant_id` to canonical `.blend`
   and `.glb` files, front axis, anchor, dimensions, and scale policy.
2. Generate a deterministic preview (top view or lightweight GLB) from
   `scene_config.json` before depending on Blender.
3. Add a headless `bpy` generator behind an optional integration boundary. Unit
   tests must not require Blender; Blender smoke tests should run separately.
4. Build PySide6 correction UI only after the review JSON operations and schema are
   stable, so the GUI remains a client of the same contracts.

## Proposed next three pull requests

### PR 1: floor rotation and transform consistency

- add rotation-to-Z utility and tilted synthetic-room tests;
- rotate points and normals before clipping;
- persist and test the complete homogeneous transform;
- add explicit floor-fit diagnostics.

### PR 2: shape-aware candidate retention

- replace the universal two-axis cutoff with planar/volumetric and linear policies;
- preserve long thin primitives;
- report rejection reason counters;
- add synthetic low-floor and internal-frame regression tests.

### PR 3: safe bounded ZIP resolver

- split archive inspection/selection from extraction;
- add resource limits and deterministic selection;
- choose scale from the resolved mesh format;
- add adversarial ZIP tests.

These three changes reduce silent geometry corruption and object loss before the
project accumulates APIs or labeled data on top of unstable inputs.

## Data and measurement needed from the project owner

- exact dimensions and installation anchors for all three bullet-trap variants;
- a written definition of the start position/front direction in a completed stage;
- redistribution-safe synthetic or commissioned integration fixtures;
- several representative failure scans: corridor leakage, tilt, partial walls,
  mesh partitions, low fault lines, and target/trap configurations;
- explicit UGScan export/commercial-use confirmation before scans are stored in a
  shared or public dataset.

## Definition of ready for recognition work

Recognition work should start when all of the following hold:

- room normalization passes tilted, corridor, and missing-wall regression suites;
- candidate recall is measured on a small manually labeled validation set;
- every discarded point/candidate has an auditable reason;
- catalog and scene files are schema-validated and versioned;
- source-to-room transforms round-trip within numerical tolerance;
- a safe, redistributable end-to-end fixture runs in CI.

Until then, geometry reliability and candidate recall have higher value than adding
classifiers, ICP, a desktop UI, or Blender automation.
