"""Plan native adoption bindings and compensate failed file effects."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from pathlib import Path

from ethos.adapters.openspec.configuration import official_config_report
from ethos.contracts.openspec.models import OpenSpecPolicy
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import render_repository_profile

PROFILE_PATH = ".ethos/profile.toml"
APPLY_CRITERIA = (
    "planned_files contains only the adopter profile and official OpenSpec config",
    "existing nonempty binding content is not replaced",
    "rollback path is understood before apply",
)


def adoption_plan(
    root: Path,
    *,
    apply: bool = False,
    expect_plan_digest: str | None = None,
) -> dict[str, object]:
    """Compose native initialization with one reviewed, source-bound file-effect plan."""
    current_profile = _current_binding(root, root / PROFILE_PATH)
    configuration = official_config_report(root, initialize=True)
    config_path = Path(str(configuration["path"])).relative_to(root.resolve()).as_posix()
    observed_content = configuration.get("content")
    current_openspec = (
        observed_content if isinstance(observed_content, str) else None,
        configuration.get("exists") is True,
        configuration.get("safe") is True,
    )
    existing_profile = load_repository_profile(root)
    profile_id = (
        existing_profile.declaration.profile_id
        if existing_profile.state == "valid" and existing_profile.declaration is not None
        else root.resolve().name
    )
    profile = render_repository_profile(
        RepositoryProfileDeclaration.bootstrap(profile_id).model_copy(
            update={"openspec": OpenSpecPolicy(material_paths=("**",))}
        )
    )
    openspec = str(configuration["default_content"])
    contents: dict[str, str] = {
        PROFILE_PATH: current_profile[0]
        if isinstance(current_profile[0], str) and _existing_profile_is_valid(root, current_profile)
        else profile,
        config_path: current_openspec[0] if isinstance(current_openspec[0], str) else openspec,
    }
    bindings = {
        PROFILE_PATH: (*current_profile, contents[PROFILE_PATH]),
        config_path: (*current_openspec, contents[config_path]),
    }
    conflicts = [
        path
        for path, (current, _exists, safe, content) in bindings.items()
        if (not safe or current not in {None, "", content})
        and not (path == config_path and configuration["verdict"] == "unknown")
    ]
    config_gaps = list(string_sequence(configuration["required_gaps"]))
    if config_gaps and configuration["verdict"] == "block" and config_path not in conflicts:
        conflicts.append(config_path)
    required_gaps = [f"adoption_conflict:{path}" for path in conflicts]
    required_gaps.extend(config_gaps)
    applied = False
    write_plan = []
    generated = []
    pending: list[tuple[Path, str, str | None]] = []
    for path, (current, exists, _safe, content) in bindings.items():
        conflict = path in conflicts
        action = (
            "skip_existing_nonempty"
            if conflict
            else "keep_existing"
            if current == content
            else "write_empty"
            if current == ""
            else "create"
        )
        if action != "keep_existing":
            pending.append((root / path, content, current))
        if action in {"create", "write_empty"}:
            generated.append(path)
        write_plan.append(
            {
                "path": path,
                "action": action,
                "conflict": conflict,
                "existed": exists,
                "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                "preview": content.partition("\n")[0],
            }
        )
    plan_digest = hashlib.sha256(
        (
            str(configuration["input_digest"])
            + "\n"
            + "\n".join(
                f"{item['path']}:{item['action']}:{item['content_sha256']}" for item in write_plan
            )
        ).encode()
    ).hexdigest()
    if apply and expect_plan_digest is not None and expect_plan_digest != plan_digest:
        required_gaps.append("adoption_plan_digest_mismatch")
    applied = apply and not required_gaps
    if applied:
        _apply_bindings(root, pending)
    return {
        "root": str(root),
        "repository_id": f"repository:{profile_id}",
        "plan_digest": plan_digest,
        "planned_files": list(contents),
        "read_files": list(contents),
        "applied": applied,
        "verdict": reduce_verdicts(
            report_verdict(configuration),
            "block" if conflicts else "pass",
            required_gaps=tuple(required_gaps),
        ),
        "openspec": {
            key: configuration.get(key)
            for key in (
                "verdict",
                "path",
                "schema",
                "warnings",
                "required_gaps",
                "inputs",
                "input_digest",
            )
        },
        "existing_files": [
            path for path, (_current, exists, _safe, _content) in bindings.items() if exists
        ],
        "write_plan": write_plan,
        "apply_criteria": list(APPLY_CRITERIA),
        "required_gaps": required_gaps,
        "rollback": {
            "mode": "remove_generated_binding_or_restore_git_state",
            "planned_files": [PROFILE_PATH, config_path],
            "generated_files": generated,
        },
    }


def _existing_profile_is_valid(root: Path, binding: tuple[str | None, bool, bool]) -> bool:
    current, _exists, safe = binding
    return bool(current and safe and load_repository_profile(root).state == "valid")


def _current_binding(root: Path, target: Path) -> tuple[str | None, bool, bool]:
    """Read the binding only when every path component is repository-contained and native."""
    repo = root.resolve()
    parent = target.parent
    if parent.is_symlink():
        return None, True, False
    try:
        parent.resolve(strict=False).relative_to(repo)
    except (OSError, RuntimeError, ValueError):
        return None, parent.exists() or parent.is_symlink(), False
    try:
        mode = target.lstat().st_mode
        if stat.S_ISREG(mode):
            return target.read_bytes().decode("utf-8"), True, True
    except FileNotFoundError:
        return None, False, True
    except (OSError, UnicodeDecodeError):
        return None, True, False
    return None, True, False


def _apply_bindings(root: Path, bindings: list[tuple[Path, str, str | None]]) -> None:
    written: list[tuple[Path, str | None, str]] = []
    created: list[Path] = []
    try:
        for target, content, previous in bindings:
            if not target.parent.exists():
                target.parent.mkdir()
                created.append(target.parent)
            _write_atomic(root, target, content, expected=previous)
            written.append((target, previous, content))
        if bindings:
            _verify_native_postcondition(root)
        for target, _previous, content in written:
            _verify_preimage(root, target, content)
    except BaseException as original:
        failures = _compensate_bindings(root, written, created)
        if failures:
            message = "adoption_compensation_incomplete"
            raise BaseExceptionGroup(message, [original, *failures]) from None
        raise


def _compensate_bindings(
    root: Path, written: list[tuple[Path, str | None, str]], created: list[Path]
) -> list[OSError]:
    """Preserve contested bytes while compensating every independent owned effect."""
    failures = []
    for target, previous, content in reversed(written):
        try:
            if previous is None:
                _verify_preimage(root, target, content)
                target.unlink()
            else:
                _write_atomic(root, target, previous, expected=content)
        except OSError as failure:
            failures.append(failure)
    for directory in reversed(created):
        try:
            if directory.exists() and not any(directory.iterdir()):
                directory.rmdir()
        except OSError as failure:
            failures.append(failure)
    return failures


def _verify_native_postcondition(root: Path) -> None:
    observed = official_config_report(root)
    if observed["verdict"] != "pass":
        message = "adoption_native_postcondition_failed:" + ",".join(
            string_sequence(observed.get("required_gaps"))
        )
        raise OSError(message)


def _verify_preimage(root: Path, target: Path, expected: str | None) -> None:
    if _current_binding(root, target) != (expected, expected is not None, True):
        message = f"adoption_input_changed:{target}"
        raise OSError(message)


def _write_atomic(root: Path, target: Path, content: str, *, expected: str | None) -> None:
    _verify_preimage(root, target, expected)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".profile-", dir=target.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(content.encode("utf-8"))
        temporary_path.replace(target)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
