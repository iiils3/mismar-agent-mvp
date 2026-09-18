import shutil, subprocess
from .base import BuildRequest, BuildResult, changed_files, worktree_ok

class AiderBuilder:
    name = "aider"

    def available(self) -> bool:
        return shutil.which("aider") is not None

    def run(self, request: BuildRequest) -> BuildResult:
        if not self.available() or not worktree_ok(request.repo_path):
            return BuildResult(False, "Aider غير متوفر أو المسار ليس مستودع Git.", [])
        p = subprocess.run(
            ["aider", "--yes-always", "--message", request.task],
            cwd=request.repo_path,
            text=True,
            capture_output=True,
            timeout=1800,
            check=False,
        )
        return BuildResult(
            p.returncode == 0,
            "تم تشغيل Aider." if p.returncode == 0 else "Aider فشل.",
            changed_files(request.repo_path),
            (p.stdout + "\n" + p.stderr)[-12000:],
        )
