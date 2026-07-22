"""Business rules that decide whether an extracted invoice looks wrong.

These checks never touch the model. They are plain arithmetic and format rules
run against what was extracted, so every flag on a row can be explained to an
accountant without appealing to what an LLM thought.

Each rule returns a human-readable reason when it fires, or an empty string
when it does not. Empty means "checked, nothing to report", which is why the
keys are always present in the output.
"""

import json
import re
from datetime import datetime

from processor.models import ExtractedInvoice, InvoiceLine

# VAT rates in force in France. A computed rate outside this set means either a
# misread amount or a foreign invoice, both worth a human look.
VALID_TVA_RATES = (0.055, 0.10, 0.20)

# Rounding slack. Invoice totals are rounded to the cent, and a few cents of
# drift across a dozen lines is normal, not an error.
MATH_TOLERANCE = 0.05
LINE_TOLERANCE = 0.02
RATE_TOLERANCE = 0.015

IBAN_FR_PATTERN = re.compile(r"^FR\d{25}$")

FLAG_KEYS = (
    "flag_lines_math",
    "flag_sum_ht",
    "flag_math_ttc",
    "flag_tva_rate",
    "flag_iban_format",
    "flag_date_paradox",
)


def _parse_date(value: str | None) -> datetime | None:
    """Parse an ISO date, tolerating the model returning nothing usable.

    Args:
        value: Date string as extracted, expected as YYYY-MM-DD.

    Returns:
        The parsed date, or None if absent or not in the expected format.
    """
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _check_line_math(lines: list[InvoiceLine]) -> str:
    """Check that quantity times unit price matches each line total.

    Args:
        lines: Line items read off the invoice table.

    Returns:
        Comma-separated 1-based line numbers that do not add up, or "".
    """
    wrong = [
        str(index)
        for index, line in enumerate(lines, start=1)
        if line.qty is not None
        and line.pu_ht is not None
        and line.total_ht is not None
        and abs(round(line.qty * line.pu_ht, 2) - line.total_ht) > LINE_TOLERANCE
    ]
    return ",".join(wrong)


def _check_sum_ht(lines: list[InvoiceLine], montant_ht: float | None) -> str:
    """Check that the line items add up to the stated pre-tax total.

    Args:
        lines: Line items read off the invoice table.
        montant_ht: Pre-tax total as printed on the invoice.

    Returns:
        A "sum vs stated" reason when they disagree, or "".
    """
    if not lines or montant_ht is None:
        return ""
    total = sum(line.total_ht for line in lines if line.total_ht is not None)
    if abs(total - montant_ht) > MATH_TOLERANCE:
        return f"{total:.2f} vs {montant_ht:.2f}"
    return ""


def _check_ttc_math(
    montant_ht: float | None,
    tva: float | None,
    ttc: float | None,
) -> str:
    """Check that pre-tax plus VAT equals the total charged.

    Args:
        montant_ht: Pre-tax total.
        tva: VAT amount.
        ttc: Total including tax.

    Returns:
        An "expected vs shown" reason when they disagree, or "".
    """
    if montant_ht is None or tva is None or ttc is None:
        return ""
    expected = round(montant_ht + tva, 2)
    if abs(expected - ttc) > MATH_TOLERANCE:
        return f"attendu {expected:.2f} affiché {ttc:.2f}"
    return ""


def _check_tva_rate(
    montant_ht: float | None,
    tva: float | None,
    tva_taux: float | None,
) -> str:
    """Check the VAT rate implied by the amounts against the printed one.

    Two different failures share this flag: a rate that matches no legal French
    rate at all, and a rate that is legal but contradicts what the invoice
    claims in writing.

    Args:
        montant_ht: Pre-tax total.
        tva: VAT amount.
        tva_taux: VAT rate as printed, in percent.

    Returns:
        A reason naming the computed rate, or "".
    """
    if not montant_ht or montant_ht <= 0 or tva is None or tva <= 0:
        return ""
    computed = tva / montant_ht
    if not any(abs(computed - rate) < RATE_TOLERANCE for rate in VALID_TVA_RATES):
        return f"taux calculé {computed * 100:.1f}% (non standard)"
    if tva_taux is not None and abs(computed - tva_taux / 100) > RATE_TOLERANCE:
        return f"affiché {tva_taux:.0f}% mais calculé {computed * 100:.1f}%"
    return ""


def _check_iban(iban: str | None) -> str:
    """Check that a French IBAN has the right shape.

    Args:
        iban: IBAN as extracted, spaces allowed.

    Returns:
        A reason quoting the offending value, or "".
    """
    compact = (iban or "").replace(" ", "")
    if compact and not IBAN_FR_PATTERN.match(compact):
        return f"invalide: {compact}"
    return ""


def _check_date_paradox(date_facture: str | None, echeance: str | None) -> str:
    """Check that the due date is not before the invoice date.

    Args:
        date_facture: Invoice date, YYYY-MM-DD.
        echeance: Payment due date, YYYY-MM-DD.

    Returns:
        A reason quoting both dates, or "".
    """
    issued = _parse_date(date_facture)
    due = _parse_date(echeance)
    if issued and due and due < issued:
        return f"echeance {echeance} < facture {date_facture}"
    return ""


def validate(invoice: ExtractedInvoice) -> dict[str, str | int]:
    """Run every rule against an extracted invoice.

    Args:
        invoice: Fields validated out of the model's response.

    Returns:
        A dict of flag columns to merge into the CSV row: one entry per rule
        (empty string when the rule did not fire), the line items serialised
        as JSON, and `flags_count`.
    """
    flags: dict[str, str | int] = {
        "flag_lines_math": _check_line_math(invoice.lignes),
        "flag_sum_ht": _check_sum_ht(invoice.lignes, invoice.montant_ht),
        "flag_math_ttc": _check_ttc_math(
            invoice.montant_ht, invoice.tva, invoice.montant_ttc
        ),
        "flag_tva_rate": _check_tva_rate(
            invoice.montant_ht, invoice.tva, invoice.tva_taux
        ),
        "flag_iban_format": _check_iban(invoice.iban),
        "flag_date_paradox": _check_date_paradox(
            invoice.date_facture, invoice.echeance
        ),
    }

    flags["lignes_json"] = (
        json.dumps(
            [line.model_dump() for line in invoice.lignes],
            ensure_ascii=False,
        )
        if invoice.lignes
        else ""
    )
    flags["flags_count"] = sum(1 for key in FLAG_KEYS if flags[key])
    return flags
