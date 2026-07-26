"""Plan-stage domain reducers — PlanIR, rule→gate matching, rule-fact snapshot.

Pure logic fed by adapters (rules config, workspace status) and the kernel (action
graph types). The rule-fact snapshot composes governance facts from lower-layer
reports; all imports flow downward (contracts / repository / adapters), keeping the
surface→domain→... layering acyclic.
"""

from __future__ import annotations

import fnmatch
import tomllib
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.config import rules_config
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.status.core import workspace_status
from ethos.assistants.projections import projection_contract
from ethos.contracts.context.projection import ASSISTANT_TRUTH_BOUNDARY
from ethos.contracts.rules import RuleAttestation
from ethos.contracts.rules import RuleFactSnapshot
from ethos.contracts.rules import stable_digest
from ethos.contracts.semantic import ChangeContract
from ethos.contracts.semantic import load_change_contract_file
from ethos.domain.status import audit_for_root
from ethos.domain.status import status_worktree_gaps
from ethos.normalization.core import string_list
from ethos.repository.openspec.audit import tasks_complete
from ethos.repository.policy.rules.config import resolve_profile_stack

if TYPE_CHECKING:
    from pathlib import Path


def _contract_payload(
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


def _normalize_contract_payload(payload: dict[str, object]) -> dict[str, object]:
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
            _normalize_contract_payload(
                _contract_payload(
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
    """Load one active OpenSpec ChangeContract carrier and bind its repository subject."""
    if change_id is None:
        carriers = _change_contract_ids(repo, tree_ref=tree_ref)
        if len(carriers) != 1:
            kind = "missing" if not carriers else "ambiguous"
            message = f"change_contract_{kind}"
            raise ValueError(message)
        change_id = carriers[0]
    elif _change_contract_complete(repo, change_id, tree_ref=tree_ref):
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
    normalized = _normalize_contract_payload(
        _contract_payload(path, missing_gap=message, root=repo, tree_ref=tree_ref)
    )
    normalized["subjects"] = tuple(
        repository_contract.id if subject == "repository:self" else str(subject)
        for subject in normalized.get("subjects", ())
    )
    return ChangeContract.model_validate(normalized)


def load_proof_contract(
    repo: Path,
    *,
    change_id: str | None = None,
    tree_ref: str | None = None,
) -> ChangeContract:
    """Load one selected change contract, or the repository contract when none exists."""
    try:
        return load_change_contract(repo, change_id=change_id, tree_ref=tree_ref)
    except ValueError as exc:
        if change_id is not None or str(exc) != "change_contract_missing":
            raise
        return load_repository_contract(repo, tree_ref=tree_ref)


def _change_contract_ids(repo: Path, *, tree_ref: str | None) -> list[str]:
    if tree_ref is None:
        return sorted(
            path.parent.name
            for path in (repo / "openspec" / "changes").glob("*/contract.toml")
            if not _change_contract_complete(repo, path.parent.name, tree_ref=None)
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
        and not _change_contract_complete(
            repo,
            path.removeprefix("openspec/changes/").removesuffix(suffix),
            tree_ref=tree_ref,
        )
    )


def _change_contract_complete(repo: Path, change_id: str, *, tree_ref: str | None) -> bool:
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


def path_matches(path: str, pattern: str) -> bool:
    """Match a path against a rule pattern (supports trailing /** prefix globs)."""
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(f"{prefix}/")
    return fnmatch.fnmatchcase(path, pattern)


def matching_rule_gates(
    root: Path,
    paths: tuple[str, ...],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str]]:
    """Match paths to rules and gates, returning profile validation gaps."""
    config = rules_config(root)
    profile_stack, profile_gaps = resolve_profile_stack(config)
    if profile_gaps:
        return [], [], profile_gaps
    gates = config.get("gates") if isinstance(config.get("gates"), dict) else {}
    matched_rules: list[dict[str, object]] = []
    required_gates: list[dict[str, object]] = []
    active_profiles = set(profile_stack)
    rules = config.get("rule") if isinstance(config.get("rule"), list) else []
    for raw_rule in cast("list[object]", rules):
        if not isinstance(raw_rule, dict):
            continue
        profile_layers = string_list(raw_rule.get("profile_layers"))
        if profile_layers and active_profiles.isdisjoint(profile_layers):
            continue
        matched_paths = [
            path
            for path in paths
            if any(
                path_matches(path, pattern)
                for pattern in string_list(raw_rule.get("path_globs", raw_rule.get("paths")))
            )
        ]
        if not matched_paths:
            continue
        rule_gates: list[dict[str, object]] = []
        for gate_id in string_list(raw_rule.get("required_gates", raw_rule.get("requires"))):
            gate_config = gates.get(gate_id, {}) if isinstance(gates, dict) else {}
            gate: dict[str, object] = {
                "id": gate_id,
                "command": (
                    str(gate_config.get("command", "")) if isinstance(gate_config, dict) else ""
                ),
                "blocking": gate_config.get("blocking", True) is not False
                if isinstance(gate_config, dict)
                else True,
            }
            rule_gates.append(gate)
            required_gates.append(gate)
        matched_rules.append(
            {
                "id": str(raw_rule.get("id", "")),
                "risk": str(
                    raw_rule.get("risk")
                    or raw_rule.get("subject")
                    or raw_rule.get("stop_condition")
                    or ""
                ),
                "matched_paths": matched_paths,
                "required_gates": rule_gates,
                "evidence": string_list(
                    raw_rule.get("evidence_requirements", raw_rule.get("evidence"))
                ),
            }
        )
    return matched_rules, required_gates, []


def rule_fact(
    *,
    owner: str,
    value: object,
    fresh: bool = True,
    available: bool = True,
) -> dict[str, object]:
    """Build a rule-evaluation fact envelope (owner, freshness, availability, digest)."""
    return {
        "owner": owner,
        "fresh": fresh,
        "available": available,
        "value": value,
        "digest": stable_digest(value),
    }


def unavailable_rule_fact(owner: str, exc: BaseException) -> dict[str, object]:
    """Build a fact marking a source unavailable due to an exception."""
    return rule_fact(
        owner=owner,
        fresh=False,
        available=False,
        value={"error": type(exc).__name__, "message": str(exc)},
    )


def rule_fact_snapshot(
    repo: Path,
    *,
    phase: str,
    head: str,
    changed_paths: tuple[str, ...] = (),
    mutation: bool = False,
    authorized: bool = False,
    actor: str = "local",
    scope: str = "repository",
    status_payload: dict[str, object] | None = None,
    prewrite_report: dict[str, object] | None = None,
    audit_payload: dict[str, object] | None = None,
) -> RuleFactSnapshot:
    """Compose the governance rule-fact snapshot for a phase from lower-layer reports."""
    facts: dict[str, dict[str, object]] = {
        "changed_paths": rule_fact(
            owner="ethos-adapters.status",
            value=list(changed_paths),
        ),
        "mutation": rule_fact(owner="ethos-cli", value=mutation),
        "authorization": rule_fact(owner="ethos-cli", value=authorized),
        "actor": rule_fact(owner="ethos-cli", value=actor),
        "scope": rule_fact(owner="ethos-cli", value=scope),
    }
    source_refs = [
        "ethos-adapters.status",
        "ethos-repository.self-audit",
        "ethos-assistants.projections",
    ]
    try:
        status = status_payload if status_payload is not None else workspace_status(repo)
        facts["worktree"] = rule_fact(
            owner="ethos-adapters.status",
            value={
                "branch": status.get("branch", ""),
                "role": status.get("role", ""),
                "changed_paths": status.get("changed_paths", []),
                "required_gaps": status_worktree_gaps(status),
            },
        )
    except BaseException as exc:  # pragma: no cover - defensive adapter boundary.
        facts["worktree"] = unavailable_rule_fact("ethos-adapters.status", exc)
    if prewrite_report is not None:
        source_refs.append("ethos-adapters.prewrite")
        facts["prewrite"] = rule_fact(
            owner="ethos-adapters.prewrite",
            value={
                "ok": prewrite_report.get("ok", False),
                "role": prewrite_report.get("role", ""),
                "required_gaps": prewrite_report.get("required_gaps", []),
                "paths": prewrite_report.get("paths", []),
            },
        )
    elif phase == "prewrite":
        source_refs.append("ethos-adapters.prewrite")
        facts["prewrite"] = rule_fact(
            owner="ethos-adapters.prewrite",
            value={"required_gaps": ["prewrite_guard_not_supplied"]},
            fresh=False,
            available=False,
        )
    else:
        facts["prewrite"] = rule_fact(
            owner="ethos-adapters.prewrite",
            value={"ok": True, "required_gaps": [], "not_applicable": True},
        )
    try:
        audit = audit_payload if audit_payload is not None else audit_for_root(repo)
        facts["openspec_state"] = rule_fact(
            owner="ethos-repository.self-audit",
            value=audit.get("openspec", {}),
        )
        facts["host_readiness"] = rule_fact(
            owner="ethos-repository.self-audit",
            value={
                "mode": audit.get("mode", "product"),
                "ok": audit.get("ok", False),
                "required_gaps": audit.get("required_gaps", []),
            },
        )
    except BaseException as exc:  # pragma: no cover - defensive adapter boundary.
        facts["openspec_state"] = unavailable_rule_fact("ethos-repository.self-audit", exc)
        facts["host_readiness"] = unavailable_rule_fact("ethos-repository.self-audit", exc)
    try:
        projection = projection_contract()
        facts["projection_drift"] = rule_fact(
            owner="ethos-assistants.projections",
            value={
                "truth": projection.get("truth", ""),
                "ok": projection.get("truth", "") == ASSISTANT_TRUTH_BOUNDARY,
            },
        )
    except BaseException as exc:  # pragma: no cover - defensive adapter boundary.
        facts["projection_drift"] = unavailable_rule_fact("ethos-assistants.projections", exc)
    return RuleFactSnapshot(
        phase=phase,
        head=head,
        facts=facts,
        source_refs=tuple(source_refs),
    )


def rule_attestation_for_evaluation(
    evaluation: dict[str, object],
    *,
    actor: str,
    scope: str,
) -> dict[str, object]:
    """Build the rule-attestation envelope from a rules evaluation (digest-bound)."""
    attestation = RuleAttestation(
        head=str(evaluation["head"]),
        evaluation_digest=str(evaluation["digest"]),
        rule_set_digest=str(evaluation["rule_set_digest"]),
        compiled_policy_digest=str(evaluation["compiled_policy_digest"]),
        fact_snapshot_digest=str(evaluation["fact_snapshot_digest"]),
        actor=actor,
        scope=scope,
        runner_identity="ethos-cli",
        input=dict(cast("dict[str, object]", evaluation["input_snapshot"])),
        output={
            "state": evaluation["state"],
            "required_gaps": list(cast("list[object]", evaluation["required_gaps"])),
            "required_gates": list(cast("list[object]", evaluation["required_gates"])),
        },
    )
    return attestation.to_dict()
