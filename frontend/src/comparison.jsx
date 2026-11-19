import React, { useEffect, useRef, useState } from "react";

const labels = {
  max_operating_depth_m: "Maximum operating depth",
  detection_range_m: "Detection range",
  operating_frequency_khz: "Operating frequency",
  beam_width_deg: "Beam width",
  price: "Price",
};
const units = {
  max_operating_depth_m: "m",
  detection_range_m: "m",
  operating_frequency_khz: "kHz",
  beam_width_deg: "°",
};
const operators = { min: "At least", max: "At most", exact: "Exactly", band: "Between" };

function post(request, url, data, signal) {
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
    signal,
  });
}

function RequirementRow({ item, index, update, remove }) {
  const unit = units[item.field];
  return (
    <fieldset className="requirement">
      <legend>Requirement {index + 1}</legend>
      {item.source && <p className="source">From inquiry · “{item.source}”</p>}
      <div className="fields">
        <label>Product field
          <select value={item.field} onChange={(event) => {
            const field = event.target.value;
            update({ field, currency: field === "price" ? "" : null, target: "", upper: null });
          }}>
            {Object.entries(labels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
        </label>
        <label>Threshold
          <select value={item.operator} onChange={(event) => update({ operator: event.target.value, upper: null })}>
            {Object.entries(operators).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
        </label>
        <label>{item.operator === "band" ? "Lower bound" : "Value"}{unit && ` (${unit})`}
          <input type="number" min="0" step="any" value={item.target} onChange={(event) => update({ target: event.target.value })} />
        </label>
        {item.operator === "band" && (
          <label>Upper bound{unit && ` (${unit})`}
            <input type="number" min="0" step="any" value={item.upper ?? ""} onChange={(event) => update({ upper: event.target.value })} />
          </label>
        )}
        {item.field === "price" && (
          <label>Currency
            <input maxLength={3} placeholder="USD" value={item.currency ?? ""} onChange={(event) => update({ currency: event.target.value.toUpperCase() })} />
          </label>
        )}
        <label>Priority
          <select value={item.priority} onChange={(event) => update({ priority: event.target.value })}>
            <option value="mandatory">Mandatory</option>
            <option value="preferred">Preferred</option>
          </select>
        </label>
      </div>
      <button type="button" className="secondary" onClick={remove}>Remove requirement</button>
    </fieldset>
  );
}

export function CustomerInquiry({ products, dirty, request }) {
  const [inquiry, setInquiry] = useState("");
  const [criteria, setCriteria] = useState(null);
  const [parsing, setParsing] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(null);
  const reviewed = products.filter((product) => product.reviewed);

  function changeInquiry(value) {
    pending.current?.abort();
    setParsing(false);
    setInquiry(value);
    setCriteria(null);
    setError("");
  }

  async function parse(event) {
    event.preventDefault();
    const controller = new AbortController();
    pending.current = controller;
    setCriteria(null);
    setParsing(true);
    setError("");
    try {
      const result = await post(request, "/api/requirements/parse", { request_text: inquiry }, controller.signal);
      if (!controller.signal.aborted) setCriteria(result);
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure.message);
    } finally {
      if (!controller.signal.aborted) setParsing(false);
    }
  }

  function changeRequirement(index, changes) {
    setCriteria({
      ...criteria,
      requirements: criteria.requirements.flatMap((item, position) => (
        position !== index ? [item] : changes ? [{ ...item, ...changes }] : []
      )),
    });
  }

  return (
    <>
      <section className="panel">
        <h2>Customer inquiry</h2>
        <form onSubmit={parse}>
          <label htmlFor="customer-inquiry">Email or technical requirements</label>
          <textarea id="customer-inquiry" rows={5} maxLength={8000} value={inquiry} onChange={(event) => changeInquiry(event.target.value)} />
          <button disabled={parsing || !inquiry.trim()} type="submit">{parsing ? "Extracting requirements…" : "Extract requirements"}</button>
        </form>
        {parsing && <p role="status">Reading the inquiry…</p>}
        {error && <p role="alert">{error}</p>}
      </section>
      {criteria && (
        <section className="panel">
          <h2>Confirm customer requirements</h2>
          <p>Only stated requirements are extracted. Review the thresholds and priorities before comparing.</p>
          {!criteria.requirements.length && <p>No explicit numerical requirements were extracted.</p>}
          {criteria.requirements.map((item, index) => (
            <RequirementRow key={index} item={item} index={index} update={(changes) => changeRequirement(index, changes)} remove={() => changeRequirement(index, null)} />
          ))}
          <button className="secondary" disabled={criteria.requirements.length >= 20} type="button" onClick={() => setCriteria({
            ...criteria,
            requirements: [...criteria.requirements, {
              field: "max_operating_depth_m", operator: "min", target: "", upper: null,
              currency: null, priority: "mandatory", source: null,
            }],
          })}>Add requirement</button>
          {criteria.unresolved.length > 0 && (
            <div className="clarifications">
              <h3>Needs clarification</h3>
              <ul>{criteria.unresolved.map((quote, index) => (
                <li key={index}>
                  {quote}{" "}
                  <button className="secondary" type="button" onClick={() => setCriteria({
                    ...criteria, unresolved: criteria.unresolved.filter((_, position) => position !== index),
                  })}>Mark resolved</button>
                </li>
              ))}</ul>
            </div>
          )}
          {dirty ? <p role="status">Save your product edits before comparing again.</p>
            : !reviewed.length ? <p>Review and save a product before comparing.</p>
            : <ComparisonPanel key={JSON.stringify([criteria, reviewed])} criteria={criteria} reviewed={reviewed} request={request} />}
        </section>
      )}
    </>
  );
}

function ComparisonPanel({ criteria, reviewed, request }) {
  const [comparison, setComparison] = useState(null);
  const [selected, setSelected] = useState("");
  const [recipient, setRecipient] = useState("");
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [copyMessage, setCopyMessage] = useState("");
  const pending = useRef(null);
  useEffect(() => () => pending.current?.abort(), []);

  async function run(task, work) {
    const controller = new AbortController();
    pending.current = controller;
    setBusy(task);
    setError("");
    setDraft(null);
    setCopyMessage("");
    try {
      await work(controller.signal);
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure.message);
    } finally {
      if (!controller.signal.aborted) setBusy("");
    }
  }

  function compare() {
    setComparison(null);
    return run("compare", async (signal) => {
      const data = await post(request, "/api/compare", { ...criteria, product_ids: reviewed.map((product) => product.product_id) }, signal);
      if (!signal.aborted) {
        setComparison(data);
        setSelected(data.eligible_product_ids[0] ?? data.products[0].product_id);
      }
    });
  }

  function generate(event) {
    event.preventDefault();
    return run("draft", async (signal) => {
      const data = await post(request, "/api/drafts", {
        comparison_id: comparison.comparison_id, product_id: selected, recipient: recipient.trim() || null,
      }, signal);
      if (!signal.aborted) setDraft(data);
    });
  }

  async function copyEmail() {
    try {
      await navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`);
      setCopyMessage("Email copied.");
    } catch {
      setCopyMessage("Could not copy automatically. Select and copy the email text.");
    }
  }

  const canCompare = (criteria.requirements.length > 0 || criteria.unresolved.length > 0)
    && criteria.requirements.every((item) => item.target !== ""
      && (item.operator !== "band" || (item.upper !== null && item.upper !== ""))
      && (item.field !== "price" || /^[A-Z]{3}$/.test(item.currency ?? "")));

  return (
    <div className="comparison">
      <button disabled={Boolean(busy) || !canCompare} onClick={compare}>{busy === "compare" ? "Comparing…" : "Compare reviewed products"}</button>
      {comparison && (
        <>
          <h2>Comparison results</h2>
          {comparison.products.map((product) => (
            <article className="result-card" key={product.product_id}>
              <h3>{product.model ?? "Unnamed product"}</h3>
              <p>{product.eligible ? "Eligible for recommendation" : "Compatibility not established"}</p>
              <ul className="match-list">
                {product.results.map((result, index) => {
                  const requirement = result.requirement;
                  const unit = requirement.currency ?? units[requirement.field];
                  return (
                    <li key={index}>
                      <span className={`badge ${result.status.toLowerCase()}`}>{result.status}</span>{" "}
                      <strong>{labels[requirement.field]}</strong>{" "}
                      <span>({requirement.priority}, {operators[requirement.operator].toLowerCase()} {requirement.target}{requirement.upper !== null && ` and ${requirement.upper}`} {unit})</span>
                      <p>Reviewed value {result.actual === null ? "unknown" : `${result.actual} ${result.currency ?? unit}`}
                        {result.reason === "currency_differs" && " · Different currencies"}
                      </p>
                      <p className="source">
                        {result.origin === "manual" ? "Manually corrected" : result.origin === "pdf" ? "PDF-backed" : "No source evidence"}
                        {result.evidence && ` · Original PDF page ${result.evidence.page} · “${result.evidence.excerpt}”`}
                      </p>
                    </li>
                  );
                })}
              </ul>
            </article>
          ))}
          <form className="draft-form" onSubmit={generate}>
            <label>Product for email
              <select disabled={Boolean(busy)} value={selected} onChange={(event) => {
                setSelected(event.target.value); setDraft(null); setCopyMessage(""); setError("");
              }}>
                {comparison.products.map((product) => <option key={product.product_id} value={product.product_id}>{product.model ?? "Unnamed product"}</option>)}
              </select>
            </label>
            <label>Recipient name (optional)
              <input disabled={Boolean(busy)} maxLength={80} value={recipient} onChange={(event) => {
                setRecipient(event.target.value); setDraft(null); setCopyMessage(""); setError("");
              }} />
            </label>
            <button disabled={Boolean(busy)} type="submit">{busy === "draft" ? "Generating…" : "Generate explanation and email"}</button>
          </form>
        </>
      )}
      {busy && <p role="status">{busy === "draft" ? "Preparing explanation and email…" : "Checking reviewed specifications…"}</p>}
      {error && <p role="alert">{error}</p>}
      {draft && (
        <div className="draft">
          <h3>Compatibility explanation</h3>
          <p className="explanation">{draft.explanation}</p>
          <h3>Email draft</h3>
          <label>Subject<input value={draft.subject} onChange={(event) => { setDraft({ ...draft, subject: event.target.value }); setCopyMessage(""); }} /></label>
          <label>Message<textarea rows={11} value={draft.body} onChange={(event) => { setDraft({ ...draft, body: event.target.value }); setCopyMessage(""); }} /></label>
          <button onClick={copyEmail}>Copy email</button>
          <p role="status">{copyMessage}</p>
        </div>
      )}
    </div>
  );
}
