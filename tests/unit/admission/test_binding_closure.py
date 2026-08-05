from __future__ import annotations

import json
from pathlib import Path

from ethos.repository.policy.references.closure import repository_product_reference_gaps
from ethos.repository.policy.references.declarations import native_owned_references
from ethos.repository.policy.references.declarations import native_owned_references_from_files
from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.policy.references.observation import repository_product_references

ROOT = Path(__file__).resolve().parents[3]


def test_repository_binding_scan_covers_declared_surfaces_and_active_openspec(
    tmp_path: Path,
) -> None:
    (tmp_path / "system").mkdir()
    (tmp_path / "system/surfaces.toml").write_text(
        """
schema = "system/schemas/contracts/surfaces.schema.json"

[[surface]]
name = "cli"
carrier = "src/ethos"

[[surface]]
name = "extensions"
carrier = "extensions/"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    source = tmp_path / "src/ethos"
    source.mkdir(parents=True)
    source.joinpath("application.py").write_text(
        """
from cyclopts import App

app = App(name="ethos")
lane_app = App(name="lane")
app.command(lane_app)
""".strip()
        + "\n",
        encoding="utf-8",
    )
    source.joinpath("commands.py").write_text(
        """
import external_sdk

from .application import lane_app

@lane_app.command(
    name="start",
)
def start() -> None:
    pass
""".strip()
        + "\n",
        encoding="utf-8",
    )
    extension = tmp_path / "extensions/demo"
    extension.mkdir(parents=True)
    extension.joinpath("adapter.py").write_text("import extension_sdk\n", encoding="utf-8")
    extension.joinpath("check.sh").write_text(
        "#!/usr/bin/env bash\nexternal-shell-tool --version\n", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "example"
version = "0.1.0"
dependencies = ["external-dist>=1"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    workflow = tmp_path / ".github/workflows"
    workflow.mkdir(parents=True)
    workflow.joinpath("ci.yml").write_text(
        """
jobs:
  check:
    steps:
      - uses: actions/checkout@v7
      - run: external-runner --check
""".strip()
        + "\n",
        encoding="utf-8",
    )
    active = tmp_path / "openspec/changes/current"
    active.mkdir(parents=True)
    active.joinpath("runner.yaml").write_text(
        "run: openspec validate --all --strict\n", encoding="utf-8"
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
    source = tmp_path / "src/ethos"
    source.mkdir(parents=True)
    source.joinpath("application.py").write_text(
        """
from cyclopts import App

app = App(name="ethos")
lane_app = App(name="lane")
app.command(lane_app)
""".strip()
        + "\n",
        encoding="utf-8",
    )
    files = {
        "src/ethos/commands.py": """import external_sdk
@lane_app.command(
    name="start",
)
def start() -> None:
    subprocess.run(["external-runner"], check=True)
""",
        ".github/workflows/ci.yml": "- uses: actions/checkout@v7",
        "pyproject.toml": """[project]
name = "example"
version = "0.1.0"
dependencies = ["external-dist>=1"]
""",
    }

    observed = product_references_from_files(files, root=tmp_path)

    assert observed == {
        "import": {"external_sdk"},
        "distribution": {"example", "external-dist"},
        "executable": {"external-runner"},
        "reference": {"github"},
        "command": {"ethos lane start"},
        "value": set(),
    }


def test_wrapper_extraction_observes_nested_uv_python_npx_and_uvx_executables() -> None:
    observed = product_references_from_files(
        {
            "tools/check.sh": """uv run --group dev rogue-tool --check
python -m pytest -q
npx --yes prettier --check .
uvx --from ruff ruff check .
"""
        }
    )

    assert {"uv", "rogue-tool", "python", "pytest", "npx", "prettier", "uvx", "ruff"} <= (
        observed["executable"]
    )


def test_shell_scan_observes_commands_in_single_line_functions() -> None:
    observed = product_references_from_files(
        {"tools/check.sh": 'probe() { ps -o lstart= -p "$1"; }\n'}
    )

    assert "ps" in observed["executable"]


def test_env_option_values_are_not_executables() -> None:
    observed = product_references_from_files(
        {
            "tools/check.sh": "env -u ETHOS_ACTOR python -m pytest -q\n",
            "tools/check.py": "subprocess.run(['env', '-u', 'ETHOS_ACTOR', 'python', '-m', 'pytest'])\n",
        }
    )

    assert "ETHOS_ACTOR" not in observed["executable"]
    assert {"python", "pytest"} <= observed["executable"]


def test_npm_run_resolves_the_declared_script_executable() -> None:
    observed = product_references_from_files(
        {
            "package.json": json.dumps(
                {
                    "name": "example-private-workspace",
                    "private": True,
                    "scripts": {"check": "rogue-tool --check"},
                }
            ),
            "tools/check.sh": "npm run check\n",
        }
    )

    assert {"npm", "rogue-tool"} <= observed["executable"]


def test_product_distribution_names_are_observed() -> None:
    observed = product_references_from_files(
        {
            "pyproject.toml": '[project]\nname = "ethos"\nversion = "1"\n',
            "distributions/npm/package.json": json.dumps(
                {"name": "@agentic-workflow/ethos", "private": False}
            ),
            "package.json": json.dumps({"name": "private-root", "private": True}),
        }
    )

    assert {"ethos", "@agentic-workflow/ethos"} <= observed["distribution"]
    assert "private-root" not in observed["distribution"]


def test_native_owner_closure_rejects_an_unowned_reference(tmp_path: Path) -> None:
    (tmp_path / "system").mkdir()
    (tmp_path / "system/surfaces.toml").write_text(
        'schema = "system/schemas/contracts/surfaces.schema.json"\n\n'
        '[[surface]]\nname = "cli"\ncarrier = "src/example"\n',
        encoding="utf-8",
    )
    (tmp_path / "src/example").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\nversion = "1"\n',
        encoding="utf-8",
    )
    (tmp_path / "src/example/module.py").write_text("import external_sdk\n", encoding="utf-8")

    assert repository_product_reference_gaps(tmp_path) == [
        "product_reference_not_admitted_at_baseline:import:external_sdk"
    ]


def test_native_owner_closure_compiles_only_explicit_native_declarations(
    tmp_path: Path,
) -> None:
    (tmp_path / "src/example").mkdir(parents=True)
    (tmp_path / "src/example/application.py").write_text(
        """from cyclopts import App

app = App(name="example")

@app.command
def inspect() -> None:
    pass
""",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "example"
version = "1"
dependencies = ["external-sdk>=1"]

[project.scripts]
example = "example.application:app"
""",
        encoding="utf-8",
    )
    (tmp_path / "system").mkdir()
    (tmp_path / "system/tools.toml").write_text(
        """schema = "system/schemas/contracts/tools.schema.json"

[[tool]]
concern = "external_runner"
tool = "portable host utilities"
config = "system/tools.toml"
profile = "product"
executables = ["external-runner"]
""",
        encoding="utf-8",
    )
    (tmp_path / "system/surfaces.toml").write_text(
        """schema = "system/schemas/contracts/surfaces.schema.json"

[runtime]
inputs = ["EXAMPLE_HOME"]

[[surface]]
name = "cli"
carrier = "src/example"
""",
        encoding="utf-8",
    )

    allowed = native_owned_references(tmp_path)

    assert "external_sdk" in allowed["import"]
    assert "external-sdk" in allowed["distribution"]
    assert {"example", "external-runner"} <= allowed["executable"]
    assert "example inspect" in allowed["command"]
    assert allowed["value"] == {"EXAMPLE_HOME"}


def test_native_owner_closure_derives_tool_capabilities_from_profile_and_release() -> None:
    allowed = native_owned_references_from_files(
        {
            ".ethos/profile.toml": (
                'profile_id = "example"\n\n[openspec]\nmaterial_paths = ["**"]\n'
            ),
            ".ethos/release.toml": (
                '[attestation]\nformats = ["in-toto-shaped"]\nsigning = "git-ssh"\n'
            ),
        }
    )

    assert {"openspec", "ssh-keygen"} <= allowed["executable"]


def test_native_owner_variation_axes_change_only_their_declaring_carriers() -> None:
    first = native_owned_references_from_files(
        {
            "system/surfaces.toml": '[runtime]\ninputs = ["FIRST_HOME", "FIRST_PORT"]\n',
            ".ethos/release.toml": (
                '[host_profile]\nprovider = "first-forge"\n\n'
                '[publication]\nfirst_remote = "origin"\n'
            ),
            "system/tools.toml": (
                '[[tool]]\nconcern = "extension"\ntool = "first"\n'
                'config = "first.toml"\nprofile = "product"\n'
                'executables = ["first-tool"]\nreferences = ["first-extension"]\n'
            ),
        }
    )
    second = native_owned_references_from_files(
        {
            "system/surfaces.toml": '[runtime]\ninputs = ["SECOND_HOME", "SECOND_PORT"]\n',
            ".ethos/release.toml": (
                '[host_profile]\nprovider = "second-forge"\n\n'
                '[publication]\nsecond_remote = "mirror"\n'
            ),
            "system/tools.toml": (
                '[[tool]]\nconcern = "extension"\ntool = "second"\n'
                'config = "second.toml"\nprofile = "product"\n'
                'executables = ["second-tool"]\nreferences = ["second-extension"]\n'
            ),
        }
    )

    assert first["value"] == {"FIRST_HOME", "FIRST_PORT"}
    assert second["value"] == {"SECOND_HOME", "SECOND_PORT"}
    assert first["executable"] == {"first-tool"}
    assert second["executable"] == {"second-tool"}
    assert first["reference"] == {"first-forge", "first", "first-extension"}
    assert second["reference"] == {"second-forge", "second", "second-extension"}


def test_native_owner_closure_does_not_promote_observed_consumers(tmp_path: Path) -> None:
    (tmp_path / "system").mkdir()
    (tmp_path / "system/surfaces.toml").write_text(
        'schema = "system/schemas/contracts/surfaces.schema.json"\n\n'
        '[[surface]]\nname = "cli"\ncarrier = "src/example"\n',
        encoding="utf-8",
    )
    (tmp_path / "src/example").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\nversion = "1"\n',
        encoding="utf-8",
    )
    (tmp_path / "src/example/module.py").write_text(
        """import rogue_sdk
import os
import subprocess

os.environ.get("ROGUE_HOME")
subprocess.run(["rogue-tool"], check=True)
""",
        encoding="utf-8",
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


def test_central_coupling_registry_is_absent() -> None:
    retired = (
        "system/coupling.toml",
        "system/schemas/kernel/coupling-audit.schema.json",
        "src/ethos/contracts/registry/declarations.py",
        "src/ethos/repository/policy/coupling/audit.py",
        "src/ethos/repository/policy/coupling/registry.py",
        "src/ethos/repository/policy/coupling/release.py",
        "src/ethos/repository/policy/coupling/toolchain.py",
    )

    assert [relative for relative in retired if (ROOT / relative).exists()] == []


def test_product_executables_do_not_pin_host_installation_roots() -> None:
    paths = (
        ROOT / "src/ethos/repository/policy/gates.py",
        ROOT / "src/ethos/repository/profile.py",
        ROOT / "src/ethos/adapters/admission/evidence/external.py",
    )

    assert "/usr/bin/git" not in "".join(path.read_text(encoding="utf-8") for path in paths)
    assert "/usr/bin/ssh-keygen" not in "".join(path.read_text(encoding="utf-8") for path in paths)


def test_active_markdown_extracts_executable_reference_and_option_qualified_command(
    tmp_path: Path,
) -> None:
    observed = product_references_from_files(
        {
            "openspec/changes/current/spec.md": """- **WHEN** `ethos land --closeout --json` runs

```bash
uv run --group dev rogue-tool --check
```

```yaml
- uses: actions/checkout@v7
```
"""
        },
        root=tmp_path,
        declared_commands=("ethos land", "ethos land --closeout"),
    )

    assert {"ethos", "uv", "rogue-tool"} <= observed["executable"]
    assert observed["reference"] == {"github"}
    assert "ethos land --closeout" in observed["command"]


def test_active_guidance_rejects_a_command_outside_the_declared_cyclopts_surface(
    tmp_path: Path,
) -> None:
    (tmp_path / "system").mkdir()
    (tmp_path / "system/surfaces.toml").write_text(
        'schema = "system/schemas/contracts/surfaces.schema.json"\n\n'
        '[[surface]]\nname = "cli"\ncarrier = "src/ethos"\n',
        encoding="utf-8",
    )
    source = tmp_path / "src/ethos"
    source.mkdir(parents=True)
    source.joinpath("application.py").write_text(
        """from cyclopts import App

app = App(name="ethos")

@app.command
def status() -> None:
    pass
""",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "ethos"
version = "1"
dependencies = ["cyclopts>=1"]

[project.scripts]
ethos = "ethos.application:app"
""",
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text(
        "Run `ethos orient --json` before mutation.\n",
        encoding="utf-8",
    )

    assert repository_product_reference_gaps(tmp_path) == [
        "product_reference_not_admitted_at_baseline:command:ethos orient"
    ]
