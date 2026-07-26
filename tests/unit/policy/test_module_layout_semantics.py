from __future__ import annotations

import subprocess

import pytest

from ethos.repository.policy.artifacts import _package_build_route_findings
from ethos.repository.policy.layout.facades import module_facade_findings
from ethos.repository.policy.layout.naming import ambiguous_module_findings
from ethos.repository.policy.layout.naming import multiple_command_owner_findings
from ethos.repository.policy.layout.naming import surface_core_command_findings
from ethos.repository.policy.layout.policy import package_python_files
from ethos.repository.policy.layout.policy import semantic_python_files


def _write(root, relative, source):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("producer_text", "expected_gap_count"),
    [
        (
            'artifact_dir="${repo_root}/build/artifacts/python"\n'
            'uv build --offline --wheel --out-dir "${artifact_dir}" --clear',
            0,
        ),
        ('uv build --offline --wheel --out-dir "${artifact_dir}" --clear', 1),
        (
            'artifact_dir="${repo_root}/build/runtime/python"\n'
            'uv build --offline --wheel --out-dir "${artifact_dir}" --clear',
            1,
        ),
        (
            'other_dir="${repo_root}/build/artifacts/python"\n'
            'uv build --offline --wheel --out-dir "${artifact_dir}" --clear',
            1,
        ),
    ],
)
def test_package_build_route_requires_semantic_out_dir_assignment(
    producer_text: str, expected_gap_count: int
) -> None:
    findings = _package_build_route_findings("tools/ci/scripts/example.sh", producer_text)

    assert len(findings) == expected_gap_count


def test_module_facade_with_all_is_still_blocked(tmp_path) -> None:
    _write(
        tmp_path,
        "src/ethos/legacy.py",
        'from ethos.result import EthosResult\n\n__all__ = ["EthosResult"]\n',
    )

    assert module_facade_findings(tmp_path, {"semantic_paths": ["."]})[0]["reasons"] == [
        "import_only"
    ]


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
        """from pathlib import Path

def decide():
    return Path('.')

def extra():
    return True
""",
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
        """@lane_app.command()
def status():
    pass

@retire_app.command()
def retire():
    pass
""",
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


def test_semantic_scope_covers_source_tests_tools_and_agent_scripts(tmp_path) -> None:
    expected = {
        ".agents/skills/sample/scripts/check.py",
        "src/ethos/domain/model.py",
        "tests/unit/test_model.py",
        "tools/ci/check.py",
    }
    for relative in expected:
        _write(tmp_path, relative, "VALUE = 1\n")
    policy = {
        "semantic_paths": [".agents/skills", "src/ethos", "tests", "tools"],
        "package_paths": ["src/ethos"],
    }

    assert {
        path.relative_to(tmp_path).as_posix() for path in semantic_python_files(tmp_path, policy)
    } == expected
    assert {
        path.relative_to(tmp_path).as_posix() for path in package_python_files(tmp_path, policy)
    } == {"src/ethos/domain/model.py"}


def test_semantic_scope_includes_untracked_and_excludes_deleted_python(tmp_path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    tracked = _write(tmp_path, "src/ethos/model.py", "VALUE = 1\n")
    deleted = _write(tmp_path, "src/ethos/deleted.py", "VALUE = 1\n")
    subprocess.run(["git", "add", tracked, deleted], cwd=tmp_path, check=True)
    deleted.unlink()
    _write(tmp_path, "tools/core.py", "VALUE = 1\n")

    files = {
        path.relative_to(tmp_path).as_posix()
        for path in semantic_python_files(tmp_path, {"semantic_paths": ["."]})
    }

    assert files == {"src/ethos/model.py", "tools/core.py"}


def test_ambiguous_names_are_blocked_in_every_owned_python_carrier(tmp_path) -> None:
    for relative in (
        ".agents/skills/sample/scripts/helpers.py",
        "src/ethos/domain/core.py",
        "tests/support/common.py",
        "tools/ci/utils.py",
    ):
        _write(tmp_path, relative, "VALUE = 1\n")
    policy = {
        "semantic_paths": [".agents/skills", "src/ethos", "tests", "tools"],
        "package_paths": ["src/ethos"],
        "ambiguous_module_names": ["common", "core", "helpers", "utils"],
    }

    assert {finding["path"] for finding in ambiguous_module_findings(tmp_path, policy)} == {
        ".agents/skills/sample/scripts/helpers.py",
        "src/ethos/domain/core.py",
        "tests/support/common.py",
        "tools/ci/utils.py",
    }


def test_native_test_and_tool_names_are_not_treated_as_ambiguous(tmp_path) -> None:
    for relative in (
        "tests/unit/test_change_report.py",
        "tests/unit/test_change_index.py",
        "tests/unit/test_change_native.py",
        "tools/ci/change_report.py",
        "tools/ci/change_index.py",
        "tools/ci/change_native.py",
    ):
        _write(tmp_path, relative, "VALUE = 1\n")
    policy = {
        "semantic_paths": ["src/ethos", "tests", "tools"],
        "package_paths": ["src/ethos"],
        "ambiguous_module_names": ["common", "core", "helpers", "utils"],
    }

    assert ambiguous_module_findings(tmp_path, policy) == []
