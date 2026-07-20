"""Fail-closed, provider-neutral Container Contract validation."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tomllib
import typing as t
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from ethos.repository.profile import ContainerContractPolicy
from ethos.repository.profile import load_repository_profile

_PLATFORMS = ("linux/amd64", "linux/arm64")
_VENDOR_TEXT = (
    "orbstack=orbstack|dockerdesktop=docker desktop|colima=colima|lima=lima|"
    "rancherdesktop=rancher desktop|finch=finch|podman=podman|applecontainer=apple container"
)
_VENDORS = tuple(item.split("=") for item in _VENDOR_TEXT.split("|"))
_C = "container_contract_"


def _gap(code: str, *parts: str) -> str:
    return ":".join((_C + code, *parts))


def _report(
    *, declared: bool, manifest: str, gaps: list[str], state: str = "invalid"
) -> dict[str, t.Any]:
    return {
        "ok": not gaps,
        "state": "valid" if not gaps else state,
        "declared": declared,
        "manifest": manifest,
        "required_gaps": gaps,
        "advisory_gaps": [],
    }


def _not_declared() -> dict[str, t.Any]:
    return {
        **_report(declared=False, manifest="", gaps=[]),
        "state": "not_declared",
        "advisory_gaps": [_gap("not_declared")],
    }


def _schema_gaps(schema_name: str, payload: dict[str, t.Any], *, prefix: str) -> list[str]:
    path = next(
        (
            parent / "system" / "schemas" / "kernel" / schema_name
            for parent in Path(__file__).resolve().parents
            if (parent / "system" / "schemas" / "kernel" / schema_name).is_file()
        ),
        None,
    )
    unavailable = f"{prefix}:product_schema_unavailable:{schema_name}"
    if path is None:
        return [unavailable]
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(
            Draft202012Validator(schema).iter_errors(payload), key=lambda x: x.json_path
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, SchemaError):
        return [unavailable]
    return [f"{prefix}:{error.message}" for error in errors]


def _canonical(value: str) -> str:
    return re.sub("[^a-z0-9]", "", value.lower())


def _walk(value: object) -> t.Iterator[object]:
    yield value
    children = (
        value.values() if isinstance(value, dict) else value if isinstance(value, list) else ()
    )
    for child in children:
        yield from _walk(child)


def _at(value: object, *keys: str) -> object:
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def _contained_file(repo: Path, candidate: Path, *, label: str) -> tuple[Path | None, str | None]:
    try:
        path = candidate.resolve(strict=True)
        path.relative_to(repo)
        if not path.is_file():
            return (None, f"{label}_not_regular_file")
    except FileNotFoundError:
        return (None, f"{label}_missing")
    except ValueError:
        return (None, f"{label}_path_escapes_root")
    except (OSError, RuntimeError):
        return (None, f"{label}_unreadable")
    return (path, None)


def _evidence_refs(value: object) -> list[dict[str, t.Any]]:
    mappings = (
        {str(key): child for key, child in item.items()}
        for item in _walk(value)
        if isinstance(item, dict)
    )
    return [item for item in mappings if set(item) == {"path", "sha256"}]


def _evidence_gap(repo: Path, ref: dict[str, t.Any]) -> str | None:
    relative, digest = ref.get("path"), ref.get("sha256")
    if not isinstance(relative, str) or not isinstance(digest, str):
        return None
    path, gap = _contained_file(repo, repo / relative, label=_C + "evidence")
    if gap:
        return f"{gap}:{relative}"
    assert path is not None
    try:
        tracked = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--error-unmatch", "--", relative],
            check=False,
            capture_output=True,
            text=True,
        ).returncode
    except OSError:
        return _gap("evidence_tracking_unavailable", relative)
    if tracked:
        return _gap("evidence_untracked", relative)
    try:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return _gap("evidence_unreadable", relative)
    return (
        _gap("evidence_digest_mismatch", relative)
        if actual != digest.removeprefix("sha256:")
        else None
    )


def _evidence_gaps(repo: Path, payload: dict[str, t.Any]) -> list[str]:
    return [gap for ref in _evidence_refs(payload) if (gap := _evidence_gap(repo, ref))]


def _output_schema_gaps(repo: Path, payload: dict[str, t.Any]) -> list[str]:
    relative = _at(
        payload, "trust_profiles", "untrusted", "artifact_return", "output_schema", "path"
    )
    if not isinstance(relative, str):
        return []
    path, gap = _contained_file(repo, repo / relative, label=_C + "untrusted_output_schema")
    if gap:
        return [f"{gap}:{relative}"]
    try:
        assert path is not None
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, SchemaError):
        return [_gap("untrusted_output_schema_invalid", relative)]
    return []


def _semantic_gaps(repo: Path, payload: dict[str, t.Any]) -> list[str]:
    raw_assets = _at(payload, "asset_inventory", "assets")
    raw_assets = raw_assets if isinstance(raw_assets, list) else []
    assets = [
        {str(key): value for key, value in item.items()}
        for item in raw_assets
        if isinstance(item, dict)
    ]
    ids = [value for item in assets if isinstance((value := item.get("id")), str)]
    raw_smokes = _at(payload, "delivery", "native_linux_smokes")
    smokes = raw_smokes if isinstance(raw_smokes, list) else []
    text = "\n".join(_canonical(item) for item in _walk(payload) if isinstance(item, str))
    gaps: list[str] = [
        *(_gap("vendor_brand", name) for token, name in _VENDORS if token in text),
        *(
            _gap("native_linux_smoke_required", platform)
            for platform in _PLATFORMS
            if sum(row.get("platform") == platform for row in smokes if isinstance(row, dict)) != 1
        ),
        *(_gap("duplicate_asset_id", item) for item in set(ids) if ids.count(item) > 1),
        *(
            _gap("persistent_asset_restore_required", asset_id)
            for item in assets
            if isinstance((asset_id := item.get("id")), str)
            and item.get("lifecycle") == "persistent"
            and item.get("backup_restore") != "required"
        ),
        *_evidence_gaps(repo, payload),
        *_output_schema_gaps(repo, payload),
    ]
    return sorted(set(gaps))


def _manifest_report(repo: Path, declaration: ContainerContractPolicy) -> dict[str, t.Any]:
    manifest = declaration.manifest
    path, gap = _contained_file(repo, repo / manifest, label=_C + "manifest")
    if gap:
        return _report(declared=True, manifest=manifest, gaps=[gap])
    assert path is not None
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        return _report(
            declared=True,
            manifest=manifest,
            gaps=[f"{_C}manifest_invalid_toml:{error}"],
        )
    gaps = _schema_gaps("container-contract.schema.json", payload, prefix=_C + "schema_violation")
    return _report(declared=True, manifest=manifest, gaps=gaps or _semantic_gaps(repo, payload))


def container_contract_report(root: Path) -> dict[str, t.Any]:
    """Validate an opt-in product-schema-bound Container Contract."""
    repo = root.resolve()
    profile = load_repository_profile(repo)
    if not profile.exists:
        return _not_declared()
    if profile.declaration is None:
        return _report(declared=False, manifest="", gaps=[_C + "profile_invalid"])
    declaration = profile.declaration.container_contract
    return _not_declared() if declaration is None else _manifest_report(repo, declaration)
