"""Quality command group — determinism, gates, proof-policy, docs, and coupling.

The largest surface command group (29 commands). Binds args, calls domain/repository
reports, emits. Registers onto the shared quality_app from _base; cli.py imports this
module so the decorators run. Imports only what this group needs — so the heavy
quality/repository deps load only when this group is imported (lazy path).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.git as git_adapter
import ethos.domain.prove as prove_domain
import ethos.repository.audit as repository_audit_module
import ethos.repository.release.core as release_policy_module
import ethos.surface.cli.results.tool as tool_results
from ethos.adapters.config import rules_config
from ethos.adapters.gates.signature import signature_policy_report
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun
from ethos.repository.evidence.core import provenance_envelope
from ethos.repository.policy.coupling.core import coupling_audit_report
from ethos.repository.policy.docs.topology import docs_topology_report
from ethos.repository.policy.gates import gate_registry
from ethos.repository.registry.docs.quality import docs_quality_report
from ethos.repository.registry.standards import standard_adapter_registry
from ethos.repository.release.attestation import release_attestation
from ethos.repository.release.attestation import sbom_projection
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos.surface.cli.quality.reporting import build_declarative_report_result
from ethos.surface.cli.quality.reporting import compile_report_handlers
from ethos_core.contracts.commands import ReportHandlerDeclaration
from ethos_core.contracts.commands import load_command_registry_declaration
from ethos_core.contracts.package.ontology import package_ontology_report
from ethos_core.contracts.package.ontology import workspace_package_config_report
from ethos_core.quality.docs.profile import docs_quality_profile
from ethos_core.quality.profiles import product_quality_profile
from ethos_core.quality.profiles import tool_profiles
from ethos_core.quality.proof.policy import proof_lattice

if TYPE_CHECKING:
    from pathlib import Path


_HANDLER = ReportHandlerDeclaration(
    diagnostics_path=("diagnostics",),
    data_path=("data",),
    next_actions_path=("next_actions",),
)
type _Data = Mapping[str, object]
_FORMAT_KEYS = ("formats", "artifacts", "determinism", "standards")
_PROJECTION_FIELDS = ("ok", "state", "summary", "required_gaps", "next_actions", "diagnostics")
type _Projection = tuple[object, ...]
_J = JsonFlag


def _finish(
    command: str, data: _Data, json: _J, projection: _Projection = (), **fields: object
) -> None:
    projected = dict(zip(_PROJECTION_FIELDS, projection, strict=False))
    report = {"ok": True, "data": data, **projected, **fields}
    result = build_declarative_report_result(command=command, handler=_HANDLER, report=report)
    emit(result, json_output=json, enforce=False)


def _missing(root: Path, items: list[str], prefix: str = "") -> list[str]:
    return [f"{prefix}{item}" for item in items if not (root / f"{prefix}{item}").exists()]


_product_quality_profile = product_quality_profile


def _proof_lattice(_root: Path) -> object:
    return proof_lattice()


_tool_profiles = tool_profiles


def _standard_adapter_registry(_root: Path) -> object:
    return standard_adapter_registry()


def _standards_report(root: Path) -> object:
    return {"adapters": _standard_adapter_registry(root)}


def _sbom_report(root: Path) -> object:
    return {"sbom": sbom_projection(root)}


def _gate_registry_report(root: Path) -> dict[str, object]:
    return {"gates": {gate_id: gate.to_dict() for gate_id, gate in gate_registry(root).items()}}


def _release_file_report(root: Path) -> dict[str, object]:
    release_files = repository_audit_module.release_files_report(root)
    return {
        "ok": bool(release_files["ok"]),
        "state": "ready" if release_files["ok"] else "blocked",
        "required_gaps": release_files["missing"],
        "release_files": release_files,
        "host_profile": release_policy_module.release_policy_report(root)["host_profile"],
    }


def quality_docs(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
    """Report documentation quality profile, registry health, and topology."""
    repo = resolve_root(root)
    profile = docs_quality_profile()
    report, topology = docs_quality_report(repo), docs_topology_report(repo)
    required_gaps = tuple(cast("list[str]", report["required_gaps"])) + tuple(
        cast("list[str]", topology["required_gaps"])
    )
    ok = bool(report["ok"]) and bool(topology["ok"])
    data = {
        "profile": profile,
        "style_goals": profile["style_goals"],
        "health": report,
        "topology": topology,
    }
    _finish("quality docs", data, json_output, ok=ok, required_gaps=required_gaps)


def format_policy(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
    """Report format-policy readiness."""
    policy = rules_config(resolve_root(root))
    gaps = () if policy else ("format_policy_missing:.ethos/rules.toml",)
    data = {"source": ".ethos/rules.toml"} | {key: policy.get(key, {}) for key in _FORMAT_KEYS}
    _finish("quality format-policy", data, json_output, ok=not gaps, required_gaps=gaps)


def package_ontology(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
    """Report target package ontology and migration-host state."""
    repo = resolve_root(root)
    contract = package_ontology_report()
    target_packages = cast("list[str]", contract["target_packages"])
    migration_hosts = cast("list[str]", contract["migration_hosts"])
    target_distributions = cast("list[str]", contract["target_distributions"])
    migration_distributions = cast("dict[str, object]", contract["migration_distributions"])
    target_missing = _missing(repo, target_packages, "packages/")
    host_missing = _missing(repo, migration_hosts, "packages/")
    distribution_missing = _missing(repo, target_distributions)
    workspace_config = workspace_package_config_report(repo)
    workspace_config_gaps = list(cast("list[str]", workspace_config["required_gaps"]))
    migration_complete = not migration_hosts and all(
        item.get("state") == "migrated"
        for item in migration_distributions.values()
        if isinstance(item, dict)
    )
    physical_missing = target_missing + host_missing + distribution_missing
    data = {
        **contract,
        "physical_target_homes_present": not target_missing and not distribution_missing,
        "migration_complete": migration_complete,
        "migration_status": "complete" if migration_complete else "in_progress",
        "missing": physical_missing + workspace_config_gaps,
        "distribution_status": migration_distributions,
        "workspace_config": workspace_config,
    }
    summary = {
        "target_package_count": len(target_packages),
        "migration_host_count": len(migration_hosts),
        "migration_status": data["migration_status"],
    }
    gaps = tuple(
        [f"package_ontology_missing:{item}" for item in physical_missing] + workspace_config_gaps
    )
    projection = (
        *(not data["missing"], "tracked" if not data["missing"] else "gapped", summary, gaps),
        ("ethos repository audit",),
    )
    _finish("quality package-ontology", data, json_output, projection)


def coupling_audit(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
    """Report product, profile, adapter, and product-toolchain coupling boundaries."""
    repo = resolve_root(root)
    report = coupling_audit_report(repo)
    validation = prove_domain.command_data_validation(
        repo,
        schema_name="coupling-audit.schema.json",
        payload=report,
    )
    validation_gaps = tuple(
        f"coupling_audit_schema:{gap}" for gap in cast("list[str]", validation["required_gaps"])
    )
    ok = bool(report["ok"]) and bool(validation["ok"])
    gaps = tuple(cast("list[str]", report["required_gaps"])) + validation_gaps
    projection = (ok, "", {}, gaps, (), (validation,))
    _finish("quality coupling-audit", report, json_output, projection)


def commits(
    *, enforce_head: bool = False, root: RootOption | None = None, json_output: JsonFlag = False
) -> None:
    """Report commit naming and signature policy."""
    report = signature_policy_report(resolve_root(root))
    gaps = list(cast("list[str]", report["required_gaps"]))
    if enforce_head and not report["head_subject_ok"]:
        gaps.append("head_subject_not_conventional")
    if enforce_head and not report["head_signature_ok"]:
        gaps.append("head_signature_not_good")
    data = {**report, "enforce_head": enforce_head}
    _finish("quality commits", data, json_output, ok=not gaps, required_gaps=tuple(gaps))


def release_attestation_command(
    *,
    evidence_digest: str = "planned",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit a parameterized release-attestation projection without publishing it."""
    repo = resolve_root(root)
    attestation = release_attestation(
        repo, head=git_adapter.current_head(repo), evidence_digest=evidence_digest
    )
    projection = (True, "ready", {"tag": attestation["predicate"]["tag"]})
    _finish("quality release-attestation", {"attestation": attestation}, json_output, projection)


QUALITY_DECLARATIONS = load_command_registry_declaration().group("quality")
REPORT_COMMANDS = compile_report_handlers(
    declarations=QUALITY_DECLARATIONS,
    import_path_prefix="ethos.surface.cli.quality.core:",
)
TOOL_COMMANDS = tool_results.compile_quality_tool_handlers(
    declarations=QUALITY_DECLARATIONS,
    import_path_prefix="ethos.surface.cli.quality.core:",
)
globals().update(
    {function_name: command.make_handler() for function_name, command in REPORT_COMMANDS.items()}
    | TOOL_COMMANDS
)


def provenance(
    *,
    objective: str = "ethos provenance",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit a provenance envelope for a planned ETHOS proof."""
    repo = resolve_root(root)
    evidence = EvidenceSet.from_runs(
        evidence_id=f"ethos:{objective}",
        head=git_adapter.current_head(repo),
        runs=(ProofRun("planned-proof", ("ethos", "prove", "--json"), None, "", "", "planned"),),
        durability="local",
    )
    data = {
        "evidence": evidence.to_dict(),
        "provenance": provenance_envelope(evidence),
    }
    projection = (True, "ready", {"evidence_digest": evidence.digest}, (), ("ethos prove --json",))
    _finish("quality provenance", data, json_output, projection)
