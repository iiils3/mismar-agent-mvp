from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Mismar AI Office")

MAX_PROMPT_CHARS = 5000
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024

class Attachment(BaseModel):
    name: str
    type: str
    size: int = Field(ge=0)

class CouncilRequest(BaseModel):
    request: str = Field(min_length=1, max_length=MAX_PROMPT_CHARS)
    mode: str = "balanced"
    attachments: list[Attachment] = Field(default_factory=list, max_length=10)

@app.get("/")
def home():
    return FileResponse(ROOT / "web" / "index.html")

@app.get("/health")
def health():
    return {"ok": True, "service": "mismar-agent-office"}

@app.post("/api/council")
def council(payload: CouncilRequest):
    try:
        from core.council import debate
        from core.synthesis import synthesize

        modes = {"fast": (3, 1), "balanced": (6, 2), "full": (13, 2), "deep": (13, 3)}
        _, rounds = modes.get(payload.mode, modes["balanced"])
        result = debate(
            payload.request,
            payload.mode if payload.mode in ("full", "deep") else "auto",
            rounds,
        )
        decision = synthesize(payload.request, result)
        try:
            decision_json = json.loads(decision)
        except json.JSONDecodeError:
            decision_json = {"decision": decision}
        return {"roles": result["roles"], "rounds": result["rounds"], "attachments": [a.model_dump() for a in payload.attachments], **decision_json}
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"AI engine unavailable: {type(exc).__name__}: {exc}")

@app.post("/api/upload")
def upload_metadata(payload: list[Attachment]):
    # Vercel's filesystem is ephemeral. The browser keeps selected media
    # locally for this preview; this endpoint validates metadata only.
    return {"files": [item.model_dump() for item in payload[:10]]}
