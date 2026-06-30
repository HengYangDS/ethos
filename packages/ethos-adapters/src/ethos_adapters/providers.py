from __future__ import annotations

PROVIDERS = (
    "git",
    "sqlite",
    "openspec",
    "gitlab",
    "github",
    "mcp",
    "acp",
    "superpowers",
    "pytest",
    "ruff",
)


def provider_registry() -> dict[str, object]:
    return {"providers": list(PROVIDERS)}
