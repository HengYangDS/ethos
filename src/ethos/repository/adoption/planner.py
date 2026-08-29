from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from pathlib import Path

from ethos.contracts.openspec.models import OpenSpecPolicy
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import render_repository_profile

PROFILE_PATH = ".ethos/profile.toml"
OPENSPEC_CONFIG_PATH = "openspec/config.yaml"
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
    current_profile = _current_binding(root, root / PROFILE_PATH)
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
    openspec = _openspec_config(root.resolve().name)
    contents: dict[str, str] = {
        PROFILE_PATH: current_profile[0]
        if isinstance(current_profile[0], str) and _existing_profile_is_valid(root, current_profile)
        else profile,
        OPENSPEC_CONFIG_PATH: _current_binding(root, root / OPENSPEC_CONFIG_PATH)[0] or openspec,
    }
    current_openspec = _current_binding(root, root / OPENSPEC_CONFIG_PATH)
    bindings = {
        PROFILE_PATH: (*current_profile, contents[PROFILE_PATH]),
        OPENSPEC_CONFIG_PATH: (*current_openspec, contents[OPENSPEC_CONFIG_PATH]),
    }
    conflicts = [
        path
        for path, (current, _exists, safe, content) in bindings.items()
        if not safe or current not in {None, "", content}
    ]
    required_gaps = [f"adoption_conflict:{path}" for path in conflicts]
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
        "\n".join(
            f"{item['path']}:{item['action']}:{item['content_sha256']}" for item in write_plan
        ).encode()
    ).hexdigest()
    if apply and expect_plan_digest is not None and expect_plan_digest != plan_digest:
        required_gaps.append("adoption_plan_digest_mismatch")
    applied = apply and not required_gaps
    if applied:
        _apply_bindings(pending)
    return {
        "root": str(root),
        "repository_id": f"repository:{profile_id}",
        "plan_digest": plan_digest,
        "planned_files": list(contents),
        "read_files": list(contents),
        "applied": applied,
        "existing_files": [
            path for path, (_current, exists, _safe, _content) in bindings.items() if exists
        ],
        "write_plan": write_plan,
        "apply_criteria": list(APPLY_CRITERIA),
        "required_gaps": required_gaps,
        "next_action": (
            "resolve adoption conflicts before apply"
            if conflict
            else "ethos status"
            if applied
            else "review read-only write plan"
        ),
        "rollback": {
            "mode": "remove_generated_binding_or_restore_git_state",
            "planned_files": [PROFILE_PATH, OPENSPEC_CONFIG_PATH],
            "generated_files": generated,
        },
    }


def _openspec_config(repository: str) -> str:
    return (
        "schema: spec-driven\n"
        f"context: Govern {repository} changes through ETHOS.\n"
        "rules:\n"
        "  proposal: [state intent and scope]\n"
        "  specs: [state behavioral requirements]\n"
        "  design: [state architecture and tradeoffs]\n"
        "  tasks: [track implementation and verification]\n"
    )


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
            return target.read_text(encoding="utf-8"), True, True
    except FileNotFoundError:
        return None, False, True
    except (OSError, UnicodeDecodeError):
        return None, True, False
    return None, True, False


def _apply_bindings(bindings: list[tuple[Path, str, str | None]]) -> None:
    written: list[tuple[Path, str | None]] = []
    try:
        for target, content, previous in bindings:
            target.parent.mkdir(parents=True, exist_ok=True)
            _write_atomic(target, content)
            written.append((target, previous))
    except BaseException:
        for target, previous in reversed(written):
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                target.write_text(previous, encoding="utf-8")
        raise


def _write_atomic(target: Path, content: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=".profile-", dir=target.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            temporary.write(content)
        temporary_path.replace(target)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
