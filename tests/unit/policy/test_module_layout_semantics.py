from __future__ import annotations

from ethos.repository.policy.layout.naming import ambiguous_module_findings
from ethos.repository.policy.layout.naming import multiple_command_owner_findings
from ethos.repository.policy.layout.naming import surface_core_command_findings


def _write(root, relative, source):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_ambiguous_module_requires_closed_role_contract(tmp_path) -> None:
    _write(tmp_path, "src/ethos/domain/core.py", "def decide():\n    return True\n")
    policy = {"paths": ["src/ethos"], "ambiguous_module_names": ["core"]}

    assert ambiguous_module_findings(tmp_path, policy)[0]["reasons"] == ["contract_missing"]


def test_exact_kernel_role_contract_admits_matching_module(tmp_path) -> None:
    relative = "src/ethos/domain/core.py"
    _write(tmp_path, relative, "def decide():\n    return True\n")
    policy = {
        "paths": ["src/ethos"],
        "ambiguous_module_names": ["core"],
        "ambiguous_module_roles": [
            {
                "path": relative,
                "role": "kernel",
                "concept": "pure transition decision",
                "authority_refs": ["system/workflows.toml"],
                "public_symbols": ["decide"],
                "max_eloc": 4,
                "allowed_import_roots": ["ethos.contracts"],
            }
        ],
    }

    assert ambiguous_module_findings(tmp_path, policy) == []


def test_role_contract_detects_public_and_import_drift(tmp_path) -> None:
    relative = "src/ethos/domain/core.py"
    _write(
        tmp_path,
        relative,
        "from pathlib import Path\n\ndef decide():\n    return Path('.')\n\ndef extra():\n    return True\n",
    )
    policy = {
        "paths": ["src/ethos"],
        "ambiguous_module_names": ["core"],
        "ambiguous_module_roles": [
            {
                "path": relative,
                "role": "kernel",
                "concept": "pure transition decision",
                "authority_refs": ["system/workflows.toml"],
                "public_symbols": ["decide"],
                "max_eloc": 8,
                "allowed_import_roots": ["ethos.contracts"],
            }
        ],
    }

    reasons = ambiguous_module_findings(tmp_path, policy)[0]["reasons"]
    assert reasons == ["public_drift", "import_drift"]


def test_surface_core_command_and_multiple_apps_are_blocked(tmp_path) -> None:
    relative = "src/ethos/surface/cli/lane/core.py"
    _write(
        tmp_path,
        relative,
        "@lane_app.command()\ndef status():\n    pass\n\n@retire_app.command()\ndef retire():\n    pass\n",
    )
    _write(
        tmp_path,
        "system/commands.toml",
        '[[commands]]\nname = "status"\nimport_path = "ethos.surface.cli.lane.core:status"\n',
    )
    policy = {"paths": ["src/ethos"]}

    assert surface_core_command_findings(tmp_path, policy)[0]["path"] == relative
    assert multiple_command_owner_findings(tmp_path, policy)[0]["owners"] == [
        "lane_app",
        "retire_app",
    ]
