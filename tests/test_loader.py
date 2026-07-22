from pathlib import Path

import pytest
from pdf2image.exceptions import PDFPageCountError
from PIL import Image

from processor.loader import pdf_to_images

SAMPLE = Path("tests/fixtures/sample_invoice.pdf")


def test_load_pdf_returns_images():
    if not SAMPLE.exists():
        pytest.skip("No sample PDF fixture")

    images = pdf_to_images(str(SAMPLE))

    assert len(images) >= 1
    assert all(isinstance(image, Image.Image) for image in images)


def test_load_invalid_path_raises():
    with pytest.raises(PDFPageCountError):
        pdf_to_images("/nonexistent/file.pdf")
