from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from agent import REGISTRY, Get  # noqa: E402
from agent.audit import ensure_table, get_override, known_run_ids, log_override, recent  # noqa: E402
from agent.gemini import get_provider  # noqa: E402

MAX_BYTES = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
SERVE_WEB = os.getenv("SERVE_WEB", "1") == "1"

app = FastAPI(title="Get", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def strip_api_prefix(request, call_next):
    if SERVE_WEB and request.url.path.startswith("/api/"):
        request.scope["path"] = request.url.path[len("/api") :]
    return await call_next(request)

agent = Get()
bq_table = ensure_table()


DATASET_DIR = Path(__file__).resolve().parent.parent / "demo" / "dataset"
WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "mode": agent.provider.name,
        "model": agent.provider.model,
        "skills": sorted(REGISTRY.skills),
        "bigquery_table": bq_table,
        "gcs_bucket": os.getenv("GCS_BUCKET", "") if os.getenv("GET_GCS") == "1" else None,
    }


@app.get("/skills")
def skills() -> list[dict]:
    return [
        {
            "name": s.name,
            "kind": s.kind,
            "description": s.description,
            "consumes": s.consumes,
            "produces": s.produces,
        }
        for s in REGISTRY.skills.values()
    ]


@app.post("/process")
def process(
    scenario: Annotated[str, Form()],
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> JSONResponse:
    if not scenario.strip():
        raise HTTPException(status_code=422, detail="scenario is required")

    uploads: list[tuple[str, str, bytes]] = []
    for f in files or []:
        data = f.file.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(
                status_code=413, detail=f"{f.filename} exceeds {MAX_BYTES // 1024 // 1024} MB"
            )
        uploads.append((f.filename or "upload.bin", f.content_type or "", data))

    if not uploads:
        raise HTTPException(
            status_code=422,
            detail="no sources supplied. Upload at least one file, or add a note in the scenario.",
        )

    trace = agent.run(scenario.strip(), uploads)
    return JSONResponse(trace.model_dump(mode="json"))


@app.get("/audit")
def audit(limit: int = 20) -> list[dict]:
    return recent(limit)


@app.post("/audit/{run_id}/override")
def override(run_id: str, verdict: Annotated[str, Form()], note: Annotated[str, Form()] = "") -> JSONResponse:
    if run_id not in known_run_ids():
        raise HTTPException(status_code=404, detail=f"no recorded run {run_id!r}")
    try:
        record = log_override(run_id, verdict.strip().lower(), note)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return JSONResponse(record)


@app.get("/audit/{run_id}/override")
def override_status(run_id: str) -> JSONResponse:
    if run_id not in known_run_ids():
        raise HTTPException(status_code=404, detail=f"no recorded run {run_id!r}")
    record = get_override(run_id)
    if record is None:
        return JSONResponse({"run_id": run_id, "verdict": None, "note": "", "recorded_at": None})
    return JSONResponse(record)


@app.get("/demo/dataset/{folder}/manifest")
def dataset_manifest(folder: str) -> JSONResponse:
    path = DATASET_DIR / folder
    if not path.is_dir():
        raise HTTPException(status_code=404, detail=f"no demo dataset named {folder!r}")
    return JSONResponse(sorted(p.name for p in path.iterdir() if p.is_file()))


@app.get("/demo/dataset/{folder}/{filename}")
def dataset_file(folder: str, filename: str):
    path = (DATASET_DIR / folder / filename).resolve()
    if not str(path).startswith(str(DATASET_DIR.resolve())):
        raise HTTPException(status_code=403, detail="path escapes the dataset directory")
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"{filename!r} is not in {folder!r}")
    return FileResponse(path)


if SERVE_WEB and WEB_DIST.is_dir():
    assets = WEB_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith(("health", "process", "skills", "audit", "mode", "demo")):
            raise HTTPException(status_code=404, detail=f"{full_path!r} is not a route")
        candidate = WEB_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(WEB_DIST / "index.html")


@app.post("/mode")
def set_mode(mode: str) -> dict:
    if mode not in {"mock", "auto"}:
        raise HTTPException(status_code=422, detail="mode must be mock or auto")
    if mode == "mock":
        os.environ["GET_FORCE_MOCK"] = "1"
    else:
        os.environ.pop("GET_FORCE_MOCK", None)
    agent.provider = get_provider()
    return {"mode": agent.provider.name, "model": agent.provider.model}