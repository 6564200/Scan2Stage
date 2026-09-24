from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .local_config import LocalSettings, SETTING_DESCRIPTIONS, data_root, load_settings, save_settings
from .storage import Store

PACKAGE_DIR = Path(__file__).resolve().parent
WEB_DIR = PACKAGE_DIR / "webui"

app = FastAPI(title="Scan2Stage")
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
templates = Jinja2Templates(directory=WEB_DIR / "templates")


def store() -> Store:
    return Store()


def render(request: Request, template_name: str, context: dict):
    """Render a template using the current Starlette TemplateResponse signature."""
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=context,
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/")
def home(request: Request):
    s = store()
    return render(request, "home.html", {
        "gallery_count": len(s.galleries()),
        "run_count": len(s.runs()),
        "data_root": str(s.root),
    })


@app.get("/upload")
def upload_page(request: Request):
    return render(request, "upload.html", {
        "galleries": store().galleries(),
    })


@app.post("/upload")
async def upload_files(
    gallery_id: str = Form(default=""),
    gallery_name: str = Form(default=""),
    notes: str = Form(default=""),
    files: list[UploadFile] = File(...),
):
    s = store()
    if not gallery_id:
        gallery_id = s.create_gallery(gallery_name or "Новая галерея", notes)

    gallery = s.gallery(gallery_id)
    if not gallery:
        raise HTTPException(404, "Gallery not found")

    tmp_dir = s.root / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for item in files:
        suffix = Path(item.filename or "").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=tmp_dir) as tmp:
            shutil.copyfileobj(item.file, tmp)
            temp_path = Path(tmp.name)
        try:
            s.add_scan(gallery_id, temp_path, item.filename)
        finally:
            temp_path.unlink(missing_ok=True)

    return RedirectResponse(f"/gallery/{gallery_id}", status_code=303)


@app.get("/gallery/{gallery_id}")
def gallery_page(request: Request, gallery_id: str):
    s = store()
    gallery = s.gallery(gallery_id)
    if not gallery:
        raise HTTPException(404, "Gallery not found")
    return render(request, "gallery.html", {
        "gallery": gallery,
        "scans": s.scans(gallery_id),
        "settings": load_settings(s.root),
    })


@app.post("/gallery/{gallery_id}/run")
async def create_run(request: Request, gallery_id: str):
    s = store()
    form = await request.form()
    scan_ids = form.getlist("scan_id")
    if not scan_ids:
        raise HTTPException(400, "Select at least one scan")

    cfg = load_settings(s.root)
    if s.active_run_count() >= cfg.max_parallel_runs:
        raise HTTPException(
            409,
            f"Достигнут лимит параллельных задач: {cfg.max_parallel_runs}. Дождитесь завершения текущего Run.",
        )

    rid = s.create_run(gallery_id, scan_ids, cfg.model_dump_json())
    log_handle = s.log_path(rid).open("a", encoding="utf-8")
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [sys.executable, "-m", "scan2stage.worker", rid],
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        cwd=str(PACKAGE_DIR.parent.parent),
        creationflags=creationflags,
    )
    log_handle.close()
    return RedirectResponse(f"/run/{rid}", status_code=303)


@app.get("/runs")
def runs_page(request: Request):
    return render(request, "runs.html", {
        "runs": store().runs(),
    })


@app.get("/run/{run_id}")
def run_page(request: Request, run_id: str):
    s = store()
    run = s.run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return render(request, "run.html", {
        "run": run,
        "scans": s.run_scans(run_id),
        "artifacts": s.artifacts(run_id),
    })


@app.get("/results/{run_id}")
def results_page(request: Request, run_id: str):
    s = store()
    run = s.run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")

    artifacts = s.artifacts(run_id)
    scans = {x["id"]: x for x in s.run_scans(run_id)}
    grouped = {}
    for artifact in artifacts:
        grouped.setdefault(artifact["scan_id"] or "run", []).append(artifact)

    return render(request, "results.html", {
        "run": run,
        "scans": scans,
        "grouped": grouped,
    })


@app.get("/logs/{run_id}")
def logs_page(request: Request, run_id: str):
    s = store()
    run = s.run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    path = s.log_path(run_id)
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else "Лог ещё не создан."
    return render(request, "logs.html", {
        "run": run,
        "log_text": text,
    })


@app.get("/artifact/{artifact_id}")
def artifact_file(artifact_id: str, download: bool = False):
    s = store()
    artifact = s.one("SELECT * FROM artifacts WHERE id=?", (artifact_id,))
    if not artifact:
        raise HTTPException(404, "Artifact not found")

    path = Path(artifact["path"])
    if not path.is_file():
        raise HTTPException(404, "Artifact file missing")

    if download:
        return FileResponse(path, filename=path.name)
    return FileResponse(path)


@app.get("/settings")
def settings_page(request: Request):
    s = store()
    return render(request, "settings.html", {
        "settings": load_settings(s.root),
        "descriptions": SETTING_DESCRIPTIONS,
        "data_root": str(s.root),
    })


@app.post("/settings")
def update_settings(
    sample_count: int = Form(...),
    source_up: str = Form(...),
    unit_scale: str = Form(default=""),
    topview_resolution_m: float = Form(...),
    blender_executable: str = Form(default=""),
    max_parallel_runs: int = Form(default=1),
):
    s = store()
    cfg = LocalSettings(
        sample_count=sample_count,
        source_up=source_up,
        unit_scale=float(unit_scale) if unit_scale.strip() else None,
        topview_resolution_m=topview_resolution_m,
        blender_executable=blender_executable.strip(),
        max_parallel_runs=max_parallel_runs,
    )
    save_settings(cfg, s.root)
    return RedirectResponse("/settings", status_code=303)


def main():
    import uvicorn

    root = data_root()
    root.mkdir(parents=True, exist_ok=True)
    print(f"Scan2Stage data: {root}")
    print("Open http://127.0.0.1:8765")
    uvicorn.run("scan2stage.web:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    main()
