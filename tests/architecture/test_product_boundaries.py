from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

from ethos.repository.policy.boundary.product import contributor_policy_report
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos_core.contracts.package.ontology import RETIRED_PRODUCT_FAMILIES
from ethos_core.contracts.package.ontology import RETIRED_PRODUCT_FAMILY_TOKENS
from ethos_core.contracts.package.ontology import package_ontology_report

ROOT = Path(__file__).resolve().parents[2]
RETIRED_PUBLIC_ROOTS = {
    "wt",
    "proof",
    "mission",
    "skill-evolution",
    "agent-surface-contract",
}

CURRENT_PRODUCT_SURFACES = (
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "docs" / "architecture",
    ROOT / "docs" / "concepts",
    ROOT / "docs" / "governance",
    ROOT / "docs" / "reference",
    ROOT / "openspec" / "specs",
    ROOT / "evidence" / "claims",
    ROOT / ".agents" / "skills",
)
ACTIVE_OPENSPEC_CHANGES: tuple[Path, ...] = ()
RETIRED_SELF_TERMS = (
    "ethos self",
    "self_audit",
    "self-audit",
    "self audit",
    "self-governance",
    "self-evolution",
    "self-hosting",
    "single-kernel dual-posture",
    "single_kernel_dual_posture",
    "dual-posture",
    "product_self",
    "adopter_repository",
    "posture",
)
HOST_PROJECTION_LABELS = (
    "Open Worktree",
    "Checkout",
)


CURRENT_COMPATIBILITY_RESIDUE = (
    "legacy",
    "legacy-compat",
    "legacy-compatible",
    "compatibility alias",
    "compat playbook",
    "compat mode",
)


def product_surface_files() -> list[Path]:
    files: list[Path] = []
    for surface in CURRENT_PRODUCT_SURFACES:
        if surface.is_file():
            files.append(surface)
            continue
        for path in surface.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".toml", ".yaml", ".yml"}:
                files.append(path)
    return sorted(files)


def active_openspec_files() -> list[Path]:
    files: list[Path] = []
    for root in ACTIVE_OPENSPEC_CHANGES:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".toml", ".yaml", ".yml"}:
                files.append(path)
    return sorted(files)


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_kernel_has_no_side_effect_or_profile_imports() -> None:
    forbidden = {
        "ethos.repository",
        "ethos.assistants",
        "ethos.adapters",
        "sqlite3",
        "subprocess",
        "tools",
    }

    for path in (ROOT / "packages/ethos-core/src").rglob("*.py"):
        assert imported_modules(path).isdisjoint(forbidden), path


def test_target_product_packages_exist_with_build_metadata() -> None:
    for package in package_ontology_report()["target_packages"]:
        root = ROOT / "packages" / package
        assert (root / "README.md").exists(), package
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
        assert 'build-backend = "hatchling.build"' in pyproject


def test_semantic_target_packages_do_not_import_provider_execution() -> None:
    # Keyed on the REAL terminal source trees (2-package world + intra-ethos
    # sub-packages), each asserted to exist so this scan can never silently go
    # vacuous again if a future move deletes a directory.
    forbidden_by_source = {
        # ethos-core absorbs contracts (TOML parse) — tomllib ok; no subprocess/sqlite/shell.
        "packages/ethos-core/src/ethos_core": {"subprocess", "sqlite3", "shutil"},
        # The repository layer holds read-only governance reports; it must not reach
        # UP into the adapters layer (surface>domain>adapters>repository).
        "packages/ethos/src/ethos/repository": {"ethos.adapters", "sqlite3"},
    }
    for source_rel, forbidden in forbidden_by_source.items():
        source = ROOT / source_rel
        assert source.is_dir(), (
            f"terminal source tree missing (scan would be vacuous): {source_rel}"
        )
        assert any(source.rglob("*.py")), f"no modules under {source_rel} — vacuous scan"
        for path in source.rglob("*.py"):
            assert imported_modules(path).isdisjoint(forbidden), path


def test_product_surfaces_are_author_and_adopter_neutral() -> None:
    report = product_boundary_report(ROOT)

    assert report["ok"] is True, report["findings"]


def test_workspace_contributor_policy_is_multi_actor() -> None:
    report = contributor_policy_report(ROOT)

    assert report["ok"] is True, report["findings"]
    summary = report["summary"]
    policy = report["policy"]
    assert summary["identity_mode"] == "external"
    assert summary["identity_count"] >= 2
    assert {"maintainer", "team", "bot"} <= set(summary["roles"])
    assert policy["identity_model"] == "external_role_policy"
    assert {
        "git_author",
        "git_committer",
        "work_lane_actor",
        "reviewer",
        "maintainer",
        "bot",
        "team",
        "adopter_side_owner",
    } <= set(policy["distinct_identity_facts"])


def test_product_release_metadata_has_no_person_attribution() -> None:
    import json
    import tomllib

    npm_manifest = json.loads((ROOT / "distributions/npm/package.json").read_text())
    assert "author" not in npm_manifest
    assert "authors" not in npm_manifest
    assert "maintainers" not in npm_manifest

    for rel in (
        "pyproject.toml",
        "packages/ethos/pyproject.toml",
        "packages/ethos-core/pyproject.toml",
    ):
        project = tomllib.loads((ROOT / rel).read_text(encoding="utf-8"))["project"]
        assert "authors" not in project
        assert "maintainers" not in project


def test_distribution_package_manifest_is_enterprise_neutral() -> None:
    report = product_boundary_report(ROOT)
    npm_manifest = json.loads((ROOT / "distributions/npm/package.json").read_text())
    root_manifest = json.loads((ROOT / "package.json").read_text())

    assert report["ok"] is True, report["findings"]
    assert root_manifest["private"] is True
    assert npm_manifest["files"] == ["bin/ethos.mjs", "README.md"]
    assert "author" not in npm_manifest
    assert "authors" not in npm_manifest
    assert "maintainers" not in npm_manifest
    assert "contributors" not in npm_manifest
    assert "distribution_manifest_files" in report["policy"]
    assert "historical evidence" in report["policy"]["distribution_boundary"]


def test_product_python_code_does_not_hardcode_adopter_terms() -> None:
    report = product_boundary_report(ROOT)

    assert report["ok"] is True, report["findings"]


def test_active_product_surfaces_have_no_named_private_reference_dependency() -> None:
    report = product_boundary_report(ROOT)

    assert report["ok"] is True, report["findings"]
    assert report["summary"]["by_kind"].get("private_reference_literal", 0) == 0
    assert "private_reference_boundary" in report["policy"]
    assert not (ROOT / ".ethos" / "quality-regime-decision.md").exists()


def test_current_product_surfaces_do_not_use_retired_self_terms() -> None:
    findings: list[str] = []
    for path in product_surface_files():
        text = path.read_text(encoding="utf-8").lower()
        for term in RETIRED_SELF_TERMS:
            if term in text:
                findings.append(f"{path.relative_to(ROOT)}: {term}")

    assert findings == []


def test_current_product_surfaces_do_not_use_host_projection_labels() -> None:
    findings: list[str] = []
    for path in product_surface_files():
        text = path.read_text(encoding="utf-8")
        for label in HOST_PROJECTION_LABELS:
            if label in text:
                findings.append(f"{path.relative_to(ROOT)}: {label}")

    assert findings == []


def test_current_product_surface_has_no_superpowers_execution_plan_docs() -> None:
    assert not (ROOT / "docs" / "superpowers").exists()


def test_active_openspec_changes_do_not_expose_compatibility_residue() -> None:
    findings: list[str] = []
    for path in active_openspec_files():
        text = path.read_text(encoding="utf-8").lower()
        for phrase in CURRENT_COMPATIBILITY_RESIDUE:
            if phrase in text:
                findings.append(f"{path.relative_to(ROOT)}: {phrase}")

    assert findings == []


def test_target_packages_do_not_import_migration_hosts() -> None:
    contract = package_ontology_report()
    migration_imports = {package.replace("-", "_") for package in contract["migration_hosts"]}

    for package in contract["target_packages"]:
        source = ROOT / "packages" / package / "src"
        for path in source.rglob("*.py"):
            assert imported_modules(path).isdisjoint(migration_imports), path


def test_product_workspace_has_no_migration_host_packages() -> None:
    contract = package_ontology_report()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert contract["migration_hosts"] == []
    for package in RETIRED_PRODUCT_FAMILIES:
        assert f"packages/{package}" not in pyproject
        assert not (ROOT / "packages" / package).exists()


def test_ethos_workspace_config_uses_target_product_packages() -> None:
    workspace = tomllib.loads((ROOT / ".ethos" / "workspace.toml").read_text())
    packages = workspace.get("package", [])
    names = {package["name"] for package in packages}
    paths = {package["path"] for package in packages}

    assert names == set(package_ontology_report()["target_packages"])
    core_domains = {
        domain
        for package in packages
        if package["name"] == "ethos-core"
        for domain in package.get("domains", [])
    }
    ethos_domains = {
        domain
        for package in packages
        if package["name"] == "ethos"
        for domain in package.get("domains", [])
    }
    # The two-package world: ethos-core carries the pure kernel + absorbed
    # contracts/quality; ethos carries the runtime (cli/adapters/repository/assistants).
    assert core_domains >= {"kernel", "contracts", "quality"}
    assert ethos_domains >= {"cli", "adapters", "repository-lifecycle", "assistants"}
    for retired in RETIRED_PRODUCT_FAMILY_TOKENS:
        assert retired not in names
        assert f"packages/{retired}" not in paths


def test_active_claims_do_not_use_retired_product_family_subjects() -> None:
    for path in sorted((ROOT / "evidence" / "claims").glob("*.toml")):
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        claim = payload.get("claim", {})
        if claim.get("state") != "active":
            continue
        text = "\n".join(
            [path.stem]
            + [
                str(claim.get(field, ""))
                for field in (
                    "id",
                    "subject",
                )
            ]
        )
        for retired in RETIRED_PRODUCT_FAMILY_TOKENS:
            assert retired not in text, path


def test_npm_distribution_lives_outside_python_packages() -> None:
    assert (ROOT / "distributions" / "npm" / "package.json").exists()
    assert (ROOT / "distributions" / "npm" / "bin" / "ethos.mjs").exists()
    assert not (ROOT / "packages" / "ethos-node").exists()


def test_cli_uses_cyclopts_not_legacy_parser() -> None:
    # The CLI framework (the shared App objects) lives in the surface _base module;
    # cli.py is a thin dispatcher that imports the command-group modules. The
    # invariant is that the surface uses Cyclopts and no module reaches for the legacy parser.
    base_path = ROOT / "packages/ethos/src/ethos/surface/cli/_base.py"
    assert "cyclopts" in imported_modules(base_path)
    legacy_parser = "arg" + "parse"

    for path in (ROOT / "packages/ethos/src/ethos/surface/cli").glob("*.py"):
        assert legacy_parser not in imported_modules(path), path
    assert legacy_parser not in imported_modules(ROOT / "packages/ethos/src/ethos/cli.py")


def test_tool_command_surfaces_use_cyclopts_not_legacy_parser() -> None:
    """Keep repository tool CLIs under the same command framework as product CLIs."""
    tool_cli_paths = [
        ROOT / "tools/ci/ci_templates.py",
        ROOT / "tools/ci/hosted_observation.py",
    ]

    for path in tool_cli_paths:
        modules = imported_modules(path)
        assert "cyclopts" in modules, path
        assert "arg" + "parse" not in modules, path


def test_tracked_python_follows_parser_model_and_export_policy() -> None:
    for relative in subprocess.run(
        ["git", "ls-files", "*.py"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines():
        path = ROOT / relative
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert "arg" + "parse" not in imported_modules(path), path
        assert not {"attr", "attrs"} & imported_modules(path), path
        assert all(
            ast.unparse(decorator).startswith("dataclass(frozen=True, slots=True")
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Name)
            and decorator.func.id == "dataclass"
        ), path
        assert not any(
            (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "__all__"
                    for target in node.targets
                )
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "__all__"
            )
            for node in ast.walk(tree)
        ), path


def test_openspec_is_official_governance_surface_not_command_root() -> None:
    assert (ROOT / "openspec" / "config.yaml").exists()
    assert (ROOT / "openspec" / "specs" / "kernel" / "spec.md").exists()

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "openspec =" not in pyproject


def test_openspec_specs_are_mece_product_families() -> None:
    expected = {
        "adapters",
        "assistant-projections",
        "command-plane",
        "contracts",
        "kernel",
        "distribution",
        "quality",
        "repository-governance",
        "proof-hosts",
    }
    actual = {path.parent.name for path in (ROOT / "openspec" / "specs").glob("*/spec.md")}

    assert actual == expected


def test_active_openspec_change_deltas_use_target_product_families() -> None:
    expected = {
        "adapters",
        "assistant-projections",
        "command-plane",
        "contracts",
        "kernel",
        "distribution",
        "quality",
        "repository-governance",
        "proof-hosts",
    }
    changes_root = ROOT / "openspec" / "changes"
    active_spec_files = [
        path
        for path in changes_root.glob("*/specs/*/spec.md")
        if "/archive/" not in path.as_posix()
    ]

    for path in active_spec_files:
        assert path.parent.name in expected, path


def test_openspec_workspace_validates_with_official_cli() -> None:
    completed = subprocess.run(
        ["openspec", "validate", "--all", "--strict", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 0, payload
    assert payload["summary"]["totals"]["failed"] == 0


def test_retired_public_roots_are_not_console_scripts() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    for retired in RETIRED_PUBLIC_ROOTS:
        assert f"{retired} =" not in pyproject


def test_canonical_docs_do_not_promote_retired_public_roots() -> None:
    for path in [ROOT / "README.md", *(ROOT / "docs").rglob("*.md")]:
        text = path.read_text(encoding="utf-8")
        for retired in RETIRED_PUBLIC_ROOTS:
            assert f"`{retired}`" not in text, path

        in_fence = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if not in_fence or not stripped:
                continue
            command_root = stripped.split()[0]
            assert command_root not in RETIRED_PUBLIC_ROOTS, (path, stripped)


def test_product_behavior_does_not_live_in_tools_directory() -> None:
    tools_root = ROOT / "tools"
    assert tools_root.exists()
    allowed = {tools_root / "ci", tools_root / "ci" / "scripts"}
    runtime_cache_dirs = {"__pycache__", ".pytest_cache", ".ruff_cache"}
    product_dirs = {
        path
        for path in tools_root.rglob("*")
        if path.is_dir() and not any(part in runtime_cache_dirs for part in path.parts)
    }
    assert product_dirs <= allowed
    assert all(path.suffix == ".sh" for path in (tools_root / "ci" / "scripts").iterdir())


def test_pre_commit_uses_local_deterministic_quality_hook() -> None:
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "repo: local" in config
    assert "tools/ci/scripts/run-python-lint.sh" in config
    assert "uv run --group dev ruff check" not in config
    assert "github.com" not in config


def test_repo_local_skills_are_thin_playbook_projection() -> None:
    skills_root = ROOT / ".agents" / "skills"

    assert (skills_root / "README.md").exists()
    assert (skills_root / "activation.toml").exists()
    expected = {
        "ethos-repository-governance",
        "ethos-change-lifecycle",
        "ethos-skill-portfolio-governance",
        "ethos-quality-gate-governance",
        "ethos-adoption-profile-governance",
    }
    assert expected <= {path.name for path in skills_root.iterdir() if path.is_dir()}
    for skill_id in expected:
        skill_text = (skills_root / skill_id / "SKILL.md").read_text(encoding="utf-8")
        assert "## Workflow" in skill_text
        assert "## Evidence" in skill_text
        assert "source of truth" in skill_text or "repository truth" in skill_text


def test_product_packages_have_canonical_readmes() -> None:
    for package in (
        "ethos",
        "ethos-core",
    ):
        readme = ROOT / "packages" / package / "README.md"
        assert readme.exists()
        assert "Subject" in readme.read_text(encoding="utf-8")


def test_npm_launcher_is_distribution_adapter_not_python_family() -> None:
    package = ROOT / "distributions" / "npm" / "package.json"
    manifest = json.loads(package.read_text(encoding="utf-8"))

    assert manifest["name"] == "@agentic-workflow/ethos"
    assert manifest["bin"] == {"ethos": "bin/ethos.mjs"}
    assert manifest["private"] is False
    assert manifest["repository"]["url"] == "https://example.invalid/ethos.git"
    assert manifest["homepage"] == "https://example.invalid/ethos"
    assert manifest["bugs"]["url"] == "https://example.invalid/ethos/issues"
    assert manifest["publishConfig"]["access"] == "public"
    assert "governance" in manifest["keywords"]

    root_manifest = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert root_manifest["packageManager"] == "npm@11.12.1"

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"packages/ethos-node"' not in pyproject


def test_npm_launcher_runs_source_checkout_command_plane() -> None:
    if not shutil.which("node") or not shutil.which("uv"):
        return

    completed = subprocess.run(
        ["node", "distributions/npm/bin/ethos.mjs", "--version"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "0.1.0a1"


def test_npm_launcher_fallback_executes_python_command_once(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        return

    launcher = tmp_path / "package" / "bin" / "ethos.mjs"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        (ROOT / "distributions" / "npm" / "bin" / "ethos.mjs").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    log = tmp_path / "python-calls.log"
    fake_python = fake_bin / "python3"
    fake_python.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "-c" ] || [ "$2" = "-c" ]; then exit 0; fi\n'
        f"printf '%s\\n' \"$*\" >> {log}\n"
        "printf '0.1.0a1\\n'\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}/bin{os.pathsep}/usr/bin"
    completed = subprocess.run(
        [node, str(launcher), "--version"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "0.1.0a1"
    assert log.read_text(encoding="utf-8").splitlines() == ["-P -m ethos.cli --version"]


def test_npm_launcher_does_not_execute_untrusted_cwd_source_checkout(
    tmp_path: Path,
) -> None:
    node = shutil.which("node")
    if not node:
        return

    launcher = tmp_path / "package" / "bin" / "ethos.mjs"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        (ROOT / "distributions" / "npm" / "bin" / "ethos.mjs").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    fake_repo = tmp_path / "untrusted-repo"
    (fake_repo / "packages" / "ethos").mkdir(parents=True)
    (fake_repo / "pyproject.toml").write_text("[project]\nname='fake'\n", encoding="utf-8")
    (fake_repo / "packages" / "ethos" / "pyproject.toml").write_text(
        "[project]\nname='fake-ethos'\n",
        encoding="utf-8",
    )
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    marker = tmp_path / "uv-was-called"
    fake_uv = fake_bin / "uv"
    fake_uv.write_text(f"#!/bin/sh\ntouch {marker}\nexit 42\n", encoding="utf-8")
    fake_uv.chmod(0o755)
    fake_python = fake_bin / "python3"
    fake_python.write_text(
        '#!/bin/sh\nif [ "$1" = "-c" ] || [ "$2" = "-c" ]; then exit 1; fi\nexit 127\n',
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}/bin{os.pathsep}/usr/bin"
    completed = subprocess.run(
        [node, str(launcher), "--version"],
        cwd=fake_repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 127
    assert not marker.exists()


def test_npm_launcher_selects_python_with_ethos_module(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        return

    launcher = tmp_path / "package" / "bin" / "ethos.mjs"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        (ROOT / "distributions" / "npm" / "bin" / "ethos.mjs").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    log = tmp_path / "python-calls.log"
    fake_python3 = fake_bin / "python3"
    fake_python3.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "-c" ] || [ "$2" = "-c" ]; then exit 1; fi\n'
        f"printf '%s\\n' \"python3:$*\" >> {log}\n"
        "exit 99\n",
        encoding="utf-8",
    )
    fake_python3.chmod(0o755)
    fake_python = fake_bin / "python"
    fake_python.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "-c" ] || [ "$2" = "-c" ]; then exit 0; fi\n'
        f"printf '%s\\n' \"python:$*\" >> {log}\n"
        "printf '0.1.0a1\\n'\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}/bin{os.pathsep}/usr/bin"
    completed = subprocess.run(
        [node, str(launcher), "--version"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "0.1.0a1"
    assert log.read_text(encoding="utf-8").splitlines() == ["python:-P -m ethos.cli --version"]


def test_markdown_docs_declare_subject_role_state_relations() -> None:
    for path in (ROOT / "docs").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), path
        header = text.split("---", 2)[1]
        for field in ("subject:", "role:", "state:", "relations:"):
            assert field in header, path


def test_command_plane_docs_use_gap_or_signal_explain_language() -> None:
    text = (ROOT / "docs/reference/command-plane.md").read_text(encoding="utf-8")

    assert "ethos explain <gap-or-signal>" in text
    assert "ethos explain required_gaps" not in text
    assert "projects one gap or advisory signal into that taxonomy" in text
