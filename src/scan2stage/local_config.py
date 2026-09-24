from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class LocalSettings(BaseModel):
    sample_count: int = Field(default=300_000, ge=50_000, le=2_000_000)
    source_up: Literal["x", "y", "z"] = "y"
    unit_scale: float | None = Field(default=None, gt=0)
    topview_resolution_m: float = Field(default=0.05, ge=0.01, le=0.20)
    blender_executable: str = ""
    max_parallel_runs: int = Field(default=1, ge=1, le=8)


SETTING_DESCRIPTIONS = {
    "sample_count": "Количество точек, семплируемых с mesh. 300 000 — стартовое значение; 500–750 тыс. полезны для финальной проверки.",
    "source_up": "Вертикальная ось исходного скана. Для UGScan/glTF обычно Y.",
    "unit_scale": "Множитель координат в метры. Пусто = определить по формату.",
    "topview_resolution_m": "Размер ячейки structural top-view. 0.05 м быстро; 0.02–0.03 м детальнее.",
    "blender_executable": "Путь к blender.exe. Нужен для финального FBX/GLB экспорта и clean-scene generation.",
    "max_parallel_runs": "Максимальное число одновременно запущенных тяжёлых задач. Для одной рабочей станции обычно 1–2.",
}


def data_root() -> Path:
    value = os.getenv("SCAN2STAGE_HOME")
    if value:
        return Path(value).expanduser().resolve()
    return (Path.home() / "Scan2StageData").resolve()


def settings_path(root: Path | None = None) -> Path:
    root = root or data_root()
    return root / "settings.json"


def load_settings(root: Path | None = None) -> LocalSettings:
    path = settings_path(root)
    if not path.exists():
        return LocalSettings()
    return LocalSettings.model_validate_json(path.read_text(encoding="utf-8"))


def save_settings(settings: LocalSettings, root: Path | None = None) -> None:
    root = root or data_root()
    root.mkdir(parents=True, exist_ok=True)
    settings_path(root).write_text(
        json.dumps(settings.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
