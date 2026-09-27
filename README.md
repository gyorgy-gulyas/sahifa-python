# sahifa

Python client for [Sahifa](https://sahifa.dev/en/), the HTML-to-PDF and screenshot API that gets **Arabic and right-to-left text right** and processes documents **in Saudi Arabia**.

No `arabic_reshaper`, no `python-bidi`, no fonts to install: write HTML, get a PDF with joined Arabic letters, correct word order and mixed Arabic and English, rendered by Chromium in Jeddah.

```
pip install sahifa
```

## Quick start

Get a free API key at [sahifa.dev](https://sahifa.dev/en/account): 100 renders a month, no card needed.

```python
from sahifa import Sahifa, arabic_document

sahifa = Sahifa()  # reads SAHIFA_API_KEY

pdf = sahifa.pdf(
    arabic_document('<h1>فاتورة ضريبية مبسطة</h1><p>الإجمالي: <bdi dir="ltr">1,150.00 SAR</bdi></p>'),
    format="A4",
    margin="15mm",
    footer={"source": '<div style="width:100%;text-align:center;font-size:9px">صفحة {{page}} من {{total}}</div>'},
)
with open("invoice.pdf", "wb") as f:
    f.write(pdf)
```

## PDF

`sahifa.pdf(source, **options)` calls `POST /v3/convert/pdf` (PDFShift v3 compatible) and returns `bytes`. `source` is HTML or a URL.

Options: `format`, `landscape`, `margin`, `header={"source": ...}`, `footer={"source": ...}`, `css`, `javascript`, `delay` (milliseconds), `wait_for`, `pages`, `zoom`. See the [PDF reference](https://sahifa.dev/en/docs/pdf).

### Django

```python
from django.http import HttpResponse
from django.template.loader import render_to_string
from sahifa import Sahifa

sahifa = Sahifa()

def invoice_pdf(request, pk):
    html = render_to_string("invoices/detail.html", {"invoice": Invoice.objects.get(pk=pk)})
    return HttpResponse(sahifa.pdf(html, format="A4"), content_type="application/pdf")
```

### FastAPI

```python
from fastapi import FastAPI, Response
from sahifa import Sahifa

app, sahifa = FastAPI(), Sahifa()

@app.get("/invoices/{number}.pdf")
def invoice(number: str):
    html = templates.get_template("invoice.html").render(number=number)
    return Response(sahifa.pdf(html), media_type="application/pdf")
```

## Screenshots

```python
png = sahifa.screenshot(url="https://example.com", full_page=True, block_cookie_banners=True)
jpg = sahifa.screenshot(html="<h1 dir='rtl'>مرحبا</h1>", format="jpeg")
```

Pass exactly one of `url=` or `html=`. Options: `format` (png, jpeg, webp, pdf), `full_page`, `viewport_width`, `viewport_height`, `device_scale_factor`, `selector`, `dark_mode`, `delay` (seconds), `block_ads`, `block_cookie_banners`. See the [screenshot reference](https://sahifa.dev/en/docs/screenshot).

## Errors and retries

Failures raise `SahifaError` with `.status`, `.code` and the API's message. Busy and rate-limit responses (429, 502, 503, 504) and network errors are retried up to `max_retries` times (default 3), waiting for `Retry-After`.

```python
from sahifa import SahifaError

try:
    sahifa.pdf(html)
except SahifaError as e:
    if e.status == 402:
        print("Monthly allowance used up")
    else:
        raise
```

## Options

```python
Sahifa(api_key="sk_live_...", base_url="https://api.sahifa.dev", max_retries=3, timeout=120)
```

The client can be used as a context manager (`with Sahifa() as s:`), which closes the HTTP connection pool.

## Arabic tips

- `arabic_document(fragment)` wraps HTML in a full document with `dir="rtl"`, UTF-8 and Arabic fonts.
- Wrap left-to-right parts (IBANs, VAT numbers, amounts, e-mails) in `<bdi dir="ltr">…</bdi>`.
- Use `text-align: start` / `end` rather than `left` / `right`.

## Links

[Documentation](https://sahifa.dev/en/docs) · [Examples in five languages](https://github.com/gyorgy-gulyas/sahifa-examples) · [Pricing](https://sahifa.dev/en/#pricing) · [Data residency](https://sahifa.dev/en/data-residency) · Support: [support@sahifa.dev](mailto:support@sahifa.dev)

MIT License. Sahifa is a service of Yimello LLC.
