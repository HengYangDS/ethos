from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG_RELATIVE_PATH = ".config/checks/ci/templates.toml"
CONFIG_PATH = ROOT / CONFIG_RELATIVE_PATH
EMULATOR_REQUIRED_FIELDS = (
    "emulator_tool",
    "emulator_event",
    "emulator_job",
    "emulator_image",
    "emulator_timeout_seconds",
)


def _git_output(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def projection_entries() -> list[dict[str, Any]]:
    entries = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("projection", [])
    if not isinstance(entries, list):
        message = ".config/checks/ci/templates.toml projection must be a list"
        raise SystemExit(message)
    return entries


def _surface_entries() -> list[dict[str, Any]]:
    entries = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("forge_surface", [])
    if not isinstance(entries, list):
        message = ".config/checks/ci/templates.toml forge_surface must be a list"
        raise SystemExit(message)
    return entries


def provider_entry(provider: str) -> dict[str, Any]:
    entries = [entry for entry in projection_entries() if entry.get("provider") == provider]
    if len(entries) != 1:
        message = f"expected exactly one CI projection for provider: {provider}"
        raise SystemExit(message)
    return entries[0]


def emulator_declaration(entry: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in EMULATOR_REQUIRED_FIELDS if field not in entry]
    if missing:
        provider = entry.get("provider", "unknown")
        message = f"CI emulator declaration missing for {provider}: {', '.join(missing)}"
        raise SystemExit(message)
    declaration = {field: entry[field] for field in EMULATOR_REQUIRED_FIELDS} | {
        "emulator_state_dir": entry.get("emulator_state_dir", ""),
        "forbidden_log_patterns": list(entry.get("forbidden_log_patterns", [])),
    }
    timeout_seconds = declaration["emulator_timeout_seconds"]
    if (
        not isinstance(timeout_seconds, int)
        or isinstance(timeout_seconds, bool)
        or timeout_seconds < 1
    ):
        provider = entry.get("provider", "unknown")
        message = f"CI emulator timeout invalid for {provider}: {timeout_seconds!r}"
        raise SystemExit(message)
    return declaration


def _forge_surface_reports() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    surfaces = []
    failures = []
    for entry in _surface_entries():
        projection = ROOT / str(entry["projection"])
        required = {str(section) for section in entry.get("required_sections", [])}
        missing = not projection.is_file()
        headings = (
            {
                line.removeprefix("## ").strip().lower()
                for line in projection.read_text(encoding="utf-8").splitlines()
                if line.startswith("## ")
            }
            if not missing
            else set()
        )
        absent = sorted(required - headings)
        if missing:
            failures.append(
                {
                    "provider": str(entry["provider"]),
                    "reason": f"missing forge surface: {entry['projection']}",
                }
            )
        elif absent:
            failures.append(
                {
                    "provider": str(entry["provider"]),
                    "reason": f"forge surface sections missing: {', '.join(absent)}",
                }
            )
        surfaces.append(dict(entry) | {"required_sections_present": not absent and not missing})
    return surfaces, failures


def check_templates(*, json_output: bool) -> int:
    failures: list[dict[str, str]] = []
    projections: list[dict[str, Any]] = []
    for entry in projection_entries():
        provider = str(entry["provider"])
        template = ROOT / str(entry["template"])
        projection = ROOT / str(entry["projection"])
        try:
            emulation = emulator_declaration(entry)
        except SystemExit as exc:
            failures.append({"provider": provider, "reason": str(exc)})
            continue
        missing = [
            rel
            for rel, path in [
                (str(entry["template"]), template),
                (str(entry["projection"]), projection),
            ]
            if not path.is_file()
        ]
        owner_missing = [
            script
            for script in entry.get("required_owner_scripts", [])
            if not (ROOT / str(script)).is_file()
        ]
        if missing:
            reason = f"missing files: {', '.join(missing)}"
            failures.append({"provider": provider, "reason": reason})
            continue
        if owner_missing:
            reason = f"missing owner scripts: {', '.join(owner_missing)}"
            failures.append({"provider": provider, "reason": reason})
        match = template.read_bytes() == projection.read_bytes()
        if not match:
            reason = (
                f"projection drift: {projection.relative_to(ROOT)} != {template.relative_to(ROOT)}"
            )
            failures.append({"provider": provider, "reason": reason})
        projections.append(
            {
                "provider": provider,
                "template": str(template.relative_to(ROOT)),
                "projection": str(projection.relative_to(ROOT)),
                "emulation": emulation,
                "template_sha256": _sha256(template),
                "projection_sha256": _sha256(projection),
                "projection_matches_template": match,
                "required_owner_scripts": list(entry.get("required_owner_scripts", [])),
                "provider_specific_owner_scripts": dict(
                    entry.get("provider_specific_owner_scripts", {})
                ),
            }
        )
    surfaces, surface_failures = _forge_surface_reports()
    failures.extend(surface_failures)
    evidence = {
        "schema_version": 1,
        "kind": "ethos_ci_template_consistency",
        "verdict": "block" if failures else "pass",
        "head": _git_output("rev-parse", "HEAD"),
        "dirty": bool(_git_output("status", "--short")),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "projections": projections,
        "forge_surfaces": surfaces,
        "failures": failures,
    }
    if json_output:
        sys.stdout.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    elif failures:
        for failure in failures:
            sys.stderr.write(f"{failure['provider']}: {failure['reason']}\n")
    return 0 if evidence["verdict"] == "pass" else 1
