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
