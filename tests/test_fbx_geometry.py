import numpy as np

from scan2stage.geometry import apply_transform, canonical_transform
from scan2stage.sampling import sample_mesh_surface


def test_y_up_becomes_z_up():
    point = np.array([[1.0, 2.0, 3.0]])
    out = apply_transform(point, canonical_transform("y"))
    np.testing.assert_allclose(out, [[1.0, -3.0, 2.0]])


def test_surface_sampling_stays_inside_triangle():
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    triangles = np.array([[0, 1, 2]])
    points, normals, colors = sample_mesh_surface(vertices, triangles, 1000, np.random.default_rng(42))
    assert colors is None
    assert np.all(points[:, 0] >= 0)
    assert np.all(points[:, 1] >= 0)
    assert np.all(points[:, 0] + points[:, 1] <= 1.0 + 1e-12)
    np.testing.assert_allclose(normals, np.tile([0.0, 0.0, 1.0], (1000, 1)))


def test_texture_sampling_returns_rgb():
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    triangles = np.array([[0, 1, 2]])
    triangle_uvs = np.array([[[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]])
    texture = np.zeros((4, 4, 3), dtype=np.uint8)
    texture[:, :, 0] = 200
    _, _, colors = sample_mesh_surface(vertices, triangles, 20, np.random.default_rng(1), triangle_uvs, texture)
    assert colors.shape == (20, 3)
    assert np.all(colors[:, 0] == 200)
