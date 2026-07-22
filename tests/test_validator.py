from processor.models import ExtractedInvoice, InvoiceLine
from processor.validator import validate

GOOD_IBAN = "FR76 1234 5678 9012 3456 7890 123"


def _invoice(**fields) -> ExtractedInvoice:
    return ExtractedInvoice(is_invoice=True, **fields)


def test_clean_invoice_raises_no_flag():
    flags = validate(
        _invoice(
            montant_ht=1000.0,
            tva=200.0,
            tva_taux=20,
            montant_ttc=1200.0,
            iban=GOOD_IBAN,
            date_facture="2024-01-15",
            echeance="2024-02-15",
            lignes=[
                InvoiceLine(description="Item", qty=2, pu_ht=500.0, total_ht=1000.0)
            ],
        )
    )

    assert flags["flags_count"] == 0


def test_line_total_that_does_not_multiply_out_is_flagged():
    flags = validate(
        _invoice(
            lignes=[
                InvoiceLine(qty=2, pu_ht=500.0, total_ht=1000.0),
                InvoiceLine(qty=3, pu_ht=100.0, total_ht=250.0),
            ]
        )
    )

    assert flags["flag_lines_math"] == "2"


def test_lines_not_adding_up_to_stated_total_is_flagged():
    flags = validate(
        _invoice(
            montant_ht=1500.0,
            lignes=[InvoiceLine(qty=1, pu_ht=1000.0, total_ht=1000.0)],
        )
    )

    assert "1000.00 vs 1500.00" in flags["flag_sum_ht"]


def test_ht_plus_tva_not_matching_ttc_is_flagged():
    flags = validate(_invoice(montant_ht=1000.0, tva=200.0, montant_ttc=1500.0))

    assert flags["flag_math_ttc"]


def test_rounding_to_the_cent_is_not_flagged():
    flags = validate(_invoice(montant_ht=1000.01, tva=200.0, montant_ttc=1200.02))

    assert flags["flag_math_ttc"] == ""


def test_non_standard_tva_rate_is_flagged():
    flags = validate(_invoice(montant_ht=1000.0, tva=170.0))

    assert "non standard" in flags["flag_tva_rate"]


def test_printed_tva_rate_contradicting_the_amounts_is_flagged():
    # Amounts imply 20%, the invoice claims 5.5%.
    flags = validate(_invoice(montant_ht=1000.0, tva=200.0, tva_taux=5.5))

    assert "affiché 6%" in flags["flag_tva_rate"]


def test_malformed_iban_is_flagged():
    flags = validate(_invoice(iban="FR76 1234"))

    assert flags["flag_iban_format"].startswith("invalide")


def test_missing_iban_is_not_flagged():
    flags = validate(_invoice(iban=None))

    assert flags["flag_iban_format"] == ""


def test_due_date_before_invoice_date_is_flagged():
    flags = validate(_invoice(date_facture="2024-02-15", echeance="2024-01-15"))

    assert flags["flag_date_paradox"]


def test_flags_count_matches_the_number_of_rules_fired():
    flags = validate(
        _invoice(
            montant_ht=1000.0,
            tva=200.0,
            montant_ttc=1500.0,
            iban="NOPE",
            date_facture="2024-02-15",
            echeance="2024-01-15",
        )
    )

    assert flags["flags_count"] == 3


def test_lines_are_serialised_for_the_csv():
    flags = validate(_invoice(lignes=[InvoiceLine(description="Câble", qty=1)]))

    assert "Câble" in flags["lignes_json"]


def test_no_lines_serialises_to_empty_string():
    flags = validate(_invoice())

    assert flags["lignes_json"] == ""
