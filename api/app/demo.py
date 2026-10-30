"""DEMO_MODE=1: canned results so the UI can be developed without an API key or spend.

Any upload gets one of the sample receipts' contents (picked by file hash, so
the same file always gets the same result).
"""
from __future__ import annotations

import hashlib

from .samples import EXPECTED, SAMPLE_IDS
from .schemas import Receipt


def demo_extractor(data: bytes, media_type: str) -> Receipt:
    return EXPECTED[SAMPLE_IDS[int(hashlib.md5(data).hexdigest(), 16) % len(SAMPLE_IDS)]]
