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
