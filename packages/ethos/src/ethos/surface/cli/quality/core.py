"""Quality command group — determinism, gates, proof-policy, docs, and coupling.

The largest surface command group (29 commands). Binds args, calls domain/repository
reports, emits. Registers onto the shared quality_app from _base; cli.py imports this
module so the decorators run. Imports only what this group needs — so the heavy
quality/repository deps load only when this group is imported (lazy path).
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.git as git_adapter
import ethos.domain.prove as prove_domain
import ethos.repository.audit as repository_audit_module
import ethos.repository.release.core as release_policy_module
import ethos.surface.cli.results.tool as tool_results
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
from ethos_core.contracts.commands import ReportDataField
from ethos_core.contracts.commands import ReportHandlerDeclaration
from ethos_core.contracts.commands import load_command_registry_declaration
from ethos_core.contracts.package.ontology import package_ontology_report
from ethos_core.contracts.package.ontology import workspace_package_config_report
from ethos_core.quality.docs.profile import docs_quality_profile
from ethos_core.quality.profiles import product_quality_profile
from ethos_core.quality.profiles import tool_profiles
from ethos_core.quality.proof.policy import proof_lattice
from ethos_core.result import EthosResult

if TYPE_CHECKING:
    from pathlib import Path


def _product_quality_profile(_root: Path) -> object:
    return product_quality_profile()


def _proof_lattice(_root: Path) -> object:
    return proof_lattice()


def _tool_profiles(_root: Path) -> object:
    return tool_profiles()


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
    policy = release_policy_module.release_policy_report(root)
    return {
        "ok": bool(release_files["ok"]),
        "state": "ready" if release_files["ok"] else "blocked",
        "required_gaps": release_files["missing"],
        "release_files": release_files,
        "host_profile": policy["host_profile"],
    }


def _release_attestation_report(root: Path, *, evidence_digest: str) -> dict[str, object]:
    attestation = release_attestation(
        root=root,
        head=git_adapter.current_head(root),
        evidence_digest=evidence_digest,
    )
    return {
        "ok": True,
        "state": "ready",
        "summary": {"tag": attestation["predicate"]["tag"]},
        "attestation": attestation,
    }


def quality_docs(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report documentation quality profile, registry health, and topology."""
    repo = resolve_root(root)
    profile = docs_quality_profile()
    report = docs_quality_report(repo)
    topology = docs_topology_report(repo)
    required_gaps = tuple(cast("list[str]", report["required_gaps"])) + tuple(
        cast("list[str]", topology["required_gaps"])
    )
    ok = bool(report["ok"]) and bool(topology["ok"])
    result = EthosResult(
        command="quality docs",
        ok=ok,
        state="clean" if ok else "blocked",
        required_gaps=required_gaps,
        data={
            "profile": profile,
            "style_goals": profile["style_goals"],
            "health": report,
            "topology": topology,
        },
    )
    emit(result, json_output=json_output, enforce=False)


def markdown_links(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run markdown link checks through the configured adapter."""
    repo = resolve_root(root)
    files = [
        path
        for path in git_adapter.git_files(repo, "*.md")
        if not path.startswith(("evidence/", "docs/archive/"))
    ]
    tool_results.emit_quality_tool_result(
        root=repo,
        gate_id="markdown-links",
        tool="lychee",
        command=[
            "lychee",
            "--config",
            ".config/checks/lychee/lychee.toml",
            "--no-progress",
            *files,
        ],
        files=files,
        result_command="quality markdown-links",
        json_output=json_output,
    )


def shell_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run shell script lint checks through ShellCheck."""
    repo = resolve_root(root)
    files = git_adapter.git_files(repo, "*.sh")
    tool_results.emit_quality_tool_result(
        root=repo,
        gate_id="shell-lint",
        tool="bash",
        command=["bash", "tools/ci/scripts/run-shell-lint.sh", *files],
        files=files,
        result_command="quality shell",
        json_output=json_output,
    )


def toml_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run TOML syntax and format checks through Taplo."""
    repo = resolve_root(root)
    files = git_adapter.git_files(repo, "*.toml")
    tool_results.emit_quality_tool_result(
        root=repo,
        gate_id="toml-config",
        tool="bash",
        command=["bash", "tools/ci/scripts/run-config-lint.sh", *files],
        files=files,
        result_command="quality toml",
        json_output=json_output,
    )


def yaml_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run YAML projection checks through yamllint."""
    repo = resolve_root(root)
    files = git_adapter.git_files(repo, "*.yml", "*.yaml")
    tool_results.emit_quality_tool_result(
        root=repo,
        gate_id="yaml-config",
        tool="bash",
        command=["bash", "tools/ci/scripts/run-config-lint.sh", *files],
        files=files,
        result_command="quality yaml",
        json_output=json_output,
    )


def npm_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run npm distribution pack smoke checks without publishing."""
    repo = resolve_root(root)
    files = ["package.json"] if (repo / "package.json").exists() else []
    tool_results.emit_quality_tool_result(
        root=repo,
        gate_id="npm-pack",
        tool="npm",
        command=["npm", "run", "test:npm"],
        files=files,
        result_command="quality npm",
        json_output=json_output,
    )


def format_policy(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report format-policy readiness."""
    repo = resolve_root(root)
    policy_path = repo / ".ethos" / "rules.toml"
    if policy_path.exists():
        policy = tomllib.loads(policy_path.read_text(encoding="utf-8"))
        gaps: tuple[str, ...] = ()
    else:
        policy = {}
        gaps = ("format_policy_missing:.ethos/rules.toml",)
    result = EthosResult(
        command="quality format-policy",
        ok=not gaps,
        state="clean" if not gaps else "blocked",
        required_gaps=gaps,
        data={
            "source": ".ethos/rules.toml",
            "formats": policy.get("formats", {}),
            "artifacts": policy.get("artifacts", {}),
            "determinism": policy.get("determinism", {}),
            "standards": policy.get("standards", {}),
        },
    )
    emit(result, json_output=json_output, enforce=False)


def package_ontology(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report target package ontology and migration-host state."""
    repo = resolve_root(root)
    contract = package_ontology_report()
    target_packages = cast("list[str]", contract["target_packages"])
    migration_hosts = cast("list[str]", contract["migration_hosts"])
    target_distributions = cast("list[str]", contract["target_distributions"])
    migration_distributions = cast("dict[str, object]", contract["migration_distributions"])
    target_missing = [
        f"packages/{package}"
        for package in target_packages
        if not (repo / "packages" / str(package)).exists()
    ]
    host_missing = [
        f"packages/{package}"
        for package in migration_hosts
        if not (repo / "packages" / str(package)).exists()
    ]
    distribution_missing = [
        distribution
        for distribution in target_distributions
        if not (repo / str(distribution)).exists()
    ]
    workspace_config = workspace_package_config_report(repo)
    workspace_config_gaps = [
        str(gap) for gap in cast("list[str]", workspace_config["required_gaps"])
    ]
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
    result = EthosResult(
        command="quality package-ontology",
        ok=not data["missing"],
        state="tracked" if not data["missing"] else "gapped",
        summary={
            "target_package_count": len(target_packages),
            "migration_host_count": len(migration_hosts),
            "migration_status": data["migration_status"],
        },
        required_gaps=tuple(
            [f"package_ontology_missing:{item}" for item in physical_missing]
            + workspace_config_gaps
        ),
        next_actions=("ethos repository audit",),
        data=data,
    )
    emit(result, json_output=json_output, enforce=False)


def coupling_audit(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
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
    result = EthosResult(
        command="quality coupling-audit",
        ok=ok,
        state="clean" if ok else "blocked",
        diagnostics=(validation,),
        required_gaps=tuple(cast("list[str]", report["required_gaps"])) + validation_gaps,
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


def commits(
    *,
    enforce_head: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report commit naming and signature policy."""
    repo = resolve_root(root)
    report = signature_policy_report(repo)
    gaps = list(cast("list[str]", report["required_gaps"]))
    if enforce_head and not report["head_subject_ok"]:
        gaps.append("head_subject_not_conventional")
    if enforce_head and not report["head_signature_ok"]:
        gaps.append("head_signature_not_good")
    result = EthosResult(
        command="quality commits",
        ok=not gaps,
        state="clean" if not gaps else "blocked",
        required_gaps=tuple(gaps),
        data={**report, "enforce_head": enforce_head},
    )
    emit(result, json_output=json_output, enforce=False)


def release_attestation_command(
    *,
    evidence_digest: str = "planned",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit a parameterized release-attestation projection without publishing it."""
    repo = resolve_root(root)
    result = build_declarative_report_result(
        command="quality release-attestation",
        handler=ReportHandlerDeclaration(
            provider="ethos.surface.cli.quality.core:_release_attestation_report",
            data_fields=(ReportDataField(name="attestation", path=("attestation",)),),
        ),
        report=_release_attestation_report(repo, evidence_digest=evidence_digest),
    )
    emit(result, json_output=json_output, enforce=False)


REPORT_COMMANDS = compile_report_handlers(
    declarations=load_command_registry_declaration().group("quality"),
    import_path_prefix="ethos.surface.cli.quality.core:",
)
globals().update(
    {function_name: command.make_handler() for function_name, command in REPORT_COMMANDS.items()}
)


def provenance(
    *,
    objective: str = "ethos provenance",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit a provenance envelope for a planned ETHOS proof."""
    repo = resolve_root(root)
    run = ProofRun(
        action_id="planned-proof",
        command=("ethos", "prove", "--json"),
        exit_code=None,
        stdout="",
        stderr="",
        state="planned",
    )
    evidence = EvidenceSet.from_runs(
        id=f"ethos:{objective}",
        head=git_adapter.current_head(repo),
        runs=(run,),
        durability="local",
    )
    result = EthosResult(
        command="quality provenance",
        ok=True,
        state="ready",
        summary={"evidence_digest": evidence.digest},
        next_actions=("ethos prove --json",),
        data={
            "evidence": evidence.to_dict(),
            "provenance": provenance_envelope(evidence),
        },
    )
    emit(result, json_output=json_output, enforce=False)
