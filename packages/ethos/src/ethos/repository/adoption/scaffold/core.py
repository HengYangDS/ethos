"""Adoption scaffold file builders."""

from __future__ import annotations

import hashlib
import json
import tomllib
from typing import TYPE_CHECKING

import ethos.repository.adoption.scaffold.skills.core as skill_scaffold
from ethos.repository.adoption.scaffold.decisions.core import decision_code_links
from ethos.repository.adoption.scaffold.decisions.core import decision_dependency_map
from ethos.repository.adoption.scaffold.decisions.core import decision_index
from ethos.repository.adoption.scaffold.decisions.core import decision_record_template
from ethos.repository.adoption.scaffold.decisions.core import decision_records
from ethos.repository.adoption.scaffold.decisions.core import decisions_accepted
from ethos.repository.adoption.scaffold.decisions.core import decisions_superseded
from ethos.repository.adoption.scaffold.decisions.core import decisions_templates
from ethos.repository.adoption.scaffold.documents.pages import agents_doc
from ethos.repository.adoption.scaffold.documents.pages import changelog_doc
from ethos.repository.adoption.scaffold.documents.pages import contributing_doc
from ethos.repository.adoption.scaffold.documents.pages import docs_evidence
from ethos.repository.adoption.scaffold.documents.pages import docs_history
from ethos.repository.adoption.scaffold.documents.pages import docs_index
from ethos.repository.adoption.scaffold.documents.pages import docs_readme
from ethos.repository.adoption.scaffold.documents.pages import docs_reference
from ethos.repository.adoption.scaffold.documents.pages import docs_taxonomy
from ethos.repository.adoption.scaffold.documents.pages import governance_doc
from ethos.repository.adoption.scaffold.documents.pages import quickstart
from ethos.repository.adoption.scaffold.documents.pages import release_toml
from ethos.repository.adoption.scaffold.openspec import capability_profile
from ethos.repository.adoption.scaffold.openspec import openspec_capability_template
from ethos.repository.adoption.scaffold.openspec import openspec_change_template
from ethos.repository.adoption.scaffold.openspec import openspec_changes_readme
from ethos.repository.adoption.scaffold.openspec import openspec_config
from ethos.repository.adoption.scaffold.openspec import openspec_families
from ethos.repository.adoption.scaffold.openspec import openspec_readme
from ethos.repository.adoption.scaffold.openspec import openspec_spec
from ethos.repository.adoption.scaffold.openspec import openspec_specs_readme
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
    ".gitignore",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    ".config/ethos/generated-artifacts.toml",
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


def gitignore() -> str:
    return """# Python and local editor/runtime state.
.venv/
__pycache__/
*.py[cod]

# ETHOS local coordination state is host-local.
.ethos/state/*
!.ethos/state/.gitignore

# Semantic ignored generated homes. The declarative contract lives in
# .config/ethos/generated-artifacts.toml; these directories are outputs, not
# repository truth.
.cache/
build/

# Root tool caches and package output are denied residue. Tools must route
# caches to build/runtime/tool-cache/<tool>/, provider work to
# build/runtime/work/<provider>/, machine evidence to build/evidence/ or
# build/ethos/, and local artifacts to build/artifacts/<kind>/.
.import_linter_cache/
.import-linter-cache/
.pytest_cache/
.ruff_cache/
.mypy_cache/
.tox/
.nox/
.uv-cache/
dist/

# Root coverage and pytest residue may be ignored local cleanup debt, but
# tracked copies are still generated-artifact topology violations.
.coverage
.coverage.*
coverage.xml
junit.xml
"""


def generated_artifacts_toml() -> str:
    return (
        "# Declarative generated-artifact topology contract for this adopted\n"
        "# repository.\n"
        "# Runtime bytes belong in ignored semantic homes; only curated evidence becomes\n"
        "# repository truth after review/promotion.\n"
        "\n"
        "[contract]\n"
        'name = "generated-artifact-topology"\n'
        "version = 1\n"
        'truth_boundary = "declarative_policy"\n'
        "\n"
        "[lifecycle.runtime_cache]\n"
        'homes = [".cache/local-state", ".ethos/state", "build/runtime/tool-cache", '
        '"build/runtime/work"]\n'
        "tracked = false\n"
        "promotion_allowed = false\n"
        'rule = "delete or recreate from source commands; never promote runtime cache"\n'
        "\n"
        "[lifecycle.machine_evidence]\n"
        'homes = ["build/evidence", "build/ethos"]\n'
        "tracked = false\n"
        "promotion_allowed = true\n"
        'rule = "regenerate on HEAD movement; promote only by explicit review or command"\n'
        "\n"
        "[lifecycle.local_artifact]\n"
        'homes = ["build/artifacts"]\n'
        "tracked = false\n"
        "promotion_allowed = false\n"
        'rule = "rebuild from package metadata or release commands"\n'
        "\n"
        "[lifecycle.curated_evidence]\n"
        'homes = ["docs/evidence", "evidence/chronicle", "evidence/parity"]\n'
        "tracked = true\n"
        "promotion_allowed = false\n"
        'rule = "retire or supersede by tracked review; do not clean as cache"\n'
        "\n"
        "[denied.root_cache]\n"
        "homes = [\n"
        '  ".import_linter_cache",\n'
        '  ".import-linter-cache",\n'
        '  ".pytest_cache",\n'
        '  ".ruff_cache",\n'
        '  ".mypy_cache",\n'
        '  ".tox",\n'
        '  ".nox",\n'
        '  ".uv-cache",\n'
        "]\n"
        "\n"
        "[denied.legacy_flat_home]\n"
        'homes = ["build/cache", "build/runtime/gitlab-ci-local", "dist"]\n'
        "\n"
        "[routes]\n"
        'tool_cache = "build/runtime/tool-cache/<tool>"\n'
        'provider_work = "build/runtime/work/<provider>"\n'
        'machine_evidence = "build/evidence/<concern>"\n'
        'ethos_machine_projection = "build/ethos/<concern>"\n'
        'local_artifact = "build/artifacts/<kind>"\n'
        'curated_evidence = "docs/evidence/<topic> or '
        'evidence/chronicle/<topic>/<date>.md"\n'
    )


STATIC_DEFAULT_FILES = {
    ".gitignore": gitignore(),
    ".config/ethos/generated-artifacts.toml": generated_artifacts_toml(),
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
        "    - ethos status --json\n"
        "    - ethos report --json\n"
        "    - ethos prove --json\n"
        "    - openspec validate --all --strict --json\n"
    )


def default_files(root: Path, profile: str) -> dict[str, str]:
    project_name = json.dumps(root.name)
    governance_skill_text = skill_scaffold.governance_skill()
    skill_portfolio_skill_text = skill_scaffold.skill_portfolio_skill()
    adoption_profile_skill_text = skill_scaffold.adoption_profile_skill()
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
            skill_scaffold.governance_skill_package(governance_digest)
        ),
        ".agents/skills/ethos-skill-portfolio-governance/SKILL.md": skill_portfolio_skill_text,
        ".agents/skills/ethos-skill-portfolio-governance/package.toml": (
            skill_scaffold.skill_portfolio_skill_package(skill_portfolio_digest)
        ),
        ".agents/skills/ethos-adoption-profile-governance/SKILL.md": adoption_profile_skill_text,
        ".agents/skills/ethos-adoption-profile-governance/package.toml": (
            skill_scaffold.adoption_profile_skill_package(adoption_profile_digest)
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
            "      - run: ethos status --json\n"
            "      - run: ethos report --json\n"
            "      - run: ethos prove --json\n"
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
