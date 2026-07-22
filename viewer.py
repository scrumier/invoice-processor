"""Web view of the processed-invoice CSV.

Reads the CSV the watcher appends to and renders it as a table that refreshes
on its own, so you can drop a PDF in the folder and watch the row appear.
"""

import csv
import os

from flask import Flask, Response, jsonify, redirect, render_template
from markupsafe import Markup, escape

app = Flask(__name__)

CSV_PATH = os.getenv("CSV_PATH", "data/output/invoices.csv")

# Columns the table does not show: the raw line-item JSON is unreadable at this
# width, and each flag reason is already surfaced in the flags badge tooltip.
HIDDEN_FIELDS = frozenset(
    {
        "lignes_json",
        "flag_lines_math",
        "flag_sum_ht",
        "flag_math_ttc",
        "flag_tva_rate",
        "flag_iban_format",
        "flag_date_paradox",
    }
)

FLAG_LABELS = (
    ("flag_lines_math", "ligne math"),
    ("flag_sum_ht", "somme HT"),
    ("flag_math_ttc", "TTC"),
    ("flag_tva_rate", "TVA taux"),
    ("flag_iban_format", "IBAN"),
    ("flag_date_paradox", "date"),
)

SCORE_FIELDS = ("confidence", "completeness")
SCORE_GOOD = 80
SCORE_FAIR = 50

COLOR_GOOD = "#16a34a"
COLOR_WARN = "#d97706"
COLOR_BAD = "#dc2626"

ROW_BG_WARN = "#fffbeb"
ROW_BG_BAD = "#fff1f2"
FLAGS_MANY = 2

COST_SAMPLE_SIZE = 10


def _read_csv() -> tuple[list[str], list[dict[str, str]]]:
    """Load the CSV the watcher writes to.

    Returns:
        The column names and every row, both empty if no invoice has been
        processed yet.
    """
    if not os.path.exists(CSV_PATH):
        return [], []
    with open(CSV_PATH, encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def _score_color(score: int) -> str:
    """Pick the colour for a 0-100 confidence or completeness score.

    Args:
        score: The score to colour.

    Returns:
        A CSS colour.
    """
    if score >= SCORE_GOOD:
        return COLOR_GOOD
    if score >= SCORE_FAIR:
        return COLOR_WARN
    return COLOR_BAD


def _flags_badge(row: dict[str, str]) -> Markup:
    """Render the flags cell, with every triggered rule in its tooltip.

    Args:
        row: One CSV row.

    Returns:
        The badge markup.
    """
    count = int(row.get("flags_count") or 0)
    tooltip = " | ".join(
        f"{label}: {row[key]}" for key, label in FLAG_LABELS if row.get(key)
    )
    if count == 0:
        return Markup(f"<span style='color:{COLOR_GOOD};font-weight:600'>clean</span>")
    color = COLOR_WARN if count == 1 else COLOR_BAD
    plural = "flag" if count == 1 else "flags"
    return Markup(
        f"<span style='color:{color};font-weight:600' title='{escape(tooltip)}'>"
        f"{count} {plural}</span>"
    )


def _render_cell(field: str, value: str, row: dict[str, str]) -> Markup:
    """Render one table cell.

    Values come from a PDF read by a model, so they are escaped: nothing in a
    supplier name reaches the page as markup.

    Args:
        field: Column name.
        value: Cell value.
        row: The row the cell belongs to, needed to build the flags tooltip.

    Returns:
        The `<td>` markup.
    """
    if field in SCORE_FIELDS:
        try:
            score = int(value)
        except (ValueError, TypeError):
            return Markup(f"<td>{escape(value)}</td>")
        return Markup(
            f"<td style='color:{_score_color(score)};font-weight:600'>{score}%</td>"
        )
    if field == "flags_count":
        return Markup(f"<td>{_flags_badge(row)}</td>")
    return Markup(f"<td>{escape(value)}</td>")


def _render_rows(
    fields: list[str],
    rows: list[dict[str, str]],
) -> tuple[Markup, Markup]:
    """Render the table header and body, newest invoice first.

    Args:
        fields: Every column present in the CSV.
        rows: Every processed invoice.

    Returns:
        The header cells and the table body.
    """
    visible = [field for field in fields if field not in HIDDEN_FIELDS]

    body_parts = []
    for row in reversed(rows):
        count = int(row.get("flags_count") or 0)
        if count >= FLAGS_MANY:
            style = f" style='background:{ROW_BG_BAD}'"
        elif count == 1:
            style = f" style='background:{ROW_BG_WARN}'"
        else:
            style = ""
        cells = "".join(_render_cell(f, row.get(f, ""), row) for f in visible)
        body_parts.append(f"<tr{style}>{cells}</tr>")

    headers = "".join(f"<th>{escape(field)}</th>" for field in visible)
    return Markup(headers), Markup("\n".join(body_parts))


def _summary(rows: list[dict[str, str]]) -> dict[str, str | int]:
    """Total what the run has cost so far.

    Args:
        rows: Every processed invoice.

    Returns:
        Invoice count, total spend, and spend per ten invoices.
    """
    total = sum(float(row.get("cost_usd") or 0) for row in rows)
    per_sample = total / len(rows) * COST_SAMPLE_SIZE if rows else 0.0
    return {
        "count": len(rows),
        "total_cost": f"{total:.4f}",
        "cost_per_10": f"{per_sample:.4f}",
    }


@app.route("/api/rows")
def api_rows() -> Response:
    """Serve the current table state for the page's poller.

    Returns:
        JSON with the counters and the rendered table fragments.
    """
    fields, rows = _read_csv()
    headers, tbody = _render_rows(fields, rows) if rows else (Markup(), Markup())
    return jsonify({**_summary(rows), "headers": headers, "tbody": tbody})


@app.route("/")
def index() -> str:
    """Render the invoice table.

    Returns:
        The full page.
    """
    fields, rows = _read_csv()
    headers, tbody = _render_rows(fields, rows) if rows else (Markup(), Markup())
    return render_template(
        "index.html",
        headers=headers,
        tbody=tbody,
        **_summary(rows),
    )


@app.route("/reset")
def reset() -> Response:
    """Delete the CSV so a demo can start from an empty table.

    Returns:
        A redirect back to the table.
    """
    if os.path.exists(CSV_PATH):
        os.remove(CSV_PATH)
    return redirect("/")


def main() -> None:
    """Serve the viewer on the configured host and port."""
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT") or 5052),
        debug=False,
    )


if __name__ == "__main__":
    main()
