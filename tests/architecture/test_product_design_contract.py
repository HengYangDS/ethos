from __future__ import annotations

from pathlib import Path

from ethos_repository.self_audit import REQUIRED_DOCS, self_audit

ROOT = Path(__file__).resolve().parents[2]
PROVIDER_NEUTRAL_CANONICAL_DOCS = (
    "docs/governance/product-design-contract.md",
    "docs/governance/conversation-ledger.md",
    "docs/architecture/agent-projections.md",
    "docs/governance/playbooks-and-skills.md",
    "docs/reference/command-plane.md",
    "docs/architecture/runner-and-mutation.md",
)
PRODUCT_VENDOR_TERMS = (
    "PyCharm",
    "Claude",
    "Codex",
    "OpenAI",
    "GPT",
    "IDE",
    "JetBrains",
    "Anthropic",
    "Gemini",
    "Copilot",
    "Cursor",
    "Windsurf",
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_product_design_contract_canonizes_kernel_first_principles() -> None:
    text = read("docs/governance/product-design-contract.md")

    assert "Evidence-grounded Trust for Human-Agent Operational Stewardship" in text
    kernel_chain = (
        "JudgmentSource -> Subject -> Commitment -> Change -> Evidence -> "
        "Claim -> Chronicle"
    )
    assert kernel_chain in text
    assert "North Star is a derived reader view, not the judgment source" in text
    assert "Claim binds evidence; it does not own the Change lifecycle" in text
    for principle in (
        "Judgment-source first",
        "Contracts before providers",
        "Git-native repository substrate",
        "Capability before surface",
        "Governance before tooling",
        "Proof separation",
    ):
        assert principle in text
    assert "PyPI/TestPyPI publish" in text
    assert "not current scope" in text


def test_product_design_contract_keeps_git_native_not_generic_vcs() -> None:
    text = read("docs/governance/product-design-contract.md")

    assert "ETHOS is Git-native" in text
    assert "not a generic VCS abstraction" in text
    assert "Git, OpenSpec, Backlog" not in text


def test_first_hour_docs_keep_advanced_workflows_out_of_primary_path() -> None:
    readme = read("README.md")
    quickstart = read("docs/start/quickstart.md")

    assert "First Hour" in readme
    assert "status -> plan -> prove -> land -> publish" in readme
    assert "report is a read-only scorecard" in readme
    assert "Advanced workflow:" not in readme

    first_hour = quickstart.split("## Maintainer Reference", 1)[0]
    for advanced in (
        "ethos campaign",
        "ethos quality",
        "ethos assistants",
        "ethos playbooks",
        "ethos parity",
        "ethos fleet",
    ):
        assert advanced not in first_hour
    for phrase in (
        "choose a profile",
        "review generated files",
        "apply criteria",
        "rollback",
        "report is the payoff view",
    ):
        assert phrase in first_hour


def test_product_design_contract_defines_configured_role_and_binding_contracts() -> None:
    product = read("docs/governance/product-design-contract.md")
    command_plane = read("docs/reference/command-plane.md")
    schema = read("docs/architecture/schema-validation.md")
    repository_spec = read("openspec/specs/ethos-repository/spec.md")
    adapters_spec = read("openspec/specs/ethos-adapters/spec.md")

    for text in (product, command_plane, schema):
        assert "release_root -> accepted_root -> candidate -> work_lane -> submit_lane" in text
        assert "`role_policy`" in text
        assert "`binding_registry`" in text

    assert "adapter UI text is not product state" in command_plane
    assert "OpenSpec remains mandatory governance, not a product substrate" in product
    assert "OpenSpec remains mandatory governance, not a product substrate" in (
        repository_spec
    )
    assert "not a second command plane" in repository_spec
    assert "adapters derive presentation from `worktree_binding`" in adapters_spec
    assert "host navigation labels are not product state" in adapters_spec


def test_product_design_contract_defines_single_kernel_dual_posture() -> None:
    product = read("docs/governance/product-design-contract.md")
    command_plane = read("docs/reference/command-plane.md")
    repository_spec = read("openspec/specs/ethos-repository/spec.md")
    contracts_spec = read("openspec/specs/ethos-contracts/spec.md")

    for text in (product, command_plane, repository_spec, contracts_spec):
        assert "single-kernel dual-posture" in text
        assert "product_self" in text
        assert "adopter_repository" in text
        assert "`governance_context`" in text

    assert "self-governance is not a private command plane" in product
    assert "governance_audit" in command_plane
    assert "capability_parity" in command_plane
    assert "same command semantics" in repository_spec
    assert "shared governance context contract" in contracts_spec


def test_canonical_product_docs_are_provider_neutral() -> None:
    for doc in PROVIDER_NEUTRAL_CANONICAL_DOCS:
        text = read(doc)
        for term in PRODUCT_VENDOR_TERMS:
            assert term not in text, (doc, term)


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
    assert "No active product migration host remains in `packages/`" in text
    assert "distributions/npm" in text
    assert "Python product package ontology" in text


def test_canonical_kernel_surfaces_do_not_promote_retired_chain_terms() -> None:
    retired_phrases = (
        "Constitution, Subject",
        "Contract, IR",
        "Transition, Inscription",
        "Chronicle, Evolution",
    )
    canonical_surfaces = (
        "docs/architecture/package-ontology.md",
        "packages/ethos-core/README.md",
        "openspec/specs/ethos-core/spec.md",
    )

    for surface in canonical_surfaces:
        text = read(surface)
        for phrase in retired_phrases:
            assert phrase not in text, (surface, phrase)


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
    assert target["migration_complete"] is True
    assert target["migration_status"] == "complete"
    assert target["target_packages"] == [
        "ethos-core",
        "ethos-contracts",
        "ethos-quality",
        "ethos-repository",
        "ethos-assistants",
        "ethos-adapters",
        "ethos",
        "ethos-test",
    ]
    assert target["migration_hosts"] == []
    assert target["target_distribution_adapters"] == ["distributions/npm"]
    assert target["distribution_migration_hosts"] == []


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
            "state": "migrated",
            "home": "distributions/npm",
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
    assert ontology["migration_host_lifecycle"] == {}
