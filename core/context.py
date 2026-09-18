from pathlib import Path
import subprocess

IGNORE = {".git", ".cache", "node_modules", "__pycache__", ".venv"}

def project_snapshot(root="."):
    root = Path(root)
    files = []
    for p in root.rglob("*"):
        if p.is_file() and not any(part in IGNORE for part in p.parts):
            files.append(str(p.relative_to(root)))
    return {"files": files[:400], "count": len(files)}

def git_diff(root="."):
    p = subprocess.run(["git", "-C", root, "diff", "--stat"], text=True,
                       capture_output=True, check=False)
    return p.stdout[-6000:]

def compact_context(root="."):
    snap = project_snapshot(root)
    return f"files={snap['count']}\n" + "\n".join(snap["files"][:120]) + "\n" + git_diff(root)
