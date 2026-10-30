"""Receipt extraction with Claude vision and structured outputs (a JSON schema the reply must match).

Claude Sonnet 5.5 rejects forced tool use (tool_choice "tool" or "any"), so the
schema goes in output_config.format instead, which every model supports. See
platform.claude.com/docs/en/build-with-claude/structured-outputs.
"""
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
You read receipts and invoices and record each one as JSON matching the given schema.

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
- confidence: a number from 0 to 1 for the category choice. Go lower when the receipt is ambiguous \
or mixed (for example a big-box store with both groceries and office items).
- If the document is not a receipt or invoice, set is_receipt to false, category to Other expenses, \
and leave the other fields null."""


def _nullable(t: str, description: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"anyOf": [{"type": t}, {"type": "null"}]}
    if description:
        out["description"] = description
    return out


# Structured-output rules: every object closes with additionalProperties false, and
# numeric limits such as minimum/maximum aren't allowed (Pydantic clamps confidence).
RECEIPT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "is_receipt": {"type": "boolean"},
        "merchant": _nullable("string"),
        "date": _nullable("string", "YYYY-MM-DD"),
        "currency": {"type": "string", "description": "ISO 4217 code, e.g. USD"},
        "subtotal": _nullable("number"),
        "tax": _nullable("number"),
        "tip": _nullable("number"),
        "total": _nullable("number"),
        "payment_method": _nullable("string", "e.g. 'Visa ••1234', 'Cash'"),
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"description": {"type": "string"}, "amount": _nullable("number")},
                "required": ["description", "amount"],
                "additionalProperties": False,
            },
        },
        "category": {"type": "string", "enum": CATEGORIES},
        "category_reason": {"type": "string"},
        "confidence": {"type": "number", "description": "0 to 1"},
    },
    "required": [
        "is_receipt", "merchant", "date", "currency", "subtotal", "tax", "tip", "total",
        "payment_method", "line_items", "category", "category_reason", "confidence",
    ],
    "additionalProperties": False,
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
    (SYSTEM_PROMPT + json.dumps(RECEIPT_SCHEMA, sort_keys=True)).encode()
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
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    _file_block(data, media_type),
                    {"type": "text", "text": "Extract and categorize this receipt."},
                ],
            }],
            # Sent as extra_body so it works on any version of the anthropic SDK.
            extra_body={"output_config": {"format": {"type": "json_schema", "schema": RECEIPT_SCHEMA}}},
        )
    except ExtractionError:
        raise
    except Exception as e:  # network / API errors; keep the API's own explanation for the logs
        detail = getattr(e, "message", None) or str(e)
        raise ExtractionError(f"Model request failed: {type(e).__name__}: {detail[:300]}") from e

    usage = getattr(msg, "usage", None)
    tokens = {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }
    stop = getattr(msg, "stop_reason", None)
    if stop in ("max_tokens", "refusal"):
        raise ExtractionError(f"Model stopped early ({stop}).")
    text = "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", None) == "text")
    if not text.strip():
        raise ExtractionError("Model returned no JSON.")
    try:
        return Receipt.model_validate(json.loads(text)), tokens
    except (json.JSONDecodeError, ValueError) as e:
        raise ExtractionError(f"Model output didn't match the schema: {str(e)[:200]}") from e


def extract_receipt(data: bytes, media_type: str, client: Optional[Any] = None) -> Receipt:
    return extract_receipt_detailed(data, media_type, client=client)[0]
