"""Load repository and OpenSpec ChangeContract carriers from files or Git trees."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import git_stdout
from ethos.contracts.semantic import ChangeContract
from ethos.contracts.semantic import load_change_contract_file
from ethos.normalization.core import object_sequence
from ethos.repository.openspec.audit import tasks_complete

if TYPE_CHECKING:
    from pathlib import Path


def _payload(
    path: Path,
    *,
    missing_gap: str,
    root: Path | None = None,
    tree_ref: str | None = None,
) -> dict[str, object]:
    try:
        text = (
            committed_file_text(root, tree_ref, path.relative_to(root).as_posix())
            if root is not None and tree_ref is not None
            else path.read_text(encoding="utf-8")
        )
        if not text:
            raise FileNotFoundError(path)
        return tomllib.loads(text)
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(missing_gap) from exc


def _normalized(payload: dict[str, object]) -> dict[str, object]:
    tuple_fields = {
        "subjects",
        "scope",
        "invariants",
        "acceptance",
        "risks",
        "authority_refs",
        "permissions",
        "hypotheses",
        "dependencies",
    }
    return {
        key: tuple(value) if key in tuple_fields and isinstance(value, list) else value
        for key, value in payload.items()
    }


def load_repository_contract(repo: Path, *, tree_ref: str | None = None) -> ChangeContract:
    """Load the stable repository identity and default governance contract."""
    path = repo / ".ethos" / "contract.toml"
    if tree_ref is None:
        try:
            contract = load_change_contract_file(path)
        except (OSError, UnicodeError, tomllib.TOMLDecodeError, ValueError) as exc:
            message = "repository_contract_missing:.ethos/contract.toml"
            raise ValueError(message) from exc
    else:
        contract = ChangeContract.model_validate(
            _normalized(
                _payload(
                    path,
                    missing_gap="repository_contract_missing:.ethos/contract.toml",
                    root=repo,
                    tree_ref=tree_ref,
                )
            )
        )
    if contract.subjects != (contract.id,):
        message = "repository_contract_identity_mismatch"
        raise ValueError(message)
    return contract


def load_change_contract(
    repo: Path,
    *,
    change_id: str | None = None,
    tree_ref: str | None = None,
) -> ChangeContract:
    """Load one active OpenSpec ChangeContract and bind its repository subject."""
    if change_id is None:
        carriers = _change_ids(repo, tree_ref=tree_ref)
        if len(carriers) != 1:
            kind = "missing" if not carriers else "ambiguous"
            message = f"change_contract_{kind}"
            raise ValueError(message)
        change_id = carriers[0]
    elif _change_complete(repo, change_id, tree_ref=tree_ref):
        message = f"change_contract_complete:{change_id}"
        raise ValueError(message)
    path = repo / "openspec" / "changes" / change_id / "contract.toml"
    repository_contract = load_repository_contract(repo, tree_ref=tree_ref)
    message = f"change_contract_missing:{change_id}"
    if tree_ref is None:
        try:
            return load_change_contract_file(path, repository_id=repository_contract.id)
        except (OSError, UnicodeError, tomllib.TOMLDecodeError, ValueError) as exc:
            raise ValueError(message) from exc
    normalized = _normalized(_payload(path, missing_gap=message, root=repo, tree_ref=tree_ref))
    normalized["subjects"] = tuple(
        repository_contract.id if subject == "repository:self" else str(subject)
        for subject in object_sequence(normalized.get("subjects"))
    )
    return ChangeContract.model_validate(normalized)


def load_proof_contract(
    repo: Path,
    *,
    change_id: str | None = None,
    tree_ref: str | None = None,
) -> ChangeContract:
    """Load one selected change contract, or the repository contract when absent."""
    try:
        return load_change_contract(repo, change_id=change_id, tree_ref=tree_ref)
    except ValueError as exc:
        if change_id is not None or str(exc) != "change_contract_missing":
            raise
        return load_repository_contract(repo, tree_ref=tree_ref)


def _change_ids(repo: Path, *, tree_ref: str | None) -> list[str]:
    if tree_ref is None:
        return sorted(
            path.parent.name
            for path in (repo / "openspec" / "changes").glob("*/contract.toml")
            if not _change_complete(repo, path.parent.name, tree_ref=None)
        )
    suffix = "/contract.toml"
    return sorted(
        path.removeprefix("openspec/changes/").removesuffix(suffix)
        for path in git_stdout(
            repo, "ls-tree", "-r", "--name-only", tree_ref, "--", "openspec/changes"
        ).splitlines()
        if path.startswith("openspec/changes/")
        and path.endswith(suffix)
        and "/archive/" not in path
        and "/" not in path.removeprefix("openspec/changes/").removesuffix(suffix)
        and not _change_complete(
            repo,
            path.removeprefix("openspec/changes/").removesuffix(suffix),
            tree_ref=tree_ref,
        )
    )


def _change_complete(repo: Path, change_id: str, *, tree_ref: str | None) -> bool:
    relative = f"openspec/changes/{change_id}/tasks.md"
    try:
        text = (
            committed_file_text(repo, tree_ref, relative)
            if tree_ref is not None
            else (repo / relative).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError):
        return False
    return tasks_complete(text)
