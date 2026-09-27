import json

import httpx
import pytest

from sahifa import Sahifa, SahifaError, arabic_document


def fake(responses):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return responses.pop(0)

    return httpx.MockTransport(handler), calls


def test_pdf_posts_source_and_options_with_the_key():
    transport, calls = fake([httpx.Response(200, content=b"%PDF-1.7")])
    s = Sahifa("sk_test", transport=transport)
    assert s.pdf("<h1>فاتورة</h1>", format="A4").startswith(b"%PDF")
    req = calls[0]
    assert str(req.url) == "https://api.sahifa.dev/v3/convert/pdf"
    assert req.headers["x-api-key"] == "sk_test"
    assert json.loads(req.content) == {"format": "A4", "source": "<h1>فاتورة</h1>"}


def test_screenshot_needs_exactly_one_of_url_or_html():
    transport, calls = fake([httpx.Response(200, content=b"png")])
    s = Sahifa("k", transport=transport, base_url="https://example.test/")
    s.screenshot(url="https://example.com", full_page=True)
    assert str(calls[0].url) == "https://example.test/take"
    assert json.loads(calls[0].content) == {"full_page": True, "url": "https://example.com"}
    with pytest.raises(SahifaError):
        s.screenshot()
    with pytest.raises(SahifaError):
        s.screenshot(url="a", html="b")


def test_retries_busy_responses(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    transport, calls = fake([
        httpx.Response(429, json={"error": "busy"}, headers={"retry-after": "1"}),
        httpx.Response(503, json={"error": "down"}),
        httpx.Response(200, content=b"%PDF"),
    ])
    assert Sahifa("k", transport=transport).pdf("x") == b"%PDF"
    assert len(calls) == 3


def test_errors_carry_status_message_and_code_and_400_is_not_retried():
    transport, calls = fake([httpx.Response(402, json={"success": False, "error": "Monthly render allowance used up", "error_code": "quota"})])
    with pytest.raises(SahifaError) as info:
        Sahifa("k", transport=transport).pdf("x")
    assert info.value.status == 402
    assert info.value.code == "quota"
    assert str(info.value) == "Monthly render allowance used up"
    assert len(calls) == 1


def test_key_from_environment_and_helpful_error(monkeypatch):
    monkeypatch.delenv("SAHIFA_API_KEY", raising=False)
    with pytest.raises(SahifaError, match="SAHIFA_API_KEY"):
        Sahifa()
    monkeypatch.setenv("SAHIFA_API_KEY", "from-env")
    s = Sahifa()
    assert "from-env" not in repr(s)


def test_arabic_document():
    doc = arabic_document("<h1>مرحبا</h1>")
    assert '<html dir="rtl" lang="ar">' in doc
    assert "Noto Naskh Arabic" in doc
    assert arabic_document("<html>x</html>") == "<html>x</html>"
