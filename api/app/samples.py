"""The three built-in sample receipts (web/public/samples).

Parses of these are tagged in the event log so they don't count as real users.
EXPECTED is the ground truth printed on each sample: the eval harness checks
the model against it, and DEMO_MODE returns it so the UI can be developed
without an API key.
"""
from __future__ import annotations

from .schemas import Receipt

SAMPLE_IDS = ("coffee", "office", "invoice")

EXPECTED: dict[str, Receipt] = {
    "coffee": Receipt(
        merchant="Corner Grind Coffee", date="2026-10-14", subtotal=15.75, tax=1.26, tip=3.15, total=20.16,
        payment_method="Visa ••4242",
        line_items=[{"description": "2 Oat Milk Latte 12oz", "amount": 11.50},
                    {"description": "1 Almond Croissant", "amount": 4.25}],
        category="Meals", category_reason="Coffee and pastry from a cafe.", confidence=0.92,
    ),
    "office": Receipt(
        merchant="Lantern Office Supply", date="2026-10-09", subtotal=119.47, tax=7.47, total=126.94,
        payment_method="Mastercard ••8810",
        line_items=[{"description": "Copy Paper 8.5x11, 5 Ream Case", "amount": 42.99},
                    {"description": "Gel Pens, Black, 12 Pack", "amount": 11.49},
                    {"description": "Laser Toner Cartridge, Black", "amount": 64.99}],
        category="Office expense", category_reason="Paper, pens and printer toner.", confidence=0.95,
    ),
    "invoice": Receipt(
        merchant="Fieldnote Software, Inc.", date="2026-10-01", subtotal=24.00, tax=0.0, total=24.00,
        payment_method="Visa ••4242",
        line_items=[{"description": "Fieldnote Pro, monthly plan", "amount": 24.00}],
        category="Software and subscriptions", category_reason="Monthly software plan.", confidence=0.97,
    ),
}


def sample_id(header: str | None) -> str | None:
    v = (header or "").strip().lower()
    return v if v in SAMPLE_IDS else None
