"""Executable product boundaries not duplicated by policy and schema gates."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ethos.contracts.admission import ethos_command_is_readonly
from ethos.repository.policy.boundary.product import contributor_policy_report
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.repository.policy.references.closure import repository_product_reference_gaps
from tests.support.architecture import isolated_path

ROOT = Path(__file__).resolve().parents[2]


def _launcher(tmp_path: Path) -> Path:
    target = tmp_path / "package/bin/ethos.mjs"
    target.parent.mkdir(parents=True)
    target.write_text(
        (ROOT / "distributions/npm/bin/ethos.mjs").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return target


def test_current_product_boundary_reports_close_without_unowned_references() -> None:
    reports = (product_boundary_report(ROOT), contributor_policy_report(ROOT))

    assert all(report["verdict"] == "pass" for report in reports), reports
    assert repository_product_reference_gaps(ROOT) == []


def test_npm_launcher_prefers_the_bound_source_checkout(tmp_path: Path) -> None:
    if not (node := shutil.which("node")):
        pytest.skip("node is unavailable")
    checkout = tmp_path / "source-checkout"
    uv_log = tmp_path / "uv.log"
    for path in (checkout / "src/ethos", checkout / "distributions/npm/bin"):
        path.mkdir(parents=True)
    (checkout / "pyproject.toml").write_text('[project]\nname = "ethos"\n', encoding="utf-8")
    (checkout / "src/ethos/cli.py").write_text("", encoding="utf-8")
    (checkout / "distributions/npm/bin/ethos.mjs").write_text("", encoding="utf-8")
    environment = isolated_path(
        tmp_path,
        {"uv": f'#!/bin/sh\nprintf \'%s\\n\' "$*" > "{uv_log}"\n'},
    )

    result = subprocess.run(
        [node, str(_launcher(tmp_path)), "status", "--json"],
        cwd=checkout,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert uv_log.read_text(encoding="utf-8").strip() == (
        f"run --project {checkout} ethos status --json"
    )


@pytest.mark.parametrize("mode", ["python3", "python", "untrusted"])
def test_npm_launcher_fallback_is_interpreter_selective_and_trust_bound(
    tmp_path: Path,
    mode: str,
) -> None:
    if not (node := shutil.which("node")):
        pytest.skip("node is unavailable")
    log = tmp_path / "python.log"
    uv_marker = tmp_path / "uv-called"
    python3_check = 0 if mode == "python3" else 1
    executables = {
        "uv": f"#!/bin/sh\ntouch '{uv_marker}'\n",
        "python3": (
            f'#!/bin/sh\nif [ "$1" = "-c" ] || [ "$2" = "-c" ]; then exit {python3_check}; fi\n'
            f"printf '%s\\n' \"$*\" >> \"{log}\"\nprintf '0.1.0a1\\n'\n"
        ),
    }
    if mode == "python":
        executables["python"] = (
            f'#!/bin/sh\nif [ "$1" = "-c" ] || [ "$2" = "-c" ]; then exit 0; fi\n'
            f"printf 'python:%s\\n' \"$*\" >> \"{log}\"\nprintf '0.1.0a1\\n'\n"
        )
    environment = isolated_path(tmp_path, executables)
    cwd = tmp_path
    if mode == "untrusted":
        cwd = tmp_path / "untrusted"
        (cwd / "src/ethos").mkdir(parents=True)
        (cwd / "pyproject.toml").write_text("[project]\nname='fake'\n", encoding="utf-8")
        (cwd / "src/ethos/__init__.py").write_text("", encoding="utf-8")

    result = subprocess.run(
        [node, str(_launcher(tmp_path)), "--version"],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    if mode == "untrusted":
        assert result.returncode == 127
        assert not uv_marker.exists()
    else:
        assert result.returncode == 0
        assert result.stdout.strip() == "0.1.0a1"
        assert log.read_text(encoding="utf-8").splitlines() == (
            ["-P -m ethos.cli --version"]
            if mode == "python3"
            else ["python:-P -m ethos.cli --version"]
        )


def test_npm_launcher_reaches_the_source_command_plane(tmp_path: Path) -> None:
    if not shutil.which("node") or not shutil.which("uv"):
        pytest.skip("node or uv is unavailable")
    adopter = tmp_path / "adopter"
    adopter.mkdir()
    for command in (
        ("git", "init", "-q", "-b", "main"),
        ("git", "config", "user.name", "Test User"),
        ("git", "config", "user.email", "test@example.invalid"),
    ):
        subprocess.run(command, cwd=adopter, check=True)
    (adopter / "README.md").write_text("fixture\n", encoding="utf-8")
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


@pytest.mark.parametrize(
    ("command", "verdict"),
    [
        (("ethos", "status", "--json"), True),
        (("ethos", "plan", "--json"), True),
        (("ethos", "prove", "--json"), False),
        (("ethos", "land", "--json"), False),
    ],
)
def test_command_readonly_classification_is_public_and_fail_closed(
    command: tuple[str, ...],
    verdict: object,
) -> None:
    assert ethos_command_is_readonly(command) is verdict
