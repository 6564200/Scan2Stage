from scan2stage.models import PreprocessConfig, SceneConfig


def test_default_voxel_size():
    cfg = PreprocessConfig()
    assert cfg.voxel_size_m == 0.02


def test_scene_config_collections_are_not_shared():
    a = SceneConfig()
    b = SceneConfig()
    a.objects.append({"id": "x"})
    assert b.objects == []
