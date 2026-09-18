from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent


def main() -> None:
    if not shutil.which("openhands"):
        raise SystemExit("OpenHands CLI not found. Install it separately.")

    if not (ROOT / "plan.md").exists():
        raise SystemExit("plan.md not found. Run orchestrator.py first.")

    task = (
        "Read plan.md and prompts/builder.md. Inspect the repository. "
        "Implement only the plan. If feedback.md exists, fix it first. "
        "Run relevant tests. Work on the current feature branch only."
    )

    subprocess.run(
        ["openhands", "--headless", "--override-with-envs", "-t", task],
        cwd=ROOT,
        env=os.environ.copy(),
        check=True,
    )


if __name__ == "__main__":
    main()
