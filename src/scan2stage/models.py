from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PreprocessConfig(BaseModel):
    voxel_size_m: float = Field(default=0.02, gt=0)
    outlier_nb_neighbors: int = Field(default=24, ge=3)
    outlier_std_ratio: float = Field(default=2.0, gt=0)
    estimate_normals: bool = True
    normal_radius_m: float = Field(default=0.08, gt=0)
    normal_max_nn: int = Field(default=30, ge=3)


class CoordinateSystem(BaseModel):
    units: Literal["meters"] = "meters"
    up: Literal["Z"] = "Z"
    forward: Literal["Y"] = "Y"


class SceneConfig(BaseModel):
    schema_version: str = "1.0"
    coordinate_system: CoordinateSystem = Field(default_factory=CoordinateSystem)
    objects: list[dict] = Field(default_factory=list)
