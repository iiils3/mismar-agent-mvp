from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from litellm import completion

load_dotenv()

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / os.getenv("MISMAR_CACHE_DIR", ".cache/llm")
CACHE.mkdir(parents=True, exist_ok=True)

MAX_OUTPUT = int(os.getenv("MISMAR_MAX_OUTPUT_TOKENS", "900"))
MAX_PLAN = int(os.getenv("MISMAR_MAX_PLAN_TOKENS", "700"))
MAX_SPECIALISTS = int(os.getenv("MISMAR_MAX_SPECIALISTS", "2"))


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def repo_manifest(limit: int = 120) -> str:
    ignored = {".git", ".cache", ".venv", "node_modules", "__pycache__"}
    paths = []
    for p in ROOT.rglob("*"):
        if p.is_file() and not any(part in ignored for part in p.parts):
            paths.append(str(p.relative_to(ROOT)))
    return "\n".join(sorted(paths)[:limit])


def cache_key(task: str, role: str, model: str) -> str:
    raw = json.dumps(
        {"task": normalize(task), "role": role, "model": model, "state": repo_manifest()},
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def ask(task: str, role: str, max_tokens: int = MAX_OUTPUT) -> str:
    model = os.getenv("LLM_MODEL")
    if not model:
        raise RuntimeError("Set LLM_MODEL in .env")

    path = CACHE / f"{cache_key(task, role, model)}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")

    response = completion(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a component of a token-budgeted software factory. "
                    "Return only the requested compact format. No greetings, "
                    "repetition or long explanations."
                ),
            },
            {"role": "user", "content": task},
        ],
        max_tokens=max_tokens,
        temperature=0,
    )
    text = response.choices[0].message.content or ""
    path.write_text(text, encoding="utf-8")
    return text


def choose_roles(idea: str) -> list[str]:
    s = idea.lower()
    roles = []

    if any(x in s for x in ("ui", "واجهة", "صفحة", "design", "تصميم")):
        roles.append("ux")
    if any(x in s for x in ("api", "backend", "database", "قاعدة", "auth", "تسجيل")):
        roles.append("architecture")
    if any(x in s for x in ("security", "أمان", "payment", "دفع", "بيانات")):
        roles.append("security")
    if any(x in s for x in ("growth", "marketing", "سوق", "ربح", "اشتراك")):
        roles.append("strategy")

    if not roles:
        roles = ["product"]

    return roles[:MAX_SPECIALISTS]


def write_plan(idea: str) -> None:
    planner = (ROOT / "prompts" / "planner.md").read_text(encoding="utf-8")
    roles = choose_roles(idea)

    task = f"""
{planner}

RAW IDEA:
{idea}

SELECTED SPECIALISTS:
{", ".join(roles)}

REPOSITORY MANIFEST:
{repo_manifest()}
"""

    result = ask(task, "planner", MAX_PLAN)
    (ROOT / "plan.md").write_text(result.strip() + "\n", encoding="utf-8")
    print(f"plan.md written; roles={roles}; cache enabled")


def main() -> None:
    path = ROOT / "idea.txt"

    if not path.exists():
        path.write_text("ضع فكرتك هنا ثم شغل orchestrator.py\n", encoding="utf-8")
        print("Created idea.txt. Add an idea and run again.")
        return

    idea = normalize(path.read_text(encoding="utf-8"))
    if not idea:
        raise SystemExit("idea.txt is empty")

    write_plan(idea)


if __name__ == "__main__":
    main()
