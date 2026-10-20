"""Public source formatting preserves exact inputs, native ignores and write admission."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from typing import Any
from unittest.mock import Mock

import pytest

import ethos.adapters.gates.formatting as formatting_gate
import ethos.adapters.gates.tool as gate_tool
import ethos.adapters.mutation.source_format as mutation
from ethos.adapters.gates.formatting import prepare_source_format
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import SourceContract
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import prepared_work_lane
from tests.support.governed_repository import write_test_profile

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def _write(root: Path, files: Mapping[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _command(root: Path, *arguments: str) -> tuple[int, dict[str, Any]]:
    completed = run_ethos_raw("lane", "format", *arguments, "--root", str(root), "--json", cwd=root)
    assert completed.stdout.startswith("{"), completed.stderr
    return completed.returncode, json.loads(completed.stdout)


@pytest.fixture
def lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    return prepared_work_lane(tmp_path, name="format").worktree


def test_public_native_fix_and_check_share_literal_inputs(lane: Path) -> None:
    sources = {
        "src/product.py": "value=1\n",
        "src/ignored.py": "ignored=2\n",
        "docs/with space.md": "# Exact\n\ntext   \n\n- item\n\n  ```text\n  value\n  ```\n",
        "docs/[literal]*.md": "# Literal\n\ntext   \n",
        "docs/new.md": "# New\n\ntext   \n",
        "source.json": '{"value":true}\n',
        "source.yaml": "value: [ one,two ]\n",
        "source.toml": "value=[1,2]\n",
        "src/native.mjs": "export const value={valid:true};\n",
        "tools/native.sh": "if true;then echo native;fi\n",
        "assets/native.svg": (
            '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
            '<path d="M0 0h1v1H0z"/></svg>\n'
        ),
    }
    preserved = {
        "docs/untouched.md": "# Ignored\n\ntext   \n",
        "openspec/changes/archive/old/spec.md": "# Captured\n\ntext   \n",
        "package-lock.json": '{"producer":[1,2]}\n',
    }
    _write(
        lane,
        {
            **sources,
            **preserved,
            ".gitignore": "src/ignored.py\n",
            ".config/checks/prettier/prettierignore": "../../../docs/untouched.md\n",
        },
    )
    (lane / "src/product.py").chmod(0o755)
    (lane / "docs/new.md").chmod(0o640)
    git(lane, "add", "-f", "src/ignored.py")
    head, index = git(lane, "rev-parse", "HEAD"), git(lane, "write-tree")
    paths = tuple(sources)
    code, preview = _command(lane, *paths)
    assert (code, preview["verdict"], preview["state"]) == (0, "pass", "ready")
    assert set(preview["data"]["files"]) == set(preview["data"]["changed_paths"]) == set(paths)
    assert all((lane / path).read_text() == content for path, content in sources.items())

    code, refused = _command(lane, *paths, "--check")
    assert (code, refused["verdict"]) == (1, "block")
    code, applied = _command(lane, *paths, "--apply", "--authorize", "--expect-head", head)
    assert (code, applied["verdict"], applied["state"]) == (0, "pass", "formatted"), applied
    assert (lane / "src/product.py").read_text() == "value = 1\n"
    assert (lane / "src/ignored.py").read_text() == "ignored = 2\n"
    assert (lane / "source.json").read_text() == '{ "value": true }\n'
    assert (lane / "source.yaml").read_text() == "value: [one, two]\n"
    assert (lane / "src/product.py").stat().st_mode & 0o777 == 0o755
    assert (lane / "docs/new.md").stat().st_mode & 0o777 == 0o640
    accepted = {path: (lane / path).read_bytes() for path in paths}
    code, checked = _command(lane, *paths, "--check")
    assert (code, checked["verdict"]) == (0, "pass"), checked
    code, repeated = _command(lane, *paths, "--apply", "--authorize", "--expect-head", head)
    assert (code, repeated["verdict"], repeated["data"]["changed_paths"]) == (0, "pass", [])
    assert all((lane / path).read_bytes() == content for path, content in accepted.items())
    assert all((lane / path).read_text() == content for path, content in preserved.items())
    assert (git(lane, "rev-parse", "HEAD"), git(lane, "write-tree")) == (head, index)

    code, inventory = _command(lane)
    assert (code, inventory["verdict"]) == (0, "pass"), inventory
    files = set(inventory["data"]["files"])
    assert {"src/ignored.py", "docs/new.md"} <= files
    assert not {"openspec/changes/archive/old/spec.md", "package-lock.json"} & files
    assert inventory["data"]["ignored_paths"] == ["docs/untouched.md"]


def test_native_markdown_and_formatting_share_declared_authored_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both share authored inputs and resolve Node, which reads Git state, once per operation."""
    root = init_git_repo(tmp_path / "repo")
    preserved = {
        "docs/upstream.md": "# Upstream\n\ntext   \n",
        "docs/generated.md": "# Generated\n\ntext   \n",
        "docs/projected.md": "# Projection\n\ntext   \n",
        "docs/archive/captured.md": "# Captured\n\ntext   \n",
    }
    _write(
        root,
        {
            **preserved,
            "docs/current.md": "# Current\n\nWords.\n",
            "package-lock.json": "{}\n",
            ".config/checks/ci-projection/policy.toml": (
                'schema = "ethos-ci-template-consistency-v1"\n'
                '[[projection]]\ntemplate = "docs/current.md"\n'
                'projection = "docs/projected.md"\nkind = "copy"\n'
            ),
        },
    )
    upstream = "package-lock.json#packages/node_modules/example"
    producer = ".config/checks/ci-projection/policy.toml"
    write_test_profile(
        root,
        proof=ProofPolicy(
            source_contracts=(
                SourceContract(
                    kind="upstream",
                    input_refs=(upstream,),
                    members={"docs/upstream.md": (upstream, "package/README.md")},
                    integrity_gate="upstream-integrity",
                ),
                SourceContract(
                    kind="generated",
                    input_refs=(producer,),
                    members={"docs/generated.md": (producer, "docs/generated.md")},
                    integrity_gate="generated-integrity",
                ),
            ),
        ),
    )
    expected = {"AGENTS.md", "README.md", "docs/current.md"}
    resolve = Mock(wraps=formatting_gate.resolve_node_runtime)
    monkeypatch.setattr(formatting_gate, "resolve_node_runtime", resolve)
    formatted = {item.path for item in prepare_source_format(root) if item.path.endswith(".md")}
    report = gate_tool.markdown_lint_report(root)
    assert (formatted, resolve.call_count) == (expected, 1)
    assert set(report["native"][0]["files"]) == expected, report
    assert report["native"][0]["verdict"] == "pass", report
    assert all((root / path).read_text() == content for path, content in preserved.items())


def test_official_openspec_keeps_its_owner_and_is_never_formatted(lane: Path) -> None:
    """Official OpenSpec carriers keep their byte owner; the shared formatter refuses them."""
    tasks = "openspec/changes/fixture-change/tasks.md"
    original = (
        "# Tasks\n## 1. Verification\n- [ ] 1.1 Verify `operation-intent-*` keeps its meaning.\n"
    )
    metadata = "openspec/changes/fixture-change/.openspec.yaml"
    yaml = "schema:   spec-driven\ncreated: 2026-10-14\n"
    _write(lane, {tasks: original, metadata: yaml})
    head, index = git(lane, "rev-parse", "HEAD"), git(lane, "write-tree")
    assert not any(item.path.startswith("openspec/") for item in prepare_source_format(lane))
    for relative in (tasks, metadata):
        for arguments in ((), ("--check",), ("--apply", "--authorize", "--expect-head", head)):
            code, report = _command(lane, relative, *arguments)
            assert (code, report["verdict"]) == (1, "block"), report
            assert report["required_gaps"] == [f"source_format_other_owner:{relative}"], report
    assert ((lane / tasks).read_text(), (lane / metadata).read_text()) == (original, yaml)
    assert (git(lane, "rev-parse", "HEAD"), git(lane, "write-tree")) == (head, index)


def test_captured_source_bundles_share_native_selection(lane: Path) -> None:
    """Captured bundle bytes have one owner across fix, check and Markdown lint."""
    integration = "integrations/architecture-publisher/"
    captured = {
        integration + "src/edition/authoring/edition.json": '{"captured":true}\n',
        integration + "src/edition/authoring/source.md": "# Captured\n\nOriginal text   \n",
        integration + "src/edition/static/authoring/metrics.json": '{"captured":[1,2]}\n',
        integration + "migration-baseline.json": '{"migration":true}\n',
        integration + "src/edition/refresh.json": '{"bound-request":true}\n',
        integration + "src/edition/verification-policy.json": '{"bound-request":true}\n',
    }
    source = "integrations/architecture-publisher/src/adapter/source.json"
    _write(lane, {**captured, source: '{"value":true}\n', "docs/current.md": "# Current\n"})
    for path in captured:
        (lane / path).chmod(0o640)
    head, index = git(lane, "rev-parse", "HEAD"), git(lane, "write-tree")

    selected = {item.path for item in prepare_source_format(lane)}
    assert not set(captured) & selected
    assert source in selected
    linted = gate_tool.markdown_lint_report(lane)
    assert linted["verdict"] == "pass", linted
    assert "docs/current.md" in linted["native"][0]["files"]
    assert not set(captured) & set(linted["native"][0]["files"])

    code, refused = _command(
        lane, source, *captured, "--apply", "--authorize", "--expect-head", head
    )
    assert (code, refused["verdict"]) == (1, "block"), refused
    assert (lane / source).read_text() == '{"value":true}\n'
    code, applied = _command(lane, "--apply", "--authorize", "--expect-head", head)
    assert (code, applied["verdict"]) == (0, "pass"), applied
    assert (lane / source).read_text() == '{ "value": true }\n'
    code, checked = _command(lane, "--check")
    assert (code, checked["verdict"]) == (0, "pass"), checked
    code, repeated = _command(lane, "--apply", "--authorize", "--expect-head", head)
    assert (code, repeated["data"]["changed_paths"]) == (0, []), repeated
    assert all((lane / path).read_text() == content for path, content in captured.items())
    assert all((lane / path).stat().st_mode & 0o777 == 0o640 for path in captured)
    assert (git(lane, "rev-parse", "HEAD"), git(lane, "write-tree")) == (head, index)


@pytest.mark.parametrize(
    "arguments", [("--apply",), ("--apply", "--authorize", "--expect-head", "0" * 40)]
)
def test_public_fix_refuses_missing_or_stale_authority_without_writes(
    lane: Path, arguments: tuple[str, ...]
) -> None:
    relative, original = "src/product.py", "value=1\n"
    _write(lane, {relative: original})
    (lane / relative).chmod(0o640)
    code, result = _command(lane, relative, *arguments)
    assert (code, result["verdict"]) == (1, "block"), result
    assert (lane / relative).read_text() == original
    assert (lane / relative).stat().st_mode & 0o777 == 0o640


def test_native_parse_refusal_preserves_every_selected_file(lane: Path) -> None:
    sources = {"src/product.py": "value=1\n", "source.json": "{ broken }\n"}
    _write(lane, sources)
    code, result = _command(
        lane,
        *sources,
        "--apply",
        "--authorize",
        "--expect-head",
        git(lane, "rev-parse", "HEAD"),
    )
    assert (code, result["verdict"]) == (1, "block"), result
    assert all((lane / path).read_text() == content for path, content in sources.items())


def test_native_policy_warning_refuses_postimages_and_preserves_original_diagnostics(
    lane: Path,
) -> None:
    sources = {"src/product.py": "value=1\n", "source.json": '{"value":true}\n'}
    _write(lane, {**sources, ".config/checks/prettier/prettier.toml": "unknownFormat = true\n"})
    code, result = _command(
        lane,
        *sources,
        "--apply",
        "--authorize",
        "--expect-head",
        git(lane, "rev-parse", "HEAD"),
    )
    assert (code, result["verdict"]) == (1, "block"), result
    assert all((lane / path).read_text() == content for path, content in sources.items())
    native = result["data"]["errors"][0]
    assert native["exit_code"] == 0
    assert "unknownFormat" in native["stderr"]


def test_native_ignore_and_literal_pragma_preserve_original_bytes(lane: Path) -> None:
    sources = {
        "docs/untouched.md": "# Ignored\n\ntext   \n",
        "docs/example.md": "# Native\n\n<!-- prettier-ignore -->\n|a|b|\n|-|-|\n|1|2|\n",
    }
    _write(
        lane, {**sources, ".config/checks/prettier/prettierignore": "../../../docs/untouched.md\n"}
    )
    code, result = _command(lane, *sources, "--check")
    assert (code, result["verdict"]) == (0, "pass"), result
    assert result["data"]["ignored_paths"] == ["docs/untouched.md"]
    assert all((lane / path).read_text() == content for path, content in sources.items())


def test_ignore_file_outside_its_carrier_is_refused_without_writes(lane: Path) -> None:
    sources = {"docs/untouched.md": "# Ignored\n\ntext   \n"}
    _write(lane, {**sources, ".prettierignore": "docs/untouched.md\n"})
    code, result = _command(lane, *sources, "--check")
    assert (code, result["verdict"]) == (1, "block"), result
    assert "native_tool_configuration_location_invalid:prettier-ignore" in json.dumps(result)
    assert all((lane / path).read_text() == content for path, content in sources.items())


def test_protected_root_cannot_fix_authored_source(lane: Path) -> None:
    root = lane.parent / "repo"
    relative, original = "source.json", '{"value":true}\n'
    _write(root, {relative: original})
    code, result = _command(
        root, relative, "--apply", "--authorize", "--expect-head", git(root, "rev-parse", "HEAD")
    )
    assert (code, result["verdict"]) == (1, "block"), result
    assert (root / relative).read_text() == original


def test_literal_input_without_final_newline_is_fixed_idempotently(lane: Path) -> None:
    relative = 'src/native "quote" \\ path.py'
    _write(lane, {relative: "value=1"})
    head = git(lane, "rev-parse", "HEAD")
    code, applied = _command(lane, relative, "--apply", "--authorize", "--expect-head", head)
    assert (code, applied["verdict"]) == (0, "pass"), applied
    assert (lane / relative).read_bytes() == b"value = 1\n"
    code, checked = _command(lane, relative, "--check")
    assert (code, checked["verdict"]) == (0, "pass"), checked


def test_missing_required_input_remains_unknown_without_mutation(lane: Path) -> None:
    _write(lane, {"src/valid.py": "value=1\n"})
    code, result = _command(
        lane,
        "src/valid.py",
        "src/missing.py",
        "--apply",
        "--authorize",
        "--expect-head",
        git(lane, "rev-parse", "HEAD"),
    )
    assert (code, result["verdict"]) == (1, "unknown"), result
    assert (lane / "src/valid.py").read_bytes() == b"value=1\n"


@pytest.mark.parametrize("relative", ["../outside.py", "src/linked.py"])
def test_escaping_or_linked_input_is_refused_before_any_write(lane: Path, relative: str) -> None:
    _write(lane, {"src/valid.py": "value=1\n"})
    outside = lane.parent / "outside.py"
    outside.write_text("outside=1\n")
    if relative == "src/linked.py":
        (lane / relative).symlink_to(outside)
    code, result = _command(lane, "src/valid.py", relative, "--check")
    assert (code, result["verdict"]) == (1, "block"), result
    assert (lane / "src/valid.py").read_text() == "value=1\n"
    assert outside.read_text() == "outside=1\n"


def test_conflicting_native_increment_refuses_all_postimages(lane: Path) -> None:
    sources = {
        "source.json": '{"nested":{"value":"' + "x" * 100 + '"}}\n',
        "src/valid.py": "value=1\n",
    }
    _write(lane, {**sources, ".config/checks/prettier/prettier.toml": "tabWidth = 4\n"})
    code, result = _command(lane, *sources, "--check")
    assert (code, result["verdict"]) == (1, "block"), result
    assert all((lane / path).read_text() == content for path, content in sources.items())


def test_conflicting_python_formatter_increment_cannot_replace_shared_policy(lane: Path) -> None:
    content = 'value = {"native": "' + "x" * 90 + '"}\n'
    _write(
        lane,
        {"src/valid.py": content, ".config/checks/ruff/ruff.toml": "line-length = 200\n"},
    )
    code, result = _command(lane, "src/valid.py", "--check")
    assert (code, result["verdict"]) == (1, "block"), result
    assert "native_formatter_policy_conflict" in str(result["required_gaps"])
    assert (lane / "src/valid.py").read_text() == content


@pytest.mark.parametrize("changed", ["source", "index"])
def test_source_or_index_drift_blocks_the_native_fix(
    lane: Path, monkeypatch: pytest.MonkeyPatch, changed: str
) -> None:
    sources = {"src/first.py": "first=1\n", "src/second.py": "second=2\n"}
    _write(lane, sources)
    native = mutation.prewrite_guard

    def drift(**arguments):
        decision = native(**arguments)
        if changed == "source":
            (lane / "src/first.py").write_text("peer=3\n")
        else:
            git(lane, "add", "src/first.py")
        return decision

    monkeypatch.setattr(mutation, "prewrite_guard", drift)
    code, result = _command(
        lane, *sources, "--apply", "--authorize", "--expect-head", git(lane, "rev-parse", "HEAD")
    )
    assert (code, result["verdict"]) == (1, "block"), result
    assert (lane / "src/first.py").read_text() == (
        "peer=3\n" if changed == "source" else sources["src/first.py"]
    )
    assert (lane / "src/second.py").read_text() == sources["src/second.py"]
