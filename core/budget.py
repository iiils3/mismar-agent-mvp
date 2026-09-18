from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Budget:
    max_roles: int
    rounds: int
    role_tokens: int
    critique_tokens: int
    synthesis_tokens: int

MODE_BUDGETS = {
    "fast": Budget(3, 1, 180, 140, 450),
    "balanced": Budget(6, 2, 240, 180, 600),
    "full": Budget(13, 2, 280, 190, 700),
    "deep": Budget(13, 3, 280, 190, 800),
}

def get_budget(mode: str) -> Budget:
    return MODE_BUDGETS.get(mode, MODE_BUDGETS["balanced"])

def global_cap() -> int:
    return int(os.getenv("MISMAR_MAX_OUTPUT_TOKENS", "9000"))
