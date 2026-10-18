"""Local links describe delivered source, not incidental host files."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.tool as gate_tool
from ethos.adapters.gates.tool import markdown_links_report
from ethos.adapters.repo.content.source import SourceTree
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _repository(tmp_path: Path, markdown: str) -> Path:
    repo = init_git_repo(tmp_path / "repository")
    configuration = repo / ".config/checks/lychee/lychee.toml"
    configuration.parent.mkdir(parents=True)
    configuration.write_text("offline = true\nno_progress = true\nmax_retries = 0\n")
    (repo / "README.md").write_text(markdown)
    return repo


@pytest.mark.parametrize("membership", ["ignored", "untracked", "tracked"])
def test_local_link_requires_delivered_target(tmp_path: Path, membership: str) -> None:
    """The same bytes qualify only when their target belongs to the delivery."""
    target = "build/not-delivered.txt" if membership == "ignored" else "member.txt"
    repo = _repository(tmp_path, f"# Guide\n\n[Member]({target})\n")
    if membership == "ignored":
        (repo / ".gitignore").write_text("build/\n")
    if membership == "tracked":
        (repo / target).write_text("Delivered member.\n")
    commit_fixture(repo, "declare the delivered link")
    if membership != "tracked":
        member = repo / target
        member.parent.mkdir(parents=True, exist_ok=True)
        member.write_text("Delivered member.\n")

    report = markdown_links_report(repo)

    assert report["verdict"] == ("pass" if membership == "tracked" else "block"), report


@pytest.mark.parametrize(
    "route", ["file", "directory", "alias", "reference", "image", "percent", "alias-directory"]
)
def test_native_delivered_routes_remain_valid(tmp_path: Path, route: str) -> None:
    """Native syntax, directories, and an in-tree Git alias remain usable."""
    links = {
        "file": "[Member](docs/member.md#member)",
        "directory": "[Documents](docs/)",
        "alias": "[Member](alias.md#member)",
        "reference": "[Member][selected]\n\n[selected]: docs/member.md#member",
        "image": "![Mark](assets/mark.svg)",
        "percent": "[Member](literal%2520.md#member)",
        "alias-directory": "[Documents](aliases/)",
    }
    repo = _repository(tmp_path, "# Guide\n\n" + links[route] + "\n")
    member = repo / "docs/member.md"
    member.parent.mkdir()
    member.write_text("# Member\n")
    mark = repo / "assets/mark.svg"
    mark.parent.mkdir()
    mark.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
    if route == "alias":
        (repo / "alias.md").symlink_to("docs/member.md")
    if route == "percent":
        (repo / "literal%20.md").write_text("# Member\n")
    if route == "alias-directory":
        aliases = repo / "aliases"
        aliases.mkdir()
        (aliases / "member.md").symlink_to("../docs/member.md")
    commit_fixture(repo, "declare native delivered routes")

    report = markdown_links_report(repo)

    assert report["verdict"] == "pass", report


@pytest.mark.parametrize(
    "name",
    ["guide\u2028member.md"]
    if os.name == "nt"
    else ["guide\nmember.md", "guide\rmember.md", "guide\u2028member.md"],
)
def test_native_input_identity_preserves_literal_line_separators(tmp_path: Path, name: str) -> None:
    """Native input selection preserves each committed path as one complete identity."""
    repo = _repository(tmp_path, "# Guide\n\n[Member](member.txt)\n")
    (repo / "README.md").rename(repo / name)
    (repo / "member.txt").write_text("Delivered member.\n")
    commit_fixture(repo, "declare one literal-path input")
    expected = sum(path.endswith((".md", ".markdown")) for path in SourceTree.observe(repo).entries)

    report = markdown_links_report(repo)

    assert report["verdict"] == "pass", report
    assert report["file_count"] == expected


def test_native_selection_cannot_join_distinct_line_separated_inputs(tmp_path: Path) -> None:
    """Full record verification refuses exclusions despite ambiguous aggregate output."""
    repo = _repository(tmp_path, "# Guide\n")
    name = "guide\u2028member.md" if os.name == "nt" else "guide\nmember.md"
    (repo / "README.md").rename(repo / name)
    (repo / "guide").write_text("# Separate input\n")
    (repo / "member.md").write_text("# Separate input\n")
    (repo / ".config/checks/lychee/lychee.toml").write_text(
        'offline = true\nno_progress = true\nexclude_path = ["member"]\n'
    )
    commit_fixture(repo, "declare excluded literal-path input")

    report = markdown_links_report(repo)

    assert report["verdict"] == "unknown", report
    assert report["required_gaps"] == ["markdown_link_input_selection_unproven"]


@pytest.mark.timeout(2)
def test_source_alias_expansion_is_bounded(tmp_path: Path) -> None:
    """A repeated alias cannot evade cycle detection by lengthening its suffix."""
    repo = _repository(tmp_path, "# Guide\n")
    (repo / "loop").symlink_to("loop/child")
    commit_fixture(repo, "declare an expanding alias cycle")
    source = SourceTree.observe(repo)

    with pytest.raises(ValueError, match="source_target_alias_cycle"):
        source.resolve_target("loop")


def test_native_exclusions_cannot_hide_undelivered_local_targets(tmp_path: Path) -> None:
    """Native filtering may not remove local delivery obligations."""
    repo = _repository(tmp_path, "# Guide\n\n[Member](build/not-delivered.txt)\n")
    (repo / ".gitignore").write_text("build/\n")
    (repo / ".config/checks/lychee/lychee.toml").write_text(
        'offline = true\nno_progress = true\nexclude = ["^file:"]\n'
    )
    commit_fixture(repo, "declare excluded local delivery")
    target = repo / "build/not-delivered.txt"
    target.parent.mkdir()
    target.write_text("Host-only bytes.\n")

    report = markdown_links_report(repo)

    assert report["verdict"] == "block", report


def test_changed_delivered_target_is_not_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A successful native checker cannot certify bytes changed during its invocation."""
    repo = _repository(tmp_path, "# Guide\n\n[Member](member.txt)\n")
    member = repo / "member.txt"
    member.write_text("before\n")
    commit_fixture(repo, "declare the observed member")
    original = gate_tool.run_command

    def change_after_check(root, command, **kwargs):
        result = original(root, command, **kwargs)
        if "--dump" not in command and "--dump-inputs" not in command:
            member.write_text("after!\n")
        return result

    monkeypatch.setattr(gate_tool, "run_command", change_after_check)

    report = markdown_links_report(repo)

    assert report["verdict"] == "unknown", report
    assert report["required_gaps"] == ["source_member_changed:member.txt"]


@pytest.mark.parametrize("kind", ["relative", "absolute"])
def test_source_alias_cannot_escape_delivered_root(tmp_path: Path, kind: str) -> None:
    """A committed alias does not make outside bytes part of its selected delivery."""
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\n")
    repo = _repository(tmp_path, "# Guide\n\n[Outside](alias.md)\n")
    (repo / "alias.md").symlink_to("../outside.md" if kind == "relative" else str(outside))
    commit_fixture(repo, "declare an escaping alias")

    report = markdown_links_report(repo)

    assert report["verdict"] == "block", report
    assert "source_target_outside_root" in str(report["required_gaps"])


@pytest.mark.parametrize("transform", ["base", "remap", "input"])
def test_native_transform_cannot_hide_local_obligations(tmp_path: Path, transform: str) -> None:
    """Native transport settings cannot erase selected-source membership checks."""
    repo = _repository(tmp_path, "# Guide\n\n[Member](build/not-delivered.txt)\n")
    (repo / ".gitignore").write_text("build/\n")
    configuration = {
        "base": 'base_url = "https://example.invalid/"',
        "remap": 'remap = ["file:.* https://example.invalid/"]',
        "input": 'exclude_path = ["README"]',
    }
    (repo / ".config/checks/lychee/lychee.toml").write_text(
        "offline = true\nno_progress = true\n" + configuration[transform] + "\n"
    )
    commit_fixture(repo, "declare hosted URL transformation")
    target = repo / "build/not-delivered.txt"
    target.parent.mkdir()
    target.write_text("Host-only bytes.\n")

    report = markdown_links_report(repo)

    assert report["verdict"] != "pass", report
