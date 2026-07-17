from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.repo.git as git_adapter
from ethos.repository.profile import profile_relative_root

if TYPE_CHECKING:
    from pathlib import Path

REPOSITORY_TARGET = "<repo>"
PRODUCT_REPOSITORY_TARGET = "<product-repo>"
EXTERNAL_REPOSITORY_TARGET = "<target-repo>"


def parity_evidence_repository_root(*, root: Path, target: Path | None) -> Path:
    """Return the repository that owns tracked parity evidence.

    Product self-parity evidence remains in the product repository. Evidence for a
    distinct adopter Git repository is written and read from that adopter target so
    the product core does not accumulate adopter-specific tracked artifacts. Non-Git
    or fixture targets keep the historical product-root evidence location.
    """
    product_root = root.resolve()
    if target is None:
        return product_root
    target_root = target.resolve()
    if not git_adapter.git_common_dir(target_root):
        return product_root
    if git_adapter.same_git_repository(product_root, target_root):
        return product_root
    return target_root


def parity_evidence_path(*, root: Path, adopter: str) -> Path:
    """Return profile-aware tracked shadow parity evidence path."""
    repo = root.resolve()
    return (
        repo
        / profile_relative_root(repo, "durable_evidence")
        / "parity"
        / (f"{adopter}-shadow.json")
    )


def requires_product_root_argument(*, root: Path | None, target: Path | None) -> bool:
    if root is None or target is None:
        return False
    product_root = root.resolve()
    target_root = target.resolve()
    return bool(
        git_adapter.git_common_dir(target_root)
        and not git_adapter.same_git_repository(product_root, target_root)
    )


def target_identity(*, root: Path | None, adopter: str, target: Path) -> str:
    if adopter == "generic" and root is not None and git_adapter.same_git_repository(root, target):
        return REPOSITORY_TARGET
    return target.resolve().as_posix()


def tracked_target_identity(*, root: Path | None, adopter: str, target: Path) -> str:
    """Return the target identity safe for tracked parity evidence.

    Runtime reports and refresh instructions may need an executable path. Tracked
    product/adopter evidence is different: it is release-visible provenance. For
    distinct Git repositories, keep the HEAD/digest binding but redact the raw
    workstation path to a stable repository-role placeholder.
    """
    if adopter == "generic" and root is not None and git_adapter.same_git_repository(root, target):
        return REPOSITORY_TARGET
    if root is not None and git_adapter.git_common_dir(root) and git_adapter.git_common_dir(target):
        return EXTERNAL_REPOSITORY_TARGET
    return target_identity(root=root, adopter=adopter, target=target)


def target_command_argument(identity: str) -> str:
    return "." if identity == REPOSITORY_TARGET else identity
