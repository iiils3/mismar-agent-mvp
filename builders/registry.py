from .aider import AiderBuilder
from .openhands import OpenHandsBuilder

def available_builders():
    return [b for b in (OpenHandsBuilder(), AiderBuilder()) if b.available()]

def select_builder(preferred: str | None = None):
    builders = available_builders()
    if preferred:
        for b in builders:
            if b.name == preferred:
                return b
    return builders[0] if builders else None
