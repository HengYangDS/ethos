from __future__ import annotations

from pathlib import Path

from ethos_repository.self_audit import self_audit


def write(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_minimal_self_audit_repo(tmp_path: Path) -> None:
    for package in (
        "ethos",
        "ethos-core",
        "ethos-contracts",
        "ethos-repository",
        "ethos-adapters",
        "ethos-assistants",
        "ethos-test",
    ):
        write(tmp_path / "packages" / package / "README.md")
    write(tmp_path / "distributions" / "npm" / "README.md")
    write(tmp_path / "distributions" / "npm" / "package.json", "{}\n")
    write(tmp_path / "distributions" / "npm" / "bin" / "ethos.mjs")

    for doc in (
        "docs/architecture/product-ontology.md",
        "docs/architecture/package-ontology.md",
        "docs/architecture/distribution.md",
        "docs/concepts/kernel-model.md",
        "docs/architecture/action-graph.md",
        "docs/architecture/adoption-profiles.md",
        "docs/architecture/agent-projections.md",
        "docs/architecture/gate-runner.md",
        "docs/architecture/local-state.md",
        "docs/architecture/mcp-server.md",
        "docs/architecture/fleet-and-adopters.md",
        "docs/architecture/runner-and-mutation.md",
        "docs/architecture/schema-validation.md",
        "docs/governance/commit-signature-policy.md",
        "docs/governance/provenance-and-attestation.md",
        "docs/governance/docs-registry.md",
        "docs/governance/product-design-contract.md",
        "docs/governance/product-boundary-convergence.md",
        "docs/governance/capability-parity-ledger.md",
        "docs/governance/openspec-self-governance.md",
        "docs/governance/playbooks-and-skills.md",
        "docs/governance/release-governance.md",
        "docs/governance/self-evolution-campaign.md",
    ):
        write(
            tmp_path / doc,
            "---\nsubject: test\nrole: reference\nstate: canonical\nrelations: test\n---\n",
        )

    for schema in (
        "result.schema.json",
        "claim.schema.json",
        "commit-policy.schema.json",
        "subject.schema.json",
        "commitment.schema.json",
        "change.schema.json",
        "action.schema.json",
        "evidence.schema.json",
        "proof-run.schema.json",
        "evidence-set.schema.json",
        "provenance.schema.json",
        "chronicle.schema.json",
        "evolution.schema.json",
        "docs-registry.schema.json",
        "evolution-ledger.schema.json",
        "gate.schema.json",
        "assistant-projection.schema.json",
        "mutation-decision.schema.json",
        "workspace-status.schema.json",
    ):
        write(tmp_path / "schemas" / "ethos" / schema, "{}\n")

    for path in (
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "LICENSE",
        ".ethos/release.toml",
        ".gitlab-ci.yml",
        ".gitlab/merge_request_templates/default.md",
        ".gitlab/issue_templates/task.md",
        "docs/governance/self-evolution-ledger.toml",
        "openspec/config.yaml",
        "openspec/specs/ethos-core/spec.md",
    ):
        write(tmp_path / path)


def test_self_audit_requires_skills_and_mece_specs(tmp_path: Path) -> None:
    write_minimal_self_audit_repo(tmp_path)

    report = self_audit(tmp_path, openspec_mode="shape")

    assert report["ok"] is False
    assert ".agents/skills/activation.toml" in report["playbooks"]["missing"]
    assert "openspec/specs/ethos-contracts/spec.md" in report["openspec_families"]["missing"]
    assert "adoption_scaffold_missing:.agents/skills/activation.toml" in report["required_gaps"]


def test_self_audit_includes_authority_graph() -> None:
    report = self_audit(Path.cwd(), openspec_mode="shape")

    assert report["authority_graph"]["ok"] is True
    assert report["authority_graph"]["required_gaps"] == []
    ids = {entry["id"] for entry in report["authority_graph"]["entries"]}
    assert "ethos:judgment-source" in ids
    assert "ethos:product-design-contract" in ids


def test_self_audit_surfaces_retired_command_mentions_as_required_gaps(
    tmp_path: Path,
) -> None:
    write_minimal_self_audit_repo(tmp_path)
    for path in (
        ".agents/skills/README.md",
        ".agents/skills/activation.toml",
        ".agents/skills/ethos-repository-governance/SKILL.md",
        "openspec/specs/ethos-assistants/spec.md",
        "openspec/specs/ethos-cli/spec.md",
        "openspec/specs/ethos-contracts/spec.md",
        "openspec/specs/ethos-distribution/spec.md",
        "openspec/specs/ethos-repository/spec.md",
        "openspec/specs/ethos-adapters/spec.md",
        "openspec/specs/ethos-test/spec.md",
    ):
        write(tmp_path / path)
    write(
        tmp_path / "docs" / "bad.md",
        "---\nsubject: test\nrole: reference\nstate: canonical\nrelations: test\n---\n"
        "Do not promote `proof` here.\n",
    )

    report = self_audit(tmp_path, openspec_mode="shape")

    assert report["ok"] is False
    assert report["command_registry"]["required_gaps"] == [
        "retired_public_root_mention:docs/bad.md:7:proof",
    ]
    assert "retired_public_root_mention:docs/bad.md:7:proof" in report["required_gaps"]
