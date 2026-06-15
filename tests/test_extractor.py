import pytest
from unittest.mock import patch, MagicMock
from PIL import Image


def _make_image():
    return Image.new("RGB", (100, 100), color="white")


def test_extract_returns_dict():
    from processor.extractor import extract_invoice

    mock_response = MagicMock()
    mock_response.choices[0].message.content = """{
        "is_invoice": true,
        "numero_facture": "F-2024-001",
        "date_facture": "2024-01-15",
        "fournisseur": "Rocmer",
        "montant_ht": "1000.00",
        "tva": "200.00",
        "montant_ttc": "1200.00",
        "iban": "FR76 1234 5678 9012 3456 7890 123",
        "echeance": "2024-02-15"
    }"""

    with patch("processor.extractor._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_response
        result = extract_invoice(_make_image())

    assert result["is_invoice"] is True
    assert result["fournisseur"] == "Rocmer"
    assert result["montant_ttc"] == "1200.00"


def test_extract_non_invoice_returns_is_invoice_false():
    from processor.extractor import extract_invoice

    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"is_invoice": false}'

    with patch("processor.extractor._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_response
        result = extract_invoice(_make_image())

    assert result["is_invoice"] is False


def test_extract_invalid_json_raises():
    from processor.extractor import extract_invoice

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "not json"

    with patch("processor.extractor._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_response
        with pytest.raises(ValueError, match="Invalid JSON"):
            extract_invoice(_make_image())
