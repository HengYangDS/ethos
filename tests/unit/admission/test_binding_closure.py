from __future__ import annotations

import json
from pathlib import Path

import pytest

from ethos.contracts.registry.declarations import CouplingDeclaration
from ethos.repository.policy.coupling.audit import coupling_audit_report
from ethos.repository.policy.coupling.closure import product_references_from_files
from ethos.repository.policy.coupling.closure import repository_product_reference_gaps
from ethos.repository.policy.coupling.closure import repository_product_references
from ethos.repository.policy.coupling.registry import binding_registry

ROOT = Path(__file__).resolve().parents[3]


def _binding(
    binding_id: str,
    *,
    commands: tuple[str, ...] = (),
    executables: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "id": binding_id,
        "layer": "profile_or_adapter_binding",
        "required": False,
        "owns_product_semantics": False,
        "adapter_replaceable": True,
        "required_for": ["test binding"],
        "replaceability": "replaceable-adapter",
        "degradation_state": "nonblocking:test_binding_absent",
        "proof_gate": "tests",
        "commands": list(commands),
        "executables": list(executables),
        "admission": {
            "authority_ref": "tests",
            "truth_boundary": "profile_or_adapter",
            "decision_state": "admitted",
        },
    }


def _declaration_payload(bindings: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": "test-coupling",
        "schema_version": 1,
        "layers": {"profile_or_adapter_binding": "test adapters"},
        "openspec_governance": {
            "required": True,
            "layer": "profile_or_adapter_binding",
            "capability": "test governance",
            "execution_surface": "profile_or_adapter_binding",
            "not_a_second_command_plane": True,
        },
        "native_protocols": {
            "layer": "profile_or_adapter_binding",
            "formats": [],
            "provider_optional": False,
        },
        "binding": bindings,
    }


def _minimal_coupling(*, latent: bool) -> str:
    latent_declaration = (
        'latent = { reason = "host adapter is admitted but optional", '
        'executables = ["future-tool"] }\n'
        if latent
        else ""
    )
    return f"""id = "test-coupling"
schema_version = 1
layers = {{ profile_or_adapter_binding = "test adapters" }}

[openspec_governance]
required = true
layer = "profile_or_adapter_binding"
capability = "test governance"
execution_surface = "profile_or_adapter_binding"
not_a_second_command_plane = true

[native_protocols]
layer = "profile_or_adapter_binding"
formats = []
provider_optional = false

[[binding]]
id = "future_tool"
layer = "profile_or_adapter_binding"
required = false
owns_product_semantics = false
adapter_replaceable = true
required_for = ["test binding"]
replaceability = "replaceable-adapter"
degradation_state = "nonblocking:future_tool_absent"
proof_gate = "tests"
executables = ["future-tool"]
{latent_declaration}admission = {{ authority_ref = "tests", truth_boundary = "profile_or_adapter", decision_state = "admitted" }}
"""


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


def test_patch_binding_scan_uses_the_same_normalized_five_kind_extractor(
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


def test_current_closure_rejects_stale_declared_only_binding(tmp_path: Path) -> None:
    system = tmp_path / "system"
    system.mkdir()
    system.joinpath("coupling.toml").write_text(_minimal_coupling(latent=False), encoding="utf-8")

    assert repository_product_reference_gaps(tmp_path) == [
        "product_reference_declared_but_unobserved:executable:future-tool"
    ]


def test_current_closure_accepts_explicitly_justified_latent_binding(tmp_path: Path) -> None:
    system = tmp_path / "system"
    system.mkdir()
    system.joinpath("coupling.toml").write_text(_minimal_coupling(latent=True), encoding="utf-8")

    assert repository_product_reference_gaps(tmp_path) == []


def test_audit_and_registry_load_the_explicit_root_declaration(tmp_path: Path) -> None:
    coupling = (ROOT / "system/coupling.toml").read_text(encoding="utf-8")
    coupling = coupling.replace(
        'profile_or_adapter_binding = "Configured host, provider, projection, distribution, or execution surfaces that bind evidence without owning product semantics."',
        'profile_or_adapter_binding = "root-specific adapter declaration"',
    ).replace(
        'config_source = ".ethos/workspace.toml"',
        'config_source = ".root-specific/workspace.toml"',
    )
    system = tmp_path / "system"
    system.mkdir()
    system.joinpath("coupling.toml").write_text(coupling, encoding="utf-8")

    registry = binding_registry(tmp_path)
    report = coupling_audit_report(tmp_path)

    branch_policy = next(entry for entry in registry if entry["id"] == "branch_role_policy")
    assert branch_policy["config_source"] == ".root-specific/workspace.toml"
    assert report["taxonomy"]["profile_or_adapter_binding"] == ("root-specific adapter declaration")


def test_duplicate_normalized_commands_are_rejected() -> None:
    payload = _declaration_payload(
        [
            _binding("first", commands=("ethos land --closeout",)),
            _binding("second", commands=(" ethos   land   --closeout ",)),
        ]
    )

    with pytest.raises(ValueError, match="duplicate coupling commands:ethos land --closeout"):
        CouplingDeclaration.model_validate(payload)


def test_option_qualified_command_is_distinct_from_base_command() -> None:
    payload = _declaration_payload(
        [_binding("land", commands=("ethos land", "ethos land --closeout"))]
    )

    declaration = CouplingDeclaration.model_validate(payload)

    assert declaration.bindings[0].commands == ("ethos land", "ethos land --closeout")


def test_active_markdown_extracts_executable_reference_and_option_qualified_command(
    tmp_path: Path,
) -> None:
    system = tmp_path / "system"
    system.mkdir()
    system.joinpath("coupling.toml").write_text(
        _minimal_coupling(latent=True).replace(
            'executables = ["future-tool"]',
            'commands = ["ethos land", "ethos land --closeout"]\nexecutables = ["future-tool"]',
            1,
        ),
        encoding="utf-8",
    )
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
    )

    assert {"ethos", "uv", "rogue-tool"} <= observed["executable"]
    assert observed["reference"] == {"github"}
    assert "ethos land --closeout" in observed["command"]
