from __future__ import annotations

import ast
import json
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any
from typing import cast

import pytest

from ethos.contracts.admission import ethos_command_is_readonly
from ethos.repository.policy.boundary.product import contributor_policy_report
from ethos.repository.policy.boundary.product import declared_product_surface_roots
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.repository.policy.boundary.product import product_surface_files
from ethos.repository.policy.references.closure import repository_product_reference_gaps
from tests.support.architecture import isolated_path

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = {
    "adapters",
    "assistant-projections",
    "command-plane",
    "contracts",
    "distribution",
    "kernel",
    "proof-hosts",
    "quality",
    "repository-governance",
}
RETIRED = {
    "assistants",
    "audit",
    "campaign",
    "doctor",
    "explain",
    "fleet",
    "intake",
    "openspec",
    "orient",
    "parity",
    "playbooks",
    "quality",
    "report",
    "rules",
}


def mapping(value: object) -> dict[str, Any]:
    return cast("dict[str, Any]", value)


def imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def test_runtime_package_and_dependency_boundaries() -> None:
    source = "\n".join(path.read_text() for path in sorted((ROOT / "src/ethos").rglob("*.py")))
    assert all(
        term not in source
        for term in (
            "is_product_root",
            'project.get("name") == "ethos"',
            "src/ethos/__init__.py",
        )
    )
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert project["project"]["name"] == "ethos"
    assert project["build-system"]["build-backend"] == "hatchling.build"
    assert project["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["src/ethos"]
    common = {
        "ethos.repository",
        "ethos.assistants",
        "ethos.adapters",
        "sqlite3",
        "subprocess",
        "tools",
    }
    matrix = {
        "contracts": common | {"shutil"},
        "quality": common | {"shutil"},
        "state": common | {"shutil"},
        "repository": {"ethos.adapters", "sqlite3"},
    }
    for name, forbidden in matrix.items():
        paths = list((ROOT / "src/ethos" / name).rglob("*.py"))
        assert paths
        assert [
            (path, imports(path) & forbidden) for path in paths if imports(path) & forbidden
        ] == []


def test_semantic_subpackages_have_no_facade_or_parallel_owner() -> None:
    hook = ROOT / "src/ethos/adapters/repo/hook"
    assert not (ROOT / "src/ethos/repository/hooks.py").exists()
    assert {"binding.py", "transaction.py"} <= {path.name for path in hook.glob("*.py")}
    forbidden = (
        "src/ethos/adapters/mutation/resolution",
        "src/ethos/contracts/resolution",
        "src/ethos/adapters/store/state/closeout.py",
        "src/ethos/surface/cli/lane/resolution.py",
        "system/schemas/kernel/lane-resolution-decision.schema.json",
        "system/schemas/kernel/lane-resolution-receipt.schema.json",
        "system/schemas/kernel/lane-resolution-clear-receipt.schema.json",
    )
    assert [path for item in forbidden if (path := ROOT / item).exists()] == []


def test_product_contributor_and_reference_reports() -> None:
    product, contributor = product_boundary_report(ROOT), contributor_policy_report(ROOT)
    for report in (product, contributor):
        assert report["verdict"] == "pass", report["findings"]
        assert "ok" not in report
    summary, policy = mapping(contributor["summary"]), mapping(contributor["policy"])
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
    assert mapping(product["summary"])["by_kind"].get("private_reference_literal", 0) == 0
    assert "private_reference_boundary" in mapping(product["policy"])
    assert repository_product_reference_gaps(ROOT) == []
    assert not (ROOT / "system/coupling.toml").exists()


def test_distribution_manifest_and_package_assets() -> None:
    npm, package = (
        json.loads((ROOT / path).read_text())
        for path in (
            "distributions/npm/package.json",
            "package.json",
        )
    )
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert not {"author", "authors", "maintainers"} & project.keys()
    assert not {"author", "authors", "maintainers", "contributors"} & npm.keys()
    assert package["private"] is True
    assert npm["files"] == ["bin/ethos.mjs", "README.md"]
    assert npm["name"] == "@agentic-workflow/ethos"
    assert npm["bin"] == {"ethos": "bin/ethos.mjs"}
    assert npm["private"] is False
    assert "packageManager" not in package
    assert (npm["repository"]["url"], npm["homepage"], npm["bugs"]["url"]) == (
        "https://example.invalid/ethos.git",
        "https://example.invalid/ethos",
        "https://example.invalid/ethos/issues",
    )
    assert npm["publishConfig"]["access"] == "public"
    assert "governance" in npm["keywords"]


def test_declared_product_surfaces_cover_assets_not_history() -> None:
    roots = set(declared_product_surface_roots(ROOT))
    scanned = {path.relative_to(ROOT).as_posix() for path in product_surface_files(ROOT)}
    assert {
        "src/ethos",
        "tests",
        "tools",
        "system",
        ".agents/skills",
        "distributions",
        "openspec/changes",
        "evidence/attestations",
    } <= roots
    assert not {"sdks/typescript", "scaffolds", "extensions"} & roots
    assert {
        ".gitignore",
        ".pre-commit-config.yaml",
        ".config/checks/import-linter/contracts.ini",
        ".config/checks/architecture/models/ethos_repository.c4",
        "assets/brand/ethos-logo.svg",
        "docs/architecture/_generated/ethos-repository.mmd",
        "package-lock.json",
        "ruff.toml",
        "uv.lock",
    } <= scanned
    assert not any(path.startswith("openspec/changes/archive/") for path in scanned)
    assert mapping(product_boundary_report(ROOT)["policy"])["historical_surface_prefixes"] == [
        "evidence/claims/",
        "evidence/chronicle/",
        "evidence/parity/",
        "openspec/changes/archive/",
        "docs/history/",
    ]


def test_product_boundary_rejects_identity_literals(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/identity.py").write_text(
        'key = "id_' + 'ed25519"\nfingerprint = "SHA' + "256:" + "A" * 32 + '"\n'
    )
    report = product_boundary_report(tmp_path)
    assert report["verdict"] == "block"
    assert mapping(report["summary"])["by_kind"] == {"fixed_key_or_fingerprint": 2}


def test_python_parser_model_and_export_policy() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    for relative in tracked:
        path = ROOT / relative
        if not path.exists():
            continue
        tree, imported = ast.parse(path.read_text()), imports(path)
        assert not {"arg" + "parse", "attr", "attrs"} & imported, path
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
            isinstance(node, (ast.Assign, ast.AnnAssign))
            and any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in getattr(node, "targets", (getattr(node, "target", None),))
            )
            for node in ast.walk(tree)
        ), path
        assert path.name != "__init__.py" or not any(
            isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body
        ), path


def test_portable_models_and_internal_dataclasses() -> None:
    roots = (
        ROOT / "src/ethos/contracts",
        ROOT / "src/ethos/result.py",
        ROOT / "src/ethos/repository/profile.py",
    )
    for root in roots:
        for path in [root] if root.is_file() else sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text())
            classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
            for node in classes.values():
                lineage, pending = [node], [b.id for b in node.bases if isinstance(b, ast.Name)]
                while pending:
                    parent = classes.get(pending.pop())
                    if parent is not None and parent not in lineage:
                        lineage.append(parent)
                        pending.extend(b.id for b in parent.bases if isinstance(b, ast.Name))
                if not any(
                    isinstance(b, ast.Name) and b.id == "BaseModel"
                    for model in lineage
                    for b in model.bases
                ):
                    continue
                configs = [
                    ast.unparse(stmt.value).replace(" ", "")
                    for model in lineage
                    for stmt in model.body
                    if isinstance(stmt, ast.Assign)
                    and any(
                        isinstance(target, ast.Name) and target.id == "model_config"
                        for target in stmt.targets
                    )
                ]
                assert any(
                    all(
                        item in config
                        for item in (
                            "strict=True",
                            "frozen=True",
                            "extra='forbid'",
                        )
                    )
                    for config in configs
                ), f"{path}:{node.name}"
    actual = {
        (path.relative_to(ROOT).as_posix(), node.name)
        for path in sorted((ROOT / "src/ethos/contracts").rglob("*.py"))
        for node in ast.parse(path.read_text()).body
        if isinstance(node, ast.ClassDef)
        if any(
            isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass"
            for d in node.decorator_list
        )
    }
    assert actual == {
        ("src/ethos/contracts/branch/roles.py", "BranchRolePolicy"),
        ("src/ethos/contracts/coordination.py", "LeaseOperation"),
    }


def test_tooling_shell_and_cli_boundaries() -> None:
    cli = [ROOT / "src/ethos/cli.py", *(ROOT / "src/ethos/surface/cli").rglob("*.py")]
    for path in cli:
        assert path.name != "application.py" or "cyclopts" in imports(path)
        assert "arg" + "parse" not in imports(path)
    for path in (ROOT / "tools/ci/ci_templates.py", ROOT / "tools/ci/hosted_observation.py"):
        assert "cyclopts" in imports(path), path
        assert "arg" + "parse" not in imports(path), path
    for relative in (
        "runbook_registry.py",
        "architecture_projection.py",
        "format_selection.py",
        "ci_templates.py",
    ):
        text = (ROOT / "tools/ci" / relative).read_text()
        assert '"verdict"' in text
        assert 'payload["ok"]' not in text
        assert 'evidence["ok"]' not in text
    tools = ROOT / "tools"
    directories = {
        path
        for path in tools.rglob("*")
        if path.is_dir() and not {"__pycache__", ".pytest_cache", ".ruff_cache"} & set(path.parts)
    }
    assert directories <= {
        tools / "ci",
        tools / "ci/delivery",
        tools / "ci/scripts",
        tools / "ci/toolchain",
    }
    assert all(path.suffix == ".sh" for path in (tools / "ci/scripts").iterdir())
    config = (ROOT / ".pre-commit-config.yaml").read_text()
    assert "repo: local" in config
    assert "uv run --frozen --offline python -m nox -s lint" in config
    assert "uv run --group dev ruff check" not in config
    assert "github.com" not in config


def test_openspec_docs_skills_and_command_plane() -> None:
    assert not subprocess.run(
        ["git", "ls-files", ".mailmap"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert {path.parent.name for path in (ROOT / "openspec/specs").glob("*/spec.md")} == FAMILIES
    assert all(
        path.parent.name in FAMILIES
        for path in (ROOT / "openspec/changes").glob("*/specs/*/spec.md")
        if "/archive/" not in path.as_posix()
    )
    delta = (
        ROOT / "openspec/changes/archive/2026-08-05-accepted-spec-reconciliation"
        "/specs/repository-governance/spec.md"
    ).read_text()
    assert "Historical Work Lane semantic convergence" in delta
    assert "without replaying obsolete code" in delta
    assert "no-fast-forward merge with the candidate base" not in delta
    assert "a further owned successor MUST start" not in delta
    result = subprocess.run(
        ["openspec", "validate", "--all", "--strict", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["summary"]["totals"]["failed"] == 0
    assert not (ROOT / "docs/superpowers").exists()
    for path in (ROOT / "docs").rglob("*.md"):
        header = path.read_text().split("---", 2)[1]
        assert all(field in header for field in ("subject:", "role:", "state:", "relations:")), path
        assert "state: superseded" not in header or path.relative_to(ROOT / "docs").parts[0] in {
            "decisions",
            "history",
        }
    skills = ROOT / ".agents/skills"
    expected = {
        f"ethos-{name}"
        for name in (
            "repository-governance",
            "change-lifecycle",
            "skill-portfolio-governance",
            "quality-gate-governance",
            "adoption-profile-governance",
        )
    }
    assert expected <= {path.name for path in skills.iterdir() if path.is_dir()}
    for skill in expected:
        text = (skills / skill / "SKILL.md").read_text()
        assert "## Workflow" in text
        assert "## Evidence" in text
        assert "source of truth" in text.lower() or "repository truth" in text.lower()
    docs = (ROOT / "docs/reference/command-plane.md").read_text()
    assert all(
        f"ethos {name}" in docs for name in ("status", "plan", "prove", "land", "publish", "adopt")
    )
    assert all(f"ethos {name}" not in docs for name in RETIRED)


def launcher(tmp_path: Path) -> Path:
    target = tmp_path / "package/bin/ethos.mjs"
    target.parent.mkdir(parents=True)
    target.write_text((ROOT / "distributions/npm/bin/ethos.mjs").read_text())
    return target


def test_npm_launcher_source_checkout_and_fallback_matrix(tmp_path: Path) -> None:
    if not (node := shutil.which("node")):
        return
    checkout, uv_log = tmp_path / "source-checkout", tmp_path / "uv.log"
    for path in (checkout / "src/ethos", checkout / "distributions/npm/bin"):
        path.mkdir(parents=True)
    (checkout / "pyproject.toml").write_text('[project]\nname = "ethos"\n')
    (checkout / "src/ethos/cli.py").write_text("")
    (checkout / "distributions/npm/bin/ethos.mjs").write_text("")
    env = isolated_path(tmp_path, {"uv": f'#!/bin/sh\nprintf \'%s\\n\' "$*" > "{uv_log}"\n'})
    result = subprocess.run(
        [node, str(launcher(tmp_path)), "status", "--json"],
        cwd=checkout,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert uv_log.read_text().strip() == f"run --project {checkout} ethos status --json"


@pytest.mark.parametrize("mode", ["version", "select-python", "reject-untrusted"])
def test_npm_launcher_fallback_matrix(tmp_path: Path, mode: str) -> None:
    if not (node := shutil.which("node")):
        return
    log, marker = tmp_path / "python.log", tmp_path / "uv-called"
    check = 0 if mode == "version" else 1
    python3 = (
        f'#!/bin/sh\nif [ "$1" = "-c" ] || [ "$2" = "-c" ]; then exit {check}; fi\n'
        f"printf '%s\\n' \"$*\" >> \"{log}\"\nprintf '0.1.0a1\\n'\n"
    )
    executables = {"uv": f"#!/bin/sh\ntouch '{marker}'\n", "python3": python3}
    if mode == "select-python":
        executables["python"] = (
            f'#!/bin/sh\nif [ "$1" = "-c" ] || [ "$2" = "-c" ]; then exit 0; fi\n'
            f"printf 'python:%s\\n' \"$*\" >> \"{log}\"\nprintf '0.1.0a1\\n'\n"
        )
    env, cwd = isolated_path(tmp_path, executables), tmp_path
    if mode == "reject-untrusted":
        cwd = tmp_path / "untrusted"
        (cwd / "src/ethos").mkdir(parents=True)
        (cwd / "pyproject.toml").write_text("[project]\nname='fake'\n")
        (cwd / "src/ethos/__init__.py").write_text("")
    result = subprocess.run(
        [node, str(launcher(tmp_path)), "--version"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if mode == "reject-untrusted":
        assert result.returncode == 127
        assert not marker.exists()
    else:
        assert result.returncode == 0
        assert result.stdout.strip() == "0.1.0a1"
        assert log.read_text().splitlines() == (
            ["-P -m ethos.cli --version"]
            if mode == "version"
            else ["python:-P -m ethos.cli --version"]
        )


def test_npm_launcher_runs_source_command_plane(tmp_path: Path) -> None:
    if not shutil.which("node") or not shutil.which("uv"):
        return
    adopter = tmp_path / "adopter"
    adopter.mkdir()
    for command in (
        ("git", "init", "-q", "-b", "main"),
        ("git", "config", "user.name", "Test User"),
        ("git", "config", "user.email", "test@example.invalid"),
    ):
        subprocess.run(command, cwd=adopter, check=True)
    (adopter / "README.md").write_text("fixture\n")
    subprocess.run(("git", "add", "README.md"), cwd=adopter, check=True)
    subprocess.run(("git", "commit", "-qm", "initial"), cwd=adopter, check=True)
    result = subprocess.run(
        ["node", str(ROOT / "distributions/npm/bin/ethos.mjs"), "adopt", "--json"],
        cwd=adopter,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["root"] == str(adopter)


def test_readonly_capability_matrix() -> None:
    assert all(ethos_command_is_readonly(["ethos", name, "--json"]) for name in ("status", "plan"))
    assert not any(
        ethos_command_is_readonly(["ethos", name, "--json"])
        for name in (*sorted(RETIRED - {"intake", "rules"}), "prove")
    )
