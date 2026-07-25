from __future__ import annotations

from pathlib import Path

from ethos.repository.audit import REQUIRED_DOCS
from ethos.repository.audit import repository_audit
from ethos_core.contracts.package.ontology import package_ontology_report

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


def prose(relative: str) -> str:
    return " ".join(read(relative).split())


def test_product_design_contract_canonizes_kernel_first_principles() -> None:
    text = read("docs/governance/product-design-contract.md")

    assert "Evidence-grounded Trust for Human-Agent Operational Stewardship" in text
    kernel_chain = "Authority -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle"
    assert kernel_chain in text
    assert "North Star is a derived reader view, not the authority" in text
    assert "Claim binds evidence; it does not own the Change lifecycle" in text
    for principle in (
        "Authority first",
        "Contracts before providers",
        "Git-native repository substrate",
        "Capability before surface",
        "Governance before tooling",
        "Proof separation",
    ):
        assert principle in text
    assert "PyPI/TestPyPI" in text
    assert "not active scope" in text


def test_axioms_and_kernel_keep_root_text_subordinate_and_restrained() -> None:
    contract = read("docs/governance/product-design-contract.md")
    axioms = read("system/axioms.md")
    kernel = read("docs/concepts/kernel-model.md")
    spec = read("openspec/specs/kernel/spec.md")

    root_phrases = (
        "道隐无名",
        "几动于微",
        "法乎自然",
        "生一启元",
        "分二判势",
        "孕三冲和",
        "万象昭幽",
        "度协畛域",
        "枢得环中",
        "物遂其性",
        "化育无穷",
        "玄德",
    )
    for phrase in root_phrases:
        assert phrase in contract
        assert phrase not in axioms

    for anchor in (
        "machine-adjacent engineering reading",
        "canonical root text lives only in the Product Design Contract",
        "does not restate the verse",
        "does not create a second truth center",
        "Authority before surface",
        "Evidence before claim",
        "Parsimony before expansion",
    ):
        assert anchor in axioms

    for anchor in (
        "Root Interpretation Boundary",
        "not a translation of that text",
        "not a philosophical subsystem",
        "engineering compression",
        "which kernel object it projects",
        "does not own the root text",
    ):
        assert anchor in kernel

    for anchor in (
        "root text as a judgment constraint",
        "subsystem, feature map, or low-level implementation label",
        "Root text remains canonical and restrained",
        "concrete engineering invariants rather than philosophical labels",
        "new truth center",
    ):
        assert anchor in spec


def test_product_design_contract_operationalizes_root_constraint() -> None:
    text = read("docs/governance/product-design-contract.md")

    assert "## Root Constraint" in text
    for phrase in (
        "道隐无名",
        "几动于微",
        "法乎自然",
        "生一启元",
        "分二判势",
        "孕三冲和",
        "万象昭幽",
        "度协畛域",
        "枢得环中",
        "物遂其性",
        "化育无穷",
        "玄德",
    ):
        assert phrase in text

    for operational_anchor in (
        "ETHOS 为名" + chr(0xFF0C) + "问道为根",
        "not an external slogan",
        "line-by-line",
        "module map",
        "one kernel keeps the",
        "center",
        "truth and projection remain separate",
        "evidence limits claims",
        "adapters stay adapters",
        "system/axioms.md` is only a machine-adjacent derivation",
    ):
        assert operational_anchor in text


def test_product_design_contract_defines_invalid_state_taxonomy() -> None:
    text = read("docs/governance/product-design-contract.md")

    assert "## Invalid-State Taxonomy" in text
    for category in (
        "authority_gap",
        "subject_ambiguous",
        "commitment_missing",
        "change_unbounded",
        "carrier_invalid",
        "evidence_missing_or_stale",
        "claim_unbound_or_overreaching",
        "chronicle_missing",
        "substrate_untrusted",
    ):
        assert category in text
    assert "not a new ontology" in text
    assert "Projection drift" in text
    assert "adapter bypass reduce" in text
    assert "Seven obligations judge" in text


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
    assert "status is the read-only readiness view" in readme
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
        "one binding carrier",
        "planned_files",
        "apply criteria",
        "rollback",
        "report is the payoff view",
    ):
        assert phrase in first_hour


def test_product_design_contract_defines_configured_role_and_binding_contracts() -> None:
    product = read("docs/governance/product-design-contract.md")
    command_plane = read("docs/reference/command-plane.md")
    schema = read("docs/architecture/schema-validation.md")
    repository_spec = read("openspec/specs/repository-governance/spec.md")
    adapters_spec = read("openspec/specs/adapters/spec.md")

    for text in (product, command_plane, schema):
        assert "release_root -> accepted_root -> candidate -> work_lane -> proposal_lane" in text
        assert "`role_policy`" in text
        assert "`binding_registry`" in text

    assert "adapter UI text is not product state" in command_plane
    assert "OpenSpec remains mandatory governance, not a product substrate" in product
    assert "OpenSpec remains mandatory governance, not a product substrate" in (repository_spec)
    assert "not a second command plane" in repository_spec
    assert "adapters derive presentation from `worktree_binding`" in adapters_spec
    assert "host navigation labels are not product state" in adapters_spec


def test_product_design_contract_defines_governed_repository() -> None:
    product = read("docs/governance/product-design-contract.md")
    command_plane = read("docs/reference/command-plane.md")
    repository_spec = read("openspec/specs/repository-governance/spec.md")
    contracts_spec = read("openspec/specs/contracts/spec.md")

    for text in (product, command_plane, repository_spec, contracts_spec):
        assert "governed repository" in text
        assert "`governance_context`" in text
        assert "product_self" not in text
        assert "adopter_repository" not in text
        assert "dual-posture" not in text

    assert "organization-native, not author-native" in product
    assert "Git author, Git committer" in product
    assert "single built-in personal name" in product
    assert "do not create separate command planes" in product
    assert "`transition_commands`" in product
    assert "`transition_commands`" in command_plane
    assert "governance_audit" in command_plane
    assert "capability_parity" in command_plane
    assert "same transition command semantics" in repository_spec
    assert "status is the singular reader" in repository_spec
    assert "singular lifecycle command semantics" in contracts_spec
    assert "shared governance context contract" in contracts_spec


def test_repository_governance_defines_loss_bounded_successor_continuity() -> None:
    repository_spec = read("openspec/specs/repository-governance/spec.md")

    assert (
        "### Requirement: Remote reconciliation continuation preserves historical carrier boundaries"
        in repository_spec
    )
    for phrase in (
        "original host worktree",
        "same episode Claim",
        "rerun current proof",
        "no-reconstruction boundary",
        "historical proof, temporary runtime\n  state, hosted CI, and remote publication",
    ):
        assert phrase in repository_spec


def test_first_glance_docs_make_isomorphic_governance_discoverable() -> None:
    readme = prose("README.md")
    product = prose("docs/governance/product-design-contract.md")
    glossary = prose("docs/reference/glossary.md")

    for text in (readme, product, glossary):
        assert "Isomorphic Governance" in text
        assert "same kernel" in text
        assert "profiles and adapters" in text
        assert "not product cloning" in text

    assert "governs the ETHOS product repository and adopted repositories" in readme
    assert "profile-specific checks, adapters, and proof depth" in product
    assert "Different profiles change admission, checks, adapters, and proof depth" in glossary


def test_canonical_product_docs_are_provider_neutral() -> None:
    for doc in PROVIDER_NEUTRAL_CANONICAL_DOCS:
        text = read(doc)
        for term in PRODUCT_VENDOR_TERMS:
            assert term not in text, (doc, term)


def test_canonical_product_docs_do_not_expose_predecessor_compatibility_language() -> None:
    canonical_doc_dirs = (
        "docs/governance",
        "docs/architecture",
        "docs/reference",
    )
    forbidden = (
        "legacy-compat",
        "legacy evidence",
        "legacy playbook",
        "legacy-preserving",
        "legacy embedded",
        "legacy public",
        "adopter legacy",
    )

    for directory in canonical_doc_dirs:
        for path in sorted((ROOT / directory).glob("*.md")):
            text = path.read_text(encoding="utf-8").lower()
            assert "legacy" not in text, path.relative_to(ROOT)
            for phrase in forbidden:
                assert phrase not in text, path.relative_to(ROOT)


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
        "docs/reference/glossary.md",
        "packages/ethos-core/README.md",
        "openspec/specs/kernel/spec.md",
    )

    for surface in canonical_surfaces:
        text = read(surface)
        for phrase in retired_phrases:
            assert phrase not in text, (surface, phrase)


def test_glossary_uses_canonical_kernel_terms() -> None:
    glossary = read("docs/reference/glossary.md")

    for term in (
        "Authority",
        "Subject",
        "Commitment",
        "Change",
        "Evidence",
        "Claim",
        "Chronicle",
    ):
        assert f"## {term}" in glossary

    for retired_term in ("Constitution", "Contract", "Inscription", "Transition"):
        assert f"## {retired_term}" not in glossary


def test_repository_profile_contract_requires_backend_control_manifest() -> None:
    text = read("docs/governance/repository-profile-contract.md")

    for phrase in (
        "external_backend.control",
        "ExternalEthosBackendSwitch",
        "default_backend",
        "rollback_mode",
        "configuration only",
    ):
        assert phrase in text


def test_boundary_convergence_requires_parity_freeze_and_retirement_decision() -> None:
    text = read("docs/governance/product-boundary-convergence.md")

    for phrase in (
        "migration oracle",
        "frozen fallback / reference implementation",
        "External Shadow Parity",
        "Rollback Window",
        "Retirement Decision",
        "must not be deleted automatically",
        "ethos quality generated-artifacts --root <repo> --json",
        "profile-declared backend control manifest",
    ):
        assert phrase in text
    assert "ETHOS_BACKEND=external <adopter-runner> ethos status" in text
    assert "ETHOS_BACKEND=embedded <adopter-runner> ethos status" in text
    assert "<adopter-runner>" in text
    assert "reference adopter" in text
    assert "identity and path" in text


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
        "domain data-contract rules",
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
    assert "shadow-parity.schema.json" in text


def test_product_design_contract_is_repository_audited_with_target_ontology() -> None:
    for doc in (
        "docs/governance/product-design-contract.md",
        "docs/architecture/package-ontology.md",
        "docs/governance/product-boundary-convergence.md",
        "docs/governance/capability-parity-ledger.md",
        "docs/governance/repository-profile-contract.md",
        "docs/governance/config-boundary-model.md",
        "docs/governance/adopter-boundary-and-retirement.md",
    ):
        assert doc in REQUIRED_DOCS

    report = repository_audit(ROOT, openspec_mode="shape")
    target = report["target_package_ontology"]

    assert target["ok"] is True
    assert target["contract_ok"] is True
    assert target["physical_target_homes_present"] is True
    assert target["migration_complete"] is True
    assert target["migration_status"] == "complete"
    assert target["target_packages"] == [
        "ethos-core",
        "ethos",
    ]
    assert target["migration_hosts"] == []
    assert target["target_distribution_adapters"] == ["distributions/npm"]
    assert target["distribution_migration_hosts"] == []


def test_repository_audit_uses_canonical_package_ontology_contract() -> None:
    contract = package_ontology_report()
    audit = repository_audit(ROOT, openspec_mode="shape")

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
    report = repository_audit(ROOT, openspec_mode="shape")
    ontology = report["package_ontology"]

    target_packages = set(ontology["target_package_contract"])
    migration_hosts = set(ontology["migration_host_packages"])

    assert target_packages.isdisjoint(migration_hosts)
    assert "ethos" in target_packages
    assert "ethos" not in migration_hosts
    assert ontology["migration_host_lifecycle"] == {}


def test_low_level_active_surfaces_do_not_use_philosophy_labels() -> None:
    scanned_roots = (
        ROOT / "packages",
        ROOT / "system",
        ROOT / ".config",
        ROOT / ".githooks",
    )
    allowed = {ROOT / "system" / "axioms.md"}
    forbidden = (
        "system/" + "tao",
        "tao " + "First",
        "tao " + "FP",
        "ETHOS " + "Ta" + "o",
        "道" + ":",
    )
    offenders: list[str] = []
    for base in scanned_roots:
        for path in base.rglob("*"):
            if not path.is_file() or path in allowed:
                continue
            if any(part in {"__pycache__", ".pytest_cache", ".ruff_cache"} for part in path.parts):
                continue
            if path.suffix in {".pyc", ".coverage"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if any(term in text for term in forbidden):
                offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []
