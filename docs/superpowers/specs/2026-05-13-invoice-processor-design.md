# Invoice Processor — Design Spec

**Date:** 2026-05-13

## Problem

PMEs receive supplier invoices as scanned PDFs. Data entry is manual and time-consuming. This tool automates extraction and consolidation into a CSV.

## Architecture

```
invoice-processor/
  watch.py          → folder watcher (watchdog), triggers on new PDF/image
  processor/
    loader.py       → PDF pages → PIL images (pdf2image + poppler)
    extractor.py    → image → structured JSON via LLM vision (OpenRouter)
    exporter.py     → append row to output/invoices.csv
  invoices/         → drop scanned PDFs here
  output/
    invoices.csv    → running output (append-only)
  viewer.py         → Flask on port 5052, renders CSV as HTML table
  pyproject.toml
  .env.example
  README.md
```

## Data Flow

```
New PDF dropped in invoices/
  → loader.py: convert each page to image
  → extractor.py: send image to LLM vision, get JSON
  → check: is_invoice field in JSON → skip if false
  → exporter.py: append row to CSV
```

## Extracted Fields

| Field | Description |
|---|---|
| filename | Source PDF filename |
| processed_at | Timestamp |
| is_invoice | Boolean (skip if false) |
| numero_facture | Invoice number |
| date_facture | Invoice date |
| fournisseur | Supplier name |
| montant_ht | Amount before tax |
| tva | VAT amount |
| montant_ttc | Total amount |
| iban | Payment IBAN |
| echeance | Payment due date |

## LLM

- Provider: OpenRouter
- Model: `google/gemini-flash-1.5` (vision-capable, cheap, fast)
- Single prompt: classify + extract in one call
- Output: strict JSON, no markdown

## Services (systemd)

- `invoice-watcher.service` — persistent watcher, user=sonam
- `invoice-viewer.service` — Flask on `127.0.0.1:5052`, Tailscale only

## Error Handling

- File not readable / corrupt PDF → log error, skip file
- LLM returns invalid JSON → log error, skip file
- Not an invoice → log skip, do not append to CSV

## Dependencies

- `watchdog` — folder watching
- `pdf2image` + `poppler-utils` — PDF to image
- `Pillow` — image handling
- `openai` — OpenRouter client
- `flask` — viewer
- `python-dotenv`
