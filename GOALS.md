# Industrial sonar sales copilot

Help a distributor sales rep turn two sonar datasheets and a natural-language customer request into a grounded comparison and a copyable email draft.

## MVP workflow

Upload two English, text-based PDFs with one product per PDF. Review and correct the model, maximum operating depth, detection range, operating frequency, beam width, and price with currency. Show a one-based page and excerpt per extracted field, label human corrections, and leave missing or ambiguous values unknown.

Parse the customer request and let the rep confirm its mandatory and preferred requirements. Compare reviewed values against inclusive thresholds in normalized units. Show Meets, Does not meet, or Unknown per requirement. Recommend a product only when it meets every mandatory requirement. Keep other products visible and allow a follow-up draft that names their gaps.

For the selected product, use one model task to produce the contextual explanation and personalized draft. Validate field references and insert reviewed facts and deterministic fit statements on the backend. The rep can edit and copy the result.

## Boundaries

Run locally with React/Vite, FastAPI, the official OpenAI SDK and Responses API, PyMuPDF, Pydantic, and Pytest. Keep session data in memory. The backend sends approved PDF text and relevant customer context to OpenAI.

OCR, broad PDF layout coverage, vector databases, LangChain, multi-agent orchestration, authentication, payments, actual email sending, hosting, and durable persistence are out of scope.
