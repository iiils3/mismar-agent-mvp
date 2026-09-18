"""Vercel entrypoint.
Loads root api.py explicitly so the /api directory cannot shadow it.
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location("mismar_api", ROOT / "api.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load api.py")
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
app = MODULE.app
