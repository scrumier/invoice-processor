import pytest
from pathlib import Path
from PIL import Image


def test_load_pdf_returns_images(tmp_path):
    from processor.loader import pdf_to_images

    sample = Path("tests/fixtures/sample_invoice.pdf")
    if not sample.exists():
        pytest.skip("No sample PDF fixture")

    images = pdf_to_images(str(sample))
    assert isinstance(images, list)
    assert len(images) >= 1
    assert all(isinstance(img, Image.Image) for img in images)


def test_load_invalid_path_raises():
    from processor.loader import pdf_to_images

    with pytest.raises(Exception):
        pdf_to_images("/nonexistent/file.pdf")
