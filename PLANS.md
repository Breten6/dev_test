# MVP implementation and verification

| Checkpoint | Delivered |
| --- | --- |
| Phase 1 | Git and local React/Vite and FastAPI scaffolding, proxy health check, OpenAI connectivity check, and two synthetic PDF fixtures. Checkpoint `8958676`. |
| Phase 2 | PDF upload, page-indexed extraction, structured specs, source evidence, and saved human review. Checkpoint `50c90df`. |
| Phase 3 | Inquiry extraction and confirmation, deterministic matching, status and provenance display, and stale-result invalidation. The approved Phase 3 scope also included the combined explanation and email draft originally planned as a separate phase. |
| Final verification | Live fixture workflow, browser invalidation checks, backend tests, production build, security review, and documentation. |

## API contracts

| Route | Input | Successful response |
| --- | --- | --- |
| `GET /api/health` | None | Status only. |
| `POST /api/products` | One multipart PDF | Product ID, typed extracted specs, evidence, warnings, and an empty review. |
| `PUT /api/products/{product_id}/review` | Complete reviewed fields, with nulls for unknowns | Saved snapshot, original evidence, and corrected field names. Changed values invalidate any comparison that includes the product. |
| `POST /api/requirements/parse` | Inquiry text | Sourced requirements with field, operator, normalized target or band, priority, and currency where relevant, plus unresolved details. |
| `POST /api/compare` | Reviewed product IDs and confirmed requirements | Current comparison ID, per-requirement `MATCH`, `MISMATCH`, or `UNKNOWN`, evidence and provenance, and eligible product IDs. Comparison is deterministic. |
| `POST /api/drafts` | Current comparison ID, selected product ID, and optional recipient | Compatibility explanation and editable subject and body. One structured model call selects field order and wording options. The backend renders factual statements. |

Validation errors return `422`. A missing product on review returns `404`. A superseded comparison returns `409`, including when it changed during a draft request. Provider failures return sanitized `503` or `504` messages. The frontend aborts outdated requests and drops comparison and draft state on edits. The backend retains one saved comparison per process, so a successful new compare replaces the old one.

## Verification scope

- Compare SF-100 and SF-080 for at least 100 m operating depth, 50 m detection range, and at most 2,500 USD. SF-100 matches all three. SF-080 fails depth and has unknown range and price.
- Verify that manual corrections control matching and preserve the original PDF evidence.
- Verify that product, structured requirement, and inquiry edits clear visible comparisons and drafts.
- Check invalid PDFs, provider failures, currency mismatch, unsupported model references, prompt-injection-shaped inputs, and stale results during draft generation.
- See [README.md](README.md) for commands, the full walkthrough, and operating limits.

## Deferred production work

Session isolation, upload and request quotas, structured PDF table support, stronger evidence verification for generated requirement thresholds, and explicit handling of browser refreshes and unsaved edits across tabs. Broader extraction coverage should be evaluated with representative approved datasheets. See GOALS.md for product boundaries.
