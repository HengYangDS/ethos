"""Plan native adoption bindings and compensate failed file effects."""

from __future__ import annotations

import hashlib
import os
import stat
import sys
import tempfile
from pathlib import Path

from ethos.adapters.openspec.configuration import official_config_report
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from ethos.adapters.repo.runtime.materialization.effect import materialize_runtime
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import restore_runtime_selection
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from ethos.adapters.repo.runtime.selection import runtime_selection_transaction
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
    select_runtime: bool = False,
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
    runtime = _runtime_plan(root) if select_runtime else {}
    if runtime.get("required_gaps"):
        required_gaps.extend(string_sequence(runtime["required_gaps"]))
    plan_digest = hashlib.sha256(
        (
            str(configuration["input_digest"])
            + "\n"
            + "\n".join(
                f"{item['path']}:{item['action']}:{item['content_sha256']}" for item in write_plan
            )
        ).encode()
        + (repr(runtime).encode() if select_runtime else b"")
    ).hexdigest()
    if apply and expect_plan_digest is not None and expect_plan_digest != plan_digest:
        required_gaps.append("adoption_plan_digest_mismatch")
    applied = apply and not required_gaps
    if applied:
        if select_runtime:
            _apply_runtime(root, pending, runtime)
        else:
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
        **({"runtime_selection": {**runtime, "applied": applied}} if select_runtime else {}),
        "rollback": {
            "mode": "remove_generated_binding_or_restore_git_state",
            "planned_files": [PROFILE_PATH, config_path],
            "generated_files": generated,
        },
    }


def _runtime_plan(root: Path) -> dict[str, object]:
    """Bind runtime source and selector without configuring any Git hook."""
    common = Path(git_common_dir(root))
    selector = common / "ethos/runtime/CURRENT"
    if selector.is_symlink() or selector.parent.is_symlink() or selector.parent.parent.is_symlink():
        return {"required_gaps": ["hook_runtime_current_target_invalid"]}
    try:
        previous = selector.read_bytes() if selector.exists() else None
        expected = expected_runtime_build(root).identity
    except (OSError, ValueError) as error:
        return {"required_gaps": [str(error)]}
    return {
        "source_commit": expected.source_commit,
        "source_tree": expected.source_tree,
        "previous_selector": previous.decode("utf-8") if previous is not None else None,
        "hooks": "preserved",
        "evidence_boundary": "selected_runtime_provenance_not_hook_or_delivery_acceptance",
    }


def _apply_runtime(
    root: Path, bindings: list[tuple[Path, str, str | None]], plan: dict[str, object]
) -> None:
    """Select admitted native supply under its existing exact selector transaction."""
    expected = expected_runtime_build(root)
    if (expected.identity.source_commit, expected.identity.source_tree) != (
        plan["source_commit"],
        plan["source_tree"],
    ):
        message = "adoption_runtime_source_changed"
        raise ValueError(message)
    common = Path(git_common_dir(root))
    previous = plan["previous_selector"]
    if not isinstance(previous, (str, type(None))):
        message = "adoption_runtime_selector_invalid"
        raise TypeError(message)
    prior = previous.encode("utf-8") if previous is not None else None
    python = materialize_runtime(
        root, Path(sys.executable), expected_build=expected.identity, build_source=expected.source
    )
    selected = activate_runtime(common, python.parent, expected_current=prior)
    desired = runtime_selection_bytes(common, selected.root)
    try:
        with runtime_selection_transaction(common, expected_current=desired):
            _apply_bindings(root, bindings)
    except BaseException as original:
        try:
            restore_runtime_selection(common, prior, expected_current=desired)
        except (OSError, ValueError) as compensation:
            message = "adoption_runtime_compensation_incomplete"
            raise BaseExceptionGroup(message, [original, compensation]) from None
        raise


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
