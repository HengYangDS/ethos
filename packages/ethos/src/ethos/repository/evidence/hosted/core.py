# ruff: noqa: E501 - transition source budget favors compact fail-closed predicates.
from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any
from typing import cast

# fmt: off
CONFIG, RUN = Path(".config/checks/ci/hosted-observation.toml"), "tools/ci/scripts/run-hosted-provider-observation.sh"
COMMANDS = {
    "github": ("gh", "run", "list", "--limit", "1", "--json", "status,conclusion,headSha,url"),
    "gitlab": ("glab", "ci", "list", "--per-page", "1", "--output", "json"),
}
FACTS = {
    "github": (("latest_head", "headSha"), ("latest_status", "status"), ("latest_conclusion", "conclusion"), ("latest_url", "url")),
    "gitlab": (("latest_head", "sha", "commit_sha"), ("latest_status", "status"), ("latest_conclusion", "status"), ("latest_url", "web_url", "url"), ("latest_ref", "ref")),
}
GAPS = {"not_configured": "provider_not_configured", "tool_unavailable": "provider_tool_unavailable", "observation_failed": "provider_observation_failed"}
FLAGS = ("hosted_github_status_claimed", "hosted_gitlab_status_claimed", "remote_publication_claimed")


def provider_command(provider: str, target: str) -> list[str]:
    """Return one provider query bound to an explicit repository target."""
    command = list(COMMANDS[provider])
    if target:
        command[3:3] = ["--repo", target]
    return command


def provider_output_valid(value: object) -> bool:
    """Return whether provider output has the required non-empty list shape."""
    return isinstance(value, list) and bool(value) and isinstance(value[0], dict)


def provider_facts(provider: str, value: object) -> dict[str, str]:
    """Normalize bounded facts without claiming provider success."""
    if not provider_output_valid(value):
        return {}
    item = cast("list[dict[str, Any]]", value)[0]
    return {name: str(next((item.get(key) for key in keys if item.get(key)), "")) for name, *keys in FACTS[provider]}


def observation_summary(observations: list[dict[str, Any]], *, execute: bool) -> tuple[str, list[str], bool]:
    """Derive aggregate state without minting provider authority."""
    if not execute:
        return "dry_run", [], True
    if not observations:
        return "observation_failed", ["provider_configuration_empty"], False
    states = [str(item.get("observation_state") or "") for item in observations]
    gaps = []
    for item, state in zip(observations, states, strict=True):
        prefix = "provider_output_invalid" if state == "observation_failed" and item.get("returncode") == 0 else GAPS.get(state)
        if prefix:
            gaps.append(f"{prefix}:{item.get('provider')}")
    observed = states.count("observed")
    state = "observed" if observed == len(states) else "partial" if observed else "not_configured" if set(states) == {"not_configured"} else "observation_failed"
    return state, gaps, state == "observed"


def _report(state: str, gaps: list[str], evidence_head: str = "", *, current: bool = False) -> dict[str, object]:
    return {"state": state, "ok": not gaps, "current": current, "evidence_head": evidence_head, "provider_states": {}, "advisory_gaps": gaps, "next_action": RUN if gaps else "", **dict.fromkeys(FLAGS, False)}


def _provider_state(*, execute: bool, configured: bool, available: bool, returncode: object, stdout_json: object) -> str:
    if execute and configured and available:
        return "" if type(returncode) is not int else "observed" if returncode == 0 and provider_output_valid(stdout_json) else "observation_failed"
    if returncode is not None or stdout_json is not None:
        return ""
    return "not_configured" if not configured else "tool_unavailable" if not available else "not_executed"


def _record_valid(item: dict[str, Any], provider: str, target_env: str, *, execute: bool) -> bool:
    if provider not in COMMANDS or any(key not in item for key in ("tool_path", "target", "returncode", "stdout_json")):
        return False
    target, tool_path = item["target"], item["tool_path"]
    if not isinstance(target, str) or target != target.strip() or not isinstance(tool_path, str):
        return False
    configured, available = bool(target), bool(tool_path)
    state = _provider_state(execute=execute, configured=configured, available=available, returncode=item["returncode"], stdout_json=item["stdout_json"])
    expected = {"provider": provider, "tool": COMMANDS[provider][0], "target_env": target_env, "command": provider_command(provider, target), "observation_state": state, "provider_facts": provider_facts(provider, item["stdout_json"])}
    return bool(state) and all(item.get(key) == value for key, value in expected.items()) and all((item.get("tool_available") is available, item.get("target_configured") is configured, item.get("executed") is (execute and configured and available), item.get("hosted_status_claimed") is False))


def _validated(payload: object, config: dict[str, Any]) -> tuple[list[dict[str, Any]], str, list[str]] | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("execute"), bool):
        return None
    data = cast("dict[str, Any]", payload)
    providers, policies, raw = config.get("providers"), config.get("provider"), data.get("observations")
    if not isinstance(providers, list) or not providers or len(set(map(str, providers))) != len(providers) or not isinstance(policies, dict) or not isinstance(raw, list) or len(raw) != len(providers) or not all(isinstance(item, dict) for item in raw):
        return None
    observations, execute = cast("list[dict[str, Any]]", raw), cast("bool", data["execute"])
    for provider, item in zip(providers, observations, strict=True):
        policy = policies.get(provider)
        target_env = policy.get("repository_target_env") if isinstance(policy, dict) else None
        if not isinstance(provider, str) or not isinstance(target_env, str) or not target_env or not _record_valid(item, provider, target_env, execute=execute):
            return None
    state, gaps, ok = observation_summary(observations, execute=execute)
    expected = {"schema_version": 1, "kind": "ethos_hosted_provider_observation", "evidence_class": "hosted_provider_observation", "state": state, "ok": ok, "observation_gaps": gaps, "observation_gap_count": len(gaps), **dict.fromkeys(FLAGS, False)}
    return None if any(data.get(key) != value for key, value in expected.items()) else (observations, state, gaps)


def hosted_observation_report(root: Path, *, current_head: str) -> dict[str, object]:
    """Read generated provider evidence as a bounded report projection."""
    path = root / CONFIG
    if not path.is_file():
        return _report("not_applicable", [])
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        output = config.get("output")
        payload = json.loads((root / output).read_text(encoding="utf-8")) if isinstance(output, str) and output else None
    except FileNotFoundError:
        return _report("missing", ["hosted_provider_observation_missing"])
    except (OSError, TypeError, UnicodeError, ValueError):
        return _report("invalid", ["hosted_provider_observation_invalid"])
    validated = _validated(payload, config)
    if validated is None:
        return _report("invalid", ["hosted_provider_observation_invalid"])
    data = cast("dict[str, Any]", payload)
    evidence_head = str(data.get("head") or "")
    if evidence_head != current_head:
        return _report("stale", ["hosted_provider_observation_stale"], evidence_head)
    observations, state, gaps = validated
    advisory = gaps if data["execute"] else [*gaps, "hosted_provider_observation_not_executed"]
    report = _report(state, advisory, evidence_head, current=True)
    report["provider_states"] = {str(item["provider"]): str(item["observation_state"]) for item in observations}
    return report
# fmt: on
