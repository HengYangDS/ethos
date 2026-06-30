from __future__ import annotations


def standard_adapter_registry() -> dict[str, dict[str, str]]:
    return {
        "slsa": {
            "mode": "native-standard",
            "boundary": "Evidence and release facts may project to SLSA-style provenance.",
            "fallback": "Keep unsigned JSON evidence with HEAD and digest binding.",
            "exit_strategy": "Remove the projection while preserving ETHOS Evidence schema.",
        },
        "sigstore": {
            "mode": "first-class-adapter",
            "boundary": "Sign artifacts or evidence projections; do not own truth.",
            "fallback": "Use local digest verification and Git-signed release tags.",
            "exit_strategy": "Disable signing adapter without changing proof semantics.",
        },
        "opentelemetry": {
            "mode": "native-standard",
            "boundary": "Use semantic conventions for Chronicle and action run telemetry.",
            "fallback": "Emit structured JSON events without telemetry export.",
            "exit_strategy": "Drop exporter while retaining Chronicle events.",
        },
        "dagger": {
            "mode": "runner-adapter",
            "boundary": "Run action graph nodes in programmable local or hosted CI containers.",
            "fallback": "Use local subprocess runner over the same action graph.",
            "exit_strategy": "Remove runner adapter without changing action graph schema.",
        },
        "cue": {
            "mode": "advanced-compiler",
            "boundary": "Compile advanced organization profiles into .ethos TOML and schemas.",
            "fallback": "Use TOML plus JSON Schema validation.",
            "exit_strategy": "Keep generated TOML and retire the compiler projection.",
        },
        "opa": {
            "mode": "policy-adapter",
            "boundary": "Evaluate organization policy over ETHOS JSON payloads.",
            "fallback": "Use Python policy checks inside ethos-governance.",
            "exit_strategy": "Remove policy adapter while keeping policy decision contract.",
        },
        "temporal": {
            "mode": "service-runtime-adapter",
            "boundary": "Durable service-mode execution for long campaigns and agent swarms.",
            "fallback": "Use local CLI and SQLite state.",
            "exit_strategy": "Export Chronicle events and stop service-mode workflows.",
        },
        "mcp": {
            "mode": "agent-projection",
            "boundary": "Expose ETHOS resources, prompts, and tools to agent hosts.",
            "fallback": "Use CLI JSON and docs context packs.",
            "exit_strategy": "Remove host projection without changing repository truth.",
        },
    }
