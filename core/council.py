from __future__ import annotations

import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv
from litellm import completion

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / os.getenv("MISMAR_CACHE_DIR", ".cache/llm")
CACHE.mkdir(parents=True, exist_ok=True)

ROLES = {
    "idea": "Convert the request into a precise problem and MVP.",
    "market": "Check competitors, users, differentiation and assumptions.",
    "strategy": "Check business model, priorities, risks and measurable outcomes.",
    "architect": "Design the simplest reliable architecture and interfaces.",
    "ux": "Design the clearest mobile-first user experience.",
    "backend": "Design backend APIs, data flow and server behavior.",
    "frontend": "Design implementation details for the web client.",
    "devops": "Minimize deployment cost and operational complexity.",
    "qa": "Define failure cases, tests and acceptance checks.",
    "security": "Find security, privacy and abuse risks.",
    "content": "Improve product copy and communication.",
    "growth": "Find measurable distribution and retention loops.",
    "data": "Define useful telemetry and decision metrics.",
}
DEFAULT_ACTIVE = ["idea", "architect", "qa"]

def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

def choose_roles(request: str, mode: str = "auto") -> list[str]:
    if mode in ("full", "deep"):
        return list(ROLES)
    text = request.lower()
    selected = []
    keywords = {
        "market": ("market", "competitor", "سوق", "منافس"),
        "strategy": ("money", "price", "subscription", "ربح", "اشتراك", "سعر"),
        "architect": ("api", "database", "architecture", "backend", "قاعدة", "معمار"),
        "ux": ("ui", "ux", "mobile", "واجهة", "تصميم"),
        "backend": ("backend", "server", "api", "خادم"),
        "frontend": ("frontend", "web", "react", "صفحة", "واجهة"),
        "devops": ("deploy", "docker", "cloud", "استضافة", "نشر"),
        "qa": ("test", "bug", "quality", "اختبار", "خطأ"),
        "security": ("security", "auth", "payment", "private", "أمان", "دفع"),
        "content": ("copy", "content", "نسخة", "محتوى"),
        "growth": ("growth", "marketing", "viral", "نمو", "انتشار"),
        "data": ("analytics", "metric", "data", "بيانات", "مؤشر"),
    }
    for role, words in keywords.items():
        if any(w in text for w in words):
            selected.append(role)
    return (["idea"] + selected + ["qa"])[:6] if selected else DEFAULT_ACTIVE

def model_for(role: str) -> str:
    return os.getenv("MISMAR_MODEL_" + role.upper()) or os.getenv("MISMAR_MODEL") or "openai/gpt-4o-mini"

def cache_key(role: str, task: str, context: str, model: str) -> str:
    raw = json.dumps({"role": role, "task": compact(task), "context": compact(context), "model": model}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()

def ask(role: str, task: str, context: str, max_tokens: int = 350) -> str:
    model = model_for(role)
    path = CACHE / f"{cache_key(role, task, context, model)}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    prompt = (
        f"You are the {role} specialist in Mismar's software factory.\n"
        f"Your job: {ROLES[role]}\n"
        "Be skeptical. Challenge assumptions. Do not repeat other agents. "
        "Return compact bullets: decision, evidence/reasoning, risk, action. "
        f"Maximum {max_tokens} output tokens.\n\nTASK:\n{task}\n\nCONTEXT:\n{context}"
    )
    result = completion(model=model, messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=max_tokens)
    text = result.choices[0].message.content or ""
    path.write_text(text, encoding="utf-8")
    return text

def debate(request: str, mode: str = "auto", rounds: int = 2) -> dict:
    roles = choose_roles(request, mode)
    outputs = {}
    with ThreadPoolExecutor(max_workers=min(len(roles), 8)) as pool:
        futures = {pool.submit(ask, r, request, "No prior opinions. Produce an independent position.", 300): r for r in roles}
        for f in as_completed(futures):
            outputs[futures[f]] = f.result()
    digest = "\n".join(f"[{r}] {compact(outputs[r])[:1200]}" for r in roles)

    if rounds >= 2:
        critiques = {}
        with ThreadPoolExecutor(max_workers=min(len(roles), 8)) as pool:
            futures = {
                pool.submit(
                    ask, r, request,
                    "Critique the council digest. Identify only the most important disagreement or blind spot.\n" + digest,
                    260,
                ): r for r in roles
            }
            for f in as_completed(futures):
                critiques[futures[f]] = f.result()
        digest += "\nCRITIQUES:\n" + "\n".join(f"[{r}] {compact(critiques[r])[:900]}" for r in roles)

    if rounds >= 3:
        challenge = {}
        compact_digest = "\n".join(f"[{r}] {compact(outputs[r])[:700]}" for r in roles)
        with ThreadPoolExecutor(max_workers=min(len(roles), 8)) as pool:
            futures = {
                pool.submit(
                    ask, r, request,
                    "Final challenge: find one fatal assumption or missing acceptance check.\n" + compact_digest,
                    180,
                ): r for r in roles
            }
            for f in as_completed(futures):
                challenge[futures[f]] = f.result()
        digest += "\nFINAL CHALLENGES:\n" + "\n".join(f"[{r}] {compact(challenge[r])[:650]}" for r in roles)

    return {"roles": roles, "rounds": rounds, "digest": digest}
