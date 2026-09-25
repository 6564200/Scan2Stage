from pathlib import Path

from scan2stage.local_config import LocalSettings, load_settings, save_settings
from scan2stage.storage import Store


def test_local_store_gallery_scan_run_roundtrip(tmp_path: Path):
    store = Store(tmp_path / "runtime")
    gid = store.create_gallery("Gallery A", "test")
    source = tmp_path / "scan.glb"
    source.write_bytes(b"dummy")
    sid = store.add_scan(gid, source)

    cfg = LocalSettings(sample_count=100_000)
    rid = store.create_run(gid, [sid], cfg.model_dump_json())

    assert store.gallery(gid)["name"] == "Gallery A"
    assert store.scans(gid)[0]["id"] == sid
    assert store.run(rid)["status"] == "queued"
    assert store.run_scans(rid)[0]["id"] == sid


def test_settings_roundtrip(tmp_path: Path):
    root = tmp_path / "runtime"
    cfg = LocalSettings(sample_count=500_000, topview_resolution_m=0.03)
    save_settings(cfg, root)
    loaded = load_settings(root)
    assert loaded.sample_count == 500_000
    assert loaded.topview_resolution_m == 0.03


def test_delete_run_removes_results_and_log_but_keeps_scan(tmp_path: Path):
    store = Store(tmp_path / "runtime")
    gid = store.create_gallery("Gallery A")
    source = tmp_path / "scan.glb"
    source.write_bytes(b"dummy")
    sid = store.add_scan(gid, source)
    cfg = LocalSettings()
    rid = store.create_run(gid, [sid], cfg.model_dump_json())

    run_dir = store.runs_dir / rid
    result = run_dir / "result.txt"
    result.write_text("x")
    log = store.log_path(rid)
    log.write_text("log")
    store.update_run(rid, status="completed")

    store.delete_run(rid)

    assert store.run(rid) is None
    assert not run_dir.exists()
    assert not log.exists()
    assert store.scan(sid) is not None


def test_delete_scan_upload_hides_scan_but_preserves_history(tmp_path: Path):
    store = Store(tmp_path / "runtime")
    gid = store.create_gallery("Gallery A")
    source = tmp_path / "scan.glb"
    source.write_bytes(b"dummy")
    sid = store.add_scan(gid, source)
    stored_path = Path(store.scan(sid)["stored_path"])
    cfg = LocalSettings()
    rid = store.create_run(gid, [sid], cfg.model_dump_json())
    store.update_run(rid, status="completed")

    store.delete_scan_upload(gid, sid)

    assert not stored_path.exists()
    assert store.scans(gid) == []
    history = store.run_scans(rid)
    assert history[0]["id"] == sid
    assert history[0]["deleted_at"] is not None


def test_delete_scan_upload_rejects_active_run(tmp_path: Path):
    store = Store(tmp_path / "runtime")
    gid = store.create_gallery("Gallery A")
    source = tmp_path / "scan.glb"
    source.write_bytes(b"dummy")
    sid = store.add_scan(gid, source)
    cfg = LocalSettings()
    store.create_run(gid, [sid], cfg.model_dump_json())

    import pytest
    with pytest.raises(RuntimeError):
        store.delete_scan_upload(gid, sid)


def test_mark_run_failed_releases_stuck_run(tmp_path: Path):
    store = Store(tmp_path / "runtime")
    gid = store.create_gallery("Gallery A")
    source = tmp_path / "scan.glb"
    source.write_bytes(b"dummy")
    sid = store.add_scan(gid, source)
    cfg = LocalSettings()
    rid = store.create_run(gid, [sid], cfg.model_dump_json())

    assert store.run(rid)["status"] == "queued"
    store.mark_run_failed(rid, "stale worker")
    run = store.run(rid)
    assert run["status"] == "failed"
    assert run["message"] == "stale worker"
    assert run["finished_at"] is not None
