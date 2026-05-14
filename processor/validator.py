import json
import re
from datetime import datetime

_VALID_TVA_RATES = [0.055, 0.10, 0.20]
_MATH_TOLERANCE = 0.05
_LINE_TOLERANCE = 0.02


def _to_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(str(val).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        return None


def _parse_date(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d")
    except ValueError:
        return None


def validate(data: dict) -> dict:
    """Compute validation flags from extracted invoice data. Returns dict to merge into CSV row."""
    flags: dict = {}

    lignes = data.get("lignes") or []
    flags["lignes_json"] = json.dumps(lignes, ensure_ascii=False) if lignes else ""

    # Per-line math: qty × pu_ht should equal total_ht
    line_errors = []
    sum_from_lines = 0.0
    for i, ligne in enumerate(lignes):
        qty = _to_float(ligne.get("qty"))
        pu = _to_float(ligne.get("pu_ht"))
        total = _to_float(ligne.get("total_ht"))
        if qty is not None and pu is not None and total is not None:
            expected = round(qty * pu, 2)
            if abs(expected - total) > _LINE_TOLERANCE:
                line_errors.append(i + 1)
            sum_from_lines += total

    flags["flag_lines_math"] = ",".join(str(n) for n in line_errors) if line_errors else ""

    # Sum of lines vs montant_ht
    montant_ht = _to_float(data.get("montant_ht"))
    if lignes and montant_ht is not None and abs(sum_from_lines - montant_ht) > _MATH_TOLERANCE:
        flags["flag_sum_ht"] = f"{sum_from_lines:.2f} vs {montant_ht:.2f}"
    else:
        flags["flag_sum_ht"] = ""

    # HT + TVA should equal TTC
    tva = _to_float(data.get("tva"))
    ttc = _to_float(data.get("montant_ttc"))
    if montant_ht is not None and tva is not None and ttc is not None:
        expected_ttc = round(montant_ht + tva, 2)
        if abs(expected_ttc - ttc) > _MATH_TOLERANCE:
            flags["flag_math_ttc"] = f"attendu {expected_ttc:.2f} affiché {ttc:.2f}"
        else:
            flags["flag_math_ttc"] = ""
    else:
        flags["flag_math_ttc"] = ""

    # TVA rate consistency: computed rate should be a valid rate AND match stated rate
    if montant_ht and montant_ht > 0 and tva is not None and tva > 0:
        computed_rate = tva / montant_ht
        tva_taux_stated = _to_float(data.get("tva_taux"))
        if not any(abs(computed_rate - r) < 0.015 for r in _VALID_TVA_RATES):
            flags["flag_tva_rate"] = f"taux calculé {computed_rate * 100:.1f}% (non standard)"
        elif tva_taux_stated is not None and abs(computed_rate - tva_taux_stated / 100) > 0.015:
            flags["flag_tva_rate"] = f"affiché {tva_taux_stated:.0f}% mais calculé {computed_rate * 100:.1f}%"
        else:
            flags["flag_tva_rate"] = ""
    else:
        flags["flag_tva_rate"] = ""

    # IBAN format: FR + 25 digits exactly (after removing spaces)
    iban_raw = (data.get("iban") or "").replace(" ", "")
    if iban_raw:
        if not re.match(r"^FR\d{25}$", iban_raw):
            flags["flag_iban_format"] = f"invalide: {iban_raw}"
        else:
            flags["flag_iban_format"] = ""
    else:
        flags["flag_iban_format"] = ""

    # Date paradox: echeance must not be before date_facture
    d_fac = _parse_date(data.get("date_facture"))
    d_ech = _parse_date(data.get("echeance"))
    if d_fac and d_ech and d_ech < d_fac:
        flags["flag_date_paradox"] = f"echeance {data['echeance']} < facture {data['date_facture']}"
    else:
        flags["flag_date_paradox"] = ""

    flag_keys = [
        "flag_lines_math", "flag_sum_ht", "flag_math_ttc",
        "flag_tva_rate", "flag_iban_format", "flag_date_paradox",
    ]
    flags["flags_count"] = sum(1 for k in flag_keys if flags.get(k))

    return flags
