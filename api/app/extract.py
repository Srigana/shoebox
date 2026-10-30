"""Receipt extraction with Claude vision + forced tool use for structured output."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any, Optional

from .schemas import CATEGORIES, Receipt

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
PDF_TYPE = "application/pdf"
SUPPORTED_TYPES = IMAGE_TYPES | {PDF_TYPE}

SYSTEM_PROMPT = """You are a careful bookkeeping assistant for US freelancers and small businesses. \
You read receipts and invoices and record them with the record_receipt tool.

Rules:
- Extract only what is printed. Use null for anything missing or illegible. Never guess amounts.
- total is the final amount paid, after tax and tip. Amounts are plain numbers, no currency symbols.
- date is YYYY-MM-DD. If the year is not printed, use null rather than guessing.
- Choose the single best business-expense category, the way a bookkeeper would for IRS Schedule C:
  * Restaurants, cafes, food delivery -> Meals
  * Airfare, hotels, lodging, trains, rideshare while traveling -> Travel
  * Fuel, parking, tolls, car service and repairs -> Car and truck expenses
  * SaaS, apps, cloud hosting, domains -> Software and subscriptions
  * Pens, paper, ink, postage, small office items -> Office expense
  * Materials used up in delivering the work -> Supplies
  * Payment-processor, bank or card fees -> Bank and merchant fees
  * Courses, books, conference tickets -> Education and training
  * Use Other expenses only when nothing else fits.
- category_reason: one short, plain sentence the user can check at a glance. No em dashes.
- confidence: 0 to 1 for the category choice. Go lower when the receipt is ambiguous or mixed \
(for example a big-box store with both groceries and office items).
- If the document is not a receipt or invoice, set is_receipt to false, category to Other expenses, \
and leave the other fields null."""

_num = {"type": ["number", "null"]}
_str = {"type": ["string", "null"]}

RECORD_TOOL: dict[str, Any] = {
    "name": "record_receipt",
    "description": "Record the structured contents and expense category of one receipt or invoice.",
    "input_schema": {
        "type": "object",
        "properties": {
            "is_receipt": {"type": "boolean"},
            "merchant": _str,
            "date": {**_str, "description": "YYYY-MM-DD"},
            "currency": {"type": "string", "description": "ISO 4217 code, e.g. USD"},
            "subtotal": _num,
            "tax": _num,
            "tip": _num,
            "total": _num,
            "payment_method": {**_str, "description": "e.g. 'Visa ••1234', 'Cash'"},
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"description": {"type": "string"}, "amount": _num},
                    "required": ["description", "amount"],
                },
            },
            "category": {"type": "string", "enum": CATEGORIES},
            "category_reason": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "is_receipt", "merchant", "date", "currency", "total",
            "line_items", "category", "category_reason", "confidence",
        ],
    },
}


class ExtractionError(Exception):
    pass


_client = None


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic

        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ExtractionError("Server is missing ANTHROPIC_API_KEY.")
        _client = Anthropic()
    return _client


def _file_block(data: bytes, media_type: str) -> dict[str, Any]:
    b64 = base64.standard_b64encode(data).decode("ascii")
    if media_type == PDF_TYPE:
        return {"type": "document", "source": {"type": "base64", "media_type": PDF_TYPE, "data": b64}}
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}}


# Changes whenever the prompt or schema changes, so cached eval results are
# never reused across prompt versions.
PROMPT_VERSION = hashlib.sha256(
    (SYSTEM_PROMPT + json.dumps(RECORD_TOOL, sort_keys=True)).encode()
).hexdigest()[:12]


def extract_receipt_detailed(
    data: bytes, media_type: str, client: Optional[Any] = None, model: Optional[str] = None
) -> tuple[Receipt, dict[str, int]]:
    """Like extract_receipt, but also returns token usage (used by the eval harness)."""
    if media_type not in SUPPORTED_TYPES:
        raise ExtractionError(f"Unsupported file type: {media_type}")
    client = client or _get_client()
    try:
        msg = client.messages.create(
            model=model or MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=[RECORD_TOOL],
            tool_choice={"type": "tool", "name": "record_receipt"},
            messages=[{
                "role": "user",
                "content": [
                    _file_block(data, media_type),
                    {"type": "text", "text": "Extract and categorize this receipt."},
                ],
            }],
        )
    except ExtractionError:
        raise
    except Exception as e:  # network / API errors
        raise ExtractionError(f"Model request failed: {type(e).__name__}") from e

    usage = getattr(msg, "usage", None)
    tokens = {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }
    for block in msg.content:
        if getattr(block, "type", None) == "tool_use":
            return Receipt.model_validate(block.input), tokens
    raise ExtractionError("Model did not return structured output.")


def extract_receipt(data: bytes, media_type: str, client: Optional[Any] = None) -> Receipt:
    return extract_receipt_detailed(data, media_type, client=client)[0]
