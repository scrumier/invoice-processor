from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from processor.extractor import extract_invoice

VALID_RESPONSE = """{
    "is_invoice": true,
    "confidence": 92,
    "numero_facture": "F-2024-001",
    "date_facture": "2024-01-15",
    "fournisseur": "Rocmer",
    "montant_ht": "1000.00",
    "tva": "200.00",
    "montant_ttc": "1200.00",
    "iban": "FR76 1234 5678 9012 3456 7890 123",
    "echeance": "2024-02-15"
}"""


def _make_image() -> Image.Image:
    return Image.new("RGB", (100, 100), color="white")


def _mock_completion(
    content: str,
    *,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
):
    response = MagicMock()
    response.choices[0].message.content = content
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    return response


def _extract(content: str, **usage: int):
    with patch("processor.extractor._get_client") as client:
        client.return_value.chat.completions.create.return_value = _mock_completion(
            content, **usage
        )
        return extract_invoice(_make_image())


def test_extract_returns_validated_invoice():
    invoice, _ = _extract(VALID_RESPONSE)

    assert invoice.is_invoice is True
    assert invoice.fournisseur == "Rocmer"
    assert invoice.confidence == 92


def test_extract_coerces_amount_strings_to_floats():
    invoice, _ = _extract(VALID_RESPONSE)

    assert invoice.montant_ht == 1000.00
    assert invoice.montant_ttc == 1200.00


def test_extract_coerces_french_number_format():
    invoice, _ = _extract('{"is_invoice": true, "montant_ttc": "1 234,50"}')

    assert invoice.montant_ttc == 1234.50


def test_extract_reports_cost_from_usage():
    _, cost = _extract(VALID_RESPONSE, prompt_tokens=1_000_000, completion_tokens=0)

    assert cost == pytest.approx(0.10)


def test_extract_non_invoice_returns_is_invoice_false():
    invoice, _ = _extract('{"is_invoice": false}')

    assert invoice.is_invoice is False


def test_extract_strips_markdown_code_fence():
    invoice, _ = _extract('```json\n{"is_invoice": true, "fournisseur": "Acme"}\n```')

    assert invoice.fournisseur == "Acme"


def test_extract_invalid_json_raises():
    with pytest.raises(ValueError, match="Invalid JSON"):
        _extract("not json")


def test_extract_unexpected_shape_raises():
    # is_invoice is the one field the pipeline cannot proceed without.
    with pytest.raises(ValueError, match="Unexpected invoice shape"):
        _extract('{"fournisseur": "Acme"}')


def test_extract_ignores_unknown_fields():
    invoice, _ = _extract('{"is_invoice": true, "champ_invente": "surprise"}')

    assert invoice.is_invoice is True
