"""Turn a PDF into images the vision model can read."""

from pdf2image import convert_from_path
from PIL import Image

# 200 dpi is the point where small print on a scanned invoice stays legible
# without making the base64 payload large enough to slow the request down.
DEFAULT_DPI = 200


def pdf_to_images(pdf_path: str, dpi: int = DEFAULT_DPI) -> list[Image.Image]:
    """Rasterise every page of a PDF.

    Args:
        pdf_path: Path to the PDF file.
        dpi: Rendering resolution.

    Returns:
        One image per page, in page order.

    Raises:
        PDFPageCountError: If the file is missing or is not a readable PDF.
    """
    return convert_from_path(pdf_path, dpi=dpi)
