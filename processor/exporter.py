"""Append processed invoices to the output CSV."""

import csv
import os
from typing import Any

FIELDS = [
    "filename",
    "processed_at",
    "confidence",
    "completeness",
    "cost_usd",
    "flags_count",
    "flag_lines_math",
    "flag_sum_ht",
    "flag_math_ttc",
    "flag_tva_rate",
    "flag_iban_format",
    "flag_date_paradox",
    "numero_facture",
    "date_facture",
    "fournisseur",
    "montant_ht",
    "tva",
    "montant_ttc",
    "iban",
    "echeance",
    "lignes_json",
]

# Fields the model is expected to find on any invoice. Completeness is scored
# against these only: the flag columns are computed, not extracted.
EXTRACTABLE_FIELDS = [
    "numero_facture",
    "date_facture",
    "fournisseur",
    "montant_ht",
    "tva",
    "montant_ttc",
    "iban",
    "echeance",
]

_EMPTY_VALUES = (None, "", "null")


def compute_completeness(row: dict[str, Any]) -> int:
    """Score how much of the invoice was actually read.

    Args:
        row: The CSV row being built.

    Returns:
        Percentage of extractable fields that came back with a value.
    """
    filled = sum(
        1 for field in EXTRACTABLE_FIELDS if row.get(field) not in _EMPTY_VALUES
    )
    return round(filled / len(EXTRACTABLE_FIELDS) * 100)


def append_to_csv(row: dict[str, Any], csv_path: str) -> None:
    """Write one invoice as a row, creating the file and header if needed.

    Args:
        row: Extracted fields, flags and run metadata for a single invoice.
        csv_path: Destination CSV. Its parent directory is created if missing.
    """
    row["completeness"] = compute_completeness(row)
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)
