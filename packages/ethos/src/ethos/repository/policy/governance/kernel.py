from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.context import context_for_root
from ethos.repository.registry.commands import PUBLIC_WORKFLOW_COMMANDS
from ethos.repository.registry.commands import READER_VIEW_COMMANDS
from ethos.repository.registry.commands import SCORECARD_COMMANDS
from ethos.repository.registry.profiles import governance_profile_report
from ethos_core.contracts.docs.topology import required_docs_topology_paths
from ethos_core.kernel import KERNEL_CHAIN
from ethos_core.normalization.core import string_mapping as _mapping
from ethos_core.normalization.core import string_sequence as _string_list

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from pathlib import Path

KERNEL_CHAIN_TEXT = "Authority -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle"
REQUIRED_PRODUCT_DOCS: tuple[str, ...] = (
    "README.md",
    "docs/governance/product-design-contract.md",
    "docs/reference/command-plane.md",
    "docs/reference/glossary.md",
    "openspec/specs/repository-governance/spec.md",
    "openspec/specs/contracts/spec.md",
)
REQUIRED_PRODUCT_DOC_PHRASE_GROUPS: Mapping[str, tuple[tuple[str, ...], ...]] = {
    "README.md": (
        ("Isomorphic Governance",),
        (
            "same kernel",
            "authority",
            "subject",
            "commitment",
            "change",
            "evidence",
            "claim",
            "chronicle",
        ),
        ("profiles and adapters",),
        ("not product cloning",),
        ("same commands", "transition questions"),
    ),
    "docs/governance/product-design-contract.md": (
        tuple(KERNEL_CHAIN),
        ("same kernel", "governs both cases"),
        ("profile", "checks", "adapters", "proof depth"),
        ("does not change", "subject kind", "command"),
        ("do not create separate command planes",),
    ),
    "docs/reference/command-plane.md": (
        ("same transition", "command semantics"),
        ("`transition_commands`",),
        ("`reader_view_commands`",),
        ("`scorecard_commands`",),
        ("profile", "adapter boundary"),
    ),
    "docs/reference/glossary.md": (
        ("Isomorphic Governance",),
        ("same kernel",),
        ("profiles and adapters",),
        ("not", "product cloning"),
    ),
    "openspec/specs/repository-governance/spec.md": (
        ("same transition command semantics",),
        ("not a second command plane",),
        ("read-only reader-view",),
        ("read-only scorecard command",),
    ),
    "openspec/specs/contracts/spec.md": (
        ("transition, reader-view, and scorecard command semantics",),
        ("shared governance context contract",),
    ),
}
REQUIRED_PROFILE_IDS = ("product-adopter", "self-governance")
SHARED_PROFILE_FIELDS = (
    "capability_graph",
    "kernel_chain",
    "trust_lifecycle",
    "run_steps",
    "truth_sources",
    "advisory_projections",
)
ALLOWED_DIFFERENCE_FIELDS = (
    "authority_binding",
    "profile_config",
    "adapter_binding",
    "strictness",
    "rollout",
)


def governance_kernel_report(root: Path) -> dict[str, object]:
    """Audit the single governed-repository kernel across product and adoption paths."""
    context = context_for_root(root)
    profiles = governance_profile_report()
    generic_plan = adoption_plan(root / "__ethos_generic_probe__", profile="generic", apply=False)

    checks = {
        "runtime-governance-context": _runtime_context_check(context),
        "profile-isomorphism": _profile_isomorphism_check(profiles),
        "product-docs": _product_docs_check(root),
        "generic-adoption-scaffold": _generic_adoption_scaffold_check(generic_plan),
    }
    required_gaps = _dedupe(
        gap for check in checks.values() for gap in _string_list(check.get("required_gaps"))
    )
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "summary": {
            "check_count": len(checks),
            "closed_check_count": sum(1 for check in checks.values() if check.get("ok")),
            "gap_count": len(required_gaps),
            "kernel_chain": KERNEL_CHAIN_TEXT,
            "transition_command_count": len(PUBLIC_WORKFLOW_COMMANDS),
        },
        "required_gaps": required_gaps,
        "checks": checks,
        "boundary": {
            "kernel": list(KERNEL_CHAIN),
            "subject_kind": "repository",
            "product_and_adopters": "same_kernel_profile_or_adapter_differences_only",
            "transition_commands": list(PUBLIC_WORKFLOW_COMMANDS),
            "reader_view_commands": list(READER_VIEW_COMMANDS),
            "scorecard_commands": list(SCORECARD_COMMANDS),
            "forbidden": [
                "second_command_plane",
                "product_cloning",
                "profile_changes_kernel",
                "adopter_specific_product_authority",
            ],
        },
    }


def _runtime_context_check(context: Mapping[str, object]) -> dict[str, object]:
    subject = _mapping(context.get("subject"))
    authority = _mapping(context.get("authority"))
    required_gaps = _dedupe(
        [
            *_field_gaps(
                value=context.get("contract"),
                expected="governed_repository",
                gap="governance_kernel_contract_mismatch",
            ),
            *_field_gaps(
                value=context.get("single_kernel"),
                expected=True,
                gap="governance_kernel_single_kernel_missing",
            ),
            *_list_field_gaps(
                value=context.get("kernel_chain"),
                expected=KERNEL_CHAIN,
                gap="governance_kernel_chain_mismatch",
            ),
            *_list_field_gaps(
                value=context.get("transition_commands"),
                expected=PUBLIC_WORKFLOW_COMMANDS,
                gap="governance_kernel_transition_commands_mismatch",
            ),
            *_list_field_gaps(
                value=context.get("shared_commands"),
                expected=PUBLIC_WORKFLOW_COMMANDS,
                gap="governance_kernel_shared_commands_mismatch",
            ),
            *_list_field_gaps(
                value=context.get("reader_view_commands"),
                expected=READER_VIEW_COMMANDS,
                gap="governance_kernel_reader_views_mismatch",
            ),
            *_list_field_gaps(
                value=context.get("scorecard_commands"),
                expected=SCORECARD_COMMANDS,
                gap="governance_kernel_scorecards_mismatch",
            ),
            *_field_gaps(
                value=subject.get("kind"),
                expected="repository",
                gap="governance_kernel_subject_not_repository",
            ),
            *_field_gaps(
                value=context.get("truth_boundary"),
                expected="repository",
                gap="governance_kernel_truth_boundary_mismatch",
            ),
            *_field_gaps(
                value=context.get("profile_boundary"),
                expected="profile_or_adapter",
                gap="governance_kernel_profile_boundary_mismatch",
            ),
            *(
                []
                if authority.get("policy_refs")
                else ["governance_kernel_authority_policy_refs_missing"]
            ),
        ]
    )
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "required_gaps": required_gaps,
        "summary": {
            "contract": context.get("contract"),
            "profile": context.get("profile"),
            "subject_kind": subject.get("kind"),
            "single_kernel": context.get("single_kernel"),
        },
    }


def _field_gaps(*, value: object, expected: object, gap: str) -> list[str]:
    return [] if value == expected else [gap]


def _list_field_gaps(*, value: object, expected: Iterable[str], gap: str) -> list[str]:
    return [] if _string_list(value) == [str(item) for item in expected] else [gap]


def _profile_isomorphism_check(report: Mapping[str, object]) -> dict[str, object]:
    profiles = _mapping(report.get("profiles"))
    payloads = _profile_payloads(profiles)
    required_gaps = _dedupe(
        [
            *_string_list(report.get("required_gaps")),
            *_missing_profile_gaps(profiles),
            *(
                []
                if report.get("isomorphic") is True
                else ["governance_kernel_profiles_not_isomorphic"]
            ),
            *_shared_profile_field_gaps(payloads),
            *_allowed_difference_gaps(payloads),
            *_shared_kernel_gaps(_mapping(report.get("shared_kernel"))),
        ]
    )
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "required_gaps": required_gaps,
        "summary": {
            "profile_count": len(profiles),
            "isomorphic": report.get("isomorphic"),
            "allowed_differences": _string_list(report.get("allowed_differences")),
        },
    }


def _profile_payloads(profiles: Mapping[str, object]) -> dict[str, dict[str, object]]:
    return {profile_id: _mapping(profiles.get(profile_id)) for profile_id in REQUIRED_PROFILE_IDS}


def _missing_profile_gaps(profiles: Mapping[str, object]) -> list[str]:
    return [
        f"governance_kernel_profile_missing:{profile_id}"
        for profile_id in REQUIRED_PROFILE_IDS
        if profile_id not in profiles
    ]


def _shared_profile_field_gaps(payloads: Mapping[str, Mapping[str, object]]) -> list[str]:
    if any(not payloads.get(profile_id) for profile_id in REQUIRED_PROFILE_IDS):
        return []
    reference = payloads[REQUIRED_PROFILE_IDS[0]]
    gaps: list[str] = []
    for field in SHARED_PROFILE_FIELDS:
        expected = _string_list(reference.get(field))
        for profile_id in REQUIRED_PROFILE_IDS[1:]:
            payload = payloads[profile_id]
            if _string_list(payload.get(field)) != expected:
                gaps.append(f"governance_kernel_profile_field_mismatch:{profile_id}:{field}")
    return gaps


def _allowed_difference_gaps(payloads: Mapping[str, Mapping[str, object]]) -> list[str]:
    gaps: list[str] = []
    for profile_id in REQUIRED_PROFILE_IDS:
        payload = payloads.get(profile_id, {})
        for field in ALLOWED_DIFFERENCE_FIELDS:
            value = payload.get(field)
            if value in (None, "", (), []):
                gaps.append(f"governance_kernel_allowed_difference_missing:{profile_id}:{field}")
    return gaps


def _shared_kernel_gaps(shared: Mapping[str, object]) -> list[str]:
    return _list_field_gaps(
        value=shared.get("kernel_chain"),
        expected=KERNEL_CHAIN,
        gap="governance_kernel_shared_kernel_chain_mismatch",
    )


def _product_docs_check(root: Path) -> dict[str, object]:
    required_gaps: list[str] = []
    for rel in REQUIRED_PRODUCT_DOCS:
        path = root / rel
        if not path.exists():
            required_gaps.append(f"governance_kernel_doc_missing:{rel}")
            continue
        text = path.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        for phrase_group in REQUIRED_PRODUCT_DOC_PHRASE_GROUPS[rel]:
            if not all(phrase in normalized for phrase in phrase_group):
                label = "+".join(phrase_group)
                required_gaps.append(f"governance_kernel_doc_phrase_missing:{rel}:{label}")
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "required_gaps": required_gaps,
        "summary": {
            "doc_count": len(REQUIRED_PRODUCT_DOCS),
            "phrase_group_count": sum(
                len(groups) for groups in REQUIRED_PRODUCT_DOC_PHRASE_GROUPS.values()
            ),
        },
    }


def _generic_adoption_scaffold_check(plan: Mapping[str, object]) -> dict[str, object]:
    required_gaps = _string_list(plan.get("required_gaps"))
    planned_files = set(_string_list(plan.get("planned_files")))
    docs_kernel = set(required_docs_topology_paths())
    missing_docs = sorted(docs_kernel - planned_files)
    required_gaps.extend(
        f"governance_kernel_generic_docs_path_missing:{path}" for path in missing_docs
    )
    if plan.get("profile") != "generic":
        required_gaps.append("governance_kernel_generic_profile_mismatch")
    if plan.get("applied") is not False:
        required_gaps.append("governance_kernel_generic_probe_mutated")
    for path in (
        "AGENTS.md",
        ".ethos/workspace.toml",
        "openspec/specs/kernel/spec.md",
        "openspec/specs/repository-governance/spec.md",
        "docs/governance/ethos.md",
    ):
        if path not in planned_files:
            required_gaps.append(f"governance_kernel_generic_scaffold_missing:{path}")
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "required_gaps": _dedupe(required_gaps),
        "summary": {
            "profile": plan.get("profile"),
            "planned_file_count": len(planned_files),
            "docs_kernel_path_count": len(docs_kernel),
        },
    }


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
