import io
import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture
def sample_image_bytes():
    """Generate a simple test image as bytes (PNG)."""
    import cv2
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    # Draw some circles to simulate cellular pattern
    for x, y, r in [(50, 50, 20), (120, 80, 25), (80, 150, 18), (160, 140, 22)]:
        cv2.circle(img, (x, y), r, (255, 255, 255), 2)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


@pytest.fixture
def sample_image_path(tmp_path, sample_image_bytes):
    """Write sample image to a temp file and return path."""
    path = tmp_path / "test_image.png"
    path.write_bytes(sample_image_bytes)
    return str(path)


@pytest.fixture
def branching_image_bytes():
    """Generate a branching-like test image."""
    import cv2
    img = np.zeros((200, 200), dtype=np.uint8)
    # Draw tree-like lines
    cv2.line(img, (100, 180), (100, 100), 255, 2)
    cv2.line(img, (100, 100), (60, 50), 255, 2)
    cv2.line(img, (100, 100), (140, 50), 255, 2)
    cv2.line(img, (60, 50), (40, 20), 255, 1)
    cv2.line(img, (60, 50), (70, 20), 255, 1)
    cv2.line(img, (140, 50), (130, 20), 255, 1)
    cv2.line(img, (140, 50), (160, 20), 255, 1)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


@pytest.fixture
def lattice_image_bytes():
    """Generate a grid/lattice test image."""
    import cv2
    img = np.zeros((200, 200), dtype=np.uint8)
    # Draw grid lines
    for i in range(0, 200, 25):
        cv2.line(img, (i, 0), (i, 199), 255, 1)
        cv2.line(img, (0, i), (199, i), 255, 1)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


@pytest.fixture
def clean_image_path(tmp_path):
    """High-contrast, clean image — should NOT be heavily denoised."""
    import cv2
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    # Sharp geometric shapes with strong contrast
    cv2.rectangle(img, (20, 20), (80, 80), (255, 255, 255), 2)
    cv2.circle(img, (150, 150), 50, (255, 255, 255), 2)
    cv2.line(img, (200, 50), (280, 280), (255, 255, 255), 2)
    cv2.rectangle(img, (100, 200), (180, 280), (200, 200, 200), 2)
    path = tmp_path / "clean.png"
    cv2.imwrite(str(path), img)
    return str(path)


@pytest.fixture
def noisy_image_path(tmp_path):
    """Noisy image — should be denoised more aggressively."""
    import cv2
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (80, 80), (255, 255, 255), 2)
    cv2.circle(img, (150, 150), 50, (255, 255, 255), 2)
    # Add Gaussian noise
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 40, img.shape).astype(np.int16)
    noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    path = tmp_path / "noisy.png"
    cv2.imwrite(str(path), noisy)
    return str(path)


@pytest.fixture
def object_image_path(tmp_path):
    """Image with a clear object (filled circle) on dark background."""
    import cv2
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    # Filled white circle centered — clear foreground object
    cv2.circle(img, (150, 150), 80, (255, 255, 255), -1)
    # Some pattern inside the object
    cv2.circle(img, (130, 130), 15, (100, 100, 100), 2)
    cv2.circle(img, (170, 140), 12, (100, 100, 100), 2)
    cv2.circle(img, (150, 170), 18, (100, 100, 100), 2)
    path = tmp_path / "object.png"
    cv2.imwrite(str(path), img)
    return str(path)


@pytest.fixture
def pattern_image_path(tmp_path):
    """Image where pattern fills the entire frame (no background)."""
    import cv2
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    # Grid pattern covering the whole image
    for i in range(0, 300, 30):
        cv2.line(img, (i, 0), (i, 299), (200, 200, 200), 2)
        cv2.line(img, (0, i), (299, i), (200, 200, 200), 2)
    path = tmp_path / "pattern.png"
    cv2.imwrite(str(path), img)
    return str(path)
