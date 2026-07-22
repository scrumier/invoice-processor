"""Watch a folder and process every invoice PDF dropped into it.

This is the entry point you leave running. Drop a PDF in the watched folder,
a row appears in the CSV, and the PDF moves to the processed folder so it is
never read twice.
"""

import logging
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from processor.exporter import append_to_csv
from processor.extractor import extract_invoice
from processor.loader import pdf_to_images
from processor.validator import validate

load_dotenv()

INVOICES_DIR = os.getenv("INVOICES_DIR", "data/invoices")
PROCESSED_DIR = os.getenv("PROCESSED_DIR", "data/processed")
CSV_PATH = os.getenv("CSV_PATH", "data/output/invoices.csv")

# A file event fires when the write starts, not when it finishes. Give the
# writer a moment before opening the PDF, otherwise it is read half-written.
WRITE_SETTLE_SECONDS = 0.5

EXTRACTED_FIELDS = (
    "numero_facture",
    "date_facture",
    "fournisseur",
    "montant_ht",
    "tva",
    "montant_ttc",
    "iban",
    "echeance",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def process_file(pdf_path: str) -> None:
    """Extract one PDF, append it to the CSV, and file it away.

    Only the first page is recorded: a supplier invoice is one document, and
    later pages are continuation tables rather than separate invoices.

    Args:
        pdf_path: Path to the PDF that was just dropped in.
    """
    filename = Path(pdf_path).name
    log.info("Processing %s", filename)

    try:
        images = pdf_to_images(pdf_path)
    except Exception:
        log.exception("Failed to load %s", filename)
        return

    for page_number, image in enumerate(images, start=1):
        try:
            invoice, cost = extract_invoice(image)
        except ValueError:
            log.exception("Extraction failed on page %d of %s", page_number, filename)
            continue

        flags = validate(invoice)
        row = {
            "filename": filename,
            "processed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "cost_usd": f"{cost:.6f}",
            "confidence": invoice.confidence,
            **{field: getattr(invoice, field) for field in EXTRACTED_FIELDS},
            **flags,
        }
        append_to_csv(row, CSV_PATH)

        flag_count = flags["flags_count"]
        log.info(
            "Saved: %s %s EUR (cost $%.5f)%s",
            invoice.fournisseur,
            invoice.montant_ttc,
            cost,
            f" [{flag_count} flag(s)]" if flag_count else "",
        )
        break

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.rename(pdf_path, os.path.join(PROCESSED_DIR, filename))
    log.info("Moved to processed: %s", filename)


class InvoiceHandler(FileSystemEventHandler):
    """Route newly created PDFs to the processing pipeline."""

    def on_created(self, event: FileSystemEvent) -> None:
        """Process a PDF as soon as it lands in the watched folder.

        Args:
            event: Filesystem event reported by watchdog.
        """
        if event.is_directory:
            return
        path = str(event.src_path)
        if not path.lower().endswith(".pdf"):
            return
        time.sleep(WRITE_SETTLE_SECONDS)
        process_file(path)


def main() -> None:
    """Create the working folders and watch for invoices until interrupted."""
    for directory in (INVOICES_DIR, PROCESSED_DIR, os.path.dirname(CSV_PATH)):
        os.makedirs(directory, exist_ok=True)

    log.info("Watching %s/", INVOICES_DIR)
    observer = Observer()
    observer.schedule(InvoiceHandler(), INVOICES_DIR, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
