from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from contextlib import suppress
from pathlib import Path

from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile

PROFILE_PATH = ".ethos/profile.toml"
APPLY_CRITERIA = (
    "planned_files contains only the adopter binding manifest",
    "existing nonempty binding content is not replaced",
    "rollback path is understood before apply",
)


def adoption_plan(root: Path, *, apply: bool = False) -> dict[str, object]:
    content = render_repository_profile(RepositoryProfileDeclaration.bootstrap(root.resolve().name))
    target = root / PROFILE_PATH
    current, exists, safe = _current_binding(root, target)
    conflict = not safe or current not in {None, "", content}
    action = (
        "skip_existing_nonempty"
        if conflict
        else "keep_existing"
        if current == content
        else "write_empty"
        if current == ""
        else "create"
    )
    required_gaps = [f"adoption_conflict:{PROFILE_PATH}"] if conflict else []
    applied = apply and not conflict
    if applied and action != "keep_existing":
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(target, content)
    generated = [PROFILE_PATH] if action in {"create", "write_empty"} else []
    return {
        "root": str(root),
        "planned_files": [PROFILE_PATH],
        "read_files": [PROFILE_PATH],
        "applied": applied,
        "existing_files": [PROFILE_PATH] if exists else [],
        "write_plan": [
            {
                "path": PROFILE_PATH,
                "action": action,
                "conflict": conflict,
                "existed": exists,
                "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                "preview": content.partition("\n")[0],
            }
        ],
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
            "planned_files": [PROFILE_PATH],
            "generated_files": generated,
        },
    }


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
        pass
    return None, True, False


def _write_atomic(target: Path, content: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=".profile-", dir=target.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            temporary.write(content)
        temporary_path.replace(target)
    except BaseException:
        with suppress(FileNotFoundError):
            temporary_path.unlink()
        raise
