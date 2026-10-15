"""Native formatting and semantic configuration validation share exact authored inputs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.gates.configuration import configuration_report
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.repository.release.resources import canonical_resource
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("relative", "content"),
    [
        ("source.json", '{ "values": [1, 2], "nested": { "valid": true } }\n'),
        ("source.yaml", "value: [one, two]\n"),
        (".gitlab-ci.yml", "value: [one, two]\n"),
        (".github/workflows/ci.yml", "value: [one, two]\n"),
        ("source.yaml", "command: " + "word " * 48 + "end\n"),
        ("source.yaml", "value: |\n  first\n\n\n  second\n"),
    ],
)
def test_native_prettier_accepted_layout_preserves_authored_bytes(
    tmp_path: Path, relative: str, content: str
) -> None:
    root = init_git_repo(tmp_path / "repo")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    report = configuration_report(root, paths=(relative,))
    assert report["verdict"] == "pass", report
    assert report["file_count"] == 1
    assert path.read_text() == content


@pytest.mark.parametrize(
    "relative", ["source.json", "source.yaml", ".gitlab-ci.yml", ".github/workflows/ci.yml"]
)
def test_native_format_refusal_is_not_a_write(tmp_path: Path, relative: str) -> None:
    root = init_git_repo(tmp_path / "repo")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    content = '{"value":true}\n' if relative.endswith("json") else "value: [ one,two ]\n"
    path.write_text(content)
    report = configuration_report(root, paths=(relative,))
    assert report["verdict"] == "block", report
    assert report["required_gaps"]
    assert path.read_text() == content


@pytest.mark.parametrize(
    ("content", "diagnostic"),
    [("value: 1\nvalue: 2\n", "key-duplicates"), ("value: *missing\n", "undeclared alias")],
)
def test_native_semantic_yaml_rejects_invalid_relations_without_layout_policy(
    tmp_path: Path,
    content: str,
    diagnostic: str,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    (root / "source.yaml").write_text(content)
    report = configuration_report(root, paths=("source.yaml",))
    assert report["verdict"] == "block", report
    assert diagnostic in str(report["required_gaps"])
    assert (root / "source.yaml").read_text() == content


def test_native_dependency_resolution_keeps_its_byte_owner(tmp_path: Path) -> None:
    root = init_git_repo(tmp_path / "repo")
    baseline = configuration_report(root)
    relative = ".mise/locks/npm/fixture/aube-lock.yaml"
    path = root / relative
    path.parent.mkdir(parents=True)
    content = "producer-owned: [ x,y ]\n"
    path.write_text(content)
    git(root, "add", relative)
    report = configuration_report(root)
    assert report["verdict"] == baseline["verdict"] == "pass", report
    assert report["file_count"] == baseline["file_count"], report
    refused = configuration_report(root, paths=(relative,))
    assert refused["verdict"] == "block"
    assert "another owner" in str(refused["required_gaps"])
    assert path.read_text() == content


@pytest.mark.parametrize(
    "relative", ["source.json", "source.yaml", ".gitlab-ci.yml", ".github/workflows/ci.yml"]
)
def test_native_formatter_fix_and_check_are_one_idempotent_path(
    tmp_path: Path, relative: str
) -> None:
    root = init_git_repo(tmp_path / "repo")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    content = '{"value":true}\n' if relative.endswith("json") else "value: [ one,two ]\n"
    path.write_text(content)
    command = (
        str(resolve_node_runtime().executable),
        str(product_node_module("prettier") / "bin/prettier.cjs"),
        "--config",
        str(canonical_resource(".config/checks/prettier/prettier.toml")),
        "--no-editorconfig",
        "--write",
        "--",
        relative,
    )
    assert configuration_report(root, paths=(relative,))["verdict"] == "block"
    run_command(root, command, timeout=30, check=True, remove_env=("NODE_OPTIONS", "NODE_PATH"))
    accepted = path.read_bytes()
    assert accepted != content.encode()
    assert configuration_report(root, paths=(relative,))["verdict"] == "pass"
    run_command(root, command, timeout=30, check=True, remove_env=("NODE_OPTIONS", "NODE_PATH"))
    assert path.read_bytes() == accepted
    assert configuration_report(root, paths=(relative,))["verdict"] == "pass"
