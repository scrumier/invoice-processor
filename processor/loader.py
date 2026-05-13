from pdf2image import convert_from_path
from PIL import Image


def pdf_to_images(pdf_path: str, dpi: int = 200) -> list[Image.Image]:
    return convert_from_path(pdf_path, dpi=dpi)
