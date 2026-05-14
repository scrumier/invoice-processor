import os
import time
import logging
from datetime import datetime
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

from processor.loader import pdf_to_images
from processor.extractor import extract_invoice
from processor.exporter import append_to_csv
from processor.validator import validate

load_dotenv()

INVOICES_DIR = os.getenv("INVOICES_DIR", "data/invoices")
PROCESSED_DIR = os.getenv("PROCESSED_DIR", "data/processed")
CSV_PATH = os.getenv("CSV_PATH", "data/output/invoices.csv")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def process_file(pdf_path: str) -> None:
    filename = Path(pdf_path).name
    log.info(f"Processing {filename}")
    try:
        images = pdf_to_images(pdf_path)
    except Exception as e:
        log.error(f"Failed to load {filename}: {e}")
        return

    for i, image in enumerate(images):
        try:
            data, cost = extract_invoice(image)
        except Exception as e:
            log.error(f"Extraction failed on page {i+1} of {filename}: {e}")
            continue

        if not data.get("is_invoice"):
            log.info(f"Skipped {filename} page {i+1}: not an invoice")
            continue

        flags = validate(data)
        row = {
            "filename": filename,
            "processed_at": datetime.now().isoformat(timespec="seconds"),
            "cost_usd": f"{cost:.6f}",
            **{k: data.get(k) for k in [
                "numero_facture", "date_facture", "fournisseur",
                "montant_ht", "tva", "montant_ttc", "iban", "echeance"
            ]},
            **flags,
        }
        row["confidence"] = data.get("confidence")
        n_flags = flags.get("flags_count", 0)
        flag_label = f" [{n_flags} flag(s)]" if n_flags else ""
        append_to_csv(row, CSV_PATH)
        log.info(f"Saved: {data.get('fournisseur')} - {data.get('montant_ttc')} EUR (cost: ${cost:.5f}){flag_label}")
        break  # one row per PDF (first invoice page)

    dest = os.path.join(PROCESSED_DIR, Path(pdf_path).name)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.rename(pdf_path, dest)
    log.info(f"Moved to processed/: {Path(pdf_path).name}")


class InvoiceHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".pdf"):
            time.sleep(0.5)  # wait for file to finish writing
            process_file(event.src_path)


if __name__ == "__main__":
    os.makedirs(INVOICES_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    log.info(f"Watching {INVOICES_DIR}/")
    observer = Observer()
    observer.schedule(InvoiceHandler(), INVOICES_DIR, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
