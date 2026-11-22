"""A staged admission is judged by its staged tree, at the preview and at the commit.

The index-target preview and the commit's staged admission ask one function for the OpenSpec scope
of their staged tree: every file is read from a projection of that tree, and Git, the Lease and
history are read at the lane. The staged tree's answer stands when it passes. While the obligation
`staged-openspec-tree` reports, an answer that does not pass yields to the working files' answer,
which carries the staged tree's gaps as reported; armed, the staged tree alone decides.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from ruff import find_ruff_bin

import ethos.adapters.admission.prewrite as prewrite
import ethos.adapters.admission.staged_tree as staged_tree
import ethos.adapters.openspec.cli as openspec_cli
import ethos.adapters.repo.git as git_adapter
from ethos.adapters.openspec.selection import selected_change
from ethos.adapters.repo.hook.protocol import execute_hook
from ethos.adapters.store.state.lease.projection import lease_rows
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from tests.support import governed_repository as gr
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import install_fixture_hook_runtime

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator

_CHANGE = "landing-change"
_PROFILE = ".ethos/profile.toml"
_PRODUCT = "src/landing.py"
_SCHEMA = "local-spec-driven"
_STRAY = "openspec/specs/stray.txt"
_STRAY_GAP = "openspec_specs_root_entry_unexpected:stray.txt"
_CAPABILITY = "openspec/specs/contracts/capability.toml"
_FAMILIES = "openspec/specs/families.toml"
_TEMPLATE = "openspec/specs/template.md"
_ROOT_TEMPLATE = "openspec/specs/capability.template.toml"
_REFUSED = (_CAPABILITY, "openspec/specs/broken", _FAMILIES, _ROOT_TEMPLATE, _TEMPLATE)
_PROJECTION = "ethos-openspec-tree-"
_UNPROVEN = (
    "\n### Requirement: Unproven\n\nThe capability SHALL be exercised without any scenario.\n"
)
# What the official report says of the refused base, in its own order, before the Change's gap.
_BASE_GAPS = [
    "openspec_spec_capability_entry_unexpected:broken:capability.toml",
    "openspec_specs_root_entry_unexpected:capability.template.toml",
    "openspec_spec_capability_entry_unexpected:contracts:capability.toml",
    "openspec_specs_root_entry_unexpected:families.toml",
    "openspec_specs_root_entry_unexpected:template.md",
    "openspec_validation_failed:spec:broken",
]
_MISSING = f"openspec_requested_change_missing:{_CHANGE}"


@pytest.fixture(autouse=True)
def _no_inherited_change(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ETHOS_CHANGE", raising=False)


@pytest.fixture(autouse=True)
def _git_never_runs_in_a_projection(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Every Git command of every case runs at the repository, never below a projection."""
    roots: list[str] = []
    run_command = git_adapter.process_adapter.run_command

    def spy(root, command, **options):
        roots.append(Path(root).as_posix())
        return run_command(root, command, **options)

    monkeypatch.setattr(git_adapter.process_adapter, "run_command", spy)
    yield
    assert not [root for root in roots if _PROJECTION in root]


def _lane(tmp_path: Path, *, refused: bool = False) -> Path:
    """Build a governed repository with an owned Work Lane on a whole or a refused base.

    The refused base has the shape of an adopter's accepted branch: a repository-local schema,
    undeclared capability files, three unexpected specs-root entries and a failing spec.
    """
    repo = gr.build(gr.RepositorySpec(adoption="governance"), tmp_path / "repo").repository
    profile = repo / _PROFILE
    declared = profile.read_text(encoding="utf-8")
    material = '"**"' if refused else '"openspec/**", "src/**"'
    assert '"openspec/**"' in declared
    profile.write_text(declared.replace('"openspec/**"', material), encoding="utf-8")
    if refused:
        command = openspec_cli.openspec_base_command(execution_probe=False)
        assert command is not None
        native = Path(command[1]).resolve().parent.parent / "schemas/spec-driven"
        shutil.copytree(native, repo / "openspec/schemas" / _SCHEMA)
        config = repo / "openspec/config.yaml"
        text = config.read_text(encoding="utf-8")
        config.write_text(text.replace("schema: spec-driven", f"schema: {_SCHEMA}"), "utf-8")
        valid = (repo / "openspec/specs/contracts/spec.md").read_text(encoding="utf-8")
        gr.write_tree(
            repo,
            {
                _CAPABILITY: '[capability]\nfamily = "core"\n',
                "openspec/specs/broken/capability.toml": '[capability]\nfamily = "core"\n',
                _FAMILIES: '[families]\ncore = ["contracts"]\n',
                _ROOT_TEMPLATE: '[capability]\nfamily = "<family>"\n',
                _TEMPLATE: "# Canonical Specification Template\n\n## Purpose\n\nDescribe it.\n",
                "openspec/specs/broken/spec.md": valid + _UNPROVEN,
            },
        )
    gr.commit_fixture(repo, "chore: declare the base of the landing")
    candidate, lane = Path(f"{repo}-candidate-dev"), Path(f"{repo}-work-landing")
    gr.git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    install_fixture_hook_runtime(repo)
    gr.git(repo, "worktree", "add", "-b", "work/landing", lane.as_posix(), "candidate/dev")
    gr.acquire_lease(
        gr.state_database(repo),
        lease=gr.LaneLease(
            lane_ref="work/landing",
            holder_ref="agent:test:case:agent-test",
            generation=1,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        ),
    )
    return lane


def _change(lane: Path, change: str = _CHANGE, *, schema: str = "spec-driven") -> None:
    """Write one complete official Change and leave the configuration as it was."""
    config = lane / "openspec/config.yaml"
    kept = config.read_text(encoding="utf-8")
    gr.write_active_commitment(lane, change_id=change)
    config.write_text(kept, encoding="utf-8")
    metadata = lane / f"openspec/changes/{change}/.openspec.yaml"
    metadata.write_text(f"schema: {schema}\ncreated: 2026-11-22\n", encoding="utf-8")


def _product(lane: Path) -> None:
    (lane / _PRODUCT).parent.mkdir(exist_ok=True)
    (lane / _PRODUCT).write_text("VALUE = 1\n", encoding="utf-8")


def _remove(lane: Path, *paths: str) -> None:
    for path in paths:
        target = lane / path
        shutil.rmtree(target) if target.is_dir() else target.unlink()


def _landing(lane: Path, *, retire_schema: bool = False) -> None:
    """The whole landing on the refused base: its Change, a product path and every repair."""
    _change(lane, schema="spec-driven" if retire_schema else _SCHEMA)
    _product(lane)
    _remove(lane, *_REFUSED)
    if retire_schema:
        _remove(lane, f"openspec/schemas/{_SCHEMA}")
        config = lane / "openspec/config.yaml"
        text = config.read_text(encoding="utf-8")
        config.write_text(text.replace(f"schema: {_SCHEMA}", "schema: spec-driven"), "utf-8")
        profile = lane / _PROFILE
        text = profile.read_text(encoding="utf-8")
        assert 'material_paths = ["**"]' in text
        replaced = text.replace(
            'material_paths = ["**"]', 'material_paths = ["openspec/**", "src/**"]'
        )
        profile.write_text(replaced, encoding="utf-8")
        gr.write_release_mirror(lane, "independent")


def _patch(lane: Path, build: Callable[[Path], object]) -> tuple[str, list[str]]:
    """Take the patch of one final tree against the head; the lane goes back to the head."""
    build(lane)
    gr.git(lane, "add", "-A")
    patch = gr.git(lane, "diff", "--cached", "--no-renames") + "\n"
    rows = gr.git(lane, "diff", "--cached", "--no-renames", "--name-status").splitlines()
    gr.git(lane, "reset", "-q", "--hard")
    gr.git(lane, "clean", "-fdq")
    return patch, [row.split("\t", 1)[1] for row in rows]


def _stage(lane: Path, patch: str, *, working_files: bool) -> None:
    """Apply the patch to the index, and to the working files when asked."""
    file = lane.parent / "landing.patch"
    file.write_text(patch, encoding="utf-8")
    gr.git(lane, "apply", "--index" if working_files else "--cached", file.as_posix())


def _working_files_follow(lane: Path, paths: list[str]) -> None:
    """Bring the working files of the staged paths to the staged content, and no other file."""
    staged = set(gr.git(lane, "ls-files", "--", *paths).splitlines())
    for path in paths:
        if path in staged:
            gr.git(lane, "checkout-index", "-f", "--", path)
        elif (lane / path).exists():
            (lane / path).unlink()
            # As Git does, a directory that the removal emptied goes with its last file.
            for parent in (lane / path).parents:
                if parent == lane or any(parent.iterdir()):
                    break
                parent.rmdir()


def _preview(
    lane: Path, patch: str, paths: list[str], *, target: str = "index", change: str | None = None
) -> dict:
    with selected_change(change):
        return prewrite.prewrite_guard(
            root=lane, paths=[lane / p for p in paths], editor_root=lane, patch=patch, target=target
        )


def _hook(lane: Path, paths: list[str], *, change: str | None = None) -> dict:
    """Ask as the `pre-commit` hook asks: the staged paths, no target."""
    with selected_change(change):
        return prewrite.prewrite_guard(
            root=lane,
            paths=[lane / p for p in paths],
            editor_root=lane,
            require_editor_root=True,
            staged=True,
        )


def _pre_commit(lane: Path, capfd: pytest.CaptureFixture[str], change: str | None = None) -> str:
    """Run the whole `pre-commit` hook in this process; return what it says when it admits."""
    capfd.readouterr()
    with selected_change(change):
        code = execute_hook(lane, "pre-commit", (), stdin=StringIO())
    said = capfd.readouterr().err
    assert code == 0, said
    return said


def _formatter_for_the_installed_hook(lane: Path) -> None:
    """Give the installed hook runtime the formatter that a staged Python path is checked with."""
    install_fixture_hook_runtime(lane, native_executables={"ruff": Path(find_ruff_bin())})
    assert (Path(gr.git(lane, "config", "core.hooksPath")) / "pre-commit").is_file()


def _git_commit(lane: Path, *, admitted: bool = True) -> str:
    """Let Git itself commit the index through every installed hook; return what they say."""
    completed = git_process(lane, "commit", "-m", "feat: land the staged tree")
    assert (completed.returncode == 0) is admitted, completed.stderr
    return completed.stderr


def _state(lane: Path, *, index_bytes: bool = True) -> tuple:
    """The lane's index, working files, head, refs and Lease rows.

    The commit's admission writes the index's tree, as it does today, which may rewrite the
    index's cache of trees: its entries are compared then, and not its bytes.
    """
    index = Path(gr.git(lane, "rev-parse", "--path-format=absolute", "--git-path", "index"))
    return (
        index.read_bytes() if index_bytes else gr.git(lane, "ls-files", "--stage", "--debug"),
        {p.relative_to(lane): p.read_bytes() for p in lane.rglob("*") if p.is_file()},
        gr.git(lane, "rev-parse", "HEAD"),
        gr.git(lane, "show-ref"),
        lease_rows(gr.state_database(lane)),
    )


def _strings(value: object) -> Iterator[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def _judged_by_its_tree(report: dict, *, change: str = _CHANGE) -> str:
    """The staged tree's own answer passed; return the tree that the answer names."""
    assert report["verdict"] == "pass", report["required_gaps"]
    assert report["reported_gaps"] == []
    assert report["material_scope"]["state"] == "attributed"
    assert [item["name"] for item in report["material_scope"]["changes"]] == [change]
    assert report["openspec"]["observed_tree"] == report["patch_admission"]["index_tree"]
    # The payload names repository-relative paths and the tree, never the removed projection.
    assert not [text for text in _strings(report) if _PROJECTION in text]
    assert report["openspec"]["official_config"]["path"] == "openspec/config.yaml"
    return report["openspec"]["observed_tree"]


@pytest.mark.parametrize(("retire_schema", "change"), [(False, _CHANGE), (True, None)])
def test_the_whole_landing_commits_from_the_index_alone(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], *, retire_schema: bool, change: str | None
) -> None:
    lane = _lane(tmp_path, refused=True)
    patch, paths = _patch(lane, lambda root: _landing(root, retire_schema=retire_schema))
    assert (_PROFILE in paths) is retire_schema
    before = _state(lane)

    preview = _preview(lane, patch, paths, change=change)

    tree = _judged_by_its_tree(preview)
    assert tree != preview["index_prewrite"]["expected_index_tree"]
    assert _state(lane) == before
    # The patch is staged and the working files stay at the refused base.
    _stage(lane, patch, working_files=False)
    staged = _state(lane, index_bytes=False)
    commit = _hook(lane, paths, change=change)
    assert _judged_by_its_tree(commit) == tree == gr.git(lane, "write-tree")
    assert commit["material_scope"] == preview["material_scope"]
    assert commit["openspec"]["commitment"] == preview["openspec"]["commitment"]
    assert _state(lane, index_bytes=False) == staged
    # The hook itself admits it without a word, and Git commits it; the working files stay.
    assert _pre_commit(lane, capfd, change) == ""
    base = gr.git(lane, "rev-parse", "HEAD")
    gr.git(lane, "commit", "--no-verify", "--no-gpg-sign", "-q", "-m", "feat: land the whole")
    assert gr.git(lane, "rev-parse", "HEAD^{tree}") == tree
    assert _state(lane, index_bytes=False)[1] == staged[1]
    gr.git(lane, "reset", "-q", "--soft", base)
    # The working files then follow the staged content, and the answer is the same.
    _working_files_follow(lane, paths)
    status = gr.git(lane, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
    assert status
    assert all(entry[1] == " " for entry in status)
    followed = _hook(lane, paths, change=change)
    assert _judged_by_its_tree(followed) == tree
    assert followed["material_scope"] == commit["material_scope"]
    assert _pre_commit(lane, capfd, change) == ""


def test_the_landing_in_the_index_and_the_working_files_commits_as_before(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    lane = _lane(tmp_path, refused=True)
    patch, paths = _patch(lane, lambda root: _landing(root, retire_schema=True))
    _stage(lane, patch, working_files=True)

    commit = _hook(lane, paths)

    _judged_by_its_tree(commit)
    assert _pre_commit(lane, capfd) == ""
    with pytest.MonkeyPatch.context() as today:
        today.setattr(prewrite, "staged_tree_scope", lambda *inputs, **_: inputs[3](None))
        before = _hook(lane, paths)
    assert before["verdict"] == "pass"
    assert before["material_scope"] == commit["material_scope"]
    assert before["openspec"]["commitment"] == commit["openspec"]["commitment"]


def test_git_commits_the_landing_from_the_index_alone_through_the_installed_hook(
    tmp_path: Path,
) -> None:
    lane = _lane(tmp_path, refused=True)
    _formatter_for_the_installed_hook(lane)
    patch, _paths = _patch(lane, lambda root: _landing(root, retire_schema=True))
    _stage(lane, patch, working_files=False)
    base, tree = gr.git(lane, "rev-parse", "HEAD"), gr.git(lane, "write-tree")
    staged = _state(lane, index_bytes=False)

    _git_commit(lane)

    assert gr.git(lane, "rev-parse", "HEAD^") == base
    assert gr.git(lane, "rev-parse", "HEAD^{tree}") == tree
    # The working files still sit at the refused base.
    assert _state(lane, index_bytes=False)[1] == staged[1]
    assert (lane / _FAMILIES).is_file()
    assert not (lane / _PRODUCT).exists()
    # Staged back, the refused base is refused by the same installed hook.
    gr.git(lane, "add", "-A")
    assert _BASE_GAPS[0] in _git_commit(lane, admitted=False)
    assert gr.git(lane, "rev-parse", "HEAD^{tree}") == tree


def test_git_commits_beside_an_unstaged_fault_and_refuses_the_fault_once_it_is_staged(
    tmp_path: Path,
) -> None:
    lane = _lane(tmp_path)
    _change(lane)
    gr.commit_fixture(lane, f"docs(openspec): declare {_CHANGE}")
    _formatter_for_the_installed_hook(lane)
    patch, _paths = _patch(lane, _product)
    # The commit's own content is whole, in the index and the working files; the fault is unstaged.
    _stage(lane, patch, working_files=True)
    (lane / _STRAY).write_text("not a capability\n", encoding="utf-8")
    tree = gr.git(lane, "write-tree")

    _git_commit(lane)

    assert gr.git(lane, "rev-parse", "HEAD^{tree}") == tree
    assert gr.git(lane, "status", "--porcelain=v1", "--untracked-files=all") == f"?? {_STRAY}"
    gr.git(lane, "add", _STRAY)
    assert _STRAY_GAP in _git_commit(lane, admitted=False)
    assert gr.git(lane, "rev-parse", "HEAD^{tree}") == tree


@pytest.mark.parametrize("refused", [False, True])
def test_the_worktree_target_and_a_merge_continuation_read_the_working_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, refused: bool
) -> None:
    lane = _lane(tmp_path, refused=refused)
    build = _landing if refused else lambda root: (_change(root), _product(root))
    patch, paths = _patch(lane, build)
    projected: list[str] = []
    project = staged_tree.openspec_tree_projection
    monkeypatch.setattr(
        staged_tree,
        "openspec_tree_projection",
        lambda root, tree, **options: (projected.append(tree), project(root, tree, **options))[1],
    )

    report = _preview(lane, patch, paths, target="worktree", change=_CHANGE)
    _stage(lane, patch, working_files=False)
    with selected_change(_CHANGE):
        merge = prewrite.prewrite_guard(
            root=lane,
            paths=[lane / path for path in paths],
            editor_root=lane,
            require_editor_root=True,
            staged=True,
            require_workspace=True,
        )

    gaps = [*_BASE_GAPS, _MISSING] if refused else [_MISSING]
    for answer in (report, merge):
        assert answer["verdict"] == "block"
        assert answer["material_scope"]["required_gaps"] == gaps
        assert answer["reported_gaps"] == []
        assert "observed_tree" not in answer["openspec"]
    assert projected == []


def _breaking_patch(tmp_path: Path) -> tuple[Path, str, list[str]]:
    """A whole base under a committed complete Change; the patch adds an unexpected entry."""
    lane = _lane(tmp_path)
    _change(lane)
    gr.commit_fixture(lane, f"docs(openspec): declare {_CHANGE}")
    patch, paths = _patch(
        lane, lambda root: (root / _STRAY).write_text("not a capability\n", encoding="utf-8")
    )
    return lane, patch, paths


def _passes_and_reports(report: dict) -> None:
    """The working files' answer stands and carries the staged tree's gap as reported."""
    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["reported_gaps"] == [_STRAY_GAP]
    assert report["material_scope"]["state"] == "attributed"
    assert report["material_scope"]["required_gaps"] == []
    assert "observed_tree" not in report["openspec"]
    assert not [text for text in _strings(report) if _PROJECTION in text]


def test_a_staged_tree_that_is_broken_beside_whole_working_files_passes_and_is_reported(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    lane, patch, paths = _breaking_patch(tmp_path)

    _passes_and_reports(_preview(lane, patch, paths))
    _stage(lane, patch, working_files=False)
    _passes_and_reports(_hook(lane, paths))
    # The hook itself admits the commit and says what it reports to the committer.
    said = json.loads(_pre_commit(lane, capfd))
    assert said == {"hook": "pre-commit", "reported_gaps": [_STRAY_GAP], "verdict": "pass"}
    # A note that cannot be written refuses nothing: no stream, then one that refuses a write.
    reader, writer = os.pipe()
    with os.fdopen(reader) as unwritable, os.fdopen(writer, "w"):
        for stream in (None, unwritable):
            with pytest.MonkeyPatch.context() as patched:
                patched.setattr(sys, "stderr", stream)
                assert execute_hook(lane, "pre-commit", (), stdin=StringIO()) == 0
    # With the entry in the working files too, the commit is refused as it is today.
    _working_files_follow(lane, paths)
    refused = _hook(lane, paths)
    assert refused["verdict"] == "block"
    assert refused["required_gaps"] == [_STRAY_GAP]
    assert refused["reported_gaps"] == [_STRAY_GAP]


def test_armed_the_staged_tree_alone_decides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    armed = load_repository_paradigm().model_copy(update={"reporting": ()})
    monkeypatch.setattr(staged_tree, "load_repository_paradigm", lambda: armed)
    lane, patch, paths = _breaking_patch(tmp_path)

    preview = _preview(lane, patch, paths)
    _stage(lane, patch, working_files=False)
    commit = _hook(lane, paths)

    for report in (preview, commit):
        assert report["verdict"] == "block"
        assert report["required_gaps"] == [_STRAY_GAP]
        assert report["reported_gaps"] == []
        assert report["openspec"]["observed_tree"] == report["patch_admission"]["index_tree"]
        assert not [text for text in _strings(report) if _PROJECTION in text]


@pytest.mark.parametrize("fault", [OSError, KeyError])
def test_armed_a_tree_that_cannot_be_observed_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, fault: type[Exception]
) -> None:
    """Any fault of the projection is reported with its type, and refused once armed."""
    lane, patch, paths = _breaking_patch(tmp_path)
    gap = f"openspec_tree_projection_missing:{fault.__name__}"

    def unobservable(*_: object, **__: object) -> None:
        raise fault

    monkeypatch.setattr(staged_tree, "openspec_tree_projection", unobservable)
    reporting = _preview(lane, patch, paths)
    armed = load_repository_paradigm().model_copy(update={"reporting": ()})
    monkeypatch.setattr(staged_tree, "load_repository_paradigm", lambda: armed)
    refused = _preview(lane, patch, paths)

    assert reporting["verdict"] == "pass"
    assert reporting["reported_gaps"] == [gap]
    assert refused["verdict"] == "unknown"
    assert refused["required_gaps"] == [gap]
    assert "observed_tree" not in refused["openspec"]


@pytest.mark.parametrize("fault", [ValueError, KeyError, AttributeError])
def test_reporting_a_fault_of_the_staged_evaluation_leaves_the_working_files_verdict(
    tmp_path: Path, *, fault: type[Exception]
) -> None:
    """A fault below the projection is reported by its type, and the projection is removed."""
    lane, patch, _paths = _breaking_patch(tmp_path)
    _stage(lane, patch, working_files=False)
    working = ({"verdict": "pass", "required_gaps": []}, {}, False)
    projected: list[Path] = []

    def evaluate(files: Path | None) -> tuple[dict[str, object], dict[str, object], bool]:
        if files is None:
            return working
        projected.append(files)
        raise fault

    tree = gr.git(lane, "write-tree")
    scope, official, _invalid = staged_tree.staged_tree_scope(lane, tree, None, evaluate)

    gap = f"openspec_tree_projection_missing:{fault.__name__}"
    assert scope == {"verdict": "pass", "required_gaps": [], "reported_gaps": [gap]}
    assert official == {}
    assert [path.exists() for path in projected] == [False]
