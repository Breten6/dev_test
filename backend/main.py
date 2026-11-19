from fastapi import FastAPI

app = FastAPI(title="Sonar Sales Copilot")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
