from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import tomllib
import uuid
from contextlib import suppress
from pathlib import Path

from pydantic import ValidationError

from ethos.contracts.semantic import Commitment
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import render_repository_profile

PROFILE_PATH = ".ethos/profile.toml"
CONTRACT_PATH = ".ethos/commitment.toml"
APPLY_CRITERIA = (
    "planned_files contains only the adopter profile and repository contract bindings",
    "existing nonempty binding content is not replaced",
    "rollback path is understood before apply",
)


def adoption_plan(
    root: Path,
    *,
    apply: bool = False,
    repository_id: str | None = None,
    expect_plan_digest: str | None = None,
) -> dict[str, object]:
    repository_id = repository_id or f"repository:{uuid.uuid4()}"
    current_profile = _current_binding(root, root / PROFILE_PATH)
    current_contract = _current_binding(root, root / CONTRACT_PATH)
    repository_id = _repository_id(current_contract) or repository_id
    profile = render_repository_profile(RepositoryProfileDeclaration.bootstrap(root.resolve().name))
    contract = _repository_contract(repository_id)
    contents: dict[str, str] = {
        PROFILE_PATH: current_profile[0]
        if isinstance(current_profile[0], str) and _existing_profile_is_valid(root, current_profile)
        else profile,
        CONTRACT_PATH: current_contract[0]
        if isinstance(current_contract[0], str) and _existing_contract_is_valid(current_contract)
        else contract,
    }
    bindings = {
        PROFILE_PATH: (*current_profile, contents[PROFILE_PATH]),
        CONTRACT_PATH: (*current_contract, contents[CONTRACT_PATH]),
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
        "repository_id": repository_id,
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
            "planned_files": [PROFILE_PATH, CONTRACT_PATH],
            "generated_files": generated,
        },
    }


def _repository_contract(repository_id: str) -> str:
    return (
        "schema_version = 1\n"
        f'id = "{repository_id}"\n'
        'intent = "Govern repository change through ETHOS."\n'
        f'subjects = ["{repository_id}"]\n'
        'scope = ["**"]\n'
        'authority_refs = [".ethos/profile.toml"]\n'
        'permissions = ["repository.read", "git.ref.compare-and-swap"]\n'
    )


def _existing_profile_is_valid(root: Path, binding: tuple[str | None, bool, bool]) -> bool:
    current, _exists, safe = binding
    return bool(current and safe and load_repository_profile(root).state == "valid")


def _existing_contract_is_valid(binding: tuple[str | None, bool, bool]) -> bool:
    current, _exists, safe = binding
    if not current or not safe:
        return False
    try:
        payload = tomllib.loads(current)
        for field in (
            "subjects",
            "scope",
            "invariants",
            "acceptance",
            "risks",
            "authority_refs",
            "permissions",
            "hypotheses",
            "dependencies",
        ):
            if isinstance(payload.get(field), list):
                payload[field] = tuple(payload[field])
        contract = Commitment.model_validate(payload)
    except (tomllib.TOMLDecodeError, ValidationError):
        return False
    return contract.id.startswith("repository:") and contract.subjects == (contract.id,)


def _repository_id(binding: tuple[str | None, bool, bool]) -> str:
    current, _exists, _safe = binding
    if not current:
        return ""
    try:
        value = tomllib.loads(current).get("id")
    except tomllib.TOMLDecodeError:
        return ""
    return str(value) if isinstance(value, str) and value.startswith("repository:") else ""


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
        with suppress(FileNotFoundError):
            temporary_path.unlink()
        raise
