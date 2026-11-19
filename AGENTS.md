# Working in this repository

Work one approved phase at a time. See GOALS.md for product boundaries and PLANS.md for API contracts and acceptance criteria.

## Run locally

- Create a Python environment with `python3 -m venv .venv`, then run `.venv/bin/python -m pip install -r backend/requirements.txt`.
- Run `npm --prefix frontend ci`.
- Start the API with `.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`.
- Start the frontend with `npm --prefix frontend run dev` and open http://127.0.0.1:5173.
- Check model connectivity from a shell with `OPENAI_API_KEY` and `OPENAI_MODEL` exported using `.venv/bin/python -m backend.verify_openai`.
- Run `npm --prefix frontend run build` and, once tests exist, `.venv/bin/python -m pytest`.

## Implementation rules

Keep model calls in Python using the official SDK and Responses API. Read configuration from the environment. Keep credentials and raw provider errors out of logs and browser responses. Use structured outputs, explicit timeouts, and at most one transient retry under a total deadline. Use stubbed model calls in Pytest.

Process approved PDFs with PyMuPDF. Preserve source evidence and unknown values, and distinguish operating depth from detection range. Require explicit review before comparison or generation. Keep comparison rules and eligibility deterministic. Use simple product field references and server-rendered claims in the combined explanation and draft call. Clear comparisons and drafts when reviewed product data changes.
