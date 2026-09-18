import os
import shutil
import subprocess
from .base import BuildRequest, BuildResult, changed_files, worktree_ok

class OpenHandsBuilder:
    name = "openhands"

    def available(self) -> bool:
        return shutil.which("openhands") is not None

    def run(self, request: BuildRequest) -> BuildResult:
        if not self.available() or not worktree_ok(request.repo_path):
            return BuildResult(False, "OpenHands غير متوفر أو المسار ليس مستودع Git.", [])
        prompt = (
            "Work only inside the repository. Read the existing code first. "
            "Implement the task, run relevant tests/checks, and do not expose secrets. "
            f"Task: {request.task}"
        )
        env = os.environ.copy()
        env["SANDBOX_RUNTIME_CONTAINER_IMAGE"] = env.get(
            "SANDBOX_RUNTIME_CONTAINER_IMAGE", ""
        )
        p = subprocess.run(
            ["openhands", "--headless", "--override-with-envs", "-t", prompt],
            cwd=request.repo_path,
            text=True,
            capture_output=True,
            timeout=1800,
            check=False,
            env=env,
        )
        files = changed_files(request.repo_path)
        return BuildResult(
            p.returncode == 0,
            "تم تشغيل OpenHands." if p.returncode == 0 else "OpenHands فشل.",
            files,
            (p.stdout + "\n" + p.stderr)[-12000:],
        )
