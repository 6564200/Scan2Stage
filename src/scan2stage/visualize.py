from __future__ import annotations

from pathlib import Path
import json

import numpy as np


def _major_segment(center, axes, length):
    center = np.asarray(center, dtype=float)
    axes = np.asarray(axes, dtype=float)
    direction = axes[:, 0]
    direction = direction / max(np.linalg.norm(direction), 1e-9)
    half = 0.5 * float(length) * direction
    return center - half, center + half


def _state_from_score(score: float) -> str:
    if score >= 0.80:
        return "CONFIRMED"
    if score >= 0.55:
        return "LIKELY"
    return "UNRESOLVED"


def object_summary(scene: dict) -> list[dict]:
    rows = []
    for obj in scene.get("structural_components", []):
        rows.append({
            "id": obj.get("id"),
            "class": obj.get("class_id"),
            "x_m": obj.get("center_xy_m", [None, None])[0],
            "y_m": obj.get("center_xy_m", [None, None])[1],
            "confidence": None,
            "state": "STRUCTURE",
        })
    for obj in scene.get("fault_lines", []):
        score = float(obj.get("confidence", 0.0))
        rows.append({
            "id": obj.get("id"),
            "class": "fault_line",
            "x_m": obj.get("center_xy_m", [None, None])[0],
            "y_m": obj.get("center_xy_m", [None, None])[1],
            "confidence": score,
            "state": _state_from_score(score),
        })
    for obj in scene.get("metric_target_proposals", []):
        score = float(obj.get("score", 0.0))
        center = obj.get("center_m", [None, None, None])
        rows.append({
            "id": obj.get("id"),
            "class": obj.get("class_id", "ipsc_metric_target"),
            "x_m": center[0],
            "y_m": center[1],
            "confidence": score,
            "state": _state_from_score(score),
        })
    for obj in scene.get("rear_metal_proposals", []):
        score = float(obj.get("confidence", 0.0))
        center = obj.get("center_m", [None, None, None])
        rows.append({
            "id": obj.get("id"),
            "class": obj.get("class_id", "metal_target"),
            "x_m": center[0],
            "y_m": center[1],
            "confidence": score,
            "state": _state_from_score(score),
        })
    return rows


def render_semantic_topview(
    structural_scene_json: str | Path,
    topview_npz: str | Path | None = None,
    output_path: str | Path | None = None,
    show_labels: bool = True,
    show_density: bool = True,
):
    """Render a readable semantic stage map from structural_scene.json.

    Symbol policy:
    - walls/partitions: thick line
    - large/unknown structures: line/outline
    - compact structures/decor: outlined footprint
    - Fault Lines: red line
    - cardboard targets: short face line + arrow toward shooter
    - poppers/metal: short line + icon label
    - plates: short line + circular icon label
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    scene_path = Path(structural_scene_json)
    scene = json.loads(scene_path.read_text(encoding="utf-8"))

    if topview_npz is None:
        artifact = scene.get("topview", {}).get("artifact")
        if artifact:
            candidate = Path(artifact)
            topview_npz = candidate if candidate.is_absolute() else scene_path.parent / candidate.name
        else:
            topview_npz = scene_path.parent / "topview_layers.npz"

    layers = np.load(topview_npz)
    density = layers["density"]
    origin = np.asarray(scene["topview"]["origin_xy_m"], dtype=float)
    res = float(scene["topview"]["resolution_m"])
    ny, nx = density.shape
    extent = [
        origin[0],
        origin[0] + nx * res,
        origin[1],
        origin[1] + ny * res,
    ]

    fig, ax = plt.subplots(figsize=(11, 12))

    if show_density:
        bg = np.log1p(density.astype(float))
        vmax = np.quantile(bg[bg > 0], 0.98) if np.any(bg > 0) else 1.0
        ax.imshow(
            bg,
            extent=extent,
            origin="lower",
            cmap="Greys",
            alpha=0.28,
            interpolation="nearest",
            vmin=0,
            vmax=max(vmax, 1e-6),
        )

    # Structural layer. Prefer the actual raster footprint boundary whenever it
    # is available; PCA centerlines are only a backwards-compatible fallback.
    structure_style = {
        "partition_or_wall": ("dimgray", 2.7, 0.90),
        "large_structure": ("saddlebrown", 3.4, 0.78),
        "compact_structure": ("darkorange", 2.2, 0.90),
        "unknown_structure": ("mediumpurple", 1.6, 0.70),
        "metal_shield": ("steelblue", 3.2, 0.95),
        "rear_zone_structure": ("slateblue", 2.4, 0.85),
    }

    for obj in scene.get("structural_components", []):
        cls = obj.get("class_id", "unknown_structure")
        center = np.asarray(obj["center_xy_m"], dtype=float)
        major = float(obj.get("extent_major_m", 0.2))
        axes = np.asarray(obj.get("axes_xy", np.eye(2)), dtype=float)
        color, linewidth, alpha = structure_style.get(cls, ("mediumpurple", 1.6, 0.70))

        segments = obj.get("boundary_segments_xy_m") or []
        if segments:
            for segment in segments:
                p0 = segment[0]
                p1 = segment[1]
                ax.plot(
                    [p0[0], p1[0]],
                    [p0[1], p1[1]],
                    linewidth=linewidth,
                    color=color,
                    alpha=alpha,
                    solid_capstyle="round",
                )
        else:
            a, b = _major_segment(center, axes, major)
            ax.plot([a[0], b[0]], [a[1], b[1]], linewidth=linewidth, color=color, alpha=alpha)

        if show_labels and cls == "metal_shield":
            ax.text(center[0], center[1], "SH", fontsize=8, ha="center", va="center", color="steelblue")
        elif show_labels and cls == "rear_zone_structure":
            ax.text(center[0], center[1], "R?", fontsize=8, ha="center", va="center", color="slateblue")

    # Rear bullet trap: draw the detected front face as the structural anchor
    # for the popper/metal zone.
    trap = scene.get("rear_bullet_trap")
    if trap and trap.get("front_segment_xy_m"):
        p0, p1 = trap["front_segment_xy_m"]
        ax.plot(
            [p0[0], p1[0]],
            [p0[1], p1[1]],
            linewidth=6.0,
            color="olive",
            alpha=0.9,
            solid_capstyle="butt",
        )
        if show_labels:
            ctrap = np.asarray(trap["center_xy_m"], dtype=float)
            ax.text(
                ctrap[0],
                ctrap[1],
                "BT",
                fontsize=9,
                ha="center",
                va="bottom",
                color="darkolivegreen",
            )

    # Fault Lines.
    for obj in scene.get("fault_lines", []):
        a, b = _major_segment(obj["center_xy_m"], obj["axes_xy"], obj["extent_major_m"])
        ax.plot([a[0], b[0]], [a[1], b[1]], linewidth=4.0, color="red", alpha=0.95)
        if show_labels:
            c = np.asarray(obj["center_xy_m"])
            ax.text(c[0], c[1], "FL", fontsize=8, ha="center", va="bottom", color="red")

    shooting = np.asarray(scene.get("shooting_direction", {}).get("direction_xy", [0.0, 1.0]), dtype=float)
    shooting /= max(np.linalg.norm(shooting), 1e-9)
    shooter_facing = -shooting
    face_axis = np.array([-shooting[1], shooting[0]])

    # Cardboard targets: face segment + arrow showing front direction.
    for i, obj in enumerate(scene.get("metric_target_proposals", []), start=1):
        center3 = np.asarray(obj["center_m"], dtype=float)
        c = center3[:2]
        width = float(obj.get("width_m", 0.414))
        half = 0.5 * min(max(width, 0.25), 0.65) * face_axis
        ax.plot([c[0] - half[0], c[0] + half[0]], [c[1] - half[1], c[1] + half[1]],
                linewidth=3.0, color="forestgreen", solid_capstyle="round")
        ax.arrow(
            c[0], c[1],
            shooter_facing[0] * 0.35, shooter_facing[1] * 0.35,
            width=0.008,
            head_width=0.12,
            head_length=0.14,
            length_includes_head=True,
            color="forestgreen",
            alpha=0.9,
        )
        if show_labels:
            ax.text(c[0], c[1], f"T{i}", fontsize=8, ha="left", va="bottom", color="darkgreen")

    # Metal targets. Generic proposals use M; future subtype ids get distinct icons.
    for i, obj in enumerate(scene.get("rear_metal_proposals", []), start=1):
        center3 = np.asarray(obj["center_m"], dtype=float)
        c = center3[:2]
        cls = obj.get("class_id", "metal_target")
        half = 0.15 * face_axis
        ax.plot([c[0] - half[0], c[0] + half[0]], [c[1] - half[1], c[1] + half[1]],
                linewidth=3.0, color="royalblue")

        if "plate" in cls:
            marker, label = "o", f"PL{i}"
        elif "popper" in cls:
            marker, label = "^", f"P{i}"
        else:
            marker, label = "D", f"M{i}"

        ax.scatter([c[0]], [c[1]], s=55, marker=marker, color="royalblue", zorder=6)
        if show_labels:
            ax.text(c[0], c[1], label, fontsize=8, ha="left", va="bottom", color="navy")

    # Global shooting direction.
    span = max(extent[1] - extent[0], extent[3] - extent[2])
    anchor = np.array([extent[0] + 0.10 * (extent[1] - extent[0]), extent[2] + 0.10 * (extent[3] - extent[2])])
    ax.arrow(
        anchor[0], anchor[1],
        shooting[0] * span * 0.10, shooting[1] * span * 0.10,
        width=0.015,
        head_width=0.20,
        head_length=0.22,
        length_includes_head=True,
        color="black",
    )
    ax.text(anchor[0], anchor[1], "shooting direction", fontsize=9, ha="left", va="top")

    ax.set_title("Scan2Stage semantic top view")
    ax.set_xlabel("X, m")
    ax.set_ylabel("Y, m")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.35, alpha=0.25)

    # Compact legend built from representative handles.
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], color="dimgray", lw=3, label="Wall / partition"),
        Line2D([0], [0], color="saddlebrown", lw=4, label="Large structure / trap candidate"),
        Line2D([0], [0], color="olive", lw=6, label="Detected rear bullet trap"),
        Line2D([0], [0], color="steelblue", lw=3, label="Metal shield (rear/popper zone)"),
        Line2D([0], [0], color="darkorange", lw=2, label="Decor / compact structure"),
        Line2D([0], [0], color="red", lw=4, label="Fault Line"),
        Line2D([0], [0], color="forestgreen", lw=3, marker=">", label="Metric target + facing"),
        Line2D([0], [0], color="royalblue", lw=3, marker="D", label="Metal target"),
    ]
    ax.legend(handles=handles, loc="best", fontsize=8)

    fig.tight_layout()
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=180, bbox_inches="tight")
    return fig, ax, scene
