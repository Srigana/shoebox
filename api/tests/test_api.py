from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.extract import ExtractionError, extract_receipt
from app.main import create_app
from app.schemas import Receipt, deductible_estimate

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100

SAMPLE = {
    "is_receipt": True,
    "merchant": "Blue Bottle Coffee",
    "date": "2026-10-20",
    "currency": "usd",
    "subtotal": 18.0,
    "tax": 1.62,
    "tip": 3.0,
    "total": 22.62,
    "payment_method": "Visa ••4242",
    "line_items": [{"description": "Latte", "amount": 6.0}],
    "category": "meals",
    "category_reason": "Coffee shop purchase.",
    "confidence": 0.93,
}


def fake_extractor(data: bytes, media_type: str) -> Receipt:
    return Receipt.model_validate(SAMPLE)


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(extractor=fake_extractor, db_path=str(tmp_path / "t.db")))


def upload(client, data=PNG, ctype="image/png", cid="user-1"):
    return client.post("/api/parse", files={"file": ("r.png", data, ctype)}, headers={"X-Client-Id": cid})


# --- schema ---------------------------------------------------------------

def test_receipt_normalizes_fields():
    r = Receipt.model_validate({**SAMPLE, "category": "Crypto mining", "confidence": 4, "date": "10/20/26"})
    assert r.category == "Other expenses"
    assert r.confidence == 1.0
    assert r.date is None
    assert Receipt.model_validate(SAMPLE).currency == "USD"


def test_meals_are_half_deductible():
    assert deductible_estimate(Receipt.model_validate(SAMPLE)) == 11.31
    assert deductible_estimate(Receipt.model_validate({**SAMPLE, "category": "Travel"})) == 22.62


# --- extractor with a fake Anthropic client ---------------------------------

class FakeMessages:
    def __init__(self, content):
        self.content, self.calls = content, []

    def create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(content=self.content)


def test_extract_forces_tool_and_sends_image():
    msgs = FakeMessages([SimpleNamespace(type="tool_use", input=SAMPLE)])
    r = extract_receipt(PNG, "image/png", client=SimpleNamespace(messages=msgs))
    assert r.merchant == "Blue Bottle Coffee" and r.category == "Meals"
    call = msgs.calls[0]
    assert call["tool_choice"] == {"type": "tool", "name": "record_receipt"}
    assert call["messages"][0]["content"][0]["type"] == "image"


def test_extract_pdf_uses_document_block():
    msgs = FakeMessages([SimpleNamespace(type="tool_use", input=SAMPLE)])
    extract_receipt(b"%PDF-1.4", "application/pdf", client=SimpleNamespace(messages=msgs))
    assert msgs.calls[0]["messages"][0]["content"][0]["type"] == "document"


def test_extract_without_tool_use_raises():
    msgs = FakeMessages([SimpleNamespace(type="text", text="hmm")])
    with pytest.raises(ExtractionError):
        extract_receipt(PNG, "image/png", client=SimpleNamespace(messages=msgs))


# --- HTTP ------------------------------------------------------------------

def test_parse_happy_path(client):
    res = upload(client)
    assert res.status_code == 200
    body = res.json()
    assert body["receipt"]["category"] == "Meals"
    assert body["schedule_c_line"] == "Line 24b"
    assert body["deductible_estimate"] == 11.31


def test_rejects_bad_type_and_empty(client):
    assert upload(client, ctype="text/plain").status_code == 415
    assert upload(client, data=b"").status_code == 400


def test_rejects_oversize(client):
    assert upload(client, data=b"0" * (6 * 1024 * 1024 + 10)).status_code == 413


def test_rate_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "2")
    c = TestClient(create_app(extractor=fake_extractor, db_path=str(tmp_path / "r.db")))
    assert [upload(c).status_code for _ in range(3)] == [200, 200, 429]
    assert upload(c, cid="someone-else").status_code == 200


def test_extraction_failure_is_502(tmp_path):
    def boom(data, mt):
        raise ExtractionError("nope")

    c = TestClient(create_app(extractor=boom, db_path=str(tmp_path / "e.db")))
    assert upload(c).status_code == 502


def test_events_and_stats(client):
    upload(client, cid="a")
    upload(client, cid="a")
    upload(client, cid="b")
    client.post("/api/events", json={"event": "visit"}, headers={"X-Client-Id": "c"})
    client.post("/api/events", json={"event": "correction", "meta": {"item": "x1"}}, headers={"X-Client-Id": "a"})
    client.post("/api/events", json={"event": "correction", "meta": {"item": "x1"}}, headers={"X-Client-Id": "a"})
    client.post("/api/events", json={"event": "feedback", "meta": {"text": "love it"}}, headers={"X-Client-Id": "b"})
    assert client.post("/api/events", json={"event": "parse"}).status_code == 400

    assert client.get("/api/stats").status_code == 401
    assert client.get("/api/stats", headers={"Authorization": "Bearer wrong"}).status_code == 401
    s = client.get("/api/stats", headers={"Authorization": "Bearer test-token"}).json()
    assert s["visitors"] == 3
    assert s["users"] == 2
    assert s["receipts_parsed"] == 3
    assert s["categories_corrected"] == 1
    assert s["category_acceptance_rate"] == round(2 / 3, 3)
    assert s["feedback"][0]["text"] == "love it"
