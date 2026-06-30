from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

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


def test_markdown_docs_declare_subject_role_state_relations() -> None:
    for path in (ROOT / "docs").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), path
        header = text.split("---", 2)[1]
        for field in ("subject:", "role:", "state:", "relations:"):
            assert field in header, path
