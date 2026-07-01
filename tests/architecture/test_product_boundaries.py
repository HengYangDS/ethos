from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
from pathlib import Path

from ethos_contracts.package_ontology import package_ontology_report

ROOT = Path(__file__).resolve().parents[2]
RETIRED_PUBLIC_ROOTS = {
    "wt",
    "proof",
    "mission",
    "skill-evolution",
    "agent-surface-contract",
}


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
        "ethos_project",
        "ethos_agent",
        "ethos_governance",
        "ethos_workspace",
        "sqlite3",
        "subprocess",
        "tools",
        "dmgr",
    }

    for path in (ROOT / "packages/ethos-kernel/src").rglob("*.py"):
        assert imported_modules(path).isdisjoint(forbidden), path


def test_target_product_packages_exist_with_build_metadata() -> None:
    for package in package_ontology_report()["target_packages"]:
        root = ROOT / "packages" / package
        assert (root / "README.md").exists(), package
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
        assert 'build-backend = "hatchling.build"' in pyproject


def test_semantic_target_packages_do_not_import_provider_execution() -> None:
    forbidden_by_package = {
        "ethos-core": {"subprocess", "sqlite3", "shutil", "tomllib"},
        "ethos-contracts": {"subprocess", "sqlite3", "shutil"},
        "ethos-repository": {"subprocess", "sqlite3", "shutil"},
    }
    for package, forbidden in forbidden_by_package.items():
        source = ROOT / "packages" / package / "src"
        for path in source.rglob("*.py"):
            assert imported_modules(path).isdisjoint(forbidden), path


def test_product_python_code_does_not_hardcode_adopter_terms() -> None:
    allowed = {
        ROOT / "packages" / "ethos-contracts" / "src" / "ethos_contracts" / "capability_parity.py",
    }
    for path in (ROOT / "packages").glob("*/src/**/*.py"):
        if path in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        assert "alphasim" not in text.lower(), path
        assert "dmgr" not in text.lower(), path


def test_target_packages_do_not_import_migration_hosts_except_cli_bridge() -> None:
    contract = package_ontology_report()
    migration_imports = {
        package.replace("-", "_") for package in contract["migration_hosts"]
    }
    bridge_exceptions = {
        ROOT / "packages" / "ethos" / "src" / "ethos" / "cli.py",
    }

    for package in contract["target_packages"]:
        source = ROOT / "packages" / package / "src"
        for path in source.rglob("*.py"):
            if path in bridge_exceptions:
                continue
            assert imported_modules(path).isdisjoint(migration_imports), path


def test_cli_uses_cyclopts_not_argparse() -> None:
    cli_path = ROOT / "packages/ethos/src/ethos/cli.py"
    imports = imported_modules(cli_path)

    assert "cyclopts" in imports
    assert "argparse" not in imports


def test_package_roots_do_not_reexport_module_surfaces() -> None:
    for path in (ROOT / "packages").glob("*/src/*/__init__.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            assert not isinstance(node, (ast.Import, ast.ImportFrom)), path
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    assert not (
                        isinstance(target, ast.Name) and target.id == "__all__"
                    ), path


def test_openspec_is_official_self_governance_surface_not_command_root() -> None:
    assert (ROOT / "openspec" / "config.yaml").exists()
    assert (ROOT / "openspec" / "specs" / "ethos-kernel" / "spec.md").exists()

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "openspec =" not in pyproject


def test_openspec_specs_are_mece_product_families() -> None:
    expected = {
        "ethos-agent",
        "ethos-distribution",
        "ethos-governance",
        "ethos-kernel",
        "ethos-project",
        "ethos-workspace",
    }
    actual = {
        path.parent.name
        for path in (ROOT / "openspec" / "specs").glob("*/spec.md")
    }

    assert actual == expected


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


def test_current_docs_do_not_promote_retired_public_roots() -> None:
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
    assert not (ROOT / "tools").exists()


def test_pre_commit_uses_local_deterministic_quality_hook() -> None:
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "repo: local" in config
    assert "uv run --group dev ruff check" in config
    assert "github.com" not in config


def test_repo_local_skills_are_thin_playbook_projection() -> None:
    skills_root = ROOT / ".agents" / "skills"

    assert (skills_root / "README.md").exists()
    assert (skills_root / "activation.toml").exists()
    assert (skills_root / "ethos-repository-governance" / "SKILL.md").exists()
    skill_text = (skills_root / "ethos-repository-governance" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "ethos " in skill_text
    assert "source of truth" in skill_text


def test_product_packages_have_canonical_readmes() -> None:
    for package in (
        "ethos",
        "ethos-kernel",
        "ethos-governance",
        "ethos-workspace",
        "ethos-agent",
        "ethos-project",
    ):
        readme = ROOT / "packages" / package / "README.md"
        assert readme.exists()
        assert "Subject" in readme.read_text(encoding="utf-8")


def test_npm_launcher_is_distribution_adapter_not_python_family() -> None:
    package = ROOT / "packages" / "ethos-node" / "package.json"
    manifest = json.loads(package.read_text(encoding="utf-8"))

    assert manifest["name"] == "@agentic-workflow/ethos"
    assert manifest["bin"] == {"ethos": "bin/ethos.mjs"}
    assert manifest["private"] is False
    assert manifest["repository"]["url"].endswith("/dig/research/agentic-workflow/ethos.git")
    assert manifest["homepage"].endswith("/dig/research/agentic-workflow/ethos")
    assert manifest["bugs"]["url"].endswith("/dig/research/agentic-workflow/ethos/-/issues")
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
        ["node", "packages/ethos-node/bin/ethos.mjs", "--version"],
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
        (ROOT / "packages" / "ethos-node" / "bin" / "ethos.mjs").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    log = tmp_path / "python-calls.log"
    fake_python = fake_bin / "python3"
    fake_python.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"-c\" ]; then exit 0; fi\n"
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
    assert log.read_text(encoding="utf-8").splitlines() == ["-m ethos.cli --version"]


def test_npm_launcher_does_not_execute_untrusted_cwd_source_checkout(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        return

    launcher = tmp_path / "package" / "bin" / "ethos.mjs"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        (ROOT / "packages" / "ethos-node" / "bin" / "ethos.mjs").read_text(
            encoding="utf-8"
        ),
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
        "#!/bin/sh\n"
        "if [ \"$1\" = \"-c\" ]; then exit 1; fi\n"
        "exit 127\n",
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
        (ROOT / "packages" / "ethos-node" / "bin" / "ethos.mjs").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    log = tmp_path / "python-calls.log"
    fake_python3 = fake_bin / "python3"
    fake_python3.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"-c\" ]; then exit 1; fi\n"
        f"printf '%s\\n' \"python3:$*\" >> {log}\n"
        "exit 99\n",
        encoding="utf-8",
    )
    fake_python3.chmod(0o755)
    fake_python = fake_bin / "python"
    fake_python.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"-c\" ]; then exit 0; fi\n"
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
    assert log.read_text(encoding="utf-8").splitlines() == ["python:-m ethos.cli --version"]


def test_markdown_docs_declare_subject_role_state_relations() -> None:
    for path in (ROOT / "docs").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), path
        header = text.split("---", 2)[1]
        for field in ("subject:", "role:", "state:", "relations:"):
            assert field in header, path
