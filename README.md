# invoice-processor

**Problem:** someone here retypes supplier invoices into a spreadsheet, one by one, every week.
**Solution:** drop the PDF in a folder and the row writes itself.

Number, date, supplier, amounts, VAT, IBAN, due date.

## Run it

```bash
sudo apt-get install -y poppler-utils
cp .env.example .env    # add your OPENROUTER_API_KEY
uv sync
uv run python watch.py  # watches data/invoices/
```

Drop a PDF into `data/invoices/` and a line appears in `data/output/invoices.csv`. `uv run python viewer.py` shows that CSV as a table on http://127.0.0.1:5052. No invoices to test with? `generate_sample_invoices.py` makes some.

## How it works

Each page is converted to an image and read by a vision model (Gemini via OpenRouter), the way a person reads it. No templates, no zone mapping per supplier, so an unfamiliar layout doesn't break the pipeline.

## What it won't do

It fills a CSV. It doesn't validate anything accounting-wise and it doesn't push into your ERP.

## This is the level 1

Real invoices arrive by email, not in a folder. They need to land in your accounting tool, not in a CSV. And someone has to review the ones the model wasn't sure about instead of trusting all of them blindly.

That version exists too, it just has to be built around your stack. That part I do case by case.

[LinkedIn](https://www.linkedin.com/in/sonam-crumiere) · [sonam.me](https://sonam.me)
