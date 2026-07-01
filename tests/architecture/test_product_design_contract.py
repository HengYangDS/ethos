from __future__ import annotations

from pathlib import Path

from ethos_governance.self_audit import REQUIRED_DOCS, self_audit

ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_product_design_contract_canonizes_kernel_first_principles() -> None:
    text = read("docs/governance/product-design-contract.md")

    assert "Evidence-grounded Trust for Human-Agent Operational Stewardship" in text
    kernel_chain = (
        "Constitution -> Subject -> Contract -> IR -> Transition -> "
        "Inscription -> Evidence -> Chronicle -> Evolution"
    )
    assert kernel_chain in text
    for principle in (
        "Kernel-first",
        "Contracts before providers",
        "Capability before surface",
        "Governance before tooling",
        "Proof separation",
    ):
        assert principle in text
    assert "PyPI/TestPyPI publish" in text
    assert "not current scope" in text


def test_package_ontology_declares_target_mece_packages_and_migration_hosts() -> None:
    text = read("docs/architecture/package-ontology.md")

    target_packages = (
        "ethos-core",
        "ethos-contracts",
        "ethos-repository",
        "ethos-assistants",
        "ethos-adapters",
        "ethos",
        "ethos-test",
    )
    for package in target_packages:
        assert f"`{package}`" in text
    for migration_host in (
        "ethos-governance",
        "ethos-workspace",
        "ethos-agent",
        "ethos-project",
    ):
        assert f"`{migration_host}`" in text
        assert "migration host" in text
    assert "distributions/npm" in text
    assert "Python product package ontology" in text


def test_boundary_convergence_requires_parity_freeze_and_retirement_decision() -> None:
    text = read("docs/governance/product-boundary-convergence.md")

    for phrase in (
        "migration oracle",
        "frozen fallback / reference implementation",
        "External Shadow Parity",
        "Rollback Window",
        "Retirement Decision",
        "must not be deleted automatically",
    ):
        assert phrase in text
    assert "ALPHASIMDMGR_ETHOS_BACKEND=external" in text
    assert "ALPHASIMDMGR_ETHOS_BACKEND=embedded" in text


def test_capability_parity_ledger_classifies_required_capabilities() -> None:
    text = read("docs/governance/capability-parity-ledger.md")

    required_capabilities = (
        "status",
        "plan",
        "prove",
        "land",
        "publish",
        "report",
        "SQLite state",
        "OpenSpec",
        "Backlog / intake",
        "campaign / mission",
        "dmgr raw/cache/conf/alphasim rules",
        "MCP / ACP / Superpowers",
    )
    for capability in required_capabilities:
        assert capability in text
    for classification in (
        "already-in-product",
        "migrate-to-product",
        "adopter-profile-only",
        "adopter-domain-only",
        "obsolete",
        "split",
        "reference-only",
    ):
        assert classification in text
    for field in (
        "source location",
        "target home",
        "migration disposition",
        "parity criterion",
        "rollback impact",
    ):
        assert field in text
    assert "accepted_summary" in text
    assert "shadow-parity.schema.json" in text


def test_product_design_contract_is_self_audited_with_target_ontology() -> None:
    for doc in (
        "docs/governance/product-design-contract.md",
        "docs/architecture/package-ontology.md",
        "docs/governance/product-boundary-convergence.md",
        "docs/governance/capability-parity-ledger.md",
    ):
        assert doc in REQUIRED_DOCS

    report = self_audit(ROOT, openspec_mode="shape")
    target = report["target_package_ontology"]

    assert target["ok"] is True
    assert target["contract_ok"] is True
    assert target["physical_target_homes_present"] is True
    assert target["migration_complete"] is False
    assert target["migration_status"] == "in_progress"
    assert target["target_packages"] == [
        "ethos-core",
        "ethos-contracts",
        "ethos-repository",
        "ethos-assistants",
        "ethos-adapters",
        "ethos",
        "ethos-test",
    ]
    assert target["migration_hosts"] == [
        "ethos-kernel",
        "ethos-governance",
        "ethos-workspace",
        "ethos-agent",
        "ethos-project",
    ]
    assert target["target_distribution_adapters"] == ["distributions/npm"]
    assert target["distribution_migration_hosts"] == ["packages/ethos-node"]


def test_self_audit_uses_canonical_package_ontology_contract() -> None:
    from ethos_contracts.package_ontology import package_ontology_report

    contract = package_ontology_report()
    audit = self_audit(ROOT, openspec_mode="shape")

    assert audit["package_ontology"]["target_package_contract"] == contract["target_packages"]
    assert audit["package_ontology"]["migration_host_packages"] == contract["migration_hosts"]
    assert audit["target_package_ontology"]["target_packages"] == contract["target_packages"]
    assert audit["target_package_ontology"]["migration_hosts"] == contract["migration_hosts"]
    assert audit["target_package_ontology"]["distribution_status"] == {
        "distributions/npm": {
            "state": "planned_not_migrated",
            "migration_host": "packages/ethos-node",
        }
    }


def test_product_package_and_migration_host_sets_are_disjoint() -> None:
    report = self_audit(ROOT, openspec_mode="shape")
    ontology = report["package_ontology"]

    target_packages = set(ontology["target_package_contract"])
    migration_hosts = set(ontology["migration_host_packages"])

    assert target_packages.isdisjoint(migration_hosts)
    assert "ethos" in target_packages
    assert "ethos" not in migration_hosts
    assert ontology["migration_host_lifecycle"] == {
        "ethos-kernel": "migration-host",
        "ethos-governance": "migration-host",
        "ethos-workspace": "migration-host",
        "ethos-agent": "migration-host",
        "ethos-project": "migration-host",
    }
