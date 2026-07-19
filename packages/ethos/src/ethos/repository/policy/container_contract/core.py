"""Fail-closed, provider-neutral Container Contract validation."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

_DECLARATION_PATH = ".ethos/container-contract.toml"
_PLATFORMS = ("linux/amd64", "linux/arm64")
_VENDOR_TOKENS = (
    ("orbstack", "orbstack"),
    ("dockerdesktop", "docker desktop"),
    ("colima", "colima"),
    ("lima", "lima"),
    ("rancherdesktop", "rancher desktop"),
    ("finch", "finch"),
    ("podman", "podman"),
    ("applecontainer", "apple container"),
)


def _report(
    *, declared: bool, manifest: str, gaps: list[str], state: str = "invalid"
) -> dict[str, Any]:
    return {
        "ok": not gaps,
        "state": "valid" if not gaps else state,
        "declared": declared,
        "manifest": manifest,
        "required_gaps": gaps,
        "advisory_gaps": [],
    }


def _not_declared() -> dict[str, Any]:
    return {
        "ok": True,
        "state": "not_declared",
        "declared": False,
        "manifest": "",
        "required_gaps": [],
        "advisory_gaps": ["container_contract_not_declared"],
    }


def _schema_gaps(schema_name: str, payload: dict[str, Any], *, prefix: str) -> list[str]:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "system" / "schemas" / "kernel" / schema_name
        if candidate.is_file():
            try:
                schema = json.loads(candidate.read_text(encoding="utf-8"))
                errors = sorted(
                    Draft202012Validator(schema).iter_errors(payload),
                    key=lambda item: item.json_path,
                )
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, SchemaError):
                return [f"{prefix}:product_schema_unavailable:{schema_name}"]
            return [f"{prefix}:{error.message}" for error in errors]
    return [f"{prefix}:product_schema_unavailable:{schema_name}"]


def _canonical(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _strings(value: object) -> list[str]:
    if isinstance(value, dict):
        return [item for child in value.values() for item in _strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _strings(child)]
    return [value] if isinstance(value, str) else []


def _contained_file(repo: Path, candidate: Path, *, label: str) -> tuple[Path | None, str | None]:
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(repo)
        if not resolved.is_file():
            return None, f"{label}_not_regular_file"
    except FileNotFoundError:
        return None, f"{label}_missing"
    except ValueError:
        return None, f"{label}_path_escapes_root"
    except (OSError, RuntimeError):
        return None, f"{label}_unreadable"
    return resolved, None


def _read_file(repo: Path, candidate: Path, *, label: str) -> tuple[str | None, str | None]:
    path, gap = _contained_file(repo, candidate, label=label)
    if path is None:
        return None, gap
    try:
        return path.read_text(encoding="utf-8"), None
    except (OSError, UnicodeDecodeError):
        return None, f"{label}_unreadable"


def _evidence_refs(value: object) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        payload = {str(key): item for key, item in value.items()}
        return ([payload] if set(payload) == {"path", "sha256"} else []) + [
            ref for item in payload.values() for ref in _evidence_refs(item)
        ]
    if isinstance(value, list):
        return [ref for item in value for ref in _evidence_refs(item)]
    return []


def _evidence_gaps(repo: Path, payload: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for ref in _evidence_refs(payload):
        relative, digest = ref.get("path"), ref.get("sha256")
        if not isinstance(relative, str) or not isinstance(digest, str):
            continue
        path, gap = _contained_file(repo, repo / relative, label="container_contract_evidence")
        if gap:
            gaps.append(f"{gap}:{relative}")
            continue
        assert path is not None
        try:
            tracked = (
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo),
                        "ls-files",
                        "--error-unmatch",
                        "--",
                        relative,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                ).returncode
                == 0
            )
        except OSError:
            gaps.append(f"container_contract_evidence_tracking_unavailable:{relative}")
            continue
        if not tracked:
            gaps.append(f"container_contract_evidence_untracked:{relative}")
            continue
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            gaps.append(f"container_contract_evidence_unreadable:{relative}")
        else:
            if actual != digest.removeprefix("sha256:"):
                gaps.append(f"container_contract_evidence_digest_mismatch:{relative}")
    return gaps


def _output_schema_gaps(repo: Path, payload: dict[str, Any]) -> list[str]:
    trust = payload.get("trust_profiles")
    untrusted = trust.get("untrusted") if isinstance(trust, dict) else None
    returned = untrusted.get("artifact_return") if isinstance(untrusted, dict) else None
    schema = returned.get("output_schema") if isinstance(returned, dict) else None
    relative = schema.get("path") if isinstance(schema, dict) else None
    if not isinstance(relative, str):
        return []
    path, gap = _contained_file(
        repo, repo / relative, label="container_contract_untrusted_output_schema"
    )
    if gap:
        return [f"{gap}:{relative}"]
    assert path is not None
    try:
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, SchemaError):
        return [f"container_contract_untrusted_output_schema_invalid:{relative}"]
    return []


def _semantic_gaps(repo: Path, payload: dict[str, Any]) -> list[str]:
    delivery = payload.get("delivery")
    smokes = delivery.get("native_linux_smokes") if isinstance(delivery, dict) else []
    inventory = payload.get("asset_inventory")
    assets = inventory.get("assets") if isinstance(inventory, dict) else []
    typed_assets = [asset for asset in assets if isinstance(asset, dict)]
    normalized = "\n".join(_canonical(value) for value in _strings(payload))
    return sorted(
        set(
            [
                f"container_contract_vendor_brand:{name}"
                for token, name in _VENDOR_TOKENS
                if token in normalized
            ]
            + [
                f"container_contract_native_linux_smoke_required:{platform}"
                for platform in _PLATFORMS
                if sum(
                    smoke.get("platform") == platform for smoke in smokes if isinstance(smoke, dict)
                )
                != 1
            ]
            + _duplicate_asset_gaps(typed_assets)
            + [
                f"container_contract_persistent_asset_restore_required:{asset_id}"
                for asset in typed_assets
                if isinstance(asset_id := asset.get("id"), str)
                and asset.get("lifecycle") == "persistent"
                and asset.get("backup_restore") != "required"
            ]
            + _evidence_gaps(repo, payload)
            + _output_schema_gaps(repo, payload)
        )
    )


def _duplicate_asset_gaps(assets: list[dict[str, Any]]) -> list[str]:
    """Return duplicate inventory identifiers without weakening schema-first validation."""
    asset_ids = [asset.get("id") for asset in assets if isinstance(asset.get("id"), str)]
    return [
        f"container_contract_duplicate_asset_id:{asset_id}"
        for asset_id in set(asset_ids)
        if asset_ids.count(asset_id) > 1
    ]


def _manifest_report(repo: Path, declaration: dict[str, Any]) -> dict[str, Any]:
    declaration_gaps = _schema_gaps(
        "container-contract-declaration.schema.json",
        declaration,
        prefix="container_contract_declaration_schema",
    )
    manifest = str(declaration.get("manifest") or "")
    if declaration_gaps:
        return _report(declared=True, manifest=manifest, gaps=declaration_gaps)
    path, gap = _contained_file(repo, repo / manifest, label="container_contract_manifest")
    if gap:
        return _report(declared=True, manifest=manifest, gaps=[gap])
    assert path is not None
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return _report(
            declared=True,
            manifest=manifest,
            gaps=[f"container_contract_manifest_invalid_toml:{exc}"],
        )
    gaps = _schema_gaps(
        "container-contract.schema.json",
        payload,
        prefix="container_contract_schema_violation",
    )
    return _report(declared=True, manifest=manifest, gaps=gaps or _semantic_gaps(repo, payload))


def container_contract_report(root: Path) -> dict[str, Any]:
    """Validate an opt-in product-schema-bound Container Contract."""
    repo = root.resolve()
    profile_text, profile_gap = _read_file(
        repo, repo / ".ethos/profile.toml", label="container_contract_profile"
    )
    if profile_gap == "container_contract_profile_missing":
        return _not_declared()
    if profile_gap:
        return _report(declared=False, manifest="", gaps=[profile_gap])
    assert profile_text is not None
    try:
        profile = tomllib.loads(profile_text)
    except tomllib.TOMLDecodeError as exc:
        return _report(
            declared=False,
            manifest="",
            gaps=[f"container_contract_profile_invalid_toml:{exc}"],
        )
    declaration = profile.get("container_contract")
    if declaration is None:
        return _not_declared()
    if not isinstance(declaration, dict):
        return _report(
            declared=True,
            manifest="",
            gaps=["container_contract_declaration_not_table"],
        )
    return _manifest_report(repo, {str(key): value for key, value in declaration.items()})
