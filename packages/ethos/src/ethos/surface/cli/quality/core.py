"""Quality command group — determinism, gates, proof-policy, docs, and coupling.

The largest surface command group (29 commands). Binds args, calls domain/repository
reports, emits. Registers onto the shared quality_app from _base; cli.py imports this
module so the decorators run. Imports only what this group needs — so the heavy
quality/repository deps load only when this group is imported (lazy path).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

import ethos.adapters.repo.git as git_adapter
import ethos.domain.prove as prove_domain
import ethos.repository.audit as repository_audit_module
import ethos.surface.cli.results.tool as tool_results
from ethos.adapters.gates.signature import signature_policy_report
from ethos.adapters.gates.ty import ty_gate_report  # noqa: F401
from ethos.assistants.projections import projection_drift_report  # noqa: F401
from ethos.repository.evidence.claims import claims_report  # noqa: F401
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun
from ethos.repository.evidence.core import provenance_envelope
from ethos.repository.evidence.freshness import evidence_freshness_report  # noqa: F401
from ethos.repository.policy.artifacts import generated_artifact_topology_report  # noqa: F401
from ethos.repository.policy.coupling.core import coupling_audit_report
from ethos.repository.policy.coverage import coverage_quality_report  # noqa: F401
from ethos.repository.policy.docs.topology import docs_topology_report
from ethos.repository.policy.docstrings.core import docstring_coverage_report  # noqa: F401
from ethos.repository.policy.gates import gate_registry
from ethos.repository.policy.layout.core import module_layout_report  # noqa: F401
from ethos.repository.policy.schema import schema_validation_report  # noqa: F401
from ethos.repository.registry.commands import command_registry_report  # noqa: F401
from ethos.repository.registry.docs.commands import command_examples_report  # noqa: F401
from ethos.repository.registry.docs.health import docs_health_report  # noqa: F401
from ethos.repository.registry.docs.quality import docs_quality_report
from ethos.repository.registry.standards import standard_adapter_registry
from ethos.repository.release.attestation import release_attestation
from ethos.repository.release.attestation import sbom_projection
from ethos.repository.release.core import release_policy_report
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos.surface.cli.quality.reporting import ReportCommandSpec
from ethos.surface.cli.quality.reporting import advisory_state
from ethos.surface.cli.quality.reporting import conditional_actions
from ethos.surface.cli.quality.reporting import constant_actions
from ethos.surface.cli.quality.reporting import count_at
from ethos.surface.cli.quality.reporting import count_of
from ethos.surface.cli.quality.reporting import emit_report_command
from ethos.surface.cli.quality.reporting import field_data
from ethos.surface.cli.quality.reporting import module_report
from ethos.surface.cli.quality.reporting import path_value
from ethos.surface.cli.quality.reporting import payload_report
from ethos.surface.cli.quality.reporting import project_summary
from ethos_core.contracts.commands import load_command_registry_declaration
from ethos_core.contracts.package.ontology import package_ontology_report
from ethos_core.contracts.package.ontology import workspace_package_config_report
from ethos_core.quality.docs.profile import docs_quality_profile
from ethos_core.quality.profiles import product_quality_profile
from ethos_core.quality.profiles import tool_profiles
from ethos_core.quality.proof.policy import proof_lattice
from ethos_core.result import EthosResult


def _quality_report_namespace() -> dict[str, object]:
    """Return live module bindings so tests and adapters can monkeypatch reports."""
    return globals()


def _current_head(root: Path) -> str:
    return git_adapter.current_head(root)


_QUALITY_COMMAND_HELP = {
    command.name: command.help for command in load_command_registry_declaration().group("quality")
}


def _report_handler(spec: ReportCommandSpec, *, enforce: bool, bind_root: bool, doc: str):
    def emit_spec(target: Path, *, json_output: bool) -> None:
        emit_report_command(
            spec,
            target,
            emit_func=lambda result: emit(result, json_output=json_output, enforce=enforce),
        )

    if bind_root:

        def handler(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
            emit_spec(resolve_root(root), json_output=json_output)
    else:

        def handler(*, json_output: JsonFlag = False) -> None:
            emit_spec(Path.cwd(), json_output=json_output)

    handler.__doc__ = doc
    return handler


def _product_quality_profile(_root: Path) -> object:
    return product_quality_profile()


def _proof_lattice(_root: Path) -> object:
    return proof_lattice()


def _tool_profiles(_root: Path) -> object:
    return tool_profiles()


def _standard_adapter_registry(_root: Path) -> object:
    return standard_adapter_registry()


def _gate_registry_report(root: Path) -> dict[str, object]:
    return {"gates": {gate_id: gate.to_dict() for gate_id, gate in gate_registry(root).items()}}


def _release_file_report(root: Path) -> dict[str, object]:
    release_files = repository_audit_module.release_files_report(root)
    policy = release_policy_report(root)
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


ASSET_POLICY_COMMAND = ReportCommandSpec(
    command="quality asset-policy",
    report=payload_report(_product_quality_profile),
    summary=project_summary(asset_class_count=count_at("payload", "asset_classes")),
    data=field_data("payload"),
)
TYPES_COMMAND = ReportCommandSpec(
    command="quality types",
    report=module_report(_quality_report_namespace(), "ty_gate_report"),
    summary=project_summary(package_count=count_of("packages")),
)


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


DOCS_TOPOLOGY_COMMAND = ReportCommandSpec(
    command="quality docs-topology",
    report=module_report(_quality_report_namespace(), "docs_topology_report"),
    next_actions=conditional_actions(
        when_blocked=(
            "restore minimal semantic docs kernel: README, decisions, evidence, "
            "history, and reference"
        ),
        when_clean=(
            "ethos prove --execute --gate docs-topology --expect-head $(git rev-parse HEAD) --json"
        ),
    ),
)
PROOF_POLICY_COMMAND = ReportCommandSpec(
    command="quality proof-policy",
    report=payload_report(_proof_lattice),
    summary=project_summary(state_count=count_at("payload", "states")),
    data=field_data("payload"),
)
TOOL_PROFILES_COMMAND = ReportCommandSpec(
    command="quality tool-profiles",
    report=payload_report(_tool_profiles),
    summary=project_summary(tool_adapter_count=count_at("payload", "tool_adapters")),
    data=field_data("payload"),
)


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


COVERAGE_COMMAND = ReportCommandSpec(
    command="quality coverage",
    report=module_report(_quality_report_namespace(), "coverage_quality_report"),
    summary=project_summary(
        current_hard_floor=path_value("policy", "current_hard_floor"),
        latest_line_percent=path_value("latest_artifact", "line_percent"),
        writer_active=path_value("latest_artifact", "writer_active", default=False),
    ),
)
DOCSTRINGS_COMMAND = ReportCommandSpec(
    command="quality docstrings",
    report=module_report(_quality_report_namespace(), "docstring_coverage_report"),
    summary=project_summary(
        coverage_percent=path_value("coverage_percent"),
        documented_count=path_value("documented_count"),
        public_count=path_value("public_count"),
        style_issue_count=path_value("style_issue_count", default=0),
        advisory_missing_count=path_value(
            "advisory_public_definition_inventory",
            "missing_count",
            default=0,
        ),
    ),
)


CODE_SIZE_COMMAND = ReportCommandSpec(
    command="quality code-size",
    report=module_report(vars(prove_domain), "code_size_report"),
)

MODULE_LAYOUT_COMMAND = ReportCommandSpec(
    command="quality module-layout",
    report=module_report(_quality_report_namespace(), "module_layout_report"),
)

GENERATED_ARTIFACTS_COMMAND = ReportCommandSpec(
    command="quality generated-artifacts",
    report=module_report(_quality_report_namespace(), "generated_artifact_topology_report"),
    next_actions=conditional_actions(
        when_blocked=(
            "move generated outputs under build/ethos or build/evidence; "
            "promote curated summaries into docs/evidence"
        ),
        when_clean="ethos prove --execute --expect-head $(git rev-parse HEAD) --json",
    ),
)

COMMAND_SURFACE_COMMAND = ReportCommandSpec(
    command="quality command-surface",
    report=module_report(_quality_report_namespace(), "command_registry_report"),
)

SCHEMAS_COMMAND = ReportCommandSpec(
    command="quality schemas",
    report=module_report(_quality_report_namespace(), "schema_validation_report"),
)

COMMAND_REGISTRY_COMMAND = ReportCommandSpec(
    command="quality command-registry",
    report=module_report(_quality_report_namespace(), "command_registry_report"),
    next_actions=constant_actions("ethos repository audit"),
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


PROJECTION_DRIFT_COMMAND = ReportCommandSpec(
    command="quality projection-drift",
    report=module_report(_quality_report_namespace(), "projection_drift_report"),
)

DOCS_REGISTRY_COMMAND = ReportCommandSpec(
    command="quality docs-registry",
    report=module_report(_quality_report_namespace(), "docs_health_report"),
    next_actions=constant_actions("ethos docs"),
)

COMMAND_EXAMPLES_COMMAND = ReportCommandSpec(
    command="quality command-examples",
    report=module_report(_quality_report_namespace(), "command_examples_report"),
)


STANDARDS_COMMAND = ReportCommandSpec(
    command="quality standards",
    report=payload_report(lambda root: {"adapters": _standard_adapter_registry(root)}),
    data=field_data("payload"),
)


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


GATES_COMMAND = ReportCommandSpec(
    command="quality gates",
    report=payload_report(_gate_registry_report, state="ready"),
    summary=project_summary(gate_count=count_at("payload", "gates")),
    data=field_data("payload"),
)


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


RELEASE_COMMAND = ReportCommandSpec(
    command="quality release",
    report=_release_file_report,
    data=lambda report: {
        "release_files": report["release_files"],
        "host_profile": report["host_profile"],
    },
    next_actions=constant_actions(
        "uv build --all-packages --out-dir build/artifacts/python --clear"
    ),
)
RELEASE_POLICY_COMMAND = ReportCommandSpec(
    command="quality release-policy",
    report=module_report(_quality_report_namespace(), "release_policy_report"),
    clean_state="ready",
    next_actions=constant_actions("ethos quality release-attestation"),
)
SBOM_COMMAND = ReportCommandSpec(
    command="quality sbom",
    report=payload_report(lambda root: {"sbom": sbom_projection(root)}, state="ready"),
    summary=project_summary(package_count=count_at("payload", "sbom", "packages")),
    data=field_data("payload"),
)


def release_attestation_command(
    *,
    evidence_digest: str = "planned",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit release attestation envelope without publishing it."""
    spec = ReportCommandSpec(
        command="quality release-attestation",
        report=lambda repo: _release_attestation_report(repo, evidence_digest=evidence_digest),
        data=lambda report: {"attestation": report["attestation"]},
    )
    emit_report_command(
        spec,
        resolve_root(root),
        emit_func=lambda result: emit(result, json_output=json_output, enforce=False),
    )


EVIDENCE_FRESHNESS_COMMAND = ReportCommandSpec(
    command="quality evidence-freshness",
    report=module_report(
        _quality_report_namespace(),
        "evidence_freshness_report",
        current_head=_current_head,
    ),
    data=field_data("data"),
    next_actions=constant_actions("ethos prove --json"),
)
CLAIMS_COMMAND = ReportCommandSpec(
    command="quality claims",
    report=module_report(
        _quality_report_namespace(),
        "claims_report",
        current_head=_current_head,
    ),
    summary=project_summary(
        claim_count=count_of("claims"),
        advisory_gap_count=count_of("advisory_gaps"),
    ),
    state=advisory_state("advisory_gaps"),
    next_actions=constant_actions("ethos prove --json"),
)


_REPORT_COMMANDS = {
    "asset_policy": ("asset-policy", ASSET_POLICY_COMMAND, False, False),
    "quality_types": ("types", TYPES_COMMAND, True, True),
    "docs_topology": ("docs-topology", DOCS_TOPOLOGY_COMMAND, True, True),
    "proof_policy": ("proof-policy", PROOF_POLICY_COMMAND, False, False),
    "tool_profiles_command": ("tool-profiles", TOOL_PROFILES_COMMAND, False, False),
    "coverage": ("coverage", COVERAGE_COMMAND, True, True),
    "docstrings": ("docstrings", DOCSTRINGS_COMMAND, True, True),
    "code_size": ("code-size", CODE_SIZE_COMMAND, False, True),
    "module_layout": ("module-layout", MODULE_LAYOUT_COMMAND, True, True),
    "generated_artifacts": ("generated-artifacts", GENERATED_ARTIFACTS_COMMAND, True, True),
    "command_surface": ("command-surface", COMMAND_SURFACE_COMMAND, False, True),
    "projection_drift": ("projection-drift", PROJECTION_DRIFT_COMMAND, False, True),
    "schemas": ("schemas", SCHEMAS_COMMAND, False, True),
    "standards": ("standards", STANDARDS_COMMAND, False, False),
    "gates": ("gates", GATES_COMMAND, False, True),
    "release": ("release", RELEASE_COMMAND, False, True),
    "release_policy": ("release-policy", RELEASE_POLICY_COMMAND, False, True),
    "sbom": ("sbom", SBOM_COMMAND, False, True),
    "command_registry": ("command-registry", COMMAND_REGISTRY_COMMAND, False, True),
    "evidence_freshness": ("evidence-freshness", EVIDENCE_FRESHNESS_COMMAND, False, True),
    "claims": ("claims", CLAIMS_COMMAND, False, True),
    "docs_registry": ("docs-registry", DOCS_REGISTRY_COMMAND, False, True),
    "command_examples": ("command-examples", COMMAND_EXAMPLES_COMMAND, False, True),
}

globals().update(
    {
        function_name: _report_handler(
            spec,
            enforce=enforce,
            bind_root=bind_root,
            doc=_QUALITY_COMMAND_HELP[command_name],
        )
        for function_name, (command_name, spec, enforce, bind_root) in _REPORT_COMMANDS.items()
    }
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
        data={"evidence": evidence.to_dict(), "provenance": provenance_envelope(evidence)},
    )
    emit(result, json_output=json_output, enforce=False)
