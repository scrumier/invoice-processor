import csv
import json
import os
from flask import Flask, redirect, jsonify

app = Flask(__name__)
CSV_PATH = os.getenv("CSV_PATH", "data/output/invoices.csv")

_HIDDEN = {
    "lignes_json", "flag_lines_math", "flag_sum_ht", "flag_math_ttc",
    "flag_tva_rate", "flag_iban_format", "flag_date_paradox",
}

FLAG_LABELS = [
    ("flag_lines_math", "ligne math"),
    ("flag_sum_ht", "somme HT"),
    ("flag_math_ttc", "TTC"),
    ("flag_tva_rate", "TVA taux"),
    ("flag_iban_format", "IBAN"),
    ("flag_date_paradox", "date"),
]


def _read_csv():
    if not os.path.exists(CSV_PATH):
        return [], []
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def _render_cell(f, val, row):
    if f in ("confidence", "completeness"):
        try:
            score = int(val)
            color = "#16a34a" if score >= 80 else ("#d97706" if score >= 50 else "#dc2626")
            return f"<td style='color:{color};font-weight:600'>{val}%</td>"
        except (ValueError, TypeError):
            return f"<td>{val}</td>"
    if f == "flags_count":
        n = int(val) if val else 0
        details = [f"{label}: {row[fk]}" for fk, label in FLAG_LABELS if row.get(fk)]
        tooltip = " | ".join(details)
        if n == 0:
            badge = "<span style='color:#16a34a;font-weight:600'>✓ clean</span>"
        elif n == 1:
            badge = f"<span style='color:#d97706;font-weight:600' title='{tooltip}'>⚠ 1 flag</span>"
        else:
            badge = f"<span style='color:#dc2626;font-weight:600' title='{tooltip}'>✗ {n} flags</span>"
        return f"<td>{badge}</td>"
    return f"<td>{val}</td>"


def _render_rows(fields, rows):
    visible = [f for f in fields if f not in _HIDDEN]
    trs = []
    for r in reversed(rows):
        n = int(r.get("flags_count") or 0)
        bg = " style='background:#fff1f2'" if n >= 2 else (" style='background:#fffbeb'" if n == 1 else "")
        cells = "".join(_render_cell(f, r.get(f, ""), r) for f in visible)
        trs.append(f"<tr{bg}>{cells}</tr>")
    headers = "".join(f"<th>{f}</th>" for f in visible)
    return headers, "\n".join(trs), visible


@app.route("/api/rows")
def api_rows():
    fields, rows = _read_csv()
    total_cost = sum(float(r.get("cost_usd", 0) or 0) for r in rows)
    cost_per_10 = total_cost / len(rows) * 10 if rows else 0
    headers, tbody, visible = _render_rows(fields, rows) if rows else ("", "", [])
    return jsonify({
        "count": len(rows),
        "total_cost": f"{total_cost:.4f}",
        "cost_per_10": f"{cost_per_10:.4f}",
        "headers": headers,
        "tbody": tbody,
    })


@app.route("/")
def index():
    fields, rows = _read_csv()
    total_cost = sum(float(r.get("cost_usd", 0) or 0) for r in rows)
    cost_per_10 = total_cost / len(rows) * 10 if rows else 0

    if rows:
        headers, tbody, _ = _render_rows(fields, rows)
        body = f"""
        <table id="inv-table">
          <thead><tr>{headers}</tr></thead>
          <tbody id="inv-tbody">{tbody}</tbody>
        </table>
        <p style='margin-top:12px;font-size:11px;color:#9ca3af'>
          Survoler le badge flags pour le détail. Mise à jour automatique toutes les 2s.
        </p>"""
    else:
        body = "<p id='empty-msg' style='color:#6b7280'>No invoices processed yet.</p>"

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Invoice Processor</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; background: #f9fafb; color: #1f2937; padding: 32px; }}
  .header {{ display: flex; align-items: center; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }}
  h1 {{ font-size: 20px; font-weight: 700; }}
  .cost-badge {{ font-size: 12px; padding: 6px 14px; background: #f0fdf4; color: #16a34a;
                border: 1px solid #bbf7d0; border-radius: 6px; font-weight: 600; }}
  .live-dot {{ width: 8px; height: 8px; background: #16a34a; border-radius: 50%;
               animation: pulse 1.5s infinite; display: inline-block; }}
  @keyframes pulse {{ 0%,100% {{ opacity:1 }} 50% {{ opacity:.3 }} }}
  .reset-btn {{ font-size: 12px; padding: 6px 14px; background: #fee2e2; color: #dc2626;
               border: 1px solid #fca5a5; border-radius: 6px; cursor: pointer;
               text-decoration: none; font-weight: 600; }}
  .reset-btn:hover {{ background: #fca5a5; }}
  table {{ width: 100%; border-collapse: collapse; background: white;
           border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; font-size: 13px; }}
  th {{ background: #f3f4f6; padding: 10px 12px; text-align: left;
        border-bottom: 1px solid #e5e7eb; font-size: 11px; text-transform: uppercase;
        letter-spacing: .5px; color: #6b7280; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f3f4f6; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f9fafb; }}
  .new-row {{ animation: highlight 2s ease-out; }}
  @keyframes highlight {{ from {{ background: #fef9c3 }} to {{ background: transparent }} }}
</style>
</head>
<body>
<div class="header">
  <h1 id="title">Invoices — {len(rows)} processed</h1>
  <span class="live-dot"></span>
  <span class="cost-badge" id="cost-badge">Total : ${total_cost:.4f} — ~${cost_per_10:.4f} / 10 factures</span>
  <a href="/reset" class="reset-btn" onclick="return confirm('Reset CSV ?')">Reset CSV</a>
</div>
<div id="content">{body}</div>
<script>
let _lastCount = {len(rows)};

async function poll() {{
  try {{
    const r = await fetch('/api/rows');
    const d = await r.json();
    document.getElementById('title').textContent = 'Invoices — ' + d.count + ' processed';
    document.getElementById('cost-badge').textContent =
      'Total : $' + d.total_cost + ' — ~$' + d.cost_per_10 + ' / 10 factures';

    if (d.count !== _lastCount) {{
      const content = document.getElementById('content');
      if (d.count === 0) {{
        content.innerHTML = "<p style='color:#6b7280'>No invoices processed yet.</p>";
      }} else {{
        const tbody = document.getElementById('inv-tbody');
        if (!tbody) {{
          content.innerHTML = '<table id="inv-table"><thead><tr>' + d.headers +
            '</tr></thead><tbody id="inv-tbody">' + d.tbody + '</tbody></table>' +
            "<p style='margin-top:12px;font-size:11px;color:#9ca3af'>Survoler le badge flags pour le détail. Mise à jour automatique toutes les 2s.</p>";
        }} else {{
          const added = d.count > _lastCount;
          tbody.innerHTML = d.tbody;
          if (added) {{
            const first = tbody.querySelector('tr');
            if (first) first.classList.add('new-row');
          }}
        }}
      }}
      _lastCount = d.count;
    }}
  }} catch(e) {{ /* serveur indisponible, on réessaie */ }}
}}

setInterval(poll, 2000);
</script>
</body>
</html>"""


@app.route("/reset")
def reset():
    if os.path.exists(CSV_PATH):
        os.remove(CSV_PATH)
    return redirect("/")


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", 5052))
    app.run(host=host, port=port, debug=False)
