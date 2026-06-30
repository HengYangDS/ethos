from __future__ import annotations

BOUNDARIES = {
    "playbooks": "repo-authored operational guides",
    "skills": "assistant-consumable projections",
    "superpowers": "external method pack",
    "mcp": "host-local context provider",
    "acp": "host-local protocol adapter",
    "assistant_output": "untrusted until promoted into repository evidence",
}


def assistant_boundary_report() -> dict[str, object]:
    return {"ok": True, "boundaries": dict(BOUNDARIES)}
