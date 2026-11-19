import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { CustomerInquiry } from "./comparison";
import "./styles.css";

const fields = [
  ["model", "Product model", "text"],
  ["max_operating_depth_m", "Maximum operating depth (m)", "number"],
  ["detection_range_m", "Detection range (m)", "number"],
  ["operating_frequency_khz", "Operating frequency (kHz)", "number"],
  ["beam_width_deg", "Beam width (°)", "number"],
  ["price", "Price", "number"],
  ["currency", "Currency (three-letter code)", "text"],
];

async function request(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const message = Array.isArray(detail)
      ? detail.map(({ loc, msg }) => {
          const label = fields.find(([name]) => name === loc.at(-1))?.[1];
          return label ? `${label}: ${msg}` : msg;
        }).join(" ")
      : detail;
    throw new Error(typeof message === "string" ? message : "The server could not complete the request. Try again.");
  }
  return payload;
}

function ProductReview({ product, onReviewed, onEdit }) {
  const [values, setValues] = useState(product.reviewed ?? product.extracted);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const reviewed = Object.fromEntries(fields.map(([name]) => {
        const value = String(values[name] ?? "").trim();
        return [name, value ? (name === "currency" ? value.toUpperCase() : value) : null];
      }));
      const result = await request(`/api/products/${product.product_id}/review`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(reviewed),
      });
      onReviewed(result);
      setValues(result.reviewed);
      setSaved(true);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="panel">
      <header className="product-heading">
        <div>
          <h2>{(product.reviewed ?? product.extracted).model ?? "Unnamed product"}</h2>
          <p>{product.filename}</p>
        </div>
        <p>{product.reviewed ? "Reviewed" : "Review required"}</p>
      </header>
      {product.warnings.length > 0 && (
        <details>
          <summary>Extraction warnings</summary>
          <ul>{product.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        </details>
      )}
      <form onSubmit={save}>
        <fieldset disabled={saving}>
          <legend>Product specifications</legend>
          <div className="fields">
            {fields.map(([name, label, type]) => {
              const id = `${product.product_id}-${name}`;
              const source = product.evidence[name];
              return (
                <div className="field" key={name}>
                  <label htmlFor={id}>{label}</label>
                  <input
                    id={id}
                    type={type}
                    min={type === "number" ? 0 : undefined}
                    step={type === "number" ? "any" : undefined}
                    maxLength={name === "currency" ? 3 : undefined}
                    placeholder="Unknown"
                    aria-describedby={`${id}-source`}
                    value={values[name] ?? ""}
                    onChange={(event) => {
                      setValues({ ...values, [name]: event.target.value });
                      onEdit(product.product_id);
                      setSaved(false);
                      setError("");
                    }}
                  />
                  <p className="source" id={`${id}-source`}>
                    {product.corrected_fields.includes(name) && <strong>Manually corrected. </strong>}
                    {source ? <>Original PDF · Page {source.page} · “{source.excerpt}”</> : "No source evidence"}
                  </p>
                </div>
              );
            })}
          </div>
          <button type="submit">{saving ? "Saving…" : "Save reviewed specifications"}</button>
        </fieldset>
        {saved && <p role="status">Reviewed specifications saved.</p>}
        {error && <p role="alert">{error}</p>}
      </form>
    </article>
  );
}

function App() {
  const [file, setFile] = useState(null);
  const [products, setProducts] = useState([]);
  const [dirtyProducts, setDirtyProducts] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function upload(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const body = new FormData();
    body.append("file", file);
    setUploading(true);
    setStatus("");
    setError("");
    try {
      const product = await request("/api/products", { method: "POST", body });
      setProducts((current) => [...current, product]);
      setStatus(`Extracted ${product.filename}. Review the specifications below.`);
      form.reset();
      setFile(null);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setUploading(false);
    }
  }

  function updateProduct(reviewed) {
    setDirtyProducts((current) => current.filter((id) => id !== reviewed.product_id));
    setProducts((current) => current.map((product) =>
      product.product_id === reviewed.product_id ? reviewed : product
    ));
  }

  return (
    <main>
      <h1>Sonar Sales Copilot</h1>
      <form className="panel upload" onSubmit={upload}>
        <label htmlFor="datasheet">Upload a sonar datasheet</label>
        <p id="upload-hint">Choose a text-based PDF up to 5 MB. Its text is sent to OpenAI for extraction.</p>
        <input
          id="datasheet"
          type="file"
          accept=".pdf,application/pdf"
          disabled={uploading}
          aria-describedby="upload-hint"
          onChange={(event) => setFile(event.target.files[0] ?? null)}
        />
        <button type="submit" disabled={!file || uploading}>Extract specifications</button>
        <p role="status">{uploading ? "Extracting specifications…" : status}</p>
        {error && <p role="alert">{error}</p>}
      </form>
      {products.map((product) => (
        <ProductReview
          key={product.product_id}
          product={product}
          onReviewed={updateProduct}
          onEdit={(id) => setDirtyProducts((current) => current.includes(id) ? current : [...current, id])}
        />
      ))}
      <CustomerInquiry products={products} dirty={dirtyProducts.length > 0} request={request} />
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
