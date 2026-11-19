from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile

from backend.matching import (
    CompareRequest, Comparison, Draft, DraftRequest, Inquiry, Requirements,
    compare_product, generate_draft, parse_requirements,
)
from backend.products import (
    Product,
    ProductFields,
    extract_with_openai,
    grounded_fields,
    upload_pages,
)

app = FastAPI(title="Sonar Sales Copilot")
products: dict[str, Product] = {}
comparisons: dict[str, Comparison] = {}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/products", status_code=201)
async def upload_product(file: UploadFile) -> Product:
    pages = await upload_pages(file)
    output = await extract_with_openai(pages)
    extracted, evidence, warnings = grounded_fields(output, pages)
    product = Product(
        product_id=str(uuid4()),
        filename=file.filename or "Datasheet",
        extracted=extracted,
        evidence=evidence,
        warnings=warnings,
    )
    products[product.product_id] = product
    return product


@app.put("/api/products/{product_id}/review")
async def review_product(product_id: str, fields: ProductFields) -> Product:
    product = products.get(product_id)
    if product is None:
        raise HTTPException(404, "This product is no longer available. Upload the PDF again.")

    corrected_fields = [
        name for name in ProductFields.model_fields
        if getattr(fields, name) != getattr(product.extracted, name)
    ]
    if fields != product.reviewed:
        stale = [
            key for key, comparison in comparisons.items()
            if any(item.product_id == product_id for item in comparison.products)
        ]
        for key in stale:
            del comparisons[key]
    updated = product.model_copy(update={"reviewed": fields, "corrected_fields": corrected_fields})
    products[product_id] = updated
    return updated


@app.post("/api/requirements/parse")
async def parse_inquiry(inquiry: Inquiry) -> Requirements:
    return await parse_requirements(inquiry)


@app.post("/api/compare")
async def compare_products(request: CompareRequest) -> Comparison:
    if not request.requirements and not request.unresolved:
        raise HTTPException(422, "Confirm at least one requirement or an item to clarify.")
    matches = []
    for product_id in dict.fromkeys(request.product_ids):
        product = products.get(product_id)
        if product is None or product.reviewed is None:
            raise HTTPException(422, "Review every selected product before comparing.")
        matches.append(compare_product(product, request))

    # Only the current comparison is needed in this single-user MVP.
    comparison = Comparison(
        comparison_id=str(uuid4()), products=matches, unresolved=request.unresolved,
        eligible_product_ids=[item.product_id for item in matches if item.eligible],
    )
    comparisons.clear()
    comparisons[comparison.comparison_id] = comparison
    return comparison


@app.post("/api/drafts")
async def draft_email(request: DraftRequest) -> Draft:
    comparison = comparisons.get(request.comparison_id)
    if comparison is None:
        raise HTTPException(409, "This comparison has changed. Compare the products again.")
    selected = next((item for item in comparison.products if item.product_id == request.product_id), None)
    if selected is None:
        raise HTTPException(422, "Choose a product from the current comparison.")
    draft = await generate_draft(selected, comparison, request.recipient)
    if comparisons.get(request.comparison_id) is not comparison:
        raise HTTPException(409, "This comparison changed while generating the draft. Compare again.")
    return draft
