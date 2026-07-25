from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.kernel import KERNEL_CHAIN
from ethos.normalization.core import string_mapping
from ethos.normalization.core import string_sequence
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.context import context_for_root
from ethos.repository.registry.commands import PUBLIC_WORKFLOW_COMMANDS
from ethos.repository.registry.profiles import governance_profile_report

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
        ("status is the singular reader",),
    ),
    "openspec/specs/contracts/spec.md": (
        ("singular lifecycle command semantics",),
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
    adoption_plan_result = adoption_plan(root / "__ethos_adoption_probe__", apply=False)

    checks = {
        "runtime-governance-context": _runtime_context_check(context),
        "profile-isomorphism": _profile_isomorphism_check(profiles),
        "product-docs": _product_docs_check(root),
        "minimal-adoption-binding": _minimal_adoption_binding_check(adoption_plan_result),
    }
    required_gaps = _dedupe(
        gap for check in checks.values() for gap in string_sequence(check.get("required_gaps"))
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
            "forbidden": [
                "second_command_plane",
                "product_cloning",
                "profile_changes_kernel",
                "adopter_specific_product_authority",
            ],
        },
    }


def _runtime_context_check(context: Mapping[str, object]) -> dict[str, object]:
    subject = string_mapping(context.get("subject"))
    authority = string_mapping(context.get("authority"))
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
    return [] if string_sequence(value) == [str(item) for item in expected] else [gap]


def _profile_isomorphism_check(report: Mapping[str, object]) -> dict[str, object]:
    profiles = string_mapping(report.get("profiles"))
    payloads = _profile_payloads(profiles)
    required_gaps = _dedupe(
        [
            *string_sequence(report.get("required_gaps")),
            *_missing_profile_gaps(profiles),
            *(
                []
                if report.get("isomorphic") is True
                else ["governance_kernel_profiles_not_isomorphic"]
            ),
            *_shared_profile_field_gaps(payloads),
            *_allowed_difference_gaps(payloads),
            *_shared_kernel_gaps(string_mapping(report.get("shared_kernel"))),
        ]
    )
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "required_gaps": required_gaps,
        "summary": {
            "profile_count": len(profiles),
            "isomorphic": report.get("isomorphic"),
            "allowed_differences": string_sequence(report.get("allowed_differences")),
        },
    }


def _profile_payloads(profiles: Mapping[str, object]) -> dict[str, dict[str, object]]:
    return {
        profile_id: string_mapping(profiles.get(profile_id)) for profile_id in REQUIRED_PROFILE_IDS
    }


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
        expected = string_sequence(reference.get(field))
        for profile_id in REQUIRED_PROFILE_IDS[1:]:
            payload = payloads[profile_id]
            if string_sequence(payload.get(field)) != expected:
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


def _minimal_adoption_binding_check(plan: Mapping[str, object]) -> dict[str, object]:
    required_gaps = string_sequence(plan.get("required_gaps"))
    planned_files = set(string_sequence(plan.get("planned_files")))
    if plan.get("applied") is not False:
        required_gaps.append("governance_kernel_adoption_probe_mutated")
    if ".ethos/profile.toml" not in planned_files:
        required_gaps.append("governance_kernel_adoption_binding_missing:.ethos/profile.toml")
    required_gaps.extend(
        f"governance_kernel_adoption_surface_unexpected:{path}"
        for path in sorted(planned_files - {".ethos/profile.toml"})
    )
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "required_gaps": _dedupe(required_gaps),
        "summary": {
            "planned_file_count": len(planned_files),
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
