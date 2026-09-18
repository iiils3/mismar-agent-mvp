from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.council import debate
from core.synthesis import synthesize

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

@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    # Initial release validates and safely accepts media metadata. Files are
    # intentionally not persisted on Vercel's ephemeral filesystem.
    accepted = []
    for item in files[:10]:
        if item.content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif", "video/mp4", "video/webm", "video/quicktime"}:
            continue
        data = await item.read(MAX_ATTACHMENT_BYTES + 1)
        if len(data) > MAX_ATTACHMENT_BYTES:
            continue
        accepted.append({"name": item.filename or "media", "type": item.content_type, "size": len(data), "id": str(uuid.uuid4())})
    return {"files": accepted}
