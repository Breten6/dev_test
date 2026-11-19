import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

function App() {
  const [status, setStatus] = useState("Checking backend connection…");

  useEffect(() => {
    async function checkBackend() {
      try {
        const response = await fetch("/api/health");
        const health = await response.json();
        if (!response.ok || health.status !== "ok") {
          throw new Error("Backend health check failed");
        }
        setStatus("Backend connected");
      } catch {
        setStatus("Backend unavailable");
      }
    }

    checkBackend();
  }, []);

  return (
    <main>
      <h1>Sonar Sales Copilot</h1>
      <p role="status">{status}</p>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
