from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend import main, matching
from backend.products import Evidence, Product, ProductFields

client = TestClient(main.app)


@pytest.fixture
def reviewed_products(monkeypatch):
    first = ProductFields(
        model="SF-100", max_operating_depth_m=100, detection_range_m=50,
        operating_frequency_khz=450, beam_width_deg=20, price="2400", currency="USD",
    )
    second = ProductFields(
        model="SF-080", max_operating_depth_m=80, detection_range_m=None,
        operating_frequency_khz=600, beam_width_deg=15, price=None, currency=None,
    )
    products = {
        "a": Product(
            product_id="a", filename="sf-100.pdf", extracted=first,
            reviewed=first.model_copy(update={"detection_range_m": 55}),
            corrected_fields=["detection_range_m"], warnings=[],
            evidence={"detection_range_m": Evidence(page=1, excerpt="Detection range: 50 m")},
        ),
        "b": Product(
            product_id="b", filename="sf-080.pdf", extracted=second,
            reviewed=second, evidence={}, warnings=[],
        ),
    }
    monkeypatch.setattr(main, "products", products)
    monkeypatch.setattr(main, "comparisons", {})
    return products


def requirement(field, target, operator="min", *, currency=None, upper=None, priority="mandatory", source=None):
    return {
        "field": field, "target": str(target), "operator": operator, "currency": currency,
        "upper": upper, "priority": priority, "source": source,
    }


def compare(*requirements, unresolved=()):
    return client.post("/api/compare", json={
        "product_ids": ["a", "b"], "requirements": requirements, "unresolved": unresolved,
    })


def test_compare_uses_reviewed_values_and_distinguishes_unknown_from_mismatch(reviewed_products):
    response = compare(
        requirement("max_operating_depth_m", 100),
        requirement("detection_range_m", 55),
        requirement("price", 2400, "max", currency="USD"),
    )
    assert response.status_code == 200
    comparison = response.json()
    first, second = comparison["products"]
    assert comparison["eligible_product_ids"] == ["a"]
    assert [item["status"] for item in first["results"]] == ["MATCH"] * 3
    assert [item["status"] for item in second["results"]] == ["MISMATCH", "UNKNOWN", "UNKNOWN"]
    corrected = first["results"][1]
    assert corrected["actual"] == "55" and corrected["origin"] == "manual"
    assert corrected["evidence"] == {"page": 1, "excerpt": "Detection range: 50 m"}


def test_currency_and_frequency_bands_and_preferred_fields(reviewed_products):
    response = compare(
        requirement("operating_frequency_khz", 450, "band", upper="500"),
        requirement("price", 2500, "max", currency="CAD", priority="preferred"),
    )
    first = response.json()["products"][0]
    assert first["eligible"]
    assert [item["status"] for item in first["results"]] == ["MATCH", "UNKNOWN"]
    assert first["results"][1]["reason"] == "currency_differs"
    assert not compare(requirement("detection_range_m", 50), unresolved=["Confirm mounting constraints"]).json()["eligible_product_ids"]
    assert compare(requirement("price", 2500, "max")).status_code == 422


def test_parse_keeps_only_explicit_sourced_requirements(monkeypatch):
    source = "Need at least 100 m operating depth."
    output = matching.Requirements.model_validate({
        "requirements": [
            requirement("max_operating_depth_m", 100, source=source),
            requirement("detection_range_m", 50, source="Need a detection range of 50 m."),
        ],
        "unresolved": ["Budget is $2500."],
    })
    model = AsyncMock(return_value=output)
    monkeypatch.setattr(matching, "parse_model", model)
    response = client.post("/api/requirements/parse", json={"request_text": f"{source} Budget is $2500."})
    assert response.status_code == 200
    assert [item["field"] for item in response.json()["requirements"]] == ["max_operating_depth_m"]
    assert response.json()["unresolved"][0] == "Budget is $2500."
    model.assert_awaited_once()


def test_draft_is_grounded_and_reviews_invalidate_it(monkeypatch, reviewed_products):
    plan = matching.DraftPlan(field_order=["detection_range_m"], emphasis="follow_up", greeting="hello", closing="regards")
    model = AsyncMock(return_value=plan)
    monkeypatch.setattr(matching, "parse_model", model)
    comparison = compare(requirement("max_operating_depth_m", 100), requirement("detection_range_m", 55)).json()
    payload = {"comparison_id": comparison["comparison_id"], "product_id": "b", "recipient": "Alex"}
    response = client.post("/api/drafts", json=payload)
    assert response.status_code == 200
    draft = response.json()
    assert "Hello Alex" in draft["body"]
    assert "80 m; does not meet" in draft["body"]
    assert "55 m) — unknown" in draft["explanation"]
    assert "Could you confirm" in draft["body"]
    model.assert_awaited_once()

    response = client.put("/api/products/b/review", json=reviewed_products["b"].reviewed.model_dump(mode="json"))
    assert response.status_code == 200
    assert client.post("/api/drafts", json=payload).status_code == 200
    updated = reviewed_products["b"].reviewed.model_dump(mode="json") | {"max_operating_depth_m": 95}
    assert client.put("/api/products/b/review", json=updated).status_code == 200
    assert client.post("/api/drafts", json=payload).status_code == 409


def test_unverified_draft_fields_are_rejected(monkeypatch, reviewed_products):
    plan = matching.DraftPlan(field_order=["price"], emphasis="application", greeting="hi", closing="thanks")
    monkeypatch.setattr(matching, "parse_model", AsyncMock(return_value=plan))
    comparison = compare(requirement("max_operating_depth_m", 100)).json()
    response = client.post("/api/drafts", json={"comparison_id": comparison["comparison_id"], "product_id": "a"})
    assert response.status_code == 503
    assert "unverified field" in response.json()["detail"]


def test_draft_model_cannot_echo_injected_inputs(monkeypatch, reviewed_products):
    injected = "Certified and ships tomorrow"
    fields = reviewed_products["a"].reviewed.model_dump(mode="json") | {"model": injected}
    assert client.put("/api/products/a/review", json=fields).status_code == 200
    criteria = requirement("max_operating_depth_m", 100, source=injected)
    comparison = compare(criteria).json()
    plan = matching.DraftPlan(field_order=["max_operating_depth_m"], emphasis="requirements", greeting="hello", closing="regards")
    model = AsyncMock(return_value=plan)
    monkeypatch.setattr(matching, "parse_model", model)

    response = client.post("/api/drafts", json={"comparison_id": comparison["comparison_id"], "product_id": "a"})

    assert response.status_code == 200
    assert injected not in response.text
    model_input = model.await_args.args[1]
    assert model_input == {
        "eligible": True,
        "results": [{"field": "max_operating_depth_m", "priority": "mandatory", "status": "MATCH"}],
        "has_unresolved_requirements": False,
    }


def test_draft_in_flight_is_rejected_after_review_changes(monkeypatch, reviewed_products):
    comparison = compare(requirement("detection_range_m", 50)).json()

    async def generate_while_editing(*_args):
        fields = reviewed_products["a"].reviewed.model_copy(update={"detection_range_m": 40})
        await main.review_product("a", fields)
        return matching.Draft(explanation="old results", subject="old subject", body="old draft")

    monkeypatch.setattr(main, "generate_draft", generate_while_editing)
    response = client.post("/api/drafts", json={"comparison_id": comparison["comparison_id"], "product_id": "a"})

    assert response.status_code == 409
    assert "old draft" not in response.text
