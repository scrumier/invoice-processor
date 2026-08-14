# invoice-processor

**Problem:** someone here retypes supplier invoices into a spreadsheet, one by one, every week.<br>
**Solution:** drop the PDF in a folder and the row writes itself.

Number, date, supplier, amounts, VAT, IBAN, due date.

## Run it

The short way, with any coding agent:

```bash
claude          # or codex, or whatever you run
> set this up for me
```

It reads `AGENTS.md`, installs what is missing, asks you for the one key it
cannot invent, and hands back the command that starts it.

The manual way:
```bash
sudo apt-get install -y poppler-utils
cp .env.example .env    # add your OPENROUTER_API_KEY
make setup
make demo               # fake invoices to try it with
make watch              # watches data/invoices/
```

Drop a PDF into `data/invoices/` and a line appears in `data/output/invoices.csv`. `make run` shows that CSV as a live table on http://127.0.0.1:5052.

`make test` runs the suite, `make lint` runs Ruff.

## How it works

Each page is converted to an image and read by a vision model (Gemini via OpenRouter), the way a person reads it. No templates, no zone mapping per supplier, so an unfamiliar layout doesn't break the pipeline.

What comes back is validated against a schema before anything else touches it, so a malformed response fails immediately instead of quietly writing a half-empty row.

Then plain arithmetic, no model involved, flags what doesn't add up: a line total that isn't quantity times unit price, lines that don't sum to the stated total, HT plus VAT that misses the total charged, a VAT rate that no French rate explains, a malformed IBAN, a due date before the invoice date. Every flag can be explained to an accountant without appealing to what a model thought.

## What it won't do

It fills a CSV. It doesn't validate anything accounting-wise and it doesn't push into your ERP.

## This is the level 1

Real invoices arrive by email, not in a folder. They need to land in your accounting tool, not in a CSV. And someone has to review the ones the model wasn't sure about instead of trusting all of them blindly.

That version exists too, it just has to be built around your stack. That part I do case by case.

[LinkedIn](https://www.linkedin.com/in/sonam-crumiere) · [sonam.me](https://sonam.me)
