from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from .fbx_pipeline import process_mesh
from .local_config import LocalSettings
from .storage import Store, utcnow
from .visualize import render_semantic_topview


def _log(handle, message: str):
    print(message, file=handle, flush=True)


def run_job(run_id: str) -> int:
    store = Store()
    run = store.run(run_id)
    if not run:
        raise SystemExit(f"Unknown run: {run_id}")

    scans = store.run_scans(run_id)
    settings = LocalSettings.model_validate_json(run["settings_json"])
    log_path = store.log_path(run_id)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with log_path.open("a", encoding="utf-8") as log:
            store.update_run(run_id, status="running", progress=2, message="Подготовка", started_at=utcnow())
            _log(log, f"Run {run_id}: {len(scans)} scan(s)")
            _log(log, f"Settings: {settings.model_dump_json()}")

            total = max(1, len(scans))
            for index, scan in enumerate(scans):
                base = int(5 + (index / total) * 88)
                store.update_run(run_id, progress=base, message=f"Обработка {scan['original_name']}")
                _log(log, f"[{index+1}/{total}] Processing {scan['stored_path']}")

                out = store.runs_dir / run_id / "scans" / scan["id"]
                out.mkdir(parents=True, exist_ok=True)
                source = Path(scan["stored_path"])
                default_scale = 0.01 if source.suffix.lower() == ".fbx" else 1.0
                unit_scale = settings.unit_scale if settings.unit_scale is not None else default_scale

                report = process_mesh(
                    source,
                    out,
                    sample_count=settings.sample_count,
                    source_up=settings.source_up,
                    unit_scale=unit_scale,
                    room_normalize=True,
                    topview_resolution_m=settings.topview_resolution_m,
                )
                _log(log, f"[{index+1}/{total}] Pipeline complete")

                scene = out / "structural_scene.json"
                layers = out / "topview_layers.npz"
                if scene.exists() and layers.exists():
                    png = out / "semantic_topview.png"
                    fig, _, _ = render_semantic_topview(scene, layers, output_path=png)
                    try:
                        import matplotlib.pyplot as plt
                        plt.close(fig)
                    except Exception:
                        pass
                    store.add_artifact(run_id, "map_png", png, scan["id"])

                for kind, filename in [
                    ("report_json", "report.json"),
                    ("scene_json", "structural_scene.json"),
                    ("room_json", "room_geometry.json"),
                    ("candidates_json", "object_candidates.json"),
                    ("topview_npz", "topview_layers.npz"),
                    ("sampled_ply", "sampled_colored.ply"),
                    ("room_ply", "room_normalized.ply"),
                    ("result_glb", "result.glb"),
                    ("result_fbx", "result.fbx"),
                ]:
                    path = out / filename
                    if path.exists():
                        store.add_artifact(run_id, kind, path, scan["id"])

                manifest = out / "run_manifest.json"
                manifest.write_text(
                    json.dumps({
                        "run_id": run_id,
                        "scan_id": scan["id"],
                        "source": scan["original_name"],
                        "settings": settings.model_dump(),
                        "report": report,
                    }, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                store.add_artifact(run_id, "manifest_json", manifest, scan["id"])
                progress = int(5 + ((index + 1) / total) * 88)
                store.update_run(run_id, progress=progress, message=f"Готов скан {index+1}/{total}")

            store.update_run(
                run_id,
                status="completed",
                progress=100,
                message="Готово",
                finished_at=utcnow(),
            )
            _log(log, "Run completed")
        return 0
    except Exception:
        with log_path.open("a", encoding="utf-8") as log:
            traceback.print_exc(file=log)
        store.update_run(
            run_id,
            status="failed",
            message="Ошибка обработки — см. логи",
            finished_at=utcnow(),
        )
        return 1


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scan2stage.worker RUN_ID")
    raise SystemExit(run_job(sys.argv[1]))


if __name__ == "__main__":
    main()
