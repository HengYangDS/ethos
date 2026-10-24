"""Local links describe delivered source, not incidental host files."""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import locale
import os
import shutil
import subprocess
import sys
from importlib.metadata import Distribution
from pathlib import Path

import pytest

import ethos.adapters.gates.tool as gate_tool
import ethos.repository.release.resources as product_resources
from ethos.adapters.gates.runner import observe_gate_execution
from ethos.adapters.gates.tool import markdown_links_report
from ethos.adapters.repo.content.source import SourceTree
from ethos.adapters.repo.git import git_executable
from ethos.adapters.repo.runtime.filesystem import runtime_scripts
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

_LYCHEE = runtime_scripts(Path(sys.prefix)) / ("lychee.exe" if os.name == "nt" else "lychee")


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

    assert (report["verdict"], report["file_count"]) == ("pass", expected), report


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


@pytest.mark.parametrize(
    "name", ["[literal].md"] if os.name == "nt" else ["[literal]*.md", "guide?.md"]
)
@pytest.mark.parametrize("target", ["member.txt", "missing.txt"])
def test_native_inputs_keep_glob_syntax_literal(tmp_path: Path, name: str, target: str) -> None:
    """A committed name containing glob syntax is selected, extracted and checked as itself."""
    repo = _repository(tmp_path, f"# Guide\n\n[Member]({target})\n")
    (repo / "README.md").rename(repo / name)
    (repo / "member.txt").write_text("Delivered member.\n")
    commit_fixture(repo, "declare one glob-literal input")
    expected = sum(path.endswith((".md", ".markdown")) for path in SourceTree.observe(repo).entries)

    report = markdown_links_report(repo)

    assert report["verdict"] == ("pass" if target == "member.txt" else "block"), report
    assert report["file_count"] == expected


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


@pytest.mark.parametrize(
    ("boundary", "verdict", "reason"),
    [
        ("empty", "unknown", "markdown_link_source_empty"),
        ("missing-tool", "unknown", "quality_tool_missing:lychee"),
        ("selection-failed", "unknown", "markdown_link_extraction_unproven"),
        ("selection-mismatch", "unknown", "markdown_link_input_selection_unproven"),
        ("nonfile", "unknown", "markdown_link_extraction_unproven"),
        ("nonlocal", "block", "source_target_nonlocal_file"),
        ("outside", "block", "source_target_outside_root"),
    ],
)
def test_native_link_refusal_preserves_source_and_stops_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str, verdict: str, reason: str
) -> None:
    """Native discovery and URI failures remain observable without another check attempt."""
    repo = _repository(tmp_path, "# Guide\n\n[Member](member.txt)\n")
    (repo / "member.txt").write_text("Delivered member.\n")
    if boundary == "empty":
        for path in repo.rglob("*.md"):
            path.unlink()
    commit_fixture(repo, "declare native link failure inputs")
    source = SourceTree.observe(repo)
    original = {path: source.read(path) for path in source.entries}
    if boundary == "missing-tool":
        is_file = Path.is_file
        monkeypatch.setattr(Path, "is_file", lambda path: path != _LYCHEE and is_file(path))
    native = gate_tool.run_command
    calls = []

    def observe(root, command, **kwargs):
        calls.append(command)
        if "--dump-inputs" in command:
            if boundary == "selection-failed":
                return subprocess.CompletedProcess(command, 7, b"", b"native selection failed\n")
            if boundary == "selection-mismatch":
                return subprocess.CompletedProcess(command, 0, b"", b"")
        if "--dump" in command and boundary in {"nonfile", "nonlocal", "outside"}:
            output = {
                "nonfile": "https://example.invalid/member.txt\n",
                "nonlocal": "file://foreign.invalid/member.txt\n",
                "outside": (tmp_path / "outside.txt").as_uri() + "\n",
            }[boundary]
            return subprocess.CompletedProcess(command, 0, output, "")
        return native(root, command, **kwargs)

    monkeypatch.setattr(gate_tool, "run_command", observe)

    report = markdown_links_report(repo)

    assert (report["verdict"], report["required_gaps"]) == (verdict, [reason]), report
    if boundary == "missing-tool":
        assert not calls
    assert all("--dump" in command or "--dump-inputs" in command for command in calls)
    assert {path: SourceTree.observe(repo).read(path) for path in original} == original


def test_markdown_link_gate_excludes_deleted_tracked_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing selected source fails before the native checker can omit it."""
    repo = committed_source_repo(
        tmp_path,
        {
            ".config/checks/lychee/lychee.toml": "offline = true\n",
            "README.md": "# Current\n",
            "docs/deleted.md": "# Deleted\n",
        },
    )
    (repo / "docs/deleted.md").unlink()
    observed: list[tuple[str, ...]] = []

    def run(
        _root: Path, command: tuple[str, ...], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        observed.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(gate_tool, "run_command", run)

    report = gate_tool.markdown_links_report(repo)

    assert report["verdict"] == "unknown", report
    assert report["file_count"] == 3
    assert report["required_gaps"] == ["source_member_link_or_type_forbidden:docs/deleted.md"]
    assert not observed


def test_markdown_links_use_declared_installed_supply_without_ambient_lychee(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the interpreter's scripts supply the link checker; its UTF-8 report decodes anywhere."""
    repo = committed_source_repo(
        tmp_path,
        {
            "README.md": "# Links\n\n[Current](README.md)\n",
            ".config/checks/lychee/lychee.toml": "offline = true\n",
        },
    )
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    git_path = str(Path(git_executable(os.environ)).parent)
    assert shutil.which("lychee", path=git_path) is None
    monkeypatch.setenv("PATH", git_path)
    # Windows interpreter homes keep python.exe outside their Scripts directory, and an ANSI
    # code page such as cp1252 cannot decode the emoji in Lychee's UTF-8 summary.
    monkeypatch.setattr(sys, "executable", str(tmp_path / "home" / "python"))
    monkeypatch.setattr(locale, "getencoding", lambda: "cp1252")

    report = gate_tool.markdown_links_report(repo)

    assert report["verdict"] == "pass", report
    assert (report["file_count"], report["source_tree"]) == (2, tree)
    assert report["native"][0]["command"][0] == str(_LYCHEE)


@pytest.mark.parametrize("state", ["intact", "changed", "missing"])
def test_installed_link_policy_retains_its_package_owner_inside_git_common(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    """Native RECORD owns shipped policy even when its installation is inside the repository."""
    repo = _repository(tmp_path, "# Links\n\n[Current](README.md)\n")
    commit_fixture(repo, "declare repository-owned link inputs")
    package = repo / ".git/ethos/runtime/installed/python/site-packages/ethos"
    shipped = package / "resources"
    inputs = {
        relative: product_resources.canonical_resource(relative).read_bytes()
        for relative in (
            ".config/checks/format-selection/policy.toml",
            ".config/checks/lychee/lychee.toml",
        )
    }
    for relative, content in inputs.items():
        path = shipped / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    metadata = package.parent / "ethos-1.0.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Metadata-Version: 2.1\nName: ethos\nVersion: 1.0.0\n")
    with (metadata / "RECORD").open("w", newline="") as stream:
        record = csv.writer(stream)
        for relative, content in inputs.items():
            digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=")
            record.writerow(
                (f"ethos/resources/{relative}", "sha256=" + digest.decode(), len(content))
            )
    monkeypatch.setattr(product_resources, "files", lambda _name: package)
    monkeypatch.setattr(product_resources, "distribution", lambda _name: Distribution.at(metadata))
    configuration = shipped / ".config/checks/lychee/lychee.toml"
    if state == "changed":
        configuration.write_bytes(configuration.read_bytes() + b"\n# changed\n")
    elif state == "missing":
        configuration.unlink()
    original = {path: path.read_bytes() for path in shipped.rglob("*") if path.is_file()}

    report = markdown_links_report(repo)

    assert report["verdict"] == ("pass" if state == "intact" else "unknown"), report
    assert report["required_gaps"] == (
        []
        if state == "intact"
        else ["product_resource_integrity_invalid:.config/checks/lychee/lychee.toml"]
    )
    assert {path: path.read_bytes() for path in original} == original
    assert git(repo, "status", "--porcelain") == ""


@pytest.mark.parametrize("membership", ["tracked", "untracked"])
@pytest.mark.parametrize("target", ["member.txt", "missing.txt"])
def test_host_links_check_current_authored_candidates(
    tmp_path: Path, membership: str, target: str
) -> None:
    """Host observation checks pending bytes; exact proof still refuses the dirty tree."""
    repo = _repository(tmp_path, "# Guide\n")
    (repo / "member.txt").write_text("Candidate target.\n")
    commit_fixture(repo, "bind the committed link baseline")
    before = git(repo, "rev-parse", "HEAD", "HEAD^{tree}")
    index = git(repo, "write-tree")
    path = repo / ("README.md" if membership == "tracked" else "pending-[literal].md")
    content = f"# Candidate\n\n[Member]({target})\n"
    path.write_text(content)
    expected_count = sum(name.endswith(".md") for name in SourceTree.observe(repo).entries)

    observed = observe_gate_execution(repo, gate_ids=("markdown-links",))

    assert observed["verdict"] == ("pass" if target == "member.txt" else "block"), observed
    native = json.loads(observed["checks"][0]["stdout"])["providers"][0]["report"]
    assert native["file_count"] == expected_count + (membership == "untracked")
    assert native["source_kind"] == "candidate"
    if native["verdict"] == "pass":
        assert native["source_head"] == before.splitlines()[0]
        assert native["source_tree"] == ""
    exact = observe_gate_execution(
        repo, gate_ids=("markdown-links",), expect_head=before.splitlines()[0]
    )
    assert exact["required_gaps"] == ["proof_execution_source_mismatch"], exact
    assert not exact["checks"]
    assert path.read_text() == content
    assert git(repo, "rev-parse", "HEAD", "HEAD^{tree}") == before
    assert git(repo, "write-tree") == index


@pytest.mark.parametrize("change", ["bytes", "membership", "alias", "head"])
def test_candidate_link_observation_refuses_inflight_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    """The native checker cannot certify a candidate that changes after observation."""
    repo = _repository(tmp_path, "# Guide\n\n[Member](alias.txt)\n")
    (repo / "member.txt").write_text("Initial member.\n")
    (repo / "other.txt").write_text("Another member.\n")
    (repo / "alias.txt").symlink_to("member.txt")
    commit_fixture(repo, "bind candidate freshness")
    native = gate_tool.run_command
    mutated = False

    def mutate_after_check(root, command, **kwargs):
        nonlocal mutated
        result = native(root, command, **kwargs)
        if not mutated and "--dump" not in command and "--dump-inputs" not in command:
            mutated = True
            if change == "bytes":
                (repo / "member.txt").write_text("Changed member.\n")
            elif change == "membership":
                (repo / "pending.md").write_text("# New candidate\n")
            elif change == "alias":
                (repo / "alias.txt").unlink()
                (repo / "alias.txt").symlink_to("other.txt")
            else:
                (repo / "head-marker.txt").write_text("Changed head.\n")
                commit_fixture(repo, "move the candidate head")
        return result

    monkeypatch.setattr(gate_tool, "run_command", mutate_after_check)
    report = markdown_links_report(repo, candidate=True)
    expected = {
        "bytes": "source_member_changed:member.txt",
        "membership": "source_candidate_membership_changed",
        "alias": "source_member_changed:alias.txt",
        "head": "source_tree_changed",
    }
    assert report["verdict"] == "unknown", report
    assert report["required_gaps"] == [expected[change]]


@pytest.mark.parametrize("ignored", [False, True])
def test_candidate_links_qualify_only_native_candidate_targets(
    tmp_path: Path, *, ignored: bool
) -> None:
    """Untracked targets are candidate members, but ignored host bytes never become delivery."""
    repo = _repository(tmp_path, "# Guide\n\n[Member](pending.txt)\n")
    if ignored:
        (repo / ".gitignore").write_text("pending.txt\n")
    commit_fixture(repo, "bind candidate target selection")
    (repo / "pending.txt").write_text("Pending member.\n")
    report = markdown_links_report(repo, candidate=True)
    assert report["verdict"] == ("block" if ignored else "pass"), report
