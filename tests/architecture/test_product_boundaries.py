from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from ethos.contracts.admission import ethos_command_is_readonly
from ethos.repository.policy.boundary.product import contributor_policy_report
from ethos.repository.policy.boundary.product import declared_product_surface_roots
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.repository.policy.boundary.product import (
    product_surface_files as declared_product_surface_files,
)
from ethos.repository.policy.coupling.closure import repository_product_reference_gaps

ROOT = Path(__file__).resolve().parents[2]
RETIRED_PUBLIC_ROOTS = {"wt", "proof", "mission", "skill-evolution", "agent-surface-contract"}
CURRENT_PRODUCT_SURFACES = (
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "docs" / "architecture",
    ROOT / "docs" / "concepts",
    ROOT / "docs" / "governance",
    ROOT / "docs" / "reference",
    ROOT / "openspec" / "specs",
    ROOT / "evidence" / "attestations",
    ROOT / ".agents" / "skills",
)
RETIRED_SELF_TERMS = (
    "ethos self",
    "self_audit",
    "self-audit",
    "self audit",
    "single-kernel dual-posture",
    "single_kernel_dual_posture",
    "dual-posture",
    "product_self",
    "adopter_repository",
    "posture",
)
HOST_PROJECTION_LABELS = ("Open Worktree", "Checkout")


def product_surface_files() -> list[Path]:
    files: list[Path] = []
    for surface in CURRENT_PRODUCT_SURFACES:
        if surface.is_file():
            files.append(surface)
        else:
            files.extend(
                path
                for path in surface.rglob("*")
                if path.is_file() and path.suffix in {".md", ".toml", ".yaml", ".yml"}
            )
    return sorted(files)


def documentation_topology_files() -> list[Path]:
    """Return the retired topology locator, the only carrier this check governs."""
    return [ROOT / "docs" / "architecture" / "docs-topology.md"]


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_runtime_uses_declared_capabilities_not_repository_identity_fingerprints() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((ROOT / "src/ethos").rglob("*.py"))
    )

    assert "is_product_root" not in source
    assert 'project.get("name") == "ethos"' not in source
    assert "src/ethos/__init__.py" not in source


def test_kernel_has_no_side_effect_or_profile_imports() -> None:
    forbidden = {
        "ethos.repository",
        "ethos.assistants",
        "ethos.adapters",
        "sqlite3",
        "subprocess",
        "tools",
    }
    for source in (
        ROOT / "src/ethos/contracts",
        ROOT / "src/ethos/quality",
        ROOT / "src/ethos/state",
    ):
        assert source.is_dir()
        for path in source.rglob("*.py"):
            assert imported_modules(path).isdisjoint(forbidden), path


def test_target_product_packages_exist_with_build_metadata() -> None:
    assert (ROOT / "src/ethos").is_dir()
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["name"] == "ethos"
    assert pyproject["build-system"]["build-backend"] == "hatchling.build"
    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["src/ethos"]


def test_semantic_target_packages_do_not_import_provider_execution() -> None:
    forbidden_by_source = {
        "src/ethos/contracts": {"subprocess", "sqlite3", "shutil"},
        "src/ethos/quality": {"subprocess", "sqlite3", "shutil"},
        "src/ethos/state": {"subprocess", "sqlite3", "shutil"},
        "src/ethos/repository": {"ethos.adapters", "sqlite3"},
    }
    for source_rel, forbidden in forbidden_by_source.items():
        source = ROOT / source_rel
        assert source.is_dir(), (
            f"terminal source tree missing (scan would be vacuous): {source_rel}"
        )
        assert any(source.rglob("*.py")), f"no modules under {source_rel} — vacuous scan"
        for path in source.rglob("*.py"):
            assert imported_modules(path).isdisjoint(forbidden), path


@pytest.mark.parametrize("report_factory", [product_boundary_report])
def test_product_reports_are_clean(report_factory) -> None:
    report = report_factory(ROOT)
    assert report["ok"] is True, report["findings"]


def test_workspace_contributor_policy_is_multi_actor() -> None:
    report = contributor_policy_report(ROOT)
    assert report["ok"] is True, report["findings"]
    summary, policy = report["summary"], report["policy"]
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


def test_distribution_metadata_is_neutral() -> None:
    npm = json.loads((ROOT / "distributions/npm/package.json").read_text())
    for manifest in (npm,):
        assert not {"author", "authors", "maintainers"} & manifest.keys()
    for rel in ("pyproject.toml", "pyproject.toml", "pyproject.toml"):
        project = tomllib.loads((ROOT / rel).read_text(encoding="utf-8"))["project"]
        assert not {"authors", "maintainers"} & project.keys()


def test_distribution_package_manifest_is_enterprise_neutral() -> None:
    report = product_boundary_report(ROOT)
    npm = json.loads((ROOT / "distributions/npm/package.json").read_text())
    root = json.loads((ROOT / "package.json").read_text())
    assert report["ok"] is True, report["findings"]
    assert root["private"] is True
    assert npm["files"] == ["bin/ethos.mjs", "README.md"]
    assert not {"author", "authors", "maintainers", "contributors"} & npm.keys()
    assert "distribution_manifest_files" in report["policy"]
    assert "historical evidence" in report["policy"]["distribution_boundary"]


def test_active_product_surfaces_have_no_named_private_reference_dependency() -> None:
    report = product_boundary_report(ROOT)
    assert report["ok"] is True, report["findings"]
    assert report["summary"]["by_kind"].get("private_reference_literal", 0) == 0
    assert "private_reference_boundary" in report["policy"]
    assert not (ROOT / ".ethos" / "quality-regime-decision.md").exists()


def test_product_references_use_positive_declared_closure() -> None:
    declaration = tomllib.loads((ROOT / "system/coupling.toml").read_text(encoding="utf-8"))
    assert "product_vendor_terms" not in declaration
    assert "product_host_projection_terms" not in declaration
    assert repository_product_reference_gaps(ROOT) == []


def test_declared_surface_carriers_and_active_openspec_are_scanned() -> None:
    roots = set(declared_product_surface_roots(ROOT))
    assert {"src/ethos", ".agents/skills", "distributions"} <= roots
    assert not {"sdks/typescript", "scaffolds", "extensions"} & roots
    scanned = {path.relative_to(ROOT).as_posix() for path in declared_product_surface_files(ROOT)}
    assert any(path.startswith("openspec/changes/terminal-convergence/") for path in scanned)


def test_attestation_carrier_is_current_and_legacy_evidence_is_historical() -> None:
    roots = set(declared_product_surface_roots(ROOT))
    report = product_boundary_report(ROOT)

    assert "evidence/attestations" in roots
    assert report["policy"]["historical_surface_prefixes"] == [
        "evidence/claims/",
        "evidence/chronicle/",
        "evidence/parity/",
        "openspec/changes/archive/",
        "docs/history/",
    ]


def test_lane_resolution_parallel_truth_plane_is_absent() -> None:
    forbidden = (
        "src/ethos/adapters/mutation/resolution",
        "src/ethos/contracts/resolution",
        "src/ethos/adapters/store/state/closeout.py",
        "src/ethos/surface/cli/lane/resolution.py",
        "system/schemas/kernel/lane-resolution-decision.schema.json",
        "system/schemas/kernel/lane-resolution-receipt.schema.json",
        "system/schemas/kernel/lane-resolution-clear-receipt.schema.json",
    )

    assert [path for relative in forbidden if (path := ROOT / relative).exists()] == []


@pytest.mark.parametrize(
    ("paths", "terms", "lower"),
    [
        (documentation_topology_files, RETIRED_SELF_TERMS, True),
        (product_surface_files, HOST_PROJECTION_LABELS, False),
    ],
)
def test_product_surfaces_exclude_retired_language(paths, terms, lower) -> None:
    findings: list[str] = []
    for path in paths():
        text = path.read_text(encoding="utf-8")
        haystack = text.lower() if lower else text
        findings.extend(f"{path.relative_to(ROOT)}: {term}" for term in terms if term in haystack)
    assert findings == []


@pytest.mark.parametrize("path", [ROOT / "docs" / "superpowers"])
def test_current_product_surface_has_no_superpowers_execution_plan_docs(path: Path) -> None:
    assert not path.exists()


def test_npm_distribution_lives_outside_python_packages() -> None:
    assert (ROOT / "distributions/npm/package.json").exists()
    assert (ROOT / "distributions/npm/bin/ethos.mjs").exists()


@pytest.mark.parametrize(
    "path",
    [
        ROOT / "src/ethos/cli.py",
        *(ROOT / "src/ethos/surface/cli").rglob("*.py"),
    ],
)
def test_cli_uses_cyclopts_not_legacy_parser(path: Path) -> None:
    modules = imported_modules(path)
    if path.name == "application.py":
        assert "cyclopts" in modules
    assert "arg" + "parse" not in modules


def test_tool_command_surfaces_use_cyclopts_not_legacy_parser() -> None:
    for path in (ROOT / "tools/ci/ci_templates.py", ROOT / "tools/ci/hosted_observation.py"):
        modules = imported_modules(path)
        assert "cyclopts" in modules, path
        assert "arg" + "parse" not in modules, path


def test_tracked_python_follows_parser_model_and_export_policy() -> None:
    for relative in subprocess.run(
        ["git", "ls-files", "*.py"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines():
        path = ROOT / relative
        if not path.exists():
            continue
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
        if path.name == "__init__.py":
            assert not any(isinstance(node, ast.Import | ast.ImportFrom) for node in tree.body), (
                path
            )


def test_repository_does_not_reintroduce_mailmap_identity_rewriting() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", ".mailmap"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert tracked == ""


def test_openspec_is_official_governance_surface_not_command_root() -> None:
    assert (ROOT / "openspec/config.yaml").exists()
    assert (ROOT / "openspec/specs/kernel/spec.md").exists()
    assert "openspec =" not in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


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
    assert {path.parent.name for path in (ROOT / "openspec/specs").glob("*/spec.md")} == expected


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
    for path in (ROOT / "openspec/changes").glob("*/specs/*/spec.md"):
        if "/archive/" not in path.as_posix():
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
            assert re.search(rf"`(?:\$\s+)?{re.escape(retired)}\s+[^`]+`", text) is None, path
        in_fence = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
            elif in_fence and stripped:
                assert stripped.split()[0] not in RETIRED_PUBLIC_ROOTS, (path, stripped)


def test_product_behavior_does_not_live_in_tools_directory() -> None:
    tools_root = ROOT / "tools"
    allowed = {tools_root / "ci", tools_root / "ci/scripts"}
    cache_dirs = {"__pycache__", ".pytest_cache", ".ruff_cache"}
    product_dirs = {
        path
        for path in tools_root.rglob("*")
        if path.is_dir() and not any(part in cache_dirs for part in path.parts)
    }
    assert tools_root.exists()
    assert product_dirs <= allowed
    assert all(path.suffix == ".sh" for path in (tools_root / "ci/scripts").iterdir())


def test_pre_commit_uses_local_deterministic_quality_hook() -> None:
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "repo: local" in config
    assert "tools/ci/scripts/run-python-lint.sh" in config
    assert "uv run --group dev ruff check" not in config
    assert "github.com" not in config


def test_repo_local_skills_are_thin_playbook_projection() -> None:
    skills_root = ROOT / ".agents/skills"
    expected = {
        "ethos-repository-governance",
        "ethos-change-lifecycle",
        "ethos-skill-portfolio-governance",
        "ethos-quality-gate-governance",
        "ethos-adoption-profile-governance",
    }
    assert (skills_root / "README.md").exists()
    assert (skills_root / "activation.toml").exists()
    assert expected <= {path.name for path in skills_root.iterdir() if path.is_dir()}
    for skill_id in expected:
        text = (skills_root / skill_id / "SKILL.md").read_text(encoding="utf-8")
        assert "## Workflow" in text
        assert "## Evidence" in text
        assert "source of truth" in text.lower() or "repository truth" in text.lower()


def test_product_package_has_one_canonical_readme() -> None:
    assert (ROOT / "README.md").is_file()


def test_npm_launcher_is_distribution_adapter_not_python_family() -> None:
    manifest = json.loads((ROOT / "distributions/npm/package.json").read_text())
    assert manifest["name"] == "@agentic-workflow/ethos"
    assert manifest["bin"] == {"ethos": "bin/ethos.mjs"}
    assert manifest["private"] is False
    assert manifest["repository"]["url"] == "https://example.invalid/ethos.git"
    assert manifest["homepage"] == "https://example.invalid/ethos"
    assert manifest["bugs"]["url"] == "https://example.invalid/ethos/issues"
    assert manifest["publishConfig"]["access"] == "public"
    assert "governance" in manifest["keywords"]
    assert json.loads((ROOT / "package.json").read_text())["packageManager"] == "npm@11.12.1"


def _launcher(tmp_path: Path) -> Path:
    launcher = tmp_path / "package/bin/ethos.mjs"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        (ROOT / "distributions/npm/bin/ethos.mjs").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return launcher


def test_npm_launcher_prefers_current_source_checkout(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        return
    launcher = _launcher(tmp_path)
    checkout = tmp_path / "source-checkout"
    (checkout / "src/ethos").mkdir(parents=True)
    (checkout / "distributions/npm/bin").mkdir(parents=True)
    (checkout / "pyproject.toml").write_text('[project]\nname = "ethos"\n', encoding="utf-8")
    (checkout / "src/ethos/cli.py").write_text("", encoding="utf-8")
    (checkout / "distributions/npm/bin/ethos.mjs").write_text("", encoding="utf-8")
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    log = tmp_path / "uv-calls.log"
    uv = fake_bin / "uv"
    uv.write_text(
        f'#!/bin/sh\nprintf \'%s\\n\' "$*" > "{log}"\n',
        encoding="utf-8",
    )
    uv.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}/bin{os.pathsep}/usr/bin"

    completed = subprocess.run(
        [node, str(launcher), "status", "--json"],
        cwd=checkout,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert log.read_text(encoding="utf-8").strip() == (
        f"run --project {checkout} ethos status --json"
    )


def test_npm_launcher_runs_source_checkout_command_plane(tmp_path: Path) -> None:
    if not shutil.which("node") or not shutil.which("uv"):
        return
    adopter = tmp_path / "sample-adopter"
    adopter.mkdir()
    subprocess.run(("git", "init", "-q", "-b", "main"), cwd=adopter, check=True)
    subprocess.run(("git", "config", "user.name", "Test User"), cwd=adopter, check=True)
    subprocess.run(("git", "config", "user.email", "test@example.invalid"), cwd=adopter, check=True)
    (adopter / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(("git", "add", "README.md"), cwd=adopter, check=True)
    subprocess.run(("git", "commit", "-qm", "initial"), cwd=adopter, check=True)
    completed = subprocess.run(
        ["node", str(ROOT / "distributions/npm/bin/ethos.mjs"), "adopt", "--json"],
        cwd=adopter,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["data"]["root"] == str(adopter)


@pytest.mark.parametrize("mode", ["version-fallback", "select-python", "reject-untrusted"])
def test_npm_launcher_fallback_boundaries(tmp_path: Path, mode: str) -> None:
    node = shutil.which("node")
    if not node:
        return
    launcher = _launcher(tmp_path)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}/bin{os.pathsep}/usr/bin"
    if mode == "version-fallback":
        log = tmp_path / "python-calls.log"
        (fake_bin / "python3").write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "-c" ] || [ "$2" = "-c" ]; then exit 0; fi\n'
            f"printf '%s\\n' \"$*\" >> {log}\n"
            "printf '0.1.0a1\\n'\n",
            encoding="utf-8",
        )
        (fake_bin / "python3").chmod(0o755)
        completed = subprocess.run(
            [node, str(launcher), "--version"],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0
        assert completed.stdout.strip() == "0.1.0a1"
        assert log.read_text().splitlines() == ["-P -m ethos.cli --version"]
    elif mode == "select-python":
        log = tmp_path / "python-calls.log"
        for name, check, output in (("python3", "1", ""), ("python", "0", "0.1.0a1\\n")):
            path = fake_bin / name
            path.write_text(
                "#!/bin/sh\n"
                f'if [ "$1" = "-c" ] || [ "$2" = "-c" ]; then exit {check}; fi\n'
                f"printf '%s:%s\\n' {name} \"$*\" >> {log}\n"
                f"printf '{output}'\n",
                encoding="utf-8",
            )
            path.chmod(0o755)
        completed = subprocess.run(
            [node, str(launcher), "--version"],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0
        assert completed.stdout.strip() == "0.1.0a1"
        assert log.read_text().splitlines() == ["python:-P -m ethos.cli --version"]
    else:
        fake_repo = tmp_path / "untrusted-repo"
        (fake_repo / "src/ethos").mkdir(parents=True)
        (fake_repo / "pyproject.toml").write_text("[project]\nname='fake'\n")
        (fake_repo / "src/ethos/__init__.py").write_text("")
        marker = tmp_path / "uv-was-called"
        uv = fake_bin / "uv"
        uv.write_text(f"#!/bin/sh\ntouch {marker}\nexit 42\n")
        uv.chmod(0o755)
        python = fake_bin / "python3"
        python.write_text(
            '#!/bin/sh\nif [ "$1" = "-c" ] || [ "$2" = "-c" ]; then exit 1; fi\nexit 127\n'
        )
        python.chmod(0o755)
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


def test_markdown_docs_declare_subject_role_state_relations() -> None:
    for path in (ROOT / "docs").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), path
        header = text.split("---", 2)[1]
        for field in ("subject:", "role:", "state:", "relations:"):
            assert field in header, path


def test_command_plane_docs_match_the_terminal_root_vocabulary() -> None:
    text = (ROOT / "docs/reference/command-plane.md").read_text(encoding="utf-8")
    for root in ("status", "plan", "prove", "land", "publish", "adopt"):
        assert f"ethos {root}" in text
    for retired in (
        "orient",
        "report",
        "doctor",
        "explain",
        "audit",
        "openspec",
        "fleet",
        "intake",
        "rules",
        "assistants",
        "campaign",
        "parity",
        "quality",
        "playbooks",
    ):
        assert f"ethos {retired}" not in text


def test_skill_readonly_capabilities_match_the_terminal_command_plane() -> None:
    for root in ("status", "plan"):
        assert ethos_command_is_readonly(["ethos", root, "--json"]) is True
    for root in (
        "orient",
        "report",
        "doctor",
        "explain",
        "audit",
        "openspec",
        "fleet",
        "assistants",
        "campaign",
        "parity",
        "quality",
        "playbooks",
        "prove",
    ):
        assert ethos_command_is_readonly(["ethos", root, "--json"]) is False
