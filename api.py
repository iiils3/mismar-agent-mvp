from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.council import debate
from core.synthesis import synthesize

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Mismar AI Office")


class CouncilRequest(BaseModel):
    request: str
    mode: str = "balanced"


@app.get("/")
def home():
    return FileResponse(ROOT / "web" / "index.html")


@app.post("/api/council")
def council(payload: CouncilRequest):
    modes = {
        "fast": (3, 1),
        "balanced": (6, 2),
        "full": (13, 2),
        "deep": (13, 3),
    }
    _, rounds = modes.get(payload.mode, modes["balanced"])
    result = debate(payload.request, payload.mode if payload.mode in ("full", "deep") else "auto", rounds)
    decision = synthesize(payload.request, result)
    try:
        decision_json = json.loads(decision)
    except json.JSONDecodeError:
        decision_json = {"decision": decision}
    return {"roles": result["roles"], "rounds": result["rounds"], **decision_json}
