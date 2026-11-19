# Implementation plan

| Time | Phase | Acceptance criteria |
| --- | --- | --- |
| 0–7 min | Scaffold and verify | React/Vite and FastAPI start. The frontend reaches the API through the Vite proxy. Backend configuration is read without exposing credentials. A minimal live Responses API call succeeds. Two synthetic PDFs are available. |
| 7–22 min | Extract and review | Both PDFs produce editable specs with verified page excerpts. Depth and range stay distinct; missing price remains unknown. Corrections save to the reviewed snapshot. A textless PDF yields a clear error. |
| 22–37 min | Parse and compare | Plain-language depth and range become independent, editable requirements. Inclusive boundaries pass and unknown mandatory values exclude a product from eligibility. Reviewed edits clear dependent comparisons and drafts. |
| 37–50 min | Explain and draft | One model call produces a contextual explanation and editable, copyable subject and body for the selected product. Follow-up drafts identify gaps. Invalid or unknown field references cannot become verified claims. |
| 50–60 min | Test, review, and demonstrate | Run Pytest and the frontend build. Review credentials, timeout handling, and claim validation. Demonstrate upload, correction, comparison, and draft copy in the browser using live calls. Record any verification limits. |

## API contracts

| Route | Input | Success |
| --- | --- | --- |
| GET /api/health | None | Status only, for startup and proxy verification. |
| POST /api/products | One multipart PDF | Product ID, unreviewed specs, per-field evidence, and warnings. |
| PUT /api/products/{product_id}/review | Complete reviewed field set, with nulls for unknowns | Reviewed snapshot retaining original evidence and identifying manual corrections. Changes clear dependent comparisons and draft UI. |
| POST /api/requirements/parse | Customer request text | Typed requirements with field, operator, target or band, units or currency where relevant, priority, and unresolved phrases. |
| POST /api/compare | Reviewed product IDs and confirmed requirements | Comparison ID, statuses by requirement and product, and eligible product IDs. This route is deterministic. |
| POST /api/drafts | Comparison ID, selected product ID, and optional recipient or company context | Explanation, subject, and body from one model task, assembled from validated field references, deterministic fit results, and approved wording. |

Use 422 for invalid inputs, 409 for cleared comparisons that must be rerun, 503 for unavailable or misconfigured model service, and 504 for model timeouts. Use structured outputs where appropriate. Keep reviewed products, comparison snapshots, and any transient state in memory. Clear affected draft text in the UI when reviewed values change.

## Demo inputs and checks

- SF-100 has 100 m maximum operating depth, 50 m detection range, 450 kHz frequency, 20 degrees beam width, and a 2,400 USD list price.
- SF-080 has 80 m maximum operating depth, unknown detection range and price, 600 kHz frequency, and 15 degrees beam width.
- A request for at least 100 m maximum operating depth and 50 m detection range qualifies SF-100 only. SF-080 fails depth and has unknown range.
- Test currency mismatch, missing values, inclusive boundaries, invalid field references, provider failures, and stale state clearing.
- If layout parsing consumes the timebox, focus on the fixture layouts and preserve time for the full demo.
