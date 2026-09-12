from __future__ import annotations

import numpy as np


def canonical_transform(source_up: str) -> np.ndarray:
    source_up = source_up.lower()
    if source_up == "z":
        return np.eye(4, dtype=np.float64)
    if source_up == "y":
        return np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, -1.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ], dtype=np.float64)
    if source_up == "x":
        return np.array([
            [0.0, 0.0, -1.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ], dtype=np.float64)
    raise ValueError("source_up must be x, y or z")


def apply_transform(points: np.ndarray, transform: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    hom = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    return (hom @ transform.T)[:, :3]


def bounds(points: np.ndarray) -> dict[str, list[float]]:
    points = np.asarray(points, dtype=np.float64)
    lo = points.min(axis=0)
    hi = points.max(axis=0)
    return {
        "min": lo.tolist(),
        "max": hi.tolist(),
        "extent": (hi - lo).tolist(),
    }
