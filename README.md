# invoice-processor

Automated extraction of data from scanned supplier invoice PDFs. Watches a folder, extracts fields via LLM vision, appends to CSV.

## What it does

1. Watches `invoices/` for new PDF files
2. Converts each page to an image (requires `poppler-utils`)
3. Sends the image to a vision LLM (OpenRouter — google/gemini-flash-1.5)
4. Extracts: invoice number, date, supplier, HT/TVA/TTC amounts, IBAN, due date
5. Appends a row to `output/invoices.csv`
6. A web viewer shows the CSV as a table (Tailscale only — http://127.0.0.1:5052)

## Setup

```bash
sudo apt-get install -y poppler-utils
uv sync
cp .env.example .env  # fill in OPENROUTER_API_KEY
```

## Usage

```bash
# Start watcher
uv run python watch.py

# Drop a PDF
cp my_invoice.pdf invoices/

# View results (from Mac on Tailscale)
# http://127.0.0.1:5052
```

## Stack

- Python, uv, watchdog, pdf2image, Pillow
- OpenRouter (google/gemini-flash-1.5 vision model)
- Flask (viewer on port 5052)

## Author

Sonam — [github.com/scrumier](https://github.com/scrumier)
