"""Data model for an extracted receipt and the Schedule C category map."""
from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Expense categories, modeled on IRS Schedule C (Form 1040) Part II.
CATEGORIES: list[str] = [
    "Advertising",
    "Car and truck expenses",
    "Contract labor",
    "Insurance",
    "Legal and professional services",
    "Office expense",
    "Rent or lease",
    "Repairs and maintenance",
    "Supplies",
    "Taxes and licenses",
    "Travel",
    "Meals",
    "Utilities",
    "Software and subscriptions",
    "Bank and merchant fees",
    "Education and training",
    "Other expenses",
]

FALLBACK_CATEGORY = "Other expenses"

# Where each category usually lands on Schedule C. Informational, not tax advice.
SCHEDULE_C_LINE: dict[str, str] = {
    "Advertising": "Line 8",
    "Car and truck expenses": "Line 9",
    "Contract labor": "Line 11",
    "Insurance": "Line 15",
    "Legal and professional services": "Line 17",
    "Office expense": "Line 18",
    "Rent or lease": "Line 20a/20b",
    "Repairs and maintenance": "Line 21",
    "Supplies": "Line 22",
    "Taxes and licenses": "Line 23",
    "Travel": "Line 24a",
    "Meals": "Line 24b",
    "Utilities": "Line 25",
    "Software and subscriptions": "Line 27b (Part V)",
    "Bank and merchant fees": "Line 27b (Part V)",
    "Education and training": "Line 27b (Part V)",
    "Other expenses": "Line 27b (Part V)",
}

# Business meals are generally 50% deductible; everything else defaults to 100%.
DEDUCTIBLE_RATE: dict[str, float] = {"Meals": 0.5}


class LineItem(BaseModel):
    description: str = ""
    amount: Optional[float] = None


class Receipt(BaseModel):
    is_receipt: bool = True
    merchant: Optional[str] = None
    date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    currency: str = "USD"
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tip: Optional[float] = None
    total: Optional[float] = None
    payment_method: Optional[str] = None
    line_items: list[LineItem] = Field(default_factory=list)
    category: str = FALLBACK_CATEGORY
    category_reason: str = ""
    confidence: float = 0.5

    @field_validator("category", mode="before")
    @classmethod
    def _known_category(cls, v: object) -> str:
        if isinstance(v, str):
            for c in CATEGORIES:
                if c.lower() == v.strip().lower():
                    return c
        return FALLBACK_CATEGORY

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp(cls, v: object) -> float:
        try:
            return max(0.0, min(1.0, float(v)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.5

    @field_validator("currency", mode="before")
    @classmethod
    def _currency(cls, v: object) -> str:
        return v.strip().upper()[:3] if isinstance(v, str) and v.strip() else "USD"

    @field_validator("merchant", "category_reason", "payment_method", mode="before")
    @classmethod
    def _plain_punctuation(cls, v: object) -> object:
        # Model-written text is shown on the site, which never uses em or en dashes.
        if not isinstance(v, str):
            return v
        v = re.sub(r"(\d)\s*–\s*(\d)", r"\1-\2", v)  # number ranges: 3–5 -> 3-5
        v = re.sub(r"\s*[—–]\s*", ", ", v)      # clause breaks -> comma
        return re.sub(r"^[,\s]+|[,\s]+$", "", v)

    @field_validator("date", mode="before")
    @classmethod
    def _iso_date(cls, v: object) -> Optional[str]:
        import re

        if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.strip()):
            return v.strip()
        return None


def deductible_estimate(receipt: Receipt) -> Optional[float]:
    if receipt.total is None:
        return None
    return round(receipt.total * DEDUCTIBLE_RATE.get(receipt.category, 1.0), 2)
