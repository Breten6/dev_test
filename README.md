# Sonar Sales Copilot

A local MVP for industrial sonar distributors. Review datasheet specifications, compare them with a customer inquiry, and generate a customer-facing email draft.

## Setup

Use Python 3.11 or newer and a Node.js release supported by Vite 7 (Node 20.19+ or 22.12+ in the respective LTS lines). From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
```

Export `OPENAI_API_KEY` and `OPENAI_MODEL` in the shell that starts FastAPI. Use a Responses API model that supports structured outputs. To confirm the environment and model connection:

```bash
.venv/bin/python -m backend.verify_openai
```

Start FastAPI and Vite in separate terminals:

```bash
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```bash
npm --prefix frontend run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Run the checks from the repository root:

```bash
.venv/bin/python -m pytest -q
npm --prefix frontend run build
```

## Demo

1. Upload `fixtures/sf-100.pdf` and `fixtures/sf-080.pdf` individually. Inspect each page excerpt. SF-100 has a 100 m operating depth, 50 m detection range, and 2,400 USD price. SF-080 has an 80 m operating depth and its range and price are unknown.
2. Change SF-100's detection range to 55 m to demonstrate manual correction. Save the reviewed specs for both products. The original source still shows 50 m for SF-100.
3. Enter this inquiry and select **Extract requirements**.

   > We need a sonar rated for operation at 100 m depth and capable of detecting targets at least 50 m away. The budget cap is 2500 USD.

4. Confirm the thresholds and select **Compare reviewed products**. SF-100 matches all three requirements. SF-080 mismatches depth and shows unknown range and price.
5. Select a product and select **Generate explanation and email**. Try SF-080 to see a follow-up draft that states the mismatch and asks for clarification. Review the draft, then select **Copy email**.
6. Change a product spec, a structured requirement, or the original inquiry to see the comparison and draft clear.

## Architecture

React and Vite run one local page. The Vite proxy forwards `/api` requests to a single FastAPI process. PyMuPDF reads the text of uploaded PDFs. The official OpenAI SDK and Pydantic structured outputs handle extraction, inquiry interpretation, and the combined explanation and draft plan. OpenAI calls have an explicit deadline and at most one SDK retry.

Product extraction checks page evidence against recognized field/value lines. The rep confirms both product data and inquiry criteria before Python compares normalized values. Comparison uses saved product values and retains their provenance. The draft model receives field names, status, priority, and eligibility. The backend renders numeric facts, product labels, and compatibility statements from typed reviewed data and fixed wording. The frontend keeps inquiry edits and drafts in the current tab. The backend keeps uploaded product records, saved reviews, and the current comparison in memory.

## Known MVP limitations

- Use one local API process and one browser tab. A backend restart clears all server state. Reloading the page clears the visible session and products must be uploaded again. Tabs share the backend's current comparison.
- PDFs must be unlocked and contain selectable text. Limits are 5 MB, 25 pages, and 50,000 extracted characters. Automatic extraction expects a labeled value on one extracted text line. Tables, split lines, complex formats, and ambiguous values may require manual review.
- The backend sends PDF text and inquiry text to OpenAI. Use approved inputs. Product and inquiry extraction can still misinterpret malicious or inaccurate source text. Check excerpts and confirm requirements before relying on a comparison.
- Matching supports numerical depth, range, frequency, beam width, and same-currency price. Unsupported constraints, strict thresholds, and ambiguous currency references require clarification. A different currency yields **UNKNOWN**.
- The application drafts emails for manual review and copying. It has no delivery, accounts, or persistent storage. Run it on localhost.
