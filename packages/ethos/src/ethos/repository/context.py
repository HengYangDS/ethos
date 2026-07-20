from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.profile import load_repository_profile
from ethos.repository.registry.commands import PUBLIC_WORKFLOW_COMMANDS
from ethos.repository.registry.commands import READER_VIEW_COMMANDS
from ethos.repository.registry.commands import SCORECARD_COMMANDS
from ethos_core.contracts.system.contracts import load_system_contract
from ethos_core.kernel import KERNEL_CHAIN
from ethos_core.models import Authority
from ethos_core.models import Subject

if TYPE_CHECKING:
    from pathlib import Path


def _authority_order(root: Path) -> tuple[str, ...]:
    """Load the authority order (rank-sorted sources) from system/authority.toml."""
    try:
        contract = load_system_contract(root, "authority")
    except (FileNotFoundError, ValueError):
        return ()
    order = contract.get("order")
    if not isinstance(order, list):
        return ()
    ranked = sorted(
        (item for item in order if isinstance(item, dict) and "rank" in item),
        key=lambda item: int(item["rank"]),
    )
    return tuple(str(item.get("source", "")) for item in ranked if item.get("source"))


def is_product_root(root: Path) -> bool:
    """Return True when ``root`` is the ETHOS product repository.

    The governed subject is still a repository in both cases. This predicate only
    selects the profile used by the shared governance context; it does not create a
    second subject kind or command plane.
    """
    return (root / "packages" / "ethos" / "README.md").exists() and (
        root / "system" / "schemas" / "kernel"
    ).exists()


def governance_profile(root: Path) -> str:
    """Return the profile for a governed repository without changing command semantics."""
    if is_product_root(root):
        return "product"
    return "adopter" if load_repository_profile(root).state == "valid" else "unbound"


def context_for_root(root: Path) -> dict[str, object]:
    """Project the governed-repository context for a product or adopted repository."""
    return governance_context(root, profile=governance_profile(root))


def governance_context(root: Path, *, profile: str) -> dict[str, object]:
    """Project the governance context, anchored on real kernel-chain head nodes.

    Constructs the actual Authority (authority-order head, loaded from
    system/authority.toml) and Subject (the governed repository) kernel models —
    ETHOS's first production constructors of the chain — rather than an inline dict
    doppelganger. The declared chain and the live payload are now one representation.
    """
    authority = Authority(
        id="repository-authority",
        order_ref="system/authority.toml",
        derived_views=(profile,),
        policy_refs=_authority_order(root),
    )
    subject = Subject(
        id=str(root.resolve()),
        kind="repository",
        name=root.name or "repository",
        owner="ethos",
    )
    return {
        "contract": "governed_repository",
        "profile": profile,
        "authority": authority.to_dict(),
        "subject": subject.to_dict(),
        "single_kernel": True,
        "kernel_chain": list(KERNEL_CHAIN),
        "shared_commands": list(PUBLIC_WORKFLOW_COMMANDS),
        "transition_commands": list(PUBLIC_WORKFLOW_COMMANDS),
        "reader_view_commands": list(READER_VIEW_COMMANDS),
        "scorecard_commands": list(SCORECARD_COMMANDS),
        "truth_boundary": "repository",
        "profile_boundary": "profile_or_adapter",
    }
