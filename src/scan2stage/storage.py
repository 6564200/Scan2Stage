from __future__ import annotations

import re
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .local_config import data_root

ALLOWED_SCAN_EXTENSIONS = {".glb", ".gltf", ".zip", ".fbx", ".obj"}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_name(name: str) -> str:
    base = Path(name).name.strip()
    base = re.sub(r"[^A-Za-z0-9._() -]+", "_", base)
    return base[:180] or "scan.glb"


class Store:
    def __init__(self, root: Path | None = None):
        self.root = (root or data_root()).resolve()
        self.db_path = self.root / "scan2stage.db"
        self.galleries_dir = self.root / "galleries"
        self.runs_dir = self.root / "runs"
        self.logs_dir = self.root / "logs"
        for p in (self.root, self.galleries_dir, self.runs_dir, self.logs_dir):
            p.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def init_db(self):
        with self.connect() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS galleries (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scans (
                id TEXT PRIMARY KEY,
                gallery_id TEXT NOT NULL REFERENCES galleries(id) ON DELETE CASCADE,
                original_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                gallery_id TEXT NOT NULL REFERENCES galleries(id) ON DELETE CASCADE,
                status TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                settings_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT
            );
            CREATE TABLE IF NOT EXISTS run_scans (
                run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
                PRIMARY KEY(run_id, scan_id)
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                scan_id TEXT,
                kind TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)
            columns = {row["name"] for row in con.execute("PRAGMA table_info(scans)")}
            if "deleted_at" not in columns:
                con.execute("ALTER TABLE scans ADD COLUMN deleted_at TEXT")

    def create_gallery(self, name: str, notes: str = "") -> str:
        gid = uuid.uuid4().hex[:12]
        with self.connect() as con:
            con.execute(
                "INSERT INTO galleries(id,name,notes,created_at) VALUES(?,?,?,?)",
                (gid, name.strip() or f"Gallery {gid}", notes.strip(), utcnow()),
            )
        (self.galleries_dir / gid / "scans").mkdir(parents=True, exist_ok=True)
        return gid

    def add_scan(self, gallery_id: str, source: Path, original_name: str | None = None) -> str:
        ext = source.suffix.lower()
        if ext not in ALLOWED_SCAN_EXTENSIONS:
            raise ValueError(f"Unsupported scan format: {ext}")
        sid = uuid.uuid4().hex[:12]
        name = safe_name(original_name or source.name)
        target_dir = self.galleries_dir / gallery_id / "scans" / sid
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / name
        shutil.copy2(source, target)
        with self.connect() as con:
            con.execute(
                """INSERT INTO scans(
                       id,gallery_id,original_name,stored_path,size_bytes,created_at,deleted_at
                   ) VALUES(?,?,?,?,?,?,NULL)""",
                (sid, gallery_id, name, str(target), target.stat().st_size, utcnow()),
            )
        return sid

    def create_run(self, gallery_id: str, scan_ids: list[str], settings_json: str) -> str:
        if not scan_ids:
            raise ValueError("At least one scan is required")
        placeholders = ",".join("?" for _ in scan_ids)
        with self.connect() as con:
            rows = con.execute(
                f"""SELECT id FROM scans
                    WHERE gallery_id=? AND deleted_at IS NULL
                      AND id IN ({placeholders})""",
                [gallery_id, *scan_ids],
            ).fetchall()
            valid = {row["id"] for row in rows}
        missing = [sid for sid in scan_ids if sid not in valid]
        if missing:
            raise ValueError(f"Unavailable scan(s): {', '.join(missing)}")

        rid = uuid.uuid4().hex[:12]
        with self.connect() as con:
            con.execute(
                "INSERT INTO runs(id,gallery_id,status,progress,message,settings_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (rid, gallery_id, "queued", 0, "В очереди", settings_json, utcnow()),
            )
            con.executemany(
                "INSERT INTO run_scans(run_id,scan_id) VALUES(?,?)",
                [(rid, x) for x in scan_ids],
            )
        (self.runs_dir / rid).mkdir(parents=True, exist_ok=True)
        return rid

    def update_run(self, run_id: str, **fields):
        allowed = {"status", "progress", "message", "started_at", "finished_at"}
        items = [(k, v) for k, v in fields.items() if k in allowed]
        if not items:
            return
        sql = "UPDATE runs SET " + ", ".join(f"{k}=?" for k, _ in items) + " WHERE id=?"
        with self.connect() as con:
            con.execute(sql, [v for _, v in items] + [run_id])

    def add_artifact(self, run_id: str, kind: str, path: Path, scan_id: str | None = None):
        aid = uuid.uuid4().hex[:12]
        with self.connect() as con:
            con.execute(
                "INSERT INTO artifacts(id,run_id,scan_id,kind,path,created_at) VALUES(?,?,?,?,?,?)",
                (aid, run_id, scan_id, kind, str(path), utcnow()),
            )
        return aid

    def one(self, sql: str, params=()):
        with self.connect() as con:
            row = con.execute(sql, params).fetchone()
            return dict(row) if row else None

    def all(self, sql: str, params=()):
        with self.connect() as con:
            return [dict(x) for x in con.execute(sql, params).fetchall()]

    def gallery(self, gallery_id: str):
        return self.one("SELECT * FROM galleries WHERE id=?", (gallery_id,))

    def galleries(self):
        return self.all("SELECT * FROM galleries ORDER BY created_at DESC")

    def scan(self, scan_id: str):
        return self.one("SELECT * FROM scans WHERE id=?", (scan_id,))

    def scans(self, gallery_id: str):
        return self.all(
            """SELECT * FROM scans
               WHERE gallery_id=? AND deleted_at IS NULL
               ORDER BY created_at DESC""",
            (gallery_id,),
        )

    def run(self, run_id: str):
        return self.one("SELECT * FROM runs WHERE id=?", (run_id,))

    def runs(self):
        return self.all(
            """SELECT runs.*, galleries.name AS gallery_name
               FROM runs JOIN galleries ON galleries.id=runs.gallery_id
               ORDER BY runs.created_at DESC"""
        )

    def run_scans(self, run_id: str):
        return self.all(
            """SELECT scans.* FROM scans
               JOIN run_scans ON run_scans.scan_id=scans.id
               WHERE run_scans.run_id=? ORDER BY scans.created_at""",
            (run_id,),
        )

    def artifacts(self, run_id: str):
        return self.all("SELECT * FROM artifacts WHERE run_id=? ORDER BY created_at", (run_id,))

    def active_run_count(self) -> int:
        row = self.one("SELECT COUNT(*) AS n FROM runs WHERE status IN ('queued','running')")
        return int(row["n"]) if row else 0

    def scan_active_run_count(self, scan_id: str) -> int:
        row = self.one(
            """SELECT COUNT(*) AS n
               FROM runs
               JOIN run_scans ON run_scans.run_id=runs.id
               WHERE run_scans.scan_id=? AND runs.status IN ('queued','running')""",
            (scan_id,),
        )
        return int(row["n"]) if row else 0

    def delete_scan_upload(self, gallery_id: str, scan_id: str) -> None:
        scan = self.one(
            """SELECT * FROM scans
               WHERE id=? AND gallery_id=? AND deleted_at IS NULL""",
            (scan_id, gallery_id),
        )
        if not scan:
            raise KeyError("Scan not found")
        if self.scan_active_run_count(scan_id):
            raise RuntimeError("Scan is used by an active Run")

        path = Path(scan["stored_path"])
        scan_dir = path.parent
        if scan_dir.exists():
            shutil.rmtree(scan_dir)

        with self.connect() as con:
            con.execute(
                "UPDATE scans SET deleted_at=? WHERE id=? AND gallery_id=?",
                (utcnow(), scan_id, gallery_id),
            )

    def delete_run(self, run_id: str) -> None:
        run = self.run(run_id)
        if not run:
            raise KeyError("Run not found")
        if run["status"] in {"queued", "running"}:
            raise RuntimeError("Active Run cannot be deleted")

        run_dir = self.runs_dir / run_id
        log_path = self.log_path(run_id)

        with self.connect() as con:
            con.execute("DELETE FROM runs WHERE id=?", (run_id,))

        if run_dir.exists():
            shutil.rmtree(run_dir)
        log_path.unlink(missing_ok=True)

    def log_path(self, run_id: str) -> Path:
        return self.logs_dir / f"{run_id}.log"
