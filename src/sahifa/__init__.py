"""Sahifa API client: Arabic-ready HTML to PDF and screenshots, rendered in Saudi Arabia.

Docs: https://sahifa.dev/en/docs
"""

from __future__ import annotations

import html as _html
import os
import re
import time
from typing import Any, Optional

import httpx

__all__ = ["Sahifa", "SahifaError", "arabic_document", "__version__"]
__version__ = "1.0.0"

_DEFAULT_BASE_URL = "https://api.sahifa.dev"
_RETRYABLE = {429, 502, 503, 504}


class SahifaError(Exception):
    """An error from the Sahifa API (or the network)."""

    def __init__(self, message: str, status: Optional[int] = None, code: Optional[str] = None,
                 retry_after: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.retry_after = retry_after


class Sahifa:
    """Client for the two Sahifa endpoints.

    >>> sahifa = Sahifa()  # reads SAHIFA_API_KEY
    >>> pdf = sahifa.pdf("<h1>فاتورة</h1>", format="A4")
    """

    def __init__(self, api_key: Optional[str] = None, *, base_url: str = _DEFAULT_BASE_URL,
                 max_retries: int = 3, timeout: float = 120.0,
                 transport: Optional[httpx.BaseTransport] = None) -> None:
        key = api_key or os.environ.get("SAHIFA_API_KEY")
        if not key:
            raise SahifaError("No API key: pass api_key or set SAHIFA_API_KEY. "
                              "Get a free key at https://sahifa.dev/en/account")
        self._key = key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self._client = httpx.Client(timeout=timeout, transport=transport,
                                    headers={"User-Agent": f"sahifa-python/{__version__}"})

    def __repr__(self) -> str:  # never show the key
        return f"Sahifa(base_url={self.base_url!r})"

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Sahifa":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def pdf(self, source: str, **options: Any) -> bytes:
        """HTML or a URL to PDF (POST /v3/convert/pdf, PDFShift v3 compatible). Returns the PDF bytes.

        Options: format, landscape, margin, header={"source": ...}, footer={"source": ...},
        css, javascript, delay (ms), wait_for, pages, zoom. See https://sahifa.dev/en/docs/pdf
        """
        if not source or not source.strip():
            raise SahifaError("pdf(): the HTML or URL is empty")
        return self._send("/v3/convert/pdf", {**options, "source": source})

    def screenshot(self, *, url: Optional[str] = None, html: Optional[str] = None, **options: Any) -> bytes:
        """Screenshot of a URL or of HTML (POST /take, ScreenshotOne compatible). Returns the image bytes.

        Options: format (png, jpeg, webp, pdf), full_page, viewport_width, viewport_height,
        device_scale_factor, selector, dark_mode, delay (seconds), block_ads, block_cookie_banners.
        """
        if bool(url) == bool(html):
            raise SahifaError("screenshot(): pass exactly one of url= or html=")
        body = {**options, ("url" if url else "html"): url or html}
        return self._send("/take", body)

    def _send(self, path: str, body: dict) -> bytes:
        headers = {"X-API-Key": self._key, "X-Access-Key": self._key}
        attempt = 0
        while True:
            try:
                res = self._client.post(self.base_url + path, json=body, headers=headers)
            except httpx.TransportError as exc:
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    attempt += 1
                    continue
                raise SahifaError(f"Network error: {exc}", code="network") from exc

            if res.is_success:
                return res.content
            retry_after = int(res.headers["retry-after"]) if res.headers.get("retry-after", "").isdigit() else None
            if res.status_code in _RETRYABLE and attempt < self.max_retries:
                time.sleep(min(60, retry_after if retry_after is not None else 2 ** attempt))
                attempt += 1
                continue
            try:
                detail = res.json()
            except ValueError:
                detail = {}
            raise SahifaError(detail.get("error") or f"HTTP {res.status_code}", status=res.status_code,
                              code=detail.get("error_code"), retry_after=retry_after)


def arabic_document(body: str, lang: str = "ar", css: str = "") -> str:
    """Wraps an HTML fragment in a right-to-left Arabic document with Arabic fonts.

    A full document (starting with <html or <!doctype) is returned unchanged.
    """
    if re.match(r"^\s*(<!doctype|<html)", body, re.I):
        return body
    return (f'<!doctype html><html dir="rtl" lang="{_html.escape(lang)}"><head><meta charset="utf-8">'
            "<style>body{font-family:'Noto Naskh Arabic','Amiri','Noto Sans Arabic',serif;line-height:1.6}"
            f".num{{font-variant-numeric:tabular-nums}}{css}</style></head><body>{body}</body></html>")
