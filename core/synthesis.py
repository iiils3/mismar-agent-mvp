from __future__ import annotations

import json
import os

from litellm import completion


def synthesize(request: str, council: dict, max_tokens: int = 700) -> str:
    prompt = f"""
You are the Chief of Staff of Mismar.
Turn the council discussion into ONE executable decision.

Do not vote by popularity. Resolve contradictions using evidence, constraints and risk.
Keep the output compact.

Return JSON:
{{
  "decision": "string",
  "why": ["string"],
  "actions": ["string"],
  "risks": ["string"],
  "acceptance": ["string"],
  "open_questions": ["string"]
}}

Maximum 5 items per array.

REQUEST:
{request}

COUNCIL:
{council["digest"]}
"""
    model = os.getenv("MISMAR_SYNTHESIS_MODEL") or os.getenv("MISMAR_MODEL")
    if not model:
        raise RuntimeError("Set MISMAR_SYNTHESIS_MODEL or MISMAR_MODEL")
    result = completion(model=model, messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=max_tokens)
    return result.choices[0].message.content or ""
