import csv
import os

FIELDS = [
    "filename", "processed_at", "confidence", "completeness", "cost_usd",
    "flags_count", "flag_lines_math", "flag_sum_ht", "flag_math_ttc",
    "flag_tva_rate", "flag_iban_format", "flag_date_paradox",
    "numero_facture", "date_facture", "fournisseur",
    "montant_ht", "tva", "montant_ttc", "iban", "echeance",
    "lignes_json",
]

_EXTRACTABLE_FIELDS = [
    "numero_facture", "date_facture", "fournisseur",
    "montant_ht", "tva", "montant_ttc", "iban", "echeance",
]


def compute_completeness(row: dict) -> int:
    filled = sum(1 for f in _EXTRACTABLE_FIELDS if row.get(f) not in (None, "", "null"))
    return round(filled / len(_EXTRACTABLE_FIELDS) * 100)


def append_to_csv(row: dict, csv_path: str) -> None:
    row["completeness"] = compute_completeness(row)
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)
