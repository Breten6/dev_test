from pathlib import Path
from unittest.mock import AsyncMock

import pymupdf
import pytest
from fastapi.testclient import TestClient
from openai import APIError, APITimeoutError

from backend import main, products

client = TestClient(main.app)
fixtures = Path(__file__).resolve().parents[1] / "fixtures"


def upload(name):
    return client.post("/api/products", files={"file": (name, (fixtures / name).read_bytes(), "application/pdf")})


def quote(literal, excerpt, page=1):
    return {"literal": literal, "evidence": {"page": page, "excerpt": excerpt}}


def extraction(**fields):
    return products.ModelExtraction.model_validate(dict.fromkeys(products.ModelExtraction.model_fields) | fields)


def test_upload_review_and_preserve_sources(monkeypatch):
    output = extraction(
        model=quote("SF-100", "Product model: SF-100"),
        max_operating_depth_m=quote("100 m", "Maximum operating depth: 100 m"),
        detection_range_m=quote("50 m", "Detection range: 50 m"),
        price=quote("2400 USD", "List price: 2400 USD"),
    )
    provider = AsyncMock(return_value=output)
    monkeypatch.setattr(main, "extract_with_openai", provider)
    response = upload("sf-100.pdf")
    assert response.status_code == 201
    product = response.json()
    assert provider.await_args.args[0][0]["page"] == 1
    assert product["reviewed"] is None
    assert product["extracted"]["max_operating_depth_m"] == 100
    assert product["extracted"]["detection_range_m"] == 50
    assert product["extracted"]["price"] == "2400"
    assert product["extracted"]["currency"] == "USD"
    assert product["evidence"]["price"] == {"page": 1, "excerpt": "List price: 2400 USD"}

    review_url = f"/api/products/{product['product_id']}/review"
    review = product["extracted"] | {"detection_range_m": 55}
    response = client.put(review_url, json=review)
    assert response.status_code == 200
    saved = response.json()
    assert saved["reviewed"]["detection_range_m"] == 55
    assert saved["extracted"]["detection_range_m"] == 50
    assert saved["corrected_fields"] == ["detection_range_m"]
    assert saved["evidence"] == product["evidence"]
    assert client.put(review_url, json=review | {"currency": None}).status_code == 422


def test_upload_discards_unsupported_values(monkeypatch):
    monkeypatch.setattr(main, "extract_with_openai", AsyncMock(return_value=extraction(
        model=quote("SF-080", "Product model: SF-080"),
        max_operating_depth_m=quote("80 m", "Maximum operating depth: 80 m", page=2),
        detection_range_m=quote("80 m", "Maximum operating depth: 80 m"),
        price=quote("1500 USD", "List price: 1500 USD"),
    )))
    response = upload("sf-080.pdf")
    assert response.status_code == 201
    product = response.json()
    assert product["extracted"]["model"] == "SF-080"
    assert product["extracted"]["detection_range_m"] is None
    assert product["extracted"]["price"] is None
    assert product["extracted"]["currency"] is None
    assert len(product["warnings"]) == 3


def test_invalid_and_textless_uploads_never_call_model(monkeypatch):
    provider = AsyncMock()
    monkeypatch.setattr(main, "extract_with_openai", provider)
    with pymupdf.open() as pdf:
        pdf.new_page()
        textless = pdf.tobytes()
    for data, message in [(b"wrong", "valid PDF"), (b"%PDF-corrupt", "could not be read"), (textless, "no selectable text")]:
        response = client.post("/api/products", files={"file": ("sample.pdf", data, "application/pdf")})
        assert response.status_code == 422
        assert message in response.json()["detail"]
    provider.assert_not_awaited()


@pytest.mark.parametrize(("error_type", "status"), [(APIError, 503), (APITimeoutError, 504)])
def test_provider_failures_return_safe_messages(monkeypatch, error_type, status):
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    error = error_type("provider-private-message", request=None, body=None) if error_type is APIError else error_type(request=None)

    class Client:
        class responses:
            parse = AsyncMock(side_effect=error)

        def __init__(self, *, timeout, max_retries):
            assert timeout == 20
            assert max_retries == 1

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

    monkeypatch.setattr(products, "AsyncOpenAI", Client)
    response = upload("sf-100.pdf")
    assert response.status_code == status
    assert "provider-private-message" not in response.text
    assert "test-key" not in response.text
