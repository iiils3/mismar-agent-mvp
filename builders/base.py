from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

@dataclass
class BuildRequest:
    task: str
    repo_path: str = "."
    branch: str = ""
    max_attempts: int = 2

@dataclass
class BuildResult:
    ok: bool
    summary: str
    changed_files: list[str]
    logs: str = ""

class Builder(Protocol):
    name: str
    def available(self) -> bool: ...
    def run(self, request: BuildRequest) -> BuildResult: ...

def changed_files(repo_path: str) -> list[str]:
    import subprocess
    p = subprocess.run(
        ["git", "-C", repo_path, "status", "--short"],
        text=True, capture_output=True, check=False
    )
    return [line[3:] for line in p.stdout.splitlines() if len(line) > 3]

def worktree_ok(repo_path: str) -> bool:
    return Path(repo_path, ".git").exists()
