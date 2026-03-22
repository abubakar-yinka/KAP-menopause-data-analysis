"""
main.py — FastAPI server for the KAP Study Analysis Dashboard.

Endpoints:
  POST /api/analyze   → Upload .xlsx/.csv → run pipeline → return JSON summary
  GET  /api/download/results/{session_id}  → Download results_output.xlsx
  GET  /api/download/cleaned/{session_id}  → Download raw_data_cleaned.xlsx
"""

import io
import time
import uuid

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from analyzer import run_pipeline

# =============================================================================
# App setup
# =============================================================================

app = FastAPI(
    title="KAP Study Analysis API",
    description="Upload KoboToolbox data → Run analysis → Download results",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory session store: { session_id: { data, created_at } }
# Sessions expire after 1 hour
sessions: dict[str, dict] = {}
SESSION_TTL_SECONDS = 3600

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _cleanup_sessions():
    """Remove sessions older than TTL."""
    now = time.time()
    expired = [
        k for k, v in sessions.items() if now - v["created_at"] > SESSION_TTL_SECONDS
    ]
    for k in expired:
        del sessions[k]


# =============================================================================
# Endpoints
# =============================================================================


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Upload a .xlsx or .csv file, run the analysis pipeline,
    and return a JSON summary for the dashboard.
    """
    _cleanup_sessions()

    # --- Validate file type ---
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("xlsx", "csv"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '.{ext}'. Please upload a .xlsx or .csv file.",
        )

    # --- Read file content ---
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read uploaded file.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(content) / 1024 / 1024:.1f} MB). Maximum is 10 MB.",
        )

    # --- Parse into DataFrame ---
    try:
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse file: {str(e)}",
        )

    if len(df) == 0:
        raise HTTPException(
            status_code=400, detail="The uploaded file contains no data rows."
        )

    # --- Run the analysis pipeline ---
    try:
        result = run_pipeline(df)
    except ValueError as e:
        # Validation errors (missing columns, no consent, etc.)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}",
        )

    # --- Store session for downloads ---
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "results_xlsx": result["results_xlsx"],
        "cleaned_xlsx": result["cleaned_xlsx"],
        "created_at": time.time(),
    }

    return JSONResponse(
        content={
            "session_id": session_id,
            "summary": result["summary"],
        }
    )


@app.get("/api/download/results/{session_id}")
async def download_results(session_id: str):
    """Download the results_output.xlsx for a given session."""
    _cleanup_sessions()

    session = sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404, detail="Session not found or expired. Please re-upload."
        )

    buf = session["results_xlsx"]
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=results_output.xlsx"},
    )


@app.get("/api/download/cleaned/{session_id}")
async def download_cleaned(session_id: str):
    """Download the raw_data_cleaned.xlsx for a given session."""
    _cleanup_sessions()

    session = sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404, detail="Session not found or expired. Please re-upload."
        )

    buf = session["cleaned_xlsx"]
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=raw_data_cleaned.xlsx"},
    )


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "active_sessions": len(sessions)}
