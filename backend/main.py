from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile

from backend.products import (
    Product,
    ProductFields,
    extract_with_openai,
    grounded_fields,
    upload_pages,
)

app = FastAPI(title="Sonar Sales Copilot")
products: dict[str, Product] = {}


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
    # Phase 3 must invalidate dependent snapshots here when reviewed values change.
    updated = product.model_copy(update={"reviewed": fields, "corrected_fields": corrected_fields})
    products[product_id] = updated
    return updated
