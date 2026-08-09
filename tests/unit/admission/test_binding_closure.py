from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.references.closure import repository_product_reference_gaps
from ethos.repository.policy.references.declarations import native_owned_references
from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.policy.references.observation import reference_gaps
from ethos.repository.policy.references.observation import repository_product_references

if TYPE_CHECKING:
    from pathlib import Path


def _write_files(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip() + "\n", encoding="utf-8")


def _minimal_product(root: Path, source: str, *, dependencies: str = "") -> None:
    _write_files(
        root,
        {
            "system/surfaces.toml": """
schema = "system/schemas/contracts/surfaces.schema.json"
[[surface]]
name = "cli"
carrier = "src/example"
""",
            "pyproject.toml": f"""[project]
name = "example"
version = "1"
{dependencies}""",
            "src/example/module.py": source,
        },
    )


def test_repository_binding_scan_covers_declared_surfaces_and_active_openspec(
    tmp_path: Path,
) -> None:
    _write_files(
        tmp_path,
        {
            "system/surfaces.toml": """
schema = "system/schemas/contracts/surfaces.schema.json"
[[surface]]
name = "cli"
carrier = "src/ethos"
[[surface]]
name = "extensions"
carrier = "extensions/"
""",
            "src/ethos/application.py": """
from cyclopts import App
app = App(name="ethos")
lane_app = App(name="lane")
app.command(lane_app)
""",
            "src/ethos/commands.py": """
import external_sdk
from .application import lane_app
@lane_app.command(name="start")
def start() -> None:
    pass
""",
            "extensions/demo/adapter.py": "import extension_sdk",
            "extensions/demo/check.sh": "external-shell-tool --version",
            "pyproject.toml": """
[project]
name = "example"
version = "0.1.0"
dependencies = ["external-dist>=1"]
""",
            ".github/workflows/ci.yml": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v7
      - run: external-runner --check
""",
            "openspec/changes/current/runner.yaml": "run: openspec validate --all --strict",
        },
    )

    observed = repository_product_references(tmp_path)

    assert {"external_sdk", "extension_sdk"} <= observed["import"]
    assert "external-dist" in observed["distribution"]
    assert {"external-runner", "external-shell-tool", "openspec"} <= observed["executable"]
    assert observed["reference"] == {"github"}
    assert "ethos lane start" in observed["command"]


def test_patch_binding_scan_uses_the_same_normalized_reference_extractor(
    tmp_path: Path,
) -> None:
    _write_files(
        tmp_path,
        {
            "src/ethos/application.py": """
from cyclopts import App
app = App(name="ethos")
lane_app = App(name="lane")
app.command(lane_app)
""",
        },
    )
    observed = product_references_from_files(
        {
            "src/ethos/commands.py": """import external_sdk
@lane_app.command(name="start")
def start() -> None:
    subprocess.run(["external-runner"], check=True)
""",
            ".github/workflows/ci.yml": "- uses: actions/checkout@v7",
            "pyproject.toml": """
[project]
name = "example"
version = "0.1.0"
dependencies = ["external-dist>=1"]
""",
        },
        root=tmp_path,
    )

    assert observed == {
        "import": {"external_sdk"},
        "distribution": {"example", "external-dist"},
        "executable": {"external-runner"},
        "reference": {"github"},
        "command": {"ethos lane start"},
        "value": set(),
    }


def test_native_owner_closure_rejects_an_unowned_reference(tmp_path: Path) -> None:
    _minimal_product(tmp_path, "import external_sdk")

    assert repository_product_reference_gaps(tmp_path) == [
        "product_reference_not_admitted_at_baseline:import:external_sdk"
    ]


def test_native_owner_closure_does_not_promote_observed_consumers(tmp_path: Path) -> None:
    _minimal_product(
        tmp_path,
        """import rogue_sdk
import os
import subprocess
os.environ.get("ROGUE_HOME")
subprocess.run(["rogue-tool"], check=True)
""",
    )

    allowed = native_owned_references(tmp_path)

    assert "rogue_sdk" not in allowed["import"]
    assert "rogue-tool" not in allowed["executable"]
    assert "ROGUE_HOME" not in allowed["value"]
    assert repository_product_reference_gaps(tmp_path) == [
        "product_reference_not_admitted_at_baseline:import:rogue_sdk",
        "product_reference_not_admitted_at_baseline:executable:rogue-tool",
        "product_reference_not_admitted_at_baseline:value:ROGUE_HOME",
    ]


def test_malformed_reference_carriers_fail_closed_without_inventing_references() -> None:
    observed = product_references_from_files(
        {
            "pyproject.toml": "[project",
            "package.json": "{",
            ".github/workflows/ci.yml": "jobs: [",
            "README.md": "Use `unterminated ' command` safely.",
        }
    )

    assert observed == {
        "import": set(),
        "distribution": set(),
        "executable": set(),
        "reference": {"github"},
        "command": set(),
        "value": set(),
    }


def test_native_declarations_and_cross_carrier_commands_are_observed() -> None:
    observed = product_references_from_files(
        {
            "pyproject.toml": """[project]
name = "Demo_Package"
dependencies = ["Requests>=2", 42]
[project.optional-dependencies]
test = ["PyTest"]
[project.scripts]
demo = "demo:main"
[dependency-groups]
dev = ["Ruff"]
[build-system]
requires = ["Hatchling"]
""",
            "package.json": """{
  "name": "@Scope/Demo",
  "dependencies": {"left-pad": "1"},
  "devDependencies": {"vitest": "1"},
  "packageManager": "pnpm@10",
  "bin": {"demo-js": "bin/demo.js"},
  "scripts": {"check": "node scripts/check.js"}
}""",
            ".gitlab-ci.yml": "script: [npm run check, false]\nimage: python:3.14",
            "docs/reference/commands.md": """```yaml
uses: docker://alpine:latest
```
```console
$ demo --help
output
```
""",
        },
        declared_commands=("demo",),
    )

    assert {
        "demo-package",
        "requests",
        "pytest",
        "ruff",
        "hatchling",
        "@scope/demo",
        "left-pad",
        "vitest",
    } <= observed["distribution"]
    assert {"demo", "pnpm", "demo-js", "node", "npm"} <= observed["executable"]
    assert observed["reference"] == {"gitlab", "docker"}
    assert "demo" in observed["command"]


def test_observation_can_exclude_dependency_declarations_but_keeps_consumers() -> None:
    observed = product_references_from_files(
        {
            "pyproject.toml": '[project]\nname = "demo"\ndependencies = ["requests"]\n',
            "package.json": '{"dependencies": {"left-pad": "1"}, "scripts": {"x": "node x.js"}}',
        },
        include_declarations=False,
    )

    assert observed["distribution"] == set()
    assert observed["executable"] == {"node"}


def test_reference_gap_report_ignores_native_modules_and_sorts_unknowns() -> None:
    gaps = reference_gaps(
        {"import": frozenset({"allowed"})},
        {
            "import": {"tools", "tests", "ethos", "zeta", "allowed"},
            "executable": {"z-tool", "a-tool"},
        },
    )

    assert gaps == [
        "product_reference_not_admitted_at_baseline:import:zeta",
        "product_reference_not_admitted_at_baseline:executable:a-tool",
        "product_reference_not_admitted_at_baseline:executable:z-tool",
    ]
