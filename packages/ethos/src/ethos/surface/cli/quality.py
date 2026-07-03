"""Quality command group — determinism, gates, proof-policy, docs, and coupling.

The largest surface command group (29 commands). Binds args, calls domain/repository
reports, emits. Registers onto the shared quality_app from _base; cli.py imports this
module so the decorators run. Imports only what this group needs — so the heavy
quality/repository deps load only when this group is imported (lazy path).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import ethos_assistants.playbooks as playbooks_module
import ethos_repository.repository_audit as repository_audit_module
from ethos.adapters import git as _gitio
from ethos.adapters import quality_tool as _qtool
from ethos.domain import prove as _prove
from ethos.surface.cli._base import ASSISTANT_TRUTH_BOUNDARY
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit as _emit
from ethos.surface.cli._base import quality_app
from ethos.surface.cli._base import resolve_root as _root
from ethos.surface.cli._base import sha256_file as _sha256_file
from ethos_adapters.commit_policy import signature_policy_report
from ethos_assistants.playbooks import playbooks_report
from ethos_assistants.projections import projection_contract
from ethos_contracts.package_ontology import package_ontology_report
from ethos_contracts.package_ontology import workspace_package_config_report
from ethos_core.result import EthosResult
from ethos_quality.docs_profile import docs_quality_profile
from ethos_quality.profiles import product_quality_profile
from ethos_quality.profiles import tool_profiles
from ethos_quality.proof_policy import proof_lattice
from ethos_repository.attestation import release_attestation
from ethos_repository.attestation import sbom_projection
from ethos_repository.claims import claims_report
from ethos_repository.command_registry import command_registry_report
from ethos_repository.coupling import coupling_audit_report
from ethos_repository.docs_registry import command_examples_report
from ethos_repository.docs_registry import docs_health_report
from ethos_repository.docs_registry import docs_quality_report
from ethos_repository.evidence import EvidenceSet
from ethos_repository.evidence import ProofRun
from ethos_repository.evidence import provenance_envelope
from ethos_repository.gates import gate_registry
from ethos_repository.release import release_policy_report
from ethos_repository.schema_validation import schema_validation_report
from ethos_repository.standards import standard_adapter_registry


@quality_app.command
def asset_policy(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report repository asset quality policy."""
    profile = product_quality_profile()
    result = EthosResult(
        command="quality asset-policy",
        ok=True,
        state="clean",
        summary={"asset_class_count": len(profile["asset_classes"])},
        data=profile,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command(name="docs")
def quality_docs(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report documentation quality profile and registry health."""
    repo = _root(root)
    profile = docs_quality_profile()
    report = docs_quality_report(repo)
    result = EthosResult(
        command="quality docs",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data={
            "profile": profile,
            "style_goals": profile["style_goals"],
            "health": report,
        },
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def proof_policy(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report proof-state lattice and trust-bearing rules."""
    lattice = proof_lattice()
    result = EthosResult(
        command="quality proof-policy",
        ok=True,
        state="clean",
        summary={"state_count": len(lattice["states"])},
        data=lattice,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command(name="tool-profiles")
def tool_profiles_command(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report quality tool adapter profiles."""
    profiles = tool_profiles()
    result = EthosResult(
        command="quality tool-profiles",
        ok=True,
        state="clean",
        summary={"tool_adapter_count": len(profiles["tool_adapters"])},
        data=profiles,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command(name="markdown-links")
def markdown_links(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run markdown link checks through the configured adapter."""
    repo = _root(root)
    files = [
        path
        for path in _gitio.git_files(repo, "*.md")
        if not path.startswith(("docs/evidence/", "docs/archive/"))
    ]
    report = _qtool.quality_tool_report(
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
    )
    result = EthosResult(
        command="quality markdown-links",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command(name="shell")
def shell_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run shell script lint checks through ShellCheck."""
    repo = _root(root)
    files = _gitio.git_files(repo, "*.sh")
    report = _qtool.quality_tool_report(
        root=repo,
        gate_id="shell-lint",
        tool="shellcheck",
        command=["shellcheck", *files],
        files=files,
    )
    result = EthosResult(
        command="quality shell",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command(name="toml")
def toml_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run TOML syntax and format checks through Taplo."""
    repo = _root(root)
    files = _gitio.git_files(repo, "*.toml")
    report = _qtool.quality_tool_report(
        root=repo,
        gate_id="toml-config",
        tool="taplo",
        command=["taplo", "check", *files],
        files=files,
    )
    result = EthosResult(
        command="quality toml",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command(name="yaml")
def yaml_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run YAML projection checks through yamllint."""
    repo = _root(root)
    files = _gitio.git_files(repo, "*.yml", "*.yaml")
    report = _qtool.quality_tool_report(
        root=repo,
        gate_id="yaml-config",
        tool="yamllint",
        command=["yamllint", "-d", "{extends: relaxed, rules: {line-length: disable}}", *files],
        files=files,
    )
    result = EthosResult(
        command="quality yaml",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command(name="code-size")
def code_size(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check effective source-file size against ratchet limits."""
    repo = _root(root)
    report = _prove.code_size_report(repo)
    result = EthosResult(
        command="quality code-size",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command(name="npm")
def npm_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run npm distribution pack smoke checks without publishing."""
    repo = _root(root)
    files = ["package.json"] if (repo / "package.json").exists() else []
    report = _qtool.quality_tool_report(
        root=repo,
        gate_id="npm-pack",
        tool="npm",
        command=["npm", "run", "test:npm"],
        files=files,
    )
    result = EthosResult(
        command="quality npm",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def command_surface(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate public command surface vocabulary."""
    repo = _root(root)
    report = command_registry_report(repo)
    result = EthosResult(
        command="quality command-surface",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def format_policy(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report format-policy readiness."""
    repo = _root(root)
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
    _emit(result, json_output, enforce=False)


@quality_app.command
def projection_drift(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report projection drift readiness."""
    repo = _root(root)
    contract = projection_contract()
    playbooks = playbooks_report(repo, mode="v2-strict")
    registry_meta = playbooks["registry"]["meta"]
    registry_digest = str(playbooks["registry"]["digest"])
    expected_registry_digest = str(registry_meta.get("expected_registry_digest") or "")
    generator_digest = _sha256_file(Path(playbooks_module.__file__))
    expected_generator_digest = str(registry_meta.get("expected_generator_digest") or "")
    activation_digest = _sha256_file(repo / ".agents" / "skills" / "activation.toml")
    drift = [
        {"kind": "skill_package", "gap": gap}
        for gap in playbooks["required_gaps"]
        if str(gap).startswith("skill_package_")
    ]
    if not expected_registry_digest:
        drift.append({"kind": "skill_registry", "gap": "skill_registry_expected_digest_missing"})
    elif expected_registry_digest != registry_digest:
        drift.append({"kind": "skill_registry", "gap": "skill_registry_digest_mismatch"})
    if not expected_generator_digest:
        drift.append(
            {"kind": "projection_generator", "gap": "projection_generator_expected_digest_missing"}
        )
    elif expected_generator_digest != generator_digest:
        drift.append(
            {"kind": "projection_generator", "gap": "projection_generator_digest_mismatch"}
        )
    ok = contract["truth"] == ASSISTANT_TRUTH_BOUNDARY and not drift
    result = EthosResult(
        command="quality projection-drift",
        ok=ok,
        state="clean" if ok else "blocked",
        required_gaps=tuple(item["gap"] for item in drift)
        if contract["truth"] == ASSISTANT_TRUTH_BOUNDARY
        else ("assistant_projection_truth_drift",),
        data={
            "contract": contract,
            "drift": drift,
            "registry_digest": registry_digest,
            "registry": {
                "digest": registry_digest,
                "expected_digest": expected_registry_digest,
                "ok": expected_registry_digest == registry_digest,
            },
            "generator": {
                "id": "ethos_assistants.playbooks",
                "digest": generator_digest,
                "expected_digest": expected_generator_digest,
                "ok": expected_generator_digest == generator_digest,
            },
            "inputs": [
                {
                    "path": ".agents/skills/activation.toml",
                    "digest": activation_digest,
                }
            ],
        },
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def standards(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report standards and framework adapter registry."""
    registry = standard_adapter_registry()
    result = EthosResult(
        command="quality standards",
        ok=True,
        state="clean",
        data={"adapters": registry},
    )
    _emit(result, json_output, enforce=False)


@quality_app.command(name="package-ontology")
def package_ontology(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report target package ontology and migration-host state."""
    repo = _root(root)
    contract = package_ontology_report()
    target_missing = [
        f"packages/{package}"
        for package in contract["target_packages"]
        if not (repo / "packages" / str(package)).exists()
    ]
    host_missing = [
        f"packages/{package}"
        for package in contract["migration_hosts"]
        if not (repo / "packages" / str(package)).exists()
    ]
    distribution_missing = [
        distribution
        for distribution in contract["target_distributions"]
        if not (repo / str(distribution)).exists()
    ]
    workspace_config = workspace_package_config_report(repo)
    workspace_config_gaps = [str(gap) for gap in workspace_config["required_gaps"]]
    migration_complete = not contract["migration_hosts"] and all(
        item.get("state") == "migrated"
        for item in contract["migration_distributions"].values()
        if isinstance(item, dict)
    )
    physical_missing = target_missing + host_missing + distribution_missing
    data = {
        **contract,
        "physical_target_homes_present": not target_missing and not distribution_missing,
        "migration_complete": migration_complete,
        "migration_status": "complete" if migration_complete else "in_progress",
        "missing": physical_missing + workspace_config_gaps,
        "distribution_status": contract["migration_distributions"],
        "workspace_config": workspace_config,
    }
    result = EthosResult(
        command="quality package-ontology",
        ok=not data["missing"],
        state="tracked" if not data["missing"] else "gapped",
        summary={
            "target_package_count": len(contract["target_packages"]),
            "migration_host_count": len(contract["migration_hosts"]),
            "migration_status": data["migration_status"],
        },
        required_gaps=tuple(
            [f"package_ontology_missing:{item}" for item in physical_missing]
            + workspace_config_gaps
        ),
        next_actions=("ethos repository audit",),
        data=data,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def schemas(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate ETHOS JSON Schemas."""
    repo = _root(root)
    report = schema_validation_report(repo)
    result = EthosResult(
        command="quality schemas",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def gates(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report executable proof gate registry."""
    registry = gate_registry()
    result = EthosResult(
        command="quality gates",
        ok=True,
        state="ready",
        summary={"gate_count": len(registry)},
        data={
            "gates": {
                gate_id: {
                    "kind": gate.kind,
                    "command": list(gate.command),
                    "policy": gate.policy,
                    "profile": gate.profile,
                    "toolchain": gate.toolchain,
                    "asset_classes": list(gate.asset_classes),
                    "dimensions": list(gate.dimensions),
                    "execution_mode": gate.execution_mode,
                    "evidence_class": gate.evidence_class,
                    "trust_bearing": gate.trust_bearing,
                    "tool_adapter": gate.tool_adapter,
                    "writes_files": gate.writes_files,
                    "network_policy": gate.network_policy,
                    "version_source": gate.version_source,
                    "depends_on": list(gate.depends_on),
                }
                for gate_id, gate in registry.items()
            }
        },
    )
    _emit(result, json_output, enforce=False)


@quality_app.command(name="coupling-audit")
def coupling_audit(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report product, profile, adapter, and product-toolchain coupling boundaries."""
    repo = _root(root)
    report = coupling_audit_report(repo)
    validation = _prove.command_data_validation(
        repo,
        schema_name="coupling-audit.schema.json",
        payload=report,
    )
    validation_gaps = tuple(f"coupling_audit_schema:{gap}" for gap in validation["required_gaps"])
    ok = bool(report["ok"]) and bool(validation["ok"])
    result = EthosResult(
        command="quality coupling-audit",
        ok=ok,
        state="clean" if ok else "blocked",
        diagnostics=(validation,),
        required_gaps=tuple(report["required_gaps"]) + validation_gaps,
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def commits(
    *,
    enforce_head: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report commit naming and signature policy."""
    repo = _root(root)
    report = signature_policy_report(repo)
    gaps = list(report["required_gaps"])
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
    _emit(result, json_output, enforce=False)


@quality_app.command
def release(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report product release surface and host-profile readiness."""
    repo = _root(root)
    release_files = repository_audit_module.release_files_report(repo)
    policy = release_policy_report(repo)
    result = EthosResult(
        command="quality release",
        ok=bool(release_files["ok"]),
        state="ready" if release_files["ok"] else "blocked",
        required_gaps=tuple(release_files["missing"]),
        next_actions=("uv build --all-packages",),
        data={
            "release_files": release_files,
            "host_profile": policy["host_profile"],
        },
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def release_policy(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate release version, host profile, protection, and attestation policy."""
    repo = _root(root)
    report = release_policy_report(repo)
    result = EthosResult(
        command="quality release-policy",
        ok=bool(report["ok"]),
        state="ready" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos quality release-attestation",),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def sbom(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit an SPDX-lite SBOM projection from workspace metadata."""
    repo = _root(root)
    projection = sbom_projection(repo)
    result = EthosResult(
        command="quality sbom",
        ok=True,
        state="ready",
        summary={"package_count": len(projection["packages"])},
        data={"sbom": projection},
    )
    _emit(result, json_output, enforce=False)


@quality_app.command(name="release-attestation")
def release_attestation_command(
    *,
    evidence_digest: str = "planned",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit release attestation envelope without publishing it."""
    repo = _root(root)
    attestation = release_attestation(
        root=repo,
        head=_gitio.current_head(repo),
        evidence_digest=evidence_digest,
    )
    result = EthosResult(
        command="quality release-attestation",
        ok=True,
        state="ready",
        summary={"tag": attestation["predicate"]["tag"]},
        data={"attestation": attestation},
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def command_registry(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate public command registry."""
    repo = _root(root)
    report = command_registry_report(repo)
    result = EthosResult(
        command="quality command-registry",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos repository audit",),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def evidence_freshness(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check declared evidence roots and claim digests."""
    repo = _root(root)
    claim_report = claims_report(repo)
    result = EthosResult(
        command="quality evidence-freshness",
        ok=bool(claim_report["ok"]),
        state="clean" if claim_report["ok"] else "blocked",
        summary={"evidence_roots": ["docs/evidence"]},
        required_gaps=tuple(claim_report["required_gaps"]),
        next_actions=("ethos prove --json",),
        data={"stale": [], "claims": claim_report},
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def claims(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate claim evidence digests."""
    repo = _root(root)
    report = claims_report(repo)
    result = EthosResult(
        command="quality claims",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos prove --json",),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def docs_registry(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate documentation metadata registry."""
    repo = _root(root)
    report = docs_health_report(repo)
    result = EthosResult(
        command="quality docs-registry",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos docs",),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def command_examples(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate documented command examples."""
    repo = _root(root)
    report = command_examples_report(repo)
    result = EthosResult(
        command="quality command-examples",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@quality_app.command
def provenance(
    *,
    objective: str = "ethos provenance",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit a provenance envelope for a planned ETHOS proof."""
    repo = _root(root)
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
        head=_gitio.current_head(repo),
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
    _emit(result, json_output, enforce=False)

