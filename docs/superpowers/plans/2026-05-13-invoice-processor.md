# Invoice Processor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Watch a folder for scanned invoice PDFs, extract structured data via LLM vision, and append rows to a CSV. A minimal Flask viewer shows the CSV as an HTML table on the Tailscale network.

**Architecture:** A watchdog-based folder watcher triggers processing on new PDFs. Each PDF is converted to images (one per page), sent to a vision LLM (OpenRouter), and the structured JSON response is appended to a running CSV. A separate Flask server serves the CSV as an HTML table.

**Tech Stack:** Python 3.12, uv, watchdog, pdf2image, Pillow, openai (OpenRouter client), flask, python-dotenv, pytest

---

## File Map

```
invoice-processor/
  watch.py                  → entry point: starts watchdog, processes new files
  viewer.py                 → Flask server, renders output/invoices.csv as HTML table
  processor/
    __init__.py
    loader.py               → PDF path → list of PIL images
    extractor.py            → PIL image → structured dict via LLM vision
    exporter.py             → dict → append row to CSV
  invoices/                 → watched folder (drop PDFs here)
  output/
    invoices.csv            → running output, created on first run
  tests/
    test_loader.py
    test_extractor.py
    test_exporter.py
  pyproject.toml
  .env.example
  README.md
```

---

### Task 0: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `processor/__init__.py`
- Create: `invoices/.gitkeep`
- Create: `output/.gitkeep`

- [ ] **Step 1: Initialize uv project**

```bash
cd /home/sonam/projects/invoice-processor
uv init --no-readme --python 3.12
uv add watchdog pdf2image Pillow openai python-dotenv flask
uv add --dev pytest
```

Expected: `pyproject.toml` updated, `.venv/` created.

- [ ] **Step 2: Install system dependency (poppler)**

```bash
sudo apt-get install -y poppler-utils
```

Verify: `pdftoppm -v` prints version.

- [ ] **Step 3: Create folder structure**

```bash
mkdir -p invoices output processor tests
touch processor/__init__.py invoices/.gitkeep output/.gitkeep
```

- [ ] **Step 4: Create .env.example**

```bash
cat > .env.example << 'EOF'
OPENROUTER_API_KEY=your_key_here
LLM_MODEL=google/gemini-flash-1.5
EOF
cp .env.example .env
```

- [ ] **Step 5: Create .gitignore**

```
.venv/
.env
output/invoices.csv
invoices/*.pdf
__pycache__/
*.pyc
```

- [ ] **Step 6: Commit**

```bash
git init
git add .
git commit -m "chore: project setup"
```

---

### Task 1: loader.py — PDF to images

**Files:**
- Create: `processor/loader.py`
- Create: `tests/test_loader.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_loader.py`:

```python
import pytest
from pathlib import Path
from PIL import Image


def test_load_pdf_returns_images(tmp_path):
    from processor.loader import pdf_to_images

    # Create a minimal 1-page PDF with reportlab or use a fixture
    # For now test with a real PDF if available, else skip
    sample = Path("tests/fixtures/sample_invoice.pdf")
    if not sample.exists():
        pytest.skip("No sample PDF fixture")

    images = pdf_to_images(str(sample))
    assert isinstance(images, list)
    assert len(images) >= 1
    assert all(isinstance(img, Image.Image) for img in images)


def test_load_invalid_path_raises():
    from processor.loader import pdf_to_images

    with pytest.raises(Exception):
        pdf_to_images("/nonexistent/file.pdf")
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_loader.py -v
```

Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Implement loader.py**

Create `processor/loader.py`:

```python
from pdf2image import convert_from_path
from PIL import Image


def pdf_to_images(pdf_path: str, dpi: int = 200) -> list[Image.Image]:
    return convert_from_path(pdf_path, dpi=dpi)
```

- [ ] **Step 4: Add sample PDF fixture**

```bash
mkdir -p tests/fixtures
# Download or copy a sample invoice PDF into tests/fixtures/sample_invoice.pdf
# For now create a placeholder:
touch tests/fixtures/.gitkeep
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_loader.py -v
```

Expected: `test_load_invalid_path_raises` PASS, `test_load_pdf_returns_images` SKIP (no fixture yet).

- [ ] **Step 6: Commit**

```bash
git add processor/loader.py tests/test_loader.py tests/fixtures/.gitkeep
git commit -m "feat: loader — PDF to PIL images"
```

---

### Task 2: extractor.py — image to structured JSON

**Files:**
- Create: `processor/extractor.py`
- Create: `tests/test_extractor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_extractor.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_extractor.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement extractor.py**

Create `processor/extractor.py`:

```python
import base64
import json
import os
from io import BytesIO

from openai import OpenAI
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an invoice data extraction expert.
Look at the image and return ONLY a valid JSON object, no markdown, no explanation.
If this is not an invoice, return: {"is_invoice": false}
If it is an invoice, return:
{
  "is_invoice": true,
  "numero_facture": "...",
  "date_facture": "YYYY-MM-DD or null",
  "fournisseur": "...",
  "montant_ht": "...",
  "tva": "...",
  "montant_ttc": "...",
  "iban": "... or null",
  "echeance": "YYYY-MM-DD or null"
}"""

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    return _client


def _image_to_base64(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode()


def extract_invoice(image: Image.Image) -> dict:
    b64 = _image_to_base64(image)
    client = _get_client()
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "google/gemini-flash-1.5"),
        max_tokens=512,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    }
                ],
            },
        ],
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.strip("```json").strip("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}\nRaw: {raw}")
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_extractor.py -v
```

Expected: all 3 PASS

- [ ] **Step 5: Commit**

```bash
git add processor/extractor.py tests/test_extractor.py
git commit -m "feat: extractor — image to structured JSON via LLM vision"
```

---

### Task 3: exporter.py — append to CSV

**Files:**
- Create: `processor/exporter.py`
- Create: `tests/test_exporter.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_exporter.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_exporter.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement exporter.py**

Create `processor/exporter.py`:

```python
import csv
import os

FIELDS = [
    "filename", "processed_at", "numero_facture", "date_facture",
    "fournisseur", "montant_ht", "tva", "montant_ttc", "iban", "echeance",
]


def append_to_csv(row: dict, csv_path: str) -> None:
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_exporter.py -v
```

Expected: both PASS

- [ ] **Step 5: Commit**

```bash
git add processor/exporter.py tests/test_exporter.py
git commit -m "feat: exporter — append invoice row to CSV"
```

---

### Task 4: watch.py — folder watcher

**Files:**
- Create: `watch.py`

- [ ] **Step 1: Implement watch.py**

Create `watch.py`:

```python
import os
import time
import logging
from datetime import datetime
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

from processor.loader import pdf_to_images
from processor.extractor import extract_invoice
from processor.exporter import append_to_csv

load_dotenv()

INVOICES_DIR = os.getenv("INVOICES_DIR", "invoices")
CSV_PATH = os.getenv("CSV_PATH", "output/invoices.csv")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def process_file(pdf_path: str) -> None:
    filename = Path(pdf_path).name
    log.info(f"Processing {filename}")
    try:
        images = pdf_to_images(pdf_path)
    except Exception as e:
        log.error(f"Failed to load {filename}: {e}")
        return

    for i, image in enumerate(images):
        try:
            data = extract_invoice(image)
        except Exception as e:
            log.error(f"Extraction failed on page {i+1} of {filename}: {e}")
            continue

        if not data.get("is_invoice"):
            log.info(f"Skipped {filename} page {i+1}: not an invoice")
            continue

        row = {
            "filename": filename,
            "processed_at": datetime.now().isoformat(timespec="seconds"),
            **{k: data.get(k) for k in [
                "numero_facture", "date_facture", "fournisseur",
                "montant_ht", "tva", "montant_ttc", "iban", "echeance"
            ]},
        }
        append_to_csv(row, CSV_PATH)
        log.info(f"Saved: {data.get('fournisseur')} — {data.get('montant_ttc')} EUR")
        break  # one row per PDF (first invoice page)


class InvoiceHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".pdf"):
            time.sleep(0.5)  # wait for file to finish writing
            process_file(event.src_path)


if __name__ == "__main__":
    os.makedirs(INVOICES_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    log.info(f"Watching {INVOICES_DIR}/")
    observer = Observer()
    observer.schedule(InvoiceHandler(), INVOICES_DIR, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
```

- [ ] **Step 2: Test manually**

```bash
# In terminal 1:
uv run python watch.py
# Expected: "Watching invoices/"

# In terminal 2: drop a test PDF
cp tests/fixtures/sample_invoice.pdf invoices/
# Expected in terminal 1: processing log + CSV row
```

- [ ] **Step 3: Commit**

```bash
git add watch.py
git commit -m "feat: watch.py — folder watcher with watchdog"
```

---

### Task 5: viewer.py — CSV table viewer

**Files:**
- Create: `viewer.py`

- [ ] **Step 1: Implement viewer.py**

Create `viewer.py`:

```python
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
```

- [ ] **Step 2: Test manually**

```bash
uv run python viewer.py
# Open http://127.0.0.1:5052 in browser
# Expected: table showing any processed invoices, or "No invoices processed yet."
```

- [ ] **Step 3: Commit**

```bash
git add viewer.py
git commit -m "feat: viewer — CSV table on Flask"
```

---

### Task 6: Systemd services + README

**Files:**
- Create: `/etc/systemd/system/invoice-watcher.service`
- Create: `/etc/systemd/system/invoice-viewer.service`
- Create: `README.md`

- [ ] **Step 1: Create watcher service**

```bash
sudo tee /etc/systemd/system/invoice-watcher.service > /dev/null << 'EOF'
[Unit]
Description=Invoice Processor Watcher
After=network.target tailscaled.service

[Service]
Type=simple
User=sonam
WorkingDirectory=/home/sonam/projects/invoice-processor
EnvironmentFile=/home/sonam/projects/invoice-processor/.env
ExecStart=/home/sonam/.local/bin/uv run python watch.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

- [ ] **Step 2: Create viewer service**

```bash
sudo tee /etc/systemd/system/invoice-viewer.service > /dev/null << 'EOF'
[Unit]
Description=Invoice Viewer
After=network.target tailscaled.service

[Service]
Type=simple
User=sonam
WorkingDirectory=/home/sonam/projects/invoice-processor
EnvironmentFile=/home/sonam/projects/invoice-processor/.env
Environment=FLASK_HOST=127.0.0.1
Environment=FLASK_PORT=5052
ExecStart=/home/sonam/.local/bin/uv run python viewer.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

- [ ] **Step 3: Enable and start services**

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now invoice-watcher invoice-viewer
sudo systemctl status invoice-watcher invoice-viewer --no-pager
```

Expected: both `active (running)`

- [ ] **Step 4: Write README.md**

Create `README.md`:

```markdown
# invoice-processor

Automated extraction of data from scanned supplier invoice PDFs. Watches a folder, extracts fields via LLM vision, appends to CSV.

## What it does

1. Watches `invoices/` for new PDF files
2. Converts each page to an image
3. Sends the image to a vision LLM (OpenRouter)
4. Extracts: invoice number, date, supplier, HT/TVA/TTC amounts, IBAN, due date
5. Appends a row to `output/invoices.csv`
6. A web viewer shows the CSV as a table (Tailscale only)

## Setup

\`\`\`bash
sudo apt-get install -y poppler-utils
uv sync
cp .env.example .env  # fill in OPENROUTER_API_KEY
\`\`\`

## Usage

\`\`\`bash
# Start watcher
uv run python watch.py

# Drop a PDF
cp my_invoice.pdf invoices/

# View results
# http://127.0.0.1:5052 (Tailscale only)
\`\`\`

## Stack

- Python, uv, watchdog, pdf2image, Pillow
- OpenRouter (google/gemini-flash-1.5 vision model)
- Flask (viewer)
```

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "feat: systemd services + README"
```

---

### Task 7: GitHub repo

- [ ] **Step 1: Create repo and push**

```bash
cd /home/sonam/projects/invoice-processor
gh repo create scrumier/invoice-processor --public --source=. --remote=origin --push
```

Expected: repo live at `github.com/scrumier/invoice-processor`
