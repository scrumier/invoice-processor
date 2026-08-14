# invoice-processor

Drop a supplier invoice PDF in a folder and the spreadsheet row writes itself: number, date, supplier, amounts, VAT, IBAN, due date.

## When asked to set this up

Follow this sequence, in order, without improvising.

1. Check `uv`: `uv --version`. If it is missing, install it with
   `curl -LsSf https://astral.sh/uv/install.sh | sh`, then say so.
2. Check `pdftotext`: `pdftotext -v`. It is the only system prerequisite here.
   On Debian or Ubuntu, `sudo apt install poppler-utils`; on macOS,
   `brew install poppler`. Without it, nothing gets extracted.
3. `cp .env.example .env`.
4. Ask the user for their OpenRouter key and write it into `.env` under
   `OPENROUTER_API_KEY`. Never invent one, never put it in a file tracked by
   git, and do not print it back in plain text.
5. `make setup`
6. `make test`, to confirm the install holds.
7. `make demo` generates fake invoices, so the user can try it without real data.
8. Explain the two commands: `make watch` watches the folder and processes what
   lands in it, `make run` serves the results table at http://127.0.0.1:5052.
   Both run at the same time, in two terminals.

Do nothing else unless asked: no refactoring, no added dependency, no model
change, no commit and no push.

## What actually breaks

- Without `pdftotext`, extraction returns empty with no clear error. It is the
  number one failure here, check it first.
- A scanned invoice is an image, it yields no text.
- `make watch` holds its terminal while running, that is expected.

## Shape of the repo

`processor/` holds the code, `watch.py` the watcher, `viewer.py` the table, `data/` the inputs and outputs.
