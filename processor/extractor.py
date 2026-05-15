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
Extract ALL line items visible in the invoice table into "lignes". Copy numbers exactly as printed, do not recompute them."""

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


# Pricing per million tokens (Gemini 2.0 Flash via OpenRouter)
_PRICE_INPUT_PER_M = 0.10
_PRICE_OUTPUT_PER_M = 0.40


def _compute_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round(
        prompt_tokens * _PRICE_INPUT_PER_M / 1_000_000
        + completion_tokens * _PRICE_OUTPUT_PER_M / 1_000_000,
        6,
    )


def extract_invoice(image: Image.Image) -> tuple[dict, float]:
    """Returns (data_dict, cost_usd)."""
    b64 = _image_to_base64(image)
    client = _get_client()
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001"),
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
    usage = response.usage
    cost = _compute_cost(
        getattr(usage, "prompt_tokens", 0),
        getattr(usage, "completion_tokens", 0),
    ) if usage else 0.0

    raw = response.choices[0].message.content.strip()
    raw = raw.strip("```json").strip("```").strip()
    try:
        return json.loads(raw), cost
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}\nRaw: {raw}")
