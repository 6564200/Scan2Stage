from pathlib import Path
import zipfile

from scan2stage.scene_io import _safe_extract_zip


def test_ugscan_zip_prefers_single_glb(tmp_path: Path):
    archive = tmp_path / 'scan.zip'
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr('TexturedMeshSimplified.glb', b'glTF')
        zf.writestr('notes.txt', b'x')
    td, mesh = _safe_extract_zip(archive)
    try:
        assert mesh.name == 'TexturedMeshSimplified.glb'
        assert mesh.suffix.lower() == '.glb'
    finally:
        td.cleanup()
