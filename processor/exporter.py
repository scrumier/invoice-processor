import csv
import os

FIELDS = [
    "filename", "processed_at", "numero_facture", "date_facture",
    "fournisseur", "montant_ht", "tva", "montant_ttc", "iban", "echeance",
]


def append_to_csv(row: dict, csv_path: str) -> None:
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)
