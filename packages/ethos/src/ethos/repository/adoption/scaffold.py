"""Adoption scaffold file builders."""

from __future__ import annotations

import hashlib
import json
import tomllib
from typing import TYPE_CHECKING

from ethos.repository.adoption.scaffold_docs.decisions import decision_code_links
from ethos.repository.adoption.scaffold_docs.decisions import decision_dependency_map
from ethos.repository.adoption.scaffold_docs.decisions import decision_index
from ethos.repository.adoption.scaffold_docs.decisions import decision_record_template
from ethos.repository.adoption.scaffold_docs.decisions import decision_records
from ethos.repository.adoption.scaffold_docs.decisions import decisions_accepted
from ethos.repository.adoption.scaffold_docs.decisions import decisions_superseded
from ethos.repository.adoption.scaffold_docs.decisions import decisions_templates
from ethos.repository.adoption.scaffold_docs.pages import agents_doc
from ethos.repository.adoption.scaffold_docs.pages import changelog_doc
from ethos.repository.adoption.scaffold_docs.pages import contributing_doc
from ethos.repository.adoption.scaffold_docs.pages import docs_evidence
from ethos.repository.adoption.scaffold_docs.pages import docs_history
from ethos.repository.adoption.scaffold_docs.pages import docs_index
from ethos.repository.adoption.scaffold_docs.pages import docs_readme
from ethos.repository.adoption.scaffold_docs.pages import docs_reference
from ethos.repository.adoption.scaffold_docs.pages import docs_taxonomy
from ethos.repository.adoption.scaffold_docs.pages import governance_doc
from ethos.repository.adoption.scaffold_docs.pages import quickstart
from ethos.repository.adoption.scaffold_docs.pages import release_toml
from ethos.repository.adoption.scaffold_docs.skills import adoption_profile_skill
from ethos.repository.adoption.scaffold_docs.skills import adoption_profile_skill_package
from ethos.repository.adoption.scaffold_docs.skills import governance_skill
from ethos.repository.adoption.scaffold_docs.skills import governance_skill_package
from ethos.repository.adoption.scaffold_docs.skills import skill_portfolio_skill
from ethos.repository.adoption.scaffold_docs.skills import skill_portfolio_skill_package
from ethos.repository.adoption.scaffold_openspec import capability_profile
from ethos.repository.adoption.scaffold_openspec import openspec_capability_template
from ethos.repository.adoption.scaffold_openspec import openspec_change_template
from ethos.repository.adoption.scaffold_openspec import openspec_changes_readme
from ethos.repository.adoption.scaffold_openspec import openspec_config
from ethos.repository.adoption.scaffold_openspec import openspec_families
from ethos.repository.adoption.scaffold_openspec import openspec_readme
from ethos.repository.adoption.scaffold_openspec import openspec_spec
from ethos.repository.adoption.scaffold_openspec import openspec_specs_readme
from ethos_core.contracts.skill.activation import normalize_skill_activation
from ethos_core.contracts.skill.activation import skill_registry_digest

if TYPE_CHECKING:
    from pathlib import Path

OPENSPEC_CAPABILITIES = (
    "kernel",
    "contracts",
    "repository-governance",
    "adapters",
    "command-plane",
    "assistant-projections",
    "distribution",
    "quality",
    "proof-hosts",
)
BASE_ADOPTION_FILES = (
    "AGENTS.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    ".ethos/project.toml",
    ".ethos/workspace.toml",
    ".ethos/rules.toml",
    ".ethos/assistants.toml",
    ".ethos/release.toml",
    ".ethos/state/.gitignore",
    ".agents/skills/README.md",
    ".agents/skills/activation.toml",
    ".agents/skills/ethos-repository-governance/SKILL.md",
    ".agents/skills/ethos-repository-governance/package.toml",
    ".agents/skills/ethos-skill-portfolio-governance/SKILL.md",
    ".agents/skills/ethos-skill-portfolio-governance/package.toml",
    ".agents/skills/ethos-adoption-profile-governance/SKILL.md",
    ".agents/skills/ethos-adoption-profile-governance/package.toml",
    "openspec/config.yaml",
    "openspec/README.md",
    "openspec/specs/README.md",
    "openspec/specs/families.toml",
    "openspec/specs/capability.template.toml",
    "openspec/changes/README.md",
    "openspec/changes/template.md",
    "openspec/changes/.gitkeep",
    "openspec/changes/archive/.gitkeep",
    "docs/README.md",
    "docs/index.md",
    "docs/decisions/README.md",
    "docs/decisions/decision-index.md",
    "docs/decisions/decision-dependency-map.md",
    "docs/decisions/decision-code-links.md",
    "docs/decisions/accepted/README.md",
    "docs/decisions/superseded/README.md",
    "docs/decisions/templates/README.md",
    "docs/decisions/templates/decision-record.md",
    "docs/evidence/README.md",
    "docs/history/README.md",
    "docs/reference/README.md",
    "docs/start/quickstart.md",
    "docs/governance/ethos.md",
    "evidence/.gitkeep",
    "evidence/claims/.gitkeep",
    "system/schemas/kernel/.gitkeep",
)

STATIC_DEFAULT_FILES = {
    ".ethos/rules.toml": """[command_plane]
public = "ethos"

[formats]
user_config = "TOML"
machine_output = "JSON"
append_only_events = "JSONL"
local_state = "SQLite"

[artifacts]
state_path = ".ethos/state/state.sqlite"
state_tracked_truth = false
durable_evidence_roots = ["evidence", "evidence/claims"]

[gates]
governance_audit = "ethos report --json"
proof = "ethos prove --json"
report = "ethos report --json"
openspec = "openspec validate --all --strict --json"
""",
    ".ethos/assistants.toml": """[projection]
truth = "repository"
thin_adapter = true

[surfaces]
codex = "projection"
jetbrains = "projection"
mcp = "protocol-projection"
acp = "protocol-projection"
""",
    ".ethos/state/.gitignore": "*\n!.gitignore\n",
    "openspec/changes/.gitkeep": "",
    "openspec/changes/archive/.gitkeep": "",
    "evidence/.gitkeep": "",
    "evidence/claims/.gitkeep": "",
    "system/schemas/kernel/.gitkeep": "",
}


def _workspace_toml(root: Path, profile: str) -> str:
    packages_dir = root / "packages"
    if profile == "monorepo" and packages_dir.exists():
        blocks = []
        for package in sorted(path for path in packages_dir.iterdir() if path.is_dir()):
            blocks.append(
                f'[[package]]\nname = "{package.name}"\n'
                f'path = "packages/{package.name}"\ndomains = ["package"]\n'
            )
        if blocks:
            return "\n".join(blocks)
    return '[[package]]\nname = "root"\npath = "."\ndomains = ["repository"]\n'


def _skills_readme() -> str:
    return """# ETHOS Skills

Repo-local skills are workflow package projections over ETHOS repository truth.
They route agents toward tracked ETHOS commands, docs, schemas, claims, and
evidence; they are not an independent source of truth.

## Available Skills

| Skill | Use when |
| --- | --- |
| ethos-repository-governance | Governing repository truth, authority, proof, docs, and adoption. |
| ethos-skill-portfolio-governance | Creating, routing, validating, or retiring repo-local skills. |
| ethos-adoption-profile-governance | Applying profiles and preserving command isomorphism. |
"""


def _skills_activation(registry_digest: str) -> str:
    return f"""[meta]
version = 2
source_of_truth = "repository"
expected_registry_digest = "{registry_digest}"

[[skill]]
id = "ethos-repository-governance"
path = ".agents/skills/ethos-repository-governance/SKILL.md"
package_manifest = ".agents/skills/ethos-repository-governance/package.toml"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
subjects = ["repository-governance", "ethos", "adoption", "changed-scope"]
path_globs = [
  "AGENTS.md",
  "docs/index.md",
  "docs/start/**",
  "evolution/**",
  "evidence/claims/**",
  "packages/**",
  "schemas/**",
  "tests/**",
  "uv.lock",
  "pyproject.toml",
]
intent_tokens = ["ethos", "governance", "proof", "adoption", "skills"]
pre_reads = ["AGENTS.md", "docs/governance/ethos.md"]
during_rules = [
  "treat skills as projections over repository truth",
  "use ETHOS command JSON as machine evidence",
]
post_checks = ["ethos playbooks check --mode v2-strict --json", "ethos report --json"]
commands = ["ethos status", "ethos plan", "ethos prove", "ethos report"]
boundary = "workflow-package-projection"

[[skill]]
id = "ethos-skill-portfolio-governance"
path = ".agents/skills/ethos-skill-portfolio-governance/SKILL.md"
package_manifest = ".agents/skills/ethos-skill-portfolio-governance/package.toml"
subject = "skill-portfolio"
operation = "govern"
authority = "primary"
lifecycle = "active"
subjects = ["skill-portfolio", "skills", "activation", "projection-drift", "changed-scope"]
path_globs = [".agents/skills/**"]
intent_tokens = ["skill", "skills", "meta-skill", "playbook", "activation", "projection"]
pre_reads = ["AGENTS.md", ".agents/skills/README.md"]
during_rules = [
  "add a skill only for repeated repository-specific procedure",
  "keep SKILL.md narrow and evidence-bound",
]
post_checks = ["ethos playbooks check --mode v2-strict --json", "ethos report --json"]
may_coactivate = ["ethos-repository-governance"]
commands = ["ethos playbooks check", "ethos playbooks route", "ethos report"]
boundary = "workflow-package-projection"

[[skill]]
id = "ethos-adoption-profile-governance"
path = ".agents/skills/ethos-adoption-profile-governance/SKILL.md"
package_manifest = ".agents/skills/ethos-adoption-profile-governance/package.toml"
subject = "adoption-profile"
operation = "adopt"
authority = "primary"
lifecycle = "active"
subjects = ["adoption-profile", "adoption", "profile", "adapter", "changed-scope"]
path_globs = [".ethos/**", "docs/governance/**", "openspec/**", ".gitlab-ci.yml", ".github/**"]
intent_tokens = ["adopt", "adoption", "profile", "adapter", "other repository"]
pre_reads = ["AGENTS.md", "docs/governance/ethos.md"]
during_rules = [
  "profile changes proof depth and adapters, not command semantics",
  "durable adopter truth must be promoted into tracked repository surfaces",
]
post_checks = ["ethos playbooks check --mode v2-strict --json", "ethos report --json"]
may_coactivate = ["ethos-repository-governance"]
commands = ["ethos adopt", "ethos status", "ethos playbooks check", "ethos report", "ethos prove"]
boundary = "workflow-package-projection"
"""


def _skills_activation_with_digest() -> str:
    placeholder = "sha256:" + ("0" * 64)
    activation = _skills_activation(placeholder)
    registry = normalize_skill_activation(
        tomllib.loads(activation), source=".agents/skills/activation.toml"
    )
    return _skills_activation(skill_registry_digest(registry))


def _gitlab_ci() -> str:
    return (
        "stages:\n"
        "  - verify\n\n"
        "ethos:verify:\n"
        "  stage: verify\n"
        "  image: python:3.12\n"
        "  script:\n"
        "    - pip install uv\n"
        "    - npm install -g @fission-ai/openspec\n"
        "    - uv run --group dev pytest tests/unit tests/architecture -q\n"
        "    - uv run --group dev ruff check .\n"
        "    - openspec validate --all --strict --json\n"
        "    - uv run --package ethos ethos report --json\n"
        "    - uv run --package ethos ethos prove --json\n"
        "    - uv run --package ethos ethos quality release-policy --json\n"
    )


def _default_files(root: Path, profile: str) -> dict[str, str]:
    project_name = json.dumps(root.name)
    governance_skill_text = governance_skill()
    skill_portfolio_skill_text = skill_portfolio_skill()
    adoption_profile_skill_text = adoption_profile_skill()
    governance_digest = _package_digest_from_content({"SKILL.md": governance_skill_text})
    skill_portfolio_digest = _package_digest_from_content({"SKILL.md": skill_portfolio_skill_text})
    adoption_profile_digest = _package_digest_from_content(
        {"SKILL.md": adoption_profile_skill_text}
    )
    files = {
        "AGENTS.md": agents_doc(),
        "CONTRIBUTING.md": contributing_doc(),
        "CHANGELOG.md": changelog_doc(),
        ".ethos/project.toml": (f'[meta]\nname = {project_name}\nproduct = "ETHOS"\nversion = 1\n'),
        ".ethos/workspace.toml": _workspace_toml(root, profile),
        ".ethos/release.toml": release_toml(profile),
        "openspec/config.yaml": openspec_config(root),
        "openspec/README.md": openspec_readme(),
        "openspec/specs/README.md": openspec_specs_readme(),
        "openspec/specs/families.toml": openspec_families(),
        "openspec/specs/capability.template.toml": openspec_capability_template(),
        "openspec/changes/README.md": openspec_changes_readme(),
        "openspec/changes/template.md": openspec_change_template(),
        ".agents/skills/README.md": _skills_readme(),
        ".agents/skills/activation.toml": _skills_activation_with_digest(),
        ".agents/skills/ethos-repository-governance/SKILL.md": governance_skill_text,
        ".agents/skills/ethos-repository-governance/package.toml": (
            governance_skill_package(governance_digest)
        ),
        ".agents/skills/ethos-skill-portfolio-governance/SKILL.md": skill_portfolio_skill_text,
        ".agents/skills/ethos-skill-portfolio-governance/package.toml": (
            skill_portfolio_skill_package(skill_portfolio_digest)
        ),
        ".agents/skills/ethos-adoption-profile-governance/SKILL.md": adoption_profile_skill_text,
        ".agents/skills/ethos-adoption-profile-governance/package.toml": (
            adoption_profile_skill_package(adoption_profile_digest)
        ),
        "docs/README.md": docs_readme(root),
        "docs/index.md": docs_index(root),
        "docs/decisions/README.md": decision_records(),
        "docs/decisions/decision-index.md": decision_index(),
        "docs/decisions/decision-dependency-map.md": decision_dependency_map(),
        "docs/decisions/decision-code-links.md": decision_code_links(),
        "docs/decisions/accepted/README.md": decisions_accepted(),
        "docs/decisions/superseded/README.md": decisions_superseded(),
        "docs/decisions/templates/README.md": decisions_templates(),
        "docs/decisions/templates/decision-record.md": decision_record_template(),
        "docs/evidence/README.md": docs_evidence(),
        "docs/history/README.md": docs_history(),
        "docs/reference/README.md": docs_reference(),
        "docs/_meta/taxonomy.toml": docs_taxonomy(),
        "docs/start/quickstart.md": quickstart(),
        "docs/governance/ethos.md": governance_doc(),
        **STATIC_DEFAULT_FILES,
    }
    for family in OPENSPEC_CAPABILITIES:
        files[f"openspec/specs/{family}/spec.md"] = openspec_spec(family)
        files[f"openspec/specs/{family}/capability.toml"] = capability_profile(family)
    if profile == "gitlab":
        files[".gitlab-ci.yml"] = _gitlab_ci()
    if profile == "github":
        files[".github/workflows/ethos.yml"] = (
            "name: ethos\non: [push, pull_request]\njobs:\n"
            "  verify:\n    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n      - uses: astral-sh/setup-uv@v5\n"
            "      - run: uv run --group dev pytest tests/unit tests/architecture -q\n"
            "      - run: uv run --package ethos ethos report --json\n"
        )
    return files


def _package_digest_from_content(files: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative, content in sorted(files.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.encode("utf-8"))
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"
