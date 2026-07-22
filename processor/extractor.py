"""Read an invoice page with a vision model and return validated fields.

A vision model reads the rendered page the way a person would, instead of
matching coordinates against a per-supplier template. That is the whole point
of the approach: an unfamiliar layout costs nothing, because there is no
template to write.
"""

import base64
import json
import os
from io import BytesIO

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
from pydantic import ValidationError

from processor.models import ExtractedInvoice

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "google/gemini-2.5-flash-lite"
MAX_TOKENS = 512

# OpenRouter pricing per million tokens for DEFAULT_MODEL, used to report the
# per-invoice cost. Update alongside the model.
PRICE_INPUT_PER_M = 0.10
PRICE_OUTPUT_PER_M = 0.40

SYSTEM_PROMPT = """You are an invoice data extraction expert.
Look at the image and return ONLY a valid JSON object, no markdown, no explanation.
Always extract as much as possible. Every field you cannot find must be null, never omit a field.
{
  "is_invoice": true,
  "confidence": <integer 0-100, your confidence in the extraction quality based on image clarity and field legibility>,
  "numero_facture": "...",
  "date_facture": "YYYY-MM-DD or null",
  "fournisseur": "...",
  "montant_ht": <number or null>,
  "tva": <number or null>,
  "tva_taux": <the TVA rate as printed on the invoice, e.g. 20 for "20%", or null if not stated>,
  "montant_ttc": <number or null>,
  "iban": "... or null",
  "echeance": "YYYY-MM-DD or null",
  "lignes": [
    {"description": "...", "qty": <number>, "pu_ht": <number>, "total_ht": <number>}
  ]
}
Extract ALL line items visible in the invoice table into "lignes". Copy numbers exactly as printed, do not recompute them."""  # noqa: E501

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Return the shared OpenRouter client, creating it on first use.

    Returns:
        An OpenAI-compatible client pointed at OpenRouter.
    """
    global _client  # noqa: PLW0603
    if _client is None:
        _client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    return _client


def _image_to_base64(image: Image.Image) -> str:
    """Encode an image as base64 JPEG for inlining in the request.

    Args:
        image: Rendered invoice page.

    Returns:
        Base64 payload, without the data-URI prefix.
    """
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode()


def _compute_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Convert a token count into a dollar cost for one invoice.

    Args:
        prompt_tokens: Tokens billed as input, including the image.
        completion_tokens: Tokens billed as output.

    Returns:
        Cost in USD, rounded to the microdollar.
    """
    return round(
        prompt_tokens * PRICE_INPUT_PER_M / 1_000_000
        + completion_tokens * PRICE_OUTPUT_PER_M / 1_000_000,
        6,
    )


def _strip_code_fence(raw: str) -> str:
    """Remove the Markdown code fence the model sometimes wraps the JSON in.

    Args:
        raw: Raw message content returned by the model.

    Returns:
        The content without its opening and closing fence.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```")
    return text.removesuffix("```").strip()


def extract_invoice(image: Image.Image) -> tuple[ExtractedInvoice, float]:
    """Extract invoice fields from a rendered page.

    Args:
        image: One page of an invoice PDF, already rasterised.

    Returns:
        The validated fields, and what the call cost in USD.

    Raises:
        ValueError: If the model returned something that is not valid JSON, or
            JSON that does not match the expected invoice shape.
    """
    client = _get_client()
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", DEFAULT_MODEL),
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{_image_to_base64(image)}"
                        },
                    }
                ],
            },
        ],
    )

    usage = response.usage
    cost = (
        _compute_cost(
            getattr(usage, "prompt_tokens", 0),
            getattr(usage, "completion_tokens", 0),
        )
        if usage
        else 0.0
    )

    raw = _strip_code_fence(response.choices[0].message.content)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON from LLM: {exc}\nRaw: {raw}") from exc

    try:
        return ExtractedInvoice.model_validate(payload), cost
    except ValidationError as exc:
        raise ValueError(f"Unexpected invoice shape from LLM: {exc}") from exc
