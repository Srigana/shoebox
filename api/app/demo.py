"""DEMO_MODE=1: canned receipts so the UI can be developed without an API key or spend."""
from __future__ import annotations

import hashlib

from .schemas import Receipt

_SAMPLES = [
    {"merchant": "Blue Bottle Coffee", "total": 14.75, "tax": 1.25, "category": "Meals",
     "category_reason": "Coffee shop purchase, likely a client meeting.", "confidence": 0.91},
    {"merchant": "Figma", "total": 15.00, "tax": 0, "category": "Software and subscriptions",
     "category_reason": "Monthly design software subscription.", "confidence": 0.97},
    {"merchant": "Target", "total": 63.18, "tax": 4.12, "category": "Office expense",
     "category_reason": "Mixed items; printer paper and pens are the largest lines.", "confidence": 0.52},
    {"merchant": "Delta Air Lines", "total": 312.40, "tax": 28.10, "category": "Travel",
     "category_reason": "Airfare.", "confidence": 0.95},
]


def demo_extractor(data: bytes, media_type: str) -> Receipt:
    s = _SAMPLES[int(hashlib.md5(data).hexdigest(), 16) % len(_SAMPLES)]
    return Receipt.model_validate({
        "is_receipt": True, "date": "2026-10-14", "currency": "USD",
        "subtotal": round(s["total"] - s["tax"], 2), "tip": None, "payment_method": "Visa ••4242",
        "line_items": [], **s,
    })
