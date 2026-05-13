import csv
import os
from flask import Flask

app = Flask(__name__)
CSV_PATH = os.getenv("CSV_PATH", "output/invoices.csv")


def _read_csv():
    if not os.path.exists(CSV_PATH):
        return [], []
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


@app.route("/")
def index():
    fields, rows = _read_csv()
    if not rows:
        body = "<p style='color:#6b7280'>No invoices processed yet.</p>"
    else:
        headers = "".join(f"<th>{f}</th>" for f in fields)
        trs = ""
        for r in reversed(rows):
            trs += "<tr>" + "".join(f"<td>{r.get(f,'')}</td>" for f in fields) + "</tr>"
        body = f"""
        <table>
          <thead><tr>{headers}</tr></thead>
          <tbody>{trs}</tbody>
        </table>"""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Invoice Processor</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; background: #f9fafb; color: #1f2937; padding: 32px; }}
  h1 {{ font-size: 20px; font-weight: 700; margin-bottom: 20px; }}
  table {{ width: 100%; border-collapse: collapse; background: white;
           border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; font-size: 13px; }}
  th {{ background: #f3f4f6; padding: 10px 12px; text-align: left;
        border-bottom: 1px solid #e5e7eb; font-size: 11px; text-transform: uppercase;
        letter-spacing: .5px; color: #6b7280; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f3f4f6; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f9fafb; }}
</style>
</head>
<body>
<h1>Invoices — {len(rows)} processed</h1>
{body}
</body>
</html>"""


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", 5052))
    app.run(host=host, port=port, debug=False)
