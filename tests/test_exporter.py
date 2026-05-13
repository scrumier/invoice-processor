import csv
import os
import pytest


def test_append_creates_file_with_header(tmp_path):
    from processor.exporter import append_to_csv

    csv_path = str(tmp_path / "invoices.csv")
    row = {
        "filename": "test.pdf",
        "processed_at": "2026-05-13T10:00:00",
        "numero_facture": "F-001",
        "date_facture": "2026-01-15",
        "fournisseur": "Acme",
        "montant_ht": "100.00",
        "tva": "20.00",
        "montant_ttc": "120.00",
        "iban": None,
        "echeance": None,
    }
    append_to_csv(row, csv_path)

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["fournisseur"] == "Acme"


def test_append_adds_row_without_duplicating_header(tmp_path):
    from processor.exporter import append_to_csv

    csv_path = str(tmp_path / "invoices.csv")
    row = {
        "filename": "a.pdf", "processed_at": "2026-05-13T10:00:00",
        "numero_facture": "F-001", "date_facture": "2026-01-15",
        "fournisseur": "A", "montant_ht": "100", "tva": "20",
        "montant_ttc": "120", "iban": None, "echeance": None,
    }
    append_to_csv(row, csv_path)
    row["filename"] = "b.pdf"
    append_to_csv(row, csv_path)

    with open(csv_path) as f:
        content = f.read()

    assert content.count("filename") == 1  # header only once
