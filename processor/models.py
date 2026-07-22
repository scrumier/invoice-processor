"""Validated shapes for what the vision model returns.

Everything the LLM produces crosses this boundary before the rest of the
pipeline touches it. A malformed response fails here, loudly, rather than
three functions later as an obscure KeyError on a half-filled CSV row.
"""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _coerce_amount(value: object) -> float | None:
    """Turn whatever the model wrote for a monetary field into a float.

    Vision models are inconsistent here: the same field comes back as 1234.5,
    as "1234.50", or as "1 234,50" copied straight off a French invoice. All
    three mean the same amount, so they are normalised rather than rejected.

    Args:
        value: Raw value for an amount field, as parsed from the JSON response.

    Returns:
        The amount as a float, or None if the field was absent or unreadable.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        # French invoices separate thousands with a plain space or, out of
        # a word processor, a narrow no-break space. Both have to go.
        cleaned = value.replace("\u202f", "").replace(" ", "").replace(",", ".")
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


Amount = Annotated[float | None, BeforeValidator(_coerce_amount)]


class InvoiceLine(BaseModel):
    """One row of the invoice's line-item table."""

    model_config = ConfigDict(extra="ignore")

    description: str | None = None
    qty: Amount = None
    pu_ht: Amount = None
    total_ht: Amount = None


class ExtractedInvoice(BaseModel):
    """Everything the vision model read off a single invoice page.

    Only `is_invoice` is required: the model is asked to return every other
    field as null when it cannot read it, and a null field is a legitimate
    outcome that the validation rules are built to report on.
    """

    model_config = ConfigDict(extra="ignore")

    is_invoice: bool
    confidence: int | None = Field(default=None, ge=0, le=100)

    numero_facture: str | None = None
    date_facture: str | None = None
    fournisseur: str | None = None
    iban: str | None = None
    echeance: str | None = None

    montant_ht: Amount = None
    tva: Amount = None
    tva_taux: Amount = None
    montant_ttc: Amount = None

    lignes: list[InvoiceLine] = Field(default_factory=list)
