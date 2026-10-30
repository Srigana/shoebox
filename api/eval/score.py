"""Field comparison rules. Kept deliberately simple so they're easy to defend in a review.

- total:    within one cent of the label.
- date:     same calendar day. Labels may be ISO (YYYY-MM-DD) or numeric dates.
- merchant: same after normalizing case, punctuation and legal suffixes, or a
            character-level similarity of at least 0.85 (tolerates OCR noise in
            labels like "BOOK TA .K" vs "BOOK TA.K").
- category: exact match against one of the 17 Schedule C categories.
"""
from __future__ import annotations

import math
import re
from datetime import date
from difflib import SequenceMatcher
from typing import Optional

FIELDS = ("merchant", "date", "total", "category")
MERCHANT_SIMILARITY = 0.85

_SUFFIXES = {
    "inc", "incorporated", "llc", "ltd", "limited", "co", "corp", "corporation", "company",
    "plc", "sdn", "bhd", "pte", "the", "enterprise", "enterprises",
}
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def normalize_merchant(s: Optional[str]) -> str:
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    words = [w for w in s.split() if w not in _SUFFIXES]
    return " ".join(words)


def merchant_match(pred: Optional[str], gold: Optional[str]) -> bool:
    p, g = normalize_merchant(pred), normalize_merchant(gold)
    if not p or not g:
        return False
    if p == g:
        return True
    return SequenceMatcher(None, p.replace(" ", ""), g.replace(" ", "")).ratio() >= MERCHANT_SIMILARITY


def _year(y: int) -> int:
    return 2000 + y if y < 100 else y


def parse_date(s: Optional[str], dayfirst: bool = False) -> Optional[date]:
    """Parse the date formats found on receipts. Returns None when unparseable."""
    if not s:
        return None
    t = s.strip().lower()
    try:
        m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t)
        if m:
            return date(int(m[1]), int(m[2]), int(m[3]))
        m = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})\b", t)
        if m:
            a, b, y = int(m[1]), int(m[2]), _year(int(m[3]))
            d, mo = (a, b) if dayfirst else (b, a)
            if mo > 12 and d <= 12:  # unambiguous: the other order is the only valid one
                d, mo = mo, d
            return date(y, mo, d)
        m = re.search(r"\b(\d{1,2})[\s\-/.]*([a-z]{3})[a-z]*[\s\-/.,]*(\d{2,4})\b", t)  # 02 Jan 2018, 02-JAN-18, 02/JAN/2017
        if m and m[2] in _MONTHS:
            return date(_year(int(m[3])), _MONTHS[m[2]], int(m[1]))
        m = re.search(r"\b([a-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{2,4})\b", t)  # Jan 2, 2018
        if m and m[1] in _MONTHS:
            return date(_year(int(m[3])), _MONTHS[m[1]], int(m[2]))
    except ValueError:
        return None
    return None


def date_match(pred: Optional[str], gold: Optional[str]) -> bool:
    g = parse_date(gold)
    return g is not None and parse_date(pred) == g


def parse_amount(v: object) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^0-9.\-]", "", str(v).replace(",", ""))
    try:
        return float(s) if s not in ("", ".", "-") else None
    except ValueError:
        return None


def total_match(pred: object, gold: object) -> bool:
    p, g = parse_amount(pred), parse_amount(gold)
    return p is not None and g is not None and abs(p - g) <= 0.01 + 1e-9


def category_match(pred: Optional[str], gold: Optional[str]) -> bool:
    return bool(pred) and bool(gold) and pred.strip().lower() == gold.strip().lower()  # type: ignore[union-attr]


MATCHERS = {"merchant": merchant_match, "date": date_match, "total": total_match, "category": category_match}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes out of n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))
