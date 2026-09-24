from pathlib import Path

from scan2stage import web
from scan2stage.storage import Store


def test_rerun_scan_uses_existing_scan_without_reupload(tmp_path: Path, monkeypatch):
    store = Store(tmp_path / "runtime")
    gallery_id = store.create_gallery("Gallery A")
    source = tmp_path / "scan.glb"
    source.write_bytes(b"dummy")
    scan_id = store.add_scan(gallery_id, source)

    captured = {}

    monkeypatch.setattr(web, "store", lambda: store)

    def fake_launch_run(current_store, current_gallery_id, scan_ids):
        captured["store"] = current_store
        captured["gallery_id"] = current_gallery_id
        captured["scan_ids"] = list(scan_ids)
        return "rerun123"

    monkeypatch.setattr(web, "launch_run", fake_launch_run)

    response = web.rerun_scan(gallery_id, scan_id)

    assert response.status_code == 303
    assert response.headers["location"] == "/run/rerun123"
    assert captured["store"] is store
    assert captured["gallery_id"] == gallery_id
    assert captured["scan_ids"] == [scan_id]
