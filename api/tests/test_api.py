from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.extract import ExtractionError, extract_receipt
from app.main import create_app
from app.schemas import Receipt, deductible_estimate

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100

SAMPLE = {
    "is_receipt": True,
    "merchant": "Corner Grind Coffee",
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


@pytest.mark.parametrize("raw,clean", [
    ("Coffee shop \u2014 likely a client meeting.", "Coffee shop, likely a client meeting."),
    ("Airfare\u2014business trip", "Airfare, business trip"),
    ("Lunch \u2013 client", "Lunch, client"),
    ("Pages 3\u20135 are fuel", "Pages 3-5 are fuel"),
    ("\u2014 leading dash", "leading dash"),
    ("No dashes here.", "No dashes here."),
])
def test_model_text_has_no_em_or_en_dashes(raw, clean):
    r = Receipt.model_validate({**SAMPLE, "category_reason": raw, "merchant": raw})
    assert r.category_reason == clean and r.merchant == clean


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
    assert r.merchant == "Corner Grind Coffee" and r.category == "Meals"
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


def test_sample_parses_do_not_count_as_users(client):
    upload(client, cid="real")
    for sid in ("coffee", "office"):
        r = client.post("/api/parse", files={"file": ("s.jpg", PNG, "image/jpeg")},
                        headers={"X-Client-Id": "founder", "X-Sample": sid})
        assert r.status_code == 200
    # unknown sample ids are treated as ordinary uploads
    client.post("/api/parse", files={"file": ("s.jpg", PNG, "image/jpeg")},
                headers={"X-Client-Id": "sneaky", "X-Sample": "made-up"})
    client.post("/api/events", json={"event": "correction", "meta": {"item": "s1", "sample": "coffee"}},
                headers={"X-Client-Id": "founder"})
    s = client.get("/api/stats", headers={"Authorization": "Bearer test-token"}).json()
    assert s["users"] == 2 and s["receipts_parsed"] == 2
    assert s["sample_users"] == 1 and s["sample_parses"] == 2
    assert s["categories_corrected"] == 0


def test_demo_mode_returns_sample_ground_truth(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    c = TestClient(create_app(db_path=str(tmp_path / "d.db")))
    r = c.post("/api/parse", files={"file": ("s.pdf", b"%PDF-1.4", "application/pdf")},
               headers={"X-Client-Id": "x", "X-Sample": "invoice"}).json()
    assert r["receipt"]["merchant"] == "Fieldnote Software, Inc."
    assert r["receipt"]["total"] == 24.0 and r["schedule_c_line"] == "Line 27b (Part V)"


def test_delete_my_data(client):
    upload(client, cid="a")
    upload(client, cid="b")
    client.post("/api/events", json={"event": "feedback", "meta": {"text": "hi"}}, headers={"X-Client-Id": "a"})
    assert client.post("/api/delete-my-data").status_code == 400
    assert client.post("/api/delete-my-data", headers={"X-Client-Id": "a"}).json() == {"deleted": 2}
    s = client.get("/api/stats", headers={"Authorization": "Bearer test-token"}).json()
    assert s["users"] == 1 and s["feedback"] == []
